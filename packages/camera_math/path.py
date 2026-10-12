from __future__ import annotations
import math
from typing import Sequence

def lerp(p0: Sequence[float], p1: Sequence[float], t: float) -> tuple[float, ...]:
    t = max(0.0, min(1.0, float(t)))
    return tuple(a + t * (b - a) for a, b in zip(p0, p1))

def catmull_rom(p0: Sequence[float], p1: Sequence[float], p2: Sequence[float], p3: Sequence[float], t: float, tension: float = 0.5) -> tuple[float, ...]:
    """Catmull-Rom spline interpolation. tension 0.5 is standard, 0 is linear-like, 1 is tight."""
    t = max(0.0, min(1.0, float(t)))
    t2 = t * t
    t3 = t2 * t
    
    alpha = 1.0 - tension
    
    res = []
    for i in range(len(p0)):
        # standard catmull rom calculation
        v0 = (p2[i] - p0[i]) * alpha
        v1 = (p3[i] - p1[i]) * alpha
        
        a = 2 * p1[i] - 2 * p2[i] + v0 + v1
        b = -3 * p1[i] + 3 * p2[i] - 2 * v0 - v1
        c = v0
        d = p1[i]
        
        val = a * t3 + b * t2 + c * t + d
        res.append(val)
        
    return tuple(res)

def look_at(eye: Sequence[float], target: Sequence[float], up: Sequence[float] = (0.0, 1.0, 0.0)) -> tuple[float, float, float, float]:
    """Computes the rotation quaternion to look from 'eye' to 'target'."""
    # forward = normalize(target - eye)
    fx = target[0] - eye[0]
    fy = target[1] - eye[1]
    fz = target[2] - eye[2]
    fn = math.sqrt(fx*fx + fy*fy + fz*fz)
    if fn < 1e-6:
        return (0.0, 0.0, 0.0, 1.0) # Identity if eye == target
    fx, fy, fz = fx/fn, fy/fn, fz/fn
    
    # right = normalize(cross(up, forward))
    rx = up[1]*fz - up[2]*fy
    ry = up[2]*fx - up[0]*fz
    rz = up[0]*fy - up[1]*fx
    rn = math.sqrt(rx*rx + ry*ry + rz*rz)
    if rn < 1e-6:
        # Collinear up and forward, fallback right vector
        rx, ry, rz = 1.0, 0.0, 0.0
    else:
        rx, ry, rz = rx/rn, ry/rn, rz/rn
        
    # true_up = cross(forward, right)
    ux = fy*rz - fz*ry
    uy = fz*rx - fx*rz
    uz = fx*ry - fy*rx
    
    # Convert rotation matrix to quaternion
    m00, m01, m02 = rx, ux, fx
    m10, m11, m12 = ry, uy, fy
    m20, m21, m22 = rz, uz, fz
    
    trace = m00 + m11 + m22
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        qw = 0.25 / s
        qx = (m21 - m12) * s
        qy = (m02 - m20) * s
        qz = (m10 - m01) * s
    else:
        if m00 > m11 and m00 > m22:
            s = 2.0 * math.sqrt(1.0 + m00 - m11 - m22)
            qw = (m21 - m12) / s
            qx = 0.25 * s
            qy = (m01 + m10) / s
            qz = (m02 + m20) / s
        elif m11 > m22:
            s = 2.0 * math.sqrt(1.0 + m11 - m00 - m22)
            qw = (m02 - m20) / s
            qx = (m01 + m10) / s
            qy = 0.25 * s
            qz = (m12 + m21) / s
        else:
            s = 2.0 * math.sqrt(1.0 + m22 - m00 - m11)
            qw = (m10 - m01) / s
            qx = (m02 + m20) / s
            qy = (m12 + m21) / s
            qz = 0.25 * s
            
    # return normalized quaternion
    from .math import normalize_quaternion
    return normalize_quaternion((qw, qx, qy, qz))
