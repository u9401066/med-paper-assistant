"""Pure measurement functions: shingles, MinHash, near-duplicates, novelty and Vendi diversity."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from pydantic import BaseModel

from cgu.domain.common import Measurement
from cgu.domain.lexical import jaccard as jaccard
from cgu.domain.lexical import normalize as normalize
from cgu.domain.lexical import shingles as shingles

JACCARD_DUPLICATE_THRESHOLD = 0.8
COSINE_DUPLICATE_THRESHOLD = 0.92
NEAR_MAX_DISTANCE = 0.35
MID_MAX_DISTANCE = 0.65
BAND_NOTE = (
    f"bands: near < {NEAR_MAX_DISTANCE} <= mid < {MID_MAX_DISTANCE} <= far (uncalibrated cut-offs)"
)
MINHASH_PREFILTER_SIZE = 256


class NoveltyAgainst(BaseModel):
    max_similarity: Measurement
    mean_similarity: Measurement
    nearest_id: str
    reference_size: int


def _hash64(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")


def _mix(x: np.ndarray) -> np.ndarray:
    x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return x ^ (x >> np.uint64(31))


@lru_cache(maxsize=8)
def _masks(num_perm: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2**63, size=num_perm, dtype=np.uint64)


def minhash_signature(items: frozenset[str], num_perm: int = 128, seed: int = 1) -> np.ndarray:
    masks = _masks(num_perm, seed)
    if not items:
        return np.full(num_perm, np.iinfo(np.uint64).max, dtype=np.uint64)
    base = np.array([_hash64(s) for s in items], dtype=np.uint64)
    mixed = _mix(base[:, None] ^ masks[None, :])
    return np.asarray(mixed.min(axis=0))


def minhash_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(a == b))


def lexical_duplicate(
    text: str,
    existing: Sequence[tuple[str, str]],
    threshold: float = JACCARD_DUPLICATE_THRESHOLD,
) -> tuple[str, Measurement] | None:
    """The most similar existing (id, text) at or above threshold, by char-shingle Jaccard."""
    target = shingles(text)
    if not target or not existing:
        return None
    pool = list(existing)
    if len(pool) > MINHASH_PREFILTER_SIZE:
        sig = minhash_signature(target)
        ranked = sorted(
            pool,
            key=lambda item: minhash_similarity(sig, minhash_signature(shingles(item[1]))),
            reverse=True,
        )
        pool = ranked[:32]
    best: tuple[str, float] | None = None
    for idea_id, other in pool:
        score = jaccard(target, shingles(other))
        if score >= threshold and (best is None or score > best[1]):
            best = (idea_id, score)
    if best is None:
        return None
    return best[0], Measurement(
        value=best[1],
        method=f"char 3-gram shingle Jaccard (duplicate if >= {threshold})",
        reference=f"existing session ideas (n={len(existing)})",
        n=len(existing),
    )


def as_matrix(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return np.asarray(matrix / norms)


def semantic_duplicate(
    vector: np.ndarray,
    refs: np.ndarray,
    ref_ids: Sequence[str],
    *,
    threshold: float,
    method: str,
) -> tuple[str, Measurement] | None:
    if refs.shape[0] == 0:
        return None
    sims = refs @ vector
    index = int(np.argmax(sims))
    if float(sims[index]) < threshold:
        return None
    return ref_ids[index], Measurement(
        value=float(sims[index]),
        method=f"{method} (duplicate if >= {threshold})",
        reference=f"existing session ideas (n={refs.shape[0]})",
        n=int(refs.shape[0]),
    )


def novelty_against(
    candidate: np.ndarray,
    refs: np.ndarray,
    ref_ids: Sequence[str],
    *,
    method: str,
    reference: str,
) -> NoveltyAgainst | None:
    """Similarity of a candidate to a reference set; an empty reference set yields None."""
    if refs.shape[0] == 0:
        return None
    sims = refs @ candidate
    index = int(np.argmax(sims))
    n = int(refs.shape[0])
    return NoveltyAgainst(
        max_similarity=Measurement(
            value=float(sims[index]), method=f"max {method}", reference=reference, n=n
        ),
        mean_similarity=Measurement(
            value=float(np.mean(sims)), method=f"mean {method}", reference=reference, n=n
        ),
        nearest_id=ref_ids[index],
        reference_size=n,
    )


def vendi_score(kernel: np.ndarray) -> float:
    n = kernel.shape[0]
    eigenvalues = np.clip(np.linalg.eigvalsh(kernel / n), 0.0, None)
    eigenvalues = eigenvalues[eigenvalues > 1e-12]
    eigenvalues = eigenvalues / eigenvalues.sum()
    return float(math.exp(-float(np.sum(eigenvalues * np.log(eigenvalues)))))


def diversity(vectors: np.ndarray, *, method: str, reference: str) -> Measurement | None:
    """Vendi score of a set (between 1 for identical items and n for orthogonal ones)."""
    n = int(vectors.shape[0])
    if n < 2:
        return None
    return Measurement(
        value=vendi_score(vectors @ vectors.T),
        method=f"Vendi score over {method}",
        reference=reference,
        n=n,
    )


def band_from_distance(distance: float) -> str:
    if distance < NEAR_MAX_DISTANCE:
        return "near"
    if distance < MID_MAX_DISTANCE:
        return "mid"
    return "far"
