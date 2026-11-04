"""Lexical text helpers: normalisation, character shingles and Jaccard. Standard library only."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Sequence
from functools import lru_cache

_NON_ALNUM = re.compile(r"[\W_]+")


def normalize(text: str) -> str:
    return _NON_ALNUM.sub("", unicodedata.normalize("NFKC", text).casefold())


@lru_cache(maxsize=4096)
def shingles(text: str, n: int = 3) -> frozenset[str]:
    norm = normalize(text)
    if not norm:
        return frozenset()
    if len(norm) <= n:
        return frozenset({norm})
    return frozenset(norm[i : i + n] for i in range(len(norm) - n + 1))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def best_lexical_match(
    text: str, candidates: Sequence[tuple[str, str]], threshold: float
) -> tuple[str, float] | None:
    """The (id, Jaccard) of the most similar candidate (id, text) at or above threshold.

    Jaccard can never exceed the ratio of the two set sizes, so candidates whose size is too
    different are skipped without intersecting.
    """
    target = shingles(text)
    if not target:
        return None
    size = len(target)
    best: tuple[str, float] | None = None
    for candidate_id, other_text in candidates:
        other = shingles(other_text)
        if not other:
            continue
        small, large = (size, len(other)) if size <= len(other) else (len(other), size)
        if small / large < threshold:
            continue
        score = len(target & other) / len(target | other)
        if score >= threshold and (best is None or score > best[1]):
            best = (candidate_id, score)
    return best


class ShingleIndex:
    """Exact 'Jaccard >= threshold' lookup over many texts, by prefix filtering.

    Two sets that overlap at Jaccard >= t share an element within the first |x| - ceil(t|x|) + 1
    elements of each (in one global order), so only texts that share such a prefix element are
    compared. The result is the same as scanning every text, and the work stays small as the
    history grows: this keeps a worker thread from hogging the interpreter lock.
    """

    def __init__(self, threshold: float) -> None:
        self._threshold = threshold
        self._keys: list[str] = []
        self._sets: list[frozenset[str]] = []
        self._postings: dict[str, list[int]] = {}

    def __len__(self) -> int:
        return len(self._keys)

    def _prefix(self, grams: frozenset[str]) -> list[str]:
        size = len(grams)
        keep = size - math.ceil(self._threshold * size - 1e-9) + 1
        return sorted(grams)[: max(keep, 1)]

    def add(self, key: str, text: str) -> None:
        grams = shingles(text)
        index = len(self._keys)
        self._keys.append(key)
        self._sets.append(grams)
        for gram in self._prefix(grams) if grams else ():
            self._postings.setdefault(gram, []).append(index)

    def best(self, text: str) -> tuple[str, float] | None:
        """The (key, Jaccard) of the closest indexed text at or above the threshold."""
        grams = shingles(text)
        if not grams:
            return None
        size = len(grams)
        seen: set[int] = set()
        best: tuple[int, float] | None = None
        for gram in self._prefix(grams):
            for index in self._postings.get(gram, ()):
                if index in seen:
                    continue
                seen.add(index)
                other = self._sets[index]
                small, large = (size, len(other)) if size <= len(other) else (len(other), size)
                if small / large < self._threshold:
                    continue
                score = len(grams & other) / len(grams | other)
                if score >= self._threshold and (
                    best is None or score > best[1] or (score == best[1] and index < best[0])
                ):
                    best = (index, score)
        return None if best is None else (self._keys[best[0]], best[1])
