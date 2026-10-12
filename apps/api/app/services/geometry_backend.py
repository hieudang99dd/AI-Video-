from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.services.capabilities import get_capabilities

from packages.colmap.repository import DEFAULT_SCENE_CONFIG, ColmapRepository, ColmapSceneData
from packages.geometry.camera_path import CameraPathDocument
from packages.geometry.keyframes import KeyframeSelection, KeyframeSelector
from packages.geometry.nerfstudio import build_colmap_dataset

logger = logging.getLogger(__name__)


class GeometryError(RuntimeError):
    """Base class for every geometry-pipeline failure (always user-actionable)."""


class GeometryUnavailable(GeometryError):
    """The environment cannot run the requested geometry step (missing COLMAP/3DGS/GPU)."""


class GeometryQualityRejected(GeometryError):
    """Reconstruction ran but did not pass the Phase 0 quality gate."""

    def __init__(self, reasons: list[str], metadata: dict | None = None) -> None:
        self.reasons = list(reasons)
        self.metadata = dict(metadata or {})
        super().__init__("; ".join(self.reasons) or "scene quality gate failed")


@dataclass(frozen=True)
class GeometrySceneResult:
    scene_uri: str
    registered_image_ratio: float
    camera_count: int
    backend: str
    backend_version: str
    metadata: dict


@dataclass(frozen=True)
class GeometryRenderResult:
    frames: tuple[Path, ...]
    output_dir: Path
    camera_path_file: Path
    training_config: Path | None
    metadata: dict = field(default_factory=dict)


class GeometryBackend(Protocol):
    def reconstruct(
        self,
        image_paths: list[Path],
        workdir: Path,
        expected_image_count: int | None = None,
    ) -> GeometrySceneResult: ...

    def render_camera_path(
        self,
        scene_uri: str,
        camera_path: CameraPathDocument | dict,
        output_dir: Path,
    ) -> GeometryRenderResult: ...


