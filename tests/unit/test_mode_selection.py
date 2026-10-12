from app.services.image_analysis import select_mode


def test_single_image_uses_safe_fallback():
    assert select_mode(1, False) == "2.5d_lite"


def test_geometry_only_when_capable():
    assert select_mode(5, True) == "geometry"
    assert select_mode(5, False) == "transition"
