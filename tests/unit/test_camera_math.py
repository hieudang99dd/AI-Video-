import math
from packages.camera_math import cinematic_ease, normalize_quaternion, slerp


def test_ease_endpoints():
    assert cinematic_ease(0) == 0
    assert cinematic_ease(1) == 1


def test_normalize():
    q = normalize_quaternion((0, 0, 0, 2))
    assert q == (0, 0, 0, 1)


def test_slerp_endpoints():
    a = (0, 0, 0, 1)
    b = (0, 1, 0, 0)
    assert all(abs(x-y)<1e-7 for x,y in zip(slerp(a,b,0), a))
    out = slerp(a,b,1)
    assert abs(sum(x*x for x in out)-1) < 1e-7

from packages.camera_math.path import catmull_rom, look_at

def test_catmull_rom():
    p0 = (0, 0, 0)
    p1 = (1, 1, 1)
    p2 = (2, 0, 2)
    p3 = (3, 1, 3)
    # At t=0 it should be exactly p1
    res0 = catmull_rom(p0, p1, p2, p3, 0.0)
    assert all(abs(x-y)<1e-7 for x,y in zip(res0, p1))
    
    # At t=1 it should be exactly p2
    res1 = catmull_rom(p0, p1, p2, p3, 1.0)
    assert all(abs(x-y)<1e-7 for x,y in zip(res1, p2))

def test_look_at():
    eye = (0, 0, 0)
    target = (0, 0, 1) # Looking down Z axis
    q = look_at(eye, target)
    # Output quaternion should be valid and normalized
    assert len(q) == 4
    assert abs(sum(x*x for x in q) - 1.0) < 1e-6
