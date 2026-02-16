from __future__ import annotations

from array import array
from math import sqrt


def to_f32_blob(vec: list[float]) -> bytes:
    arr = array("f", (float(v) for v in vec))
    return arr.tobytes()


def from_f32_blob(blob: bytes) -> list[float]:
    arr = array("f")
    arr.frombytes(blob)
    return arr.tolist()


def l2_normalize(vec: list[float]) -> list[float]:
    if not vec:
        raise ValueError("vector is empty")
    norm = sqrt(sum(float(v) * float(v) for v in vec))
    if norm <= 0:
        raise ValueError("vector norm is zero")
    return [float(v) / norm for v in vec]


def dot(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("dimension mismatch")
    total = 0.0
    for av, bv in zip(a, b, strict=True):
        total += float(av) * float(bv)
    return total
