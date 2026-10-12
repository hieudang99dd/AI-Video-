from __future__ import annotations
import math
from typing import Iterable


def cinematic_ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def normalize_quaternion(q: Iterable[float]) -> tuple[float, float, float, float]:
    q = tuple(float(x) for x in q)
    if len(q) != 4:
        raise ValueError("quaternion must have 4 components")
    n = math.sqrt(sum(x * x for x in q))
    if n == 0:
        raise ValueError("zero quaternion")
    return tuple(x / n for x in q)  # type: ignore[return-value]


def slerp(q0: Iterable[float], q1: Iterable[float], t: float) -> tuple[float, float, float, float]:
    a = normalize_quaternion(q0)
    b = normalize_quaternion(q1)
    t = max(0.0, min(1.0, float(t)))
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b = tuple(-x for x in b)
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        out = tuple(x + t * (y - x) for x, y in zip(a, b))
        return normalize_quaternion(out)
    theta_0 = math.acos(dot)
    sin_0 = math.sin(theta_0)
    s0 = math.sin((1 - t) * theta_0) / sin_0
    s1 = math.sin(t * theta_0) / sin_0
    return tuple(s0 * x + s1 * y for x, y in zip(a, b))  # type: ignore[return-value]