class CapabilityGatedGeometryBackend:
    """Canonical Phase-0 seam for COLMAP + 3DGS (Nerfstudio ``splatfacto``).

    Every method is capability-gated and raises :class:`GeometryUnavailable` with
    an actionable message instead of faking results.  Reconstruction goes through
    :class:`packages.colmap.repository.ColmapRepository` (stdlib + sqlite3 only) and
    the scene must pass the quality gate before Geometry Mode is advertised.
    Novel views are rendered by ``ns-render camera-path``, which requires CUDA.
    """

    def __init__(
        self,
        colmap_path: str | None = None,
        ns_train_path: str | None = None,
        ns_render_path: str | None = None,
        config: dict | None = None,
    ) -> None:
        self.colmap_path = colmap_path or settings.colmap_path
        self.ns_train_path = ns_train_path or settings.ns_train_path
        self.ns_render_path = ns_render_path or settings.ns_render_path
        self.config = {
            "min_registered_ratio": settings.min_registered_ratio,
            "geometry_confidence_threshold": settings.geometry_confidence_threshold,
            "max_mean_reprojection_error": settings.max_mean_reprojection_error_px,
            **DEFAULT_SCENE_CONFIG,
            **(config or {}),
        }
        self.up_axis = settings.colmap_up_axis
        self.matcher = settings.colmap_feature_matcher

    # ------------------------------------------------------------------ #
    # capability gates
    # ------------------------------------------------------------------ #
    def require_reconstruct(self) -> None:
        caps = get_capabilities()
        if not caps["geometry"]["reconstruct_available"]:
            raise GeometryUnavailable(
                caps["geometry"]["reconstruct_reason"] or "COLMAP is not available in this environment."
            )

    def require_render(self) -> None:
        caps = get_capabilities()
        if not caps["geometry"]["render_available"]:
            raise GeometryUnavailable(
                caps["geometry"]["render_reason"]
                or "3DGS rendering requires Nerfstudio (ns-render) on a CUDA GPU."
            )

    def require_geometry(self) -> None:
        caps = get_capabilities()
        if not caps["geometry"]["available"]:
            raise GeometryUnavailable(caps["geometry"]["reason"] or "Geometry Mode is unavailable.")

    # ------------------------------------------------------------------ #
    # command execution
    # ------------------------------------------------------------------ #
    def _run_command(self, args: list[str]) -> subprocess.CompletedProcess:
        logger.info("geometry command: %s", " ".join(args))
        try:
            return subprocess.run(args, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise GeometryUnavailable(f"command not found: {args[0]}") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            logger.error("geometry command failed: %s | %s", " ".join(args), detail)
            raise GeometryError(f"{args[0]} failed: {detail[-2000:]}") from exc

    def _colmap(self) -> str:
        return shutil.which(self.colmap_path) or shutil.which("colmap") or self.colmap_path

    # ------------------------------------------------------------------ #
    # reconstruction
    # ------------------------------------------------------------------ #
    def reconstruct(
        self,
        image_paths: list[Path],
        workdir: Path,
        expected_image_count: int | None = None,
    ) -> GeometrySceneResult:
        """Run COLMAP SfM and return the sparse model + statistics.

        Raises :class:`GeometryQualityRejected` when the model fails the Phase 0
        gate so callers fall back to 2.5D/transition instead of rendering an
        unreliable scene.
        """
        self.require_reconstruct()
        image_paths = [Path(p) for p in image_paths]
        if len(image_paths) < settings.min_images_geometry:
            raise GeometryError(
                f"Geometry Mode needs at least {settings.min_images_geometry} images; "
                f"got {len(image_paths)} — use 2.5D/transition instead."
            )

        workdir = Path(workdir)
        images_dir = workdir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for source in image_paths:
            target = images_dir / source.name
            if not target.exists():
                shutil.copy2(source, target)

        database = workdir / "database.db"
        sparse_dir = workdir / "sparse"
        sparse_dir.mkdir(parents=True, exist_ok=True)
        colmap = self._colmap()
        use_gpu = "1" if settings.colmap_sift_use_gpu else "0"

        self._run_command(
            [
                colmap, "feature_extractor",
                "--database_path", str(database),
                "--image_path", str(images_dir),
                "--ImageReader.camera_model", settings.colmap_camera_model,
                "--SiftExtraction.use_gpu", use_gpu,
            ]
        )
        self._run_command(self._matcher_command(colmap, database, use_gpu))
        self._run_command(
            [
                colmap, "mapper",
                "--database_path", str(database),
                "--image_path", str(images_dir),
                "--output_path", str(sparse_dir),
            ]
        )

        model_dir = self._best_model_dir(sparse_dir)
        self._run_command(
            [
                colmap, "model_converter",
                "--input_path", str(model_dir),
                "--output_path", str(model_dir),
                "--output_type", "TXT",
            ]
        )

        scene = self.load_scene(model_dir, expected_image_count or len(image_paths))
        passed, reasons = scene.quality_gate(self._quality_config())
        metadata = scene.to_dict()
        metadata["workdir"] = str(workdir)
        if not passed:
            raise GeometryQualityRejected(reasons, metadata=metadata)

        return GeometrySceneResult(
            scene_uri=str(model_dir),
            registered_image_ratio=scene.registered_ratio,
            camera_count=scene.registered_image_count,
            backend="colmap_cli",
            backend_version=self._colmap_version(),
            metadata=metadata,
        )

    # ------------------------------------------------------------------ #
    # scene access / keyframes
    # ------------------------------------------------------------------ #
    def load_scene(self, scene_uri: str | Path, expected_image_count: int | None = None) -> ColmapSceneData:
        return ColmapRepository(
            Path(scene_uri),
            expected_image_count=expected_image_count,
            up_axis=self.up_axis,
        ).load()

    def select_keyframes(self, scene_uri: str | Path, max_keyframes: int | None = None) -> KeyframeSelection:
        """Pick 2-3 keyframes from the registered cameras (never invented)."""
        scene = self.load_scene(scene_uri)
        return KeyframeSelector({"max_keyframes": max_keyframes or settings.max_keyframes}).select(
            scene.registered_views()
        )

    def build_camera_path(
        self,
        scene_uri: str | Path,
        duration_sec: float,
        fps: int,
        width: int,
        height: int,
        easing: str = "cinematic",
        path_type: str = "catmull_rom",
        max_keyframes: int | None = None,
    ) -> CameraPathDocument:
        """Keyframes -> validated camera path document for one shot."""
        selection = self.select_keyframes(scene_uri, max_keyframes=max_keyframes)
        if selection.reason is not None:
            logger.warning("keyframe selection degraded: %s", selection.reason)
        document = selection.to_camera_path(
            duration_sec=duration_sec,
            fps=fps,
            width=width,
            height=height,
            easing=easing,
            path_type=path_type,
        )
        document.validate()
        return document

    # ------------------------------------------------------------------ #
    # 3DGS novel-view rendering
    # ------------------------------------------------------------------ #
    def render_camera_path(
        self,
        scene_uri: str,
        camera_path: CameraPathDocument | dict,
        output_dir: Path,
    ) -> GeometryRenderResult:
        """Train (if needed) then render the camera path to PNG frames.

        Requires CUDA + Nerfstudio: raises :class:`GeometryUnavailable` otherwise,
        so the worker can fall back to the safe CPU renderer with a visible reason.
        """
        self.require_render()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        scene_dir = Path(scene_uri)                 # .../sparse/<model>
        workdir = scene_dir.parent.parent           # .../ (images, sparse, database.db)
        images_dir = workdir / "images"
        image_paths = (
            {p.name: p for p in sorted(images_dir.iterdir()) if p.is_file()}
            if images_dir.is_dir()
            else {}
        )
        if not image_paths:
            raise GeometryError(
                f"no source images next to {scene_uri}; the 3DGS dataset cannot be assembled"
            )
        dataset_dir = build_colmap_dataset(workdir / "ns_dataset", image_paths, scene_dir)

        document = (
            camera_path
            if isinstance(camera_path, CameraPathDocument)
            else CameraPathDocument.from_dict(camera_path)
        )
        payload = document.to_nerfstudio_camera_path()
        path_json = output_dir / "camera_path.json"
        path_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        train_dir = workdir / "3dgs_training"
        config_path = _find_training_config(train_dir)
        if config_path is None:
            ns_train = shutil.which(self.ns_train_path) or self.ns_train_path
            logger.info("training 3DGS scene (splatfacto) for %s", dataset_dir)
            self._run_command(
                [
                    ns_train, "splatfacto",
                    "--data", str(dataset_dir),
                    "--output-dir", str(train_dir),
                    "--max-num-iterations", str(settings.ns_train_iterations),
                    "--vis", "tensorboard",
                    "--experiment-name", "scene",
                    "colmap",
                    "--colmap-path", "sparse/0",
                ]
            )
            config_path = _find_training_config(train_dir)
            if config_path is None:
                raise GeometryError(
                    f"ns-train finished but no config.yml was found under {train_dir}"
                )

        frames_dir = output_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        ns_render = shutil.which(self.ns_render_path) or self.ns_render_path
        self._run_command(
            [
                ns_render, "camera-path",
                "--load-config", str(config_path),
                "--camera-path-filename", str(path_json),
                "--output-path", str(frames_dir / "frame.png"),
                "--rendered-output-names", "rgb",
            ]
        )
        frames = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() == ".png")
        if not frames:
            raise GeometryError(f"ns-render produced no frames in {frames_dir}")

        return GeometryRenderResult(
            frames=tuple(frames),
            output_dir=output_dir,
            camera_path_file=path_json,
            training_config=config_path,
            metadata={
                "backend": "nerfstudio_splatfacto",
                "frame_count": len(frames),
                "duration_sec": document.duration_sec,
                "fps": document.fps,
                "resolution": [document.width, document.height],
                "camera_path_schema_version": document.schema_version,
                "easing": document.easing,
                "path_type": document.path_type,
                "dataset_dir": str(dataset_dir),
            },
        )

    # ------------------------------------------------------------------ #
    # validation proxy
    # ------------------------------------------------------------------ #
    def scene_proxy(self, scene_uri: str | Path, max_points: int = 20000):
        """Point-cloud proxy (canonical frame) for camera path validation."""
        from packages.path_validation import PointCloudProxy

        scene = self.load_scene(scene_uri)
        return PointCloudProxy.from_sampled_cloud(
            scene.canonical_points(limit=max_points), scene.camera_centers()
        )


def _find_training_config(train_dir: Path) -> Path | None:
    """Locate the ``config.yml`` written by ``ns-train`` (Nerfstudio layout)."""
    if not train_dir.exists():
        return None
    configs = sorted(train_dir.glob("**/config.yml"))
    return configs[-1] if configs else None


_geometry_backend: CapabilityGatedGeometryBackend | None = None


def get_geometry_backend() -> CapabilityGatedGeometryBackend:
    """Process-wide capability-gated backend (Phase 0 single execution target)."""
    global _geometry_backend
    if _geometry_backend is None:
        _geometry_backend = CapabilityGatedGeometryBackend()
    return _geometry_backend


def reset_geometry_backend() -> None:
    """Testing hook: drop the cached backend instance."""
    global _geometry_backend
    _geometry_backend = None


__all__ = [
    "GeometryError",
    "GeometryUnavailable",
    "GeometryQualityRejected",
    "GeometrySceneResult",
    "GeometryRenderResult",
    "GeometryBackend",
    "CapabilityGatedGeometryBackend",
    "get_geometry_backend",
    "reset_geometry_backend",
]
