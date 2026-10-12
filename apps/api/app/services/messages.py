"""User-facing messages for fallback paths (SKILL_CANONICAL #35).

Every failure must map to an action the user can take.  Vietnamese text is kept
next to the English text because the canonical skill specifies these exact
messages for the Vietnamese product copy.
"""

INSUFFICIENT_OVERLAP = (
    "Not enough overlap for a stable 3D reconstruction; the shot continued in 2.5D. "
    "(Không đủ dữ liệu để dựng 3D ổn định. Hệ thống đã chuyển sang 2.5D.)"
)

SCENE_NOT_RECONSTRUCTED = (
    "This shot has no reconstructed scene yet; the shot continued in 2.5D. "
    "Run `POST /api/v1/scenes/{scene_id}/reconstruct` first. "
    "(Chưa có scene 3D cho shot này. Hãy reconstruct scene trước.)"
)

SCENE_REJECTED = (
    "The reconstructed scene did not pass the geometry quality gate; the shot continued in 2.5D. "
    "(Scene dựng lại chưa đạt quality gate nên hệ thống dùng 2.5D.)"
)

PATH_REJECTED = (
    "The generated camera path was rejected by path validation; the shot continued in 2.5D. "
    "(Camera path không an toàn nên hệ thống dùng 2.5D.)"
)

__all__ = [
    "INSUFFICIENT_OVERLAP",
    "SCENE_NOT_RECONSTRUCTED",
    "SCENE_REJECTED",
    "PATH_REJECTED",
]
