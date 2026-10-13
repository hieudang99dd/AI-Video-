from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from PIL import Image, ImageOps
import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}

SEMANTIC_CATEGORIES = (
    "overview",
    "road",
    "intersection",
    "bridge",
    "culvert_drainage",
    "slope_retaining_wall",
    "cross_section_detail",
    "surrounding_context",
)


def compute_dhash(img: Image.Image, hash_size: int = 8) -> str:
    """Compute a 64-bit difference perceptual hash (dHash) as a 16-char hex string."""
    gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray, dtype=np.int16)
    diff = pixels[:, 1:] > pixels[:, :-1]
    bits = diff.flatten()
    val = 0
    for bit in bits:
        val = (val << 1) | int(bool(bit))
    return f"{val:016x}"


def hamming_distance(hash_a: str | None, hash_b: str | None) -> int:
    """Return bit Hamming distance between two 16-char hex dHashes."""
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 64
    try:
        xor_val = int(hash_a, 16) ^ int(hash_b, 16)
        return bin(xor_val).count("1")
    except ValueError:
        return 64


def classify_infrastructure_image(path: Path, arr: np.ndarray) -> tuple[str, float]:
    """Classify an infrastructure image into one of the 8 Civil 3D / InfraWorks categories.

    Combines filename heuristics (Vietnamese & English CAD/BIM naming conventions)
    with visual feature cues (edge density, sky/vegetation/asphalt color ratios, aspect ratio).
    Always allows user override on the UI/API.
    """
    name = path.stem.lower()
    keyword_map: list[tuple[str, tuple[str, ...]]] = [
        ("overview", ("overview", "tong_quan", "tongthe", "master", "aerial", "toan_canh", "flyover")),
        ("bridge", ("bridge", "cau_vuot", "cau", "viaduct", "pier", "abutment", "girder", "overpass")),
        ("intersection", ("intersection", "nut_giao", "nutgiao", "roundabout", "nga_tu", "interchange", "ic_", "_ic")),
        ("culvert_drainage", ("culvert", "drain", "cong", "thoat_nuoc", "manhole", "ditch", "channel", "ranh")),
        ("slope_retaining_wall", ("slope", "taluy", "retaining", "tuong_chan", "embankment", "gabion", "ke")),
        ("cross_section_detail", ("section", "mat_cat", "matcat", "profile", "trac_doc", "trac_ngang", "cad", "detail")),
        ("surrounding_context", ("context", "hien_trang", "terrain", "dia_hinh", "landscape", "environment")),
        ("road", ("road", "highway", "duong", "tuyen", "lane", "asphalt", "corridor", "km")),
    ]
    for category, keywords in keyword_map:
        if any(k in name for k in keywords):
            return category, 0.88

    # Visual heuristic fallback based on color/edge statistics
    h, w, _ = arr.shape
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)

    # Check if CAD drawing / cross-section (very dark or very white background with sharp thin lines)
    mean_lum = float(arr.mean())
    sat = float(( np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b) ).mean())
    if (mean_lum < 35 or mean_lum > 225) and sat < 18.0:
        return "cross_section_detail", 0.72

    # Sky ratio in upper third, green vegetation ratio, gray asphalt/concrete ratio
    upper_b_ratio = float((b[: max(1, h // 3), :] > r[: max(1, h // 3), :] + 15).mean())
    green_ratio = float((g > np.maximum(r, b) + 10).mean())
    gray_mask = (np.abs(r - g) < 15) & (np.abs(g - b) < 15) & (r > 50) & (r < 190)
    gray_ratio = float(gray_mask.mean())

    if upper_b_ratio > 0.35 and green_ratio > 0.22:
        return "overview", 0.65
    if gray_ratio > 0.42 and upper_b_ratio > 0.15:
        return "bridge", 0.62
    if green_ratio > 0.45:
        return "surrounding_context", 0.64
    return "road", 0.60


def estimate_pairwise_overlap(path_a: Path, path_b: Path) -> float:
    """Estimate visual overlap score [0.0, 1.0] between two images using ORB + RANSAC homography."""
    if cv2 is not None:
        try:
            with Image.open(path_a) as ia, Image.open(path_b) as ib:
                ga = np.asarray(ImageOps.exif_transpose(ia).convert("L").resize((640, 360)))
                gb = np.asarray(ImageOps.exif_transpose(ib).convert("L").resize((640, 360)))
            orb = cv2.ORB_create(nfeatures=500)
            kp1, des1 = orb.detectAndCompute(ga, None)
            kp2, des2 = orb.detectAndCompute(gb, None)
            if des1 is not None and des2 is not None and len(kp1) >= 12 and len(kp2) >= 12:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                matches = bf.knnMatch(des1, des2, k=2)
                good = []
                for pair in matches:
                    if len(pair) == 2 and pair[0].distance < 0.78 * pair[1].distance:
                        good.append(pair[0])
                if len(good) >= 8:
                    pts1 = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                    pts2 = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                    _, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
                    inliers = int(mask.ravel().sum()) if mask is not None else len(good)
                    denom = max(20, min(len(kp1), len(kp2)) // 2)
                    return round(float(min(1.0, inliers / denom)), 4)
        except Exception:
            pass

    # Fallback: normalized histogram + thumbnail structural correlation
    try:
        with Image.open(path_a) as ia, Image.open(path_b) as ib:
            ta = np.asarray(ia.convert("L").resize((64, 64)), dtype=np.float32)
            tb = np.asarray(ib.convert("L").resize((64, 64)), dtype=np.float32)
        ta_norm = ta - ta.mean()
        tb_norm = tb - tb.mean()
        denom = float(np.linalg.norm(ta_norm) * np.linalg.norm(tb_norm))
        if denom <= 1e-6:
            return 0.5
        corr = max(0.0, float((ta_norm * tb_norm).sum() / denom))
        return round(corr, 4)
    except Exception:
        return 0.0


def analyze_image(path: Path) -> dict:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError("unsupported image format")

    file_size_bytes = path.stat().st_size if path.exists() else 0

    with Image.open(path) as raw_img:
        exif_info: dict[str, Any] = {}
        try:
            raw_exif = raw_img.getexif()
            if raw_exif:
                for k, v in list(raw_exif.items())[:15]:
                    if isinstance(v, (int, float, str)):
                        exif_info[str(k)] = v
        except Exception:
            pass
        img = ImageOps.exif_transpose(raw_img).convert("RGB")
        width, height = img.size
        dhash = compute_dhash(img)
        arr = np.asarray(img)

    gray = arr.mean(axis=2).astype(np.float32)
    exposure = float(gray.mean() / 255.0)

    if cv2 is not None:
        sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    else:
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        sharpness = float((dx.var() + dy.var()) / 2)

    aspect_ratio = round(width / max(1, height), 4)
    semantic_category, semantic_confidence = classify_infrastructure_image(path, arr)

    warnings: list[str] = []
    if width < 640 or height < 360:
        warnings.append("low_resolution")
    if sharpness < 18.0:
        warnings.append("blurry")
    if exposure < 0.12:
        warnings.append("underexposed")
    elif exposure > 0.90:
        warnings.append("overexposed")
    if aspect_ratio < 0.5 or aspect_ratio > 3.2:
        warnings.append("unusual_aspect_ratio")

    return {
        "width": width,
        "height": height,
        "file_size_bytes": file_size_bytes,
        "aspect_ratio": aspect_ratio,
        "exposure_score": round(exposure, 4),
        "sharpness_score": round(sharpness, 4),
        "perceptual_hash": dhash,
        "semantic_category": semantic_category,
        "semantic_confidence": round(semantic_confidence, 3),
        "quality_warnings": warnings,
        "exif": exif_info,
    }


def detect_duplicates_and_overlaps(asset_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate ordered asset records with duplicate flags and adjacent overlap scores.

    Each item in ``asset_records`` should contain: ``id``, ``sha256``, ``perceptual_hash``,
    ``path`` (Path), and ``quality_warnings`` (list).
    """
    seen_hashes: list[tuple[str, str, str | None]] = []
    n = len(asset_records)
    for idx, rec in enumerate(asset_records):
        is_dup = False
        dup_of = None
        for prev_id, prev_sha, prev_dhash in seen_hashes:
            if rec.get("sha256") and rec.get("sha256") == prev_sha:
                is_dup = True
                dup_of = prev_id
                break
            if hamming_distance(rec.get("perceptual_hash"), prev_dhash) <= 4:
                is_dup = True
                dup_of = prev_id
                break
        rec["is_duplicate"] = is_dup
        rec["duplicate_of"] = dup_of
        warnings = list(rec.get("quality_warnings") or [])
        if is_dup and "duplicate_or_near_duplicate" not in warnings:
            warnings.append("duplicate_or_near_duplicate")

        if idx > 0 and rec.get("path") and asset_records[idx - 1].get("path"):
            ov = estimate_pairwise_overlap(asset_records[idx - 1]["path"], rec["path"])
            rec["overlap_score"] = ov
            if ov < 0.15 and "low_overlap_with_previous" not in warnings:
                warnings.append("low_overlap_with_previous")
        else:
            rec["overlap_score"] = 1.0 if idx == 0 else None

        rec["quality_warnings"] = warnings
        seen_hashes.append((rec["id"], rec.get("sha256", ""), rec.get("perceptual_hash")))
    return asset_records


def select_mode(asset_count: int, geometry_available: bool) -> str:
    if asset_count <= 1:
        return "2.5d_lite"
    if asset_count >= 3 and geometry_available:
        return "geometry"
    if asset_count >= 2:
        return "transition"
    return "2.5d_lite"


def build_project_manifest(
    project: Any,
    assets: list[Any],
    scenes: list[Any],
    shots: list[Any],
    render_jobs: list[Any],
    ai_jobs: list[Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical Project Manifest JSON (Section 4.9 of Master Implementation Prompt)."""
    completed_renders = [j for j in render_jobs if j.status == "completed" and j.output_uri]
    latest_render = completed_renders[-1] if completed_renders else None

    primary_scene = scenes[0] if scenes else None
    reconstruction_block = {
        "status": primary_scene.reconstruction_status if primary_scene else "not_started",
        "method": (primary_scene.diagnostics or {}).get("backend", "colmap_or_2_5d_fallback") if primary_scene else "none",
        "registered_images": (primary_scene.diagnostics or {}).get("camera_count", 0) if primary_scene else 0,
        "point_count": (primary_scene.diagnostics or {}).get("scene", {}).get("point_count", 0) if primary_scene else 0,
        "confidence": round(float(primary_scene.confidence), 4) if primary_scene else 0.0,
        "scale_status": primary_scene.scale_status if primary_scene else "uncalibrated",
    }

    scene_rep_block = {
        "coordinate_system": primary_scene.coordinate_system if primary_scene else "uncalibrated_local",
        "unit": primary_scene.unit if primary_scene else "relative_units",
        "point_cloud_path": (primary_scene.point_cloud_uri or primary_scene.representation_uri) if primary_scene else None,
        "mesh_path": primary_scene.mesh_uri if primary_scene else None,
        "anchor_point": primary_scene.anchor_point if primary_scene else [0.0, 0.0, 0.0],
        "allowed_camera_bounds": primary_scene.allowed_camera_bounds if primary_scene else {},
        "engineering_disclaimer": (
            "Không tự tuyên bố dựng lại chính xác BIM từ ảnh tĩnh. "
            "Tỷ lệ hình học là uncalibrated_local (relative_units) trừ khi có mốc tọa độ thực tế được xác thực."
        ),
    }

    return {
        "project_id": project.id,
        "project_name": project.name,
        "created_at": project.created_at.isoformat() if getattr(project, "created_at", None) else datetime.now(timezone.utc).isoformat(),
        "source_type": getattr(project, "source_type", "civil3d_infraworks") or "civil3d_infraworks",
        "pipeline_state": getattr(project, "pipeline_state", "CREATED") or "CREATED",
        "images": [
            {
                "id": a.id,
                "filename": a.filename,
                "width": a.width,
                "height": a.height,
                "aspect_ratio": getattr(a, "aspect_ratio", None),
                "sequence_index": getattr(a, "sequence_index", idx),
                "scene_group": getattr(a, "scene_group", "default"),
                "semantic_category": getattr(a, "semantic_category", "road"),
                "sharpness_score": a.sharpness_score,
                "exposure_score": a.exposure_score,
                "overlap_score": getattr(a, "overlap_score", None),
                "is_duplicate": getattr(a, "is_duplicate", False),
                "quality_warnings": getattr(a, "quality_warnings", []),
            }
            for idx, a in enumerate(assets)
        ],
        "reconstruction": reconstruction_block,
        "scene_representation": scene_rep_block,
        "shots": [
            {
                "shot_id": s.id,
                "name": s.name,
                "preset": getattr(s, "preset", s.template_id or "establishing_shot"),
                "source_mode": getattr(s, "source_mode", "C_SINGLE_IMAGE_2_5D"),
                "camera_mode": s.camera_mode,
                "duration_sec": s.duration_sec,
                "fps": s.fps,
                "fov_deg": getattr(s, "fov_deg", 50.0),
                "speed": getattr(s, "speed", 1.0),
                "shake_level": getattr(s, "shake_level", 0.0),
                "start_pose": getattr(s, "start_pose", {}),
                "end_pose": getattr(s, "end_pose", {}),
                "trajectory": getattr(s, "trajectory", []),
                "confidence": getattr(s, "confidence", 1.0),
                "ai_enhanced": bool(getattr(s, "ai_enabled", False)),
                "ai_status": getattr(s, "ai_status", "disabled"),
            }
            for s in shots
        ],
        "renders": [
            {
                "job_id": j.id,
                "type": j.type,
                "status": j.status,
                "state_machine_step": getattr(j, "state_machine_step", j.status.upper()),
                "mode": j.mode,
                "resolution": [j.width, j.height],
                "fps": j.fps,
                "output_uri": j.output_uri,
                "provenance": j.provenance,
            }
            for j in render_jobs
        ],
        "ai_jobs": [
            {
                "id": aj.id,
                "shot_id": aj.shot_id,
                "module_name": aj.module_name,
                "model_id": aj.model_id,
                "status": aj.status,
                "qc_passed": aj.qc_passed,
                "user_decision": aj.user_decision,
                "disclaimer": aj.disclaimer,
            }
            for aj in (ai_jobs or [])
        ],
        "final_output": {
            "mp4_path": latest_render.output_uri if latest_render else None,
            "resolution": f"{latest_render.width}x{latest_render.height}" if latest_render else "1920x1080",
            "fps": latest_render.fps if latest_render else 30,
            "codec": getattr(latest_render, "codec", "h264") if latest_render else "h264",
        },
    }

