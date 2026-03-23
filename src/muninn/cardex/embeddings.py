from __future__ import annotations

import hashlib
import os
import re
from array import array
from math import sqrt

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_DEFAULT_MODEL = "cardex-hash-v1"
_DEFAULT_DIM = 96
_MIN_DIM = 8
_MAX_DIM = 4096

# Lightweight alias map to improve semantic recall for common retrieval phrasing.
_TOKEN_ALIASES: dict[str, str] = {
    "acquire": "growth",
    "acquired": "growth",
    "acquiring": "growth",
    "acquisition": "growth",
    "expansion": "growth",
    "scale": "growth",
    "scaling": "growth",
    "velocity": "speed",
    "fast": "speed",
    "faster": "speed",
    "rapid": "speed",
    "model": "strategy",
    "framework": "strategy",
    "playbook": "strategy",
    "plan": "strategy",
    "clinic": "healthcare",
    "clinical": "healthcare",
    "patient": "healthcare",
    "patients": "healthcare",
    "physician": "doctor",
    "physicians": "doctor",
    "grocery": "retail",
    "groceries": "retail",
    "bananas": "retail",
    "eggs": "retail",
}


def default_card_embedding_model() -> str:
    raw = os.getenv("MUNINN_CARDEX_EMBED_MODEL", "").strip()
    return raw or _DEFAULT_MODEL


def default_card_embedding_dim() -> int:
    raw = os.getenv("MUNINN_CARDEX_EMBED_DIM", "").strip()
    if not raw:
        return _DEFAULT_DIM
    try:
        dim = int(raw)
    except ValueError:
        return _DEFAULT_DIM
    return max(_MIN_DIM, min(_MAX_DIM, dim))


def pack_f32(vector: list[float]) -> bytes:
    return array("f", [float(value) for value in vector]).tobytes()


def unpack_f32(blob: bytes) -> list[float]:
    vec = array("f")
    vec.frombytes(blob)
    return vec.tolist()


def cosine_sim(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b, strict=True):
        av = float(a)
        bv = float(b)
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (sqrt(norm_a) * sqrt(norm_b))


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _canonical_token(token: str) -> str:
    lowered = token.strip().lower()
    if not lowered:
        return ""
    return _TOKEN_ALIASES.get(lowered, lowered)


def _accumulate(vector: list[float], token: str, weight: float) -> None:
    if not token:
        return
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    idx = int.from_bytes(digest[0:4], "little") % len(vector)
    sign = 1.0 if (digest[4] % 2 == 0) else -1.0
    vector[idx] += sign * float(weight)


def embed_text(text: str, dim: int | None = None) -> list[float]:
    dims = int(dim if dim is not None else default_card_embedding_dim())
    dims = max(_MIN_DIM, min(_MAX_DIM, dims))
    canonical = [_canonical_token(token) for token in _tokenize(text)]
    canonical = [token for token in canonical if token]
    if not canonical:
        canonical = ["_empty_"]

    vector = [0.0] * dims
    for token in canonical:
        _accumulate(vector, token, weight=1.0)
    for left, right in zip(canonical, canonical[1:], strict=False):
        _accumulate(vector, f"{left}:{right}", weight=0.35)

    norm = sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return [0.0] * dims
    return [value / norm for value in vector]


__all__ = [
    "cosine_sim",
    "default_card_embedding_dim",
    "default_card_embedding_model",
    "embed_text",
    "pack_f32",
    "unpack_f32",
]
