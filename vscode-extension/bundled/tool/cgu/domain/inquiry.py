"""Inquiry memory: records, families, hierarchical theme clustering and stable theme identity.

Everything here is deterministic and pure. The clustering thresholds are uncalibrated
heuristics, tuned only on a small synthetic corpus (see docs/inquiry-memory-design.md).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field

from cgu.domain.capture import FAMILY_JACCARD, parse_time
from cgu.domain.common import Measurement
from cgu.domain.lexical import ShingleIndex

InquirySource = Literal["agent", "hook", "import", "manual"]

FAMILY_COSINE = 0.92
MAX_ANALYSED = 2000
DEFAULT_MIN_SIZE = 3
IDENTITY_JACCARD = 0.5
NEAR_WINDOW_DAYS = 7
MAX_EXEMPLARS = 5
MAX_STEMS = 3
STEM_MIN_COUNT = 2
DEFAULT_THRESHOLD_NGRAM = 0.975
DEFAULT_THRESHOLD_SEMANTIC = 0.55
THRESHOLD_NOTE = (
    "uncalibrated: the n-gram default was tuned on a small synthetic corpus only; "
    "the semantic default has not been tuned at all"
)


def default_threshold(semantic: bool) -> float:
    return DEFAULT_THRESHOLD_SEMANTIC if semantic else DEFAULT_THRESHOLD_NGRAM


class Inquiry(BaseModel):
    id: str
    text: str
    gist: str | None = None
    source: InquirySource = "agent"
    project: str | None = None
    session_id: str | None = None
    occurred_at: str
    captured_at: str
    redactions: dict[str, int] = Field(default_factory=dict)
    truncated: bool = False
    family_id: str
    meta: dict[str, Any] = Field(default_factory=dict)

    def session_key(self) -> str | None:
        """The session this question belongs to: a CGU session, else the client's own."""
        if self.session_id:
            return f"cgu:{self.session_id}"
        client = self.meta.get("client_session")
        return f"client:{client}" if isinstance(client, str) and client else None

    def epoch(self) -> float:
        return parse_time(self.occurred_at).timestamp()


class ThemeRecord(BaseModel):
    id: str
    label: str | None = None
    labeled_by: str | None = None
    member_ids: list[str]
    backend: str
    updated_at: str = ""


class SourceRecord(BaseModel):
    id: str
    kind: str
    data: dict[str, Any] = Field(default_factory=dict)
    first_surfaced_at: str = ""
    last_surfaced_at: str = ""
    times_surfaced: int = 1


class InquiryConsent(BaseModel):
    """Who agreed to record questions, when, and in whose words."""

    granted: bool
    note: str = ""
    via: Literal["elicitation", "caller", "cli"]
    final: bool = True


# --- stems ---------------------------------------------------------------------------------

_LEADING = re.compile(r"^[\s\W_]+")
_ENGLISH_STEM = re.compile(r"([A-Za-z']+)(?:\s+([A-Za-z']+))?")


def question_stem(text: str) -> str:
    """The opening of a question: its first 2 characters, or first 2 words when it starts in English."""
    folded = _LEADING.sub("", unicodedata.normalize("NFKC", text).strip())
    if not folded:
        return ""
    if folded[0].isascii() and folded[0].isalpha():
        match = _ENGLISH_STEM.match(folded)
        if match:
            return " ".join(part.lower() for part in match.groups() if part)
    return folded[:2]


# --- families ------------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilyMatch:
    matched_id: str
    family_id: str
    similarity: float
    method: Literal["lexical", "semantic"]


class FamilyIndex:
    """Existing questions (oldest first), used to decide whether a new one recurs an old one."""

    def __init__(
        self,
        rows: Sequence[tuple[str, str, str, str]],
        vectors: dict[str, np.ndarray] | None = None,
    ) -> None:
        """rows: (id, family_id, text, occurred_at)."""
        self._lexical = ShingleIndex(FAMILY_JACCARD)
        for row in rows:
            self._lexical.add(row[0], row[2])
        self._family: dict[str, str] = {r[0]: r[1] for r in rows}
        self._members: dict[str, list[tuple[str, str]]] = {}
        for inquiry_id, family_id, _text, occurred_at in rows:
            self._members.setdefault(family_id, []).append((occurred_at, inquiry_id))
        have = vectors or {}
        base_ids = [r[0] for r in rows if r[0] in have]
        self._base_ids = base_ids
        self._base = np.stack([have[i] for i in base_ids]) if base_ids else None
        self._extra_ids: list[str] = []
        self._extra: list[np.ndarray] = []

    def __len__(self) -> int:
        return len(self._lexical)

    def match(self, text: str, vector: np.ndarray | None) -> FamilyMatch | None:
        lexical = self._lexical.best(text)
        if lexical is not None:
            return FamilyMatch(lexical[0], self._family[lexical[0]], lexical[1], "lexical")
        if vector is None:
            return None
        best: tuple[str, float] | None = None
        for ids, matrix in (
            (self._base_ids, self._base),
            (self._extra_ids, np.stack(self._extra) if self._extra else None),
        ):
            if matrix is None:
                continue
            sims = matrix @ vector
            index = int(np.argmax(sims))
            if best is None or float(sims[index]) > best[1]:
                best = (ids[index], float(sims[index]))
        if best is None or best[1] < FAMILY_COSINE:
            return None
        return FamilyMatch(best[0], self._family[best[0]], best[1], "semantic")

    def count(self, family_id: str) -> int:
        return len(self._members.get(family_id, []))

    def earliest(self, family_id: str) -> str | None:
        members = self._members.get(family_id)
        return min(members)[1] if members else None

    def add(
        self,
        inquiry_id: str,
        family_id: str,
        text: str,
        occurred_at: str,
        vector: np.ndarray | None,
    ) -> None:
        self._lexical.add(inquiry_id, text)
        self._family[inquiry_id] = family_id
        self._members.setdefault(family_id, []).append((occurred_at, inquiry_id))
        if vector is not None:
            self._extra_ids.append(inquiry_id)
            self._extra.append(vector)


# --- clustering ----------------------------------------------------------------------------


def average_linkage(distance: np.ndarray, threshold: float) -> list[list[int]]:
    """Average-linkage (UPGMA) clusters of a distance matrix, cut at `threshold`.

    Nearest-neighbour-chain implementation (O(n^2)). A reciprocal-nearest pair farther apart than
    the threshold can never merge with anything below it, so both are frozen as final clusters.
    """
    n = int(distance.shape[0])
    if n == 0:
        return []
    d = np.array(distance, dtype=np.float64)
    np.fill_diagonal(d, np.inf)
    size = np.ones(n, dtype=np.float64)
    active = np.ones(n, dtype=bool)
    label = np.arange(n)
    chain: list[int] = []
    remaining = n
    while remaining > 0:
        if not chain:
            chain.append(int(np.argmax(active)))
        a = chain[-1]
        row = d[a]
        b = int(np.argmin(row))
        best = float(row[b])
        if len(chain) > 1 and float(d[a, chain[-2]]) <= best:
            b = chain[-2]
            best = float(d[a, b])
        if not np.isfinite(best):
            active[a] = False
            remaining -= 1
            chain.pop()
            continue
        if len(chain) > 1 and b == chain[-2]:
            chain.pop()
            chain.pop()
            if best > threshold:
                for k in (a, b):
                    active[k] = False
                    d[k, :] = np.inf
                    d[:, k] = np.inf
                remaining -= 2
            else:
                merged = (size[a] * d[a] + size[b] * d[b]) / (size[a] + size[b])
                merged[a] = np.inf
                merged[b] = np.inf
                d[a, :] = merged
                d[:, a] = merged
                d[b, :] = np.inf
                d[:, b] = np.inf
                size[a] += size[b]
                active[b] = False
                label[label == b] = a
                remaining -= 1
        else:
            chain.append(b)
    groups: dict[int, list[int]] = {}
    for index in range(n):
        groups.setdefault(int(label[index]), []).append(index)
    return sorted(groups.values(), key=lambda members: members[0])


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector if norm == 0.0 else np.asarray(vector / norm)


def cluster_inquiries(
    matrix: np.ndarray, families: Sequence[str], threshold: float
) -> list[list[int]]:
    """Cluster inquiries by family: a family counts once, represented by its mean vector."""
    order: dict[str, list[int]] = {}
    for index, family in enumerate(families):
        order.setdefault(family, []).append(index)
    groups = list(order.values())
    if not groups:
        return []
    centers = np.stack([_unit(matrix[g].mean(axis=0)) for g in groups])
    distance = np.clip(1.0 - centers @ centers.T, 0.0, 2.0)
    return [
        sorted(index for family in cluster for index in groups[family])
        for cluster in average_linkage(distance, threshold)
    ]


@dataclass
class ThemeCandidate:
    member_ids: list[str]
    families: int
    size: int
    distinct_days: int
    first_seen: str
    last_seen: str
    projects: list[str]
    exemplar_ids: list[str]
    top_stems: list[tuple[str, int]]
    centroid: np.ndarray


def build_candidates(
    inquiries: Sequence[Inquiry], matrix: np.ndarray, threshold: float, min_size: int
) -> tuple[list[ThemeCandidate], int]:
    """Themes of at least `min_size` families, plus the number of inquiries left uncategorised."""
    clusters = cluster_inquiries(matrix, [i.family_id for i in inquiries], threshold)
    themes: list[ThemeCandidate] = []
    uncategorized = 0
    for indexes in clusters:
        members = [inquiries[i] for i in indexes]
        family_ids = {m.family_id for m in members}
        if len(family_ids) < min_size:
            uncategorized += len(members)
            continue
        centroid = _unit(matrix[indexes].mean(axis=0))
        sims = matrix[indexes] @ centroid
        ranked = sorted(
            range(len(members)),
            key=lambda j: (-float(sims[j]), members[j].occurred_at, members[j].id),
        )
        exemplars: list[str] = []
        seen: set[str] = set()
        for j in ranked:
            if members[j].family_id not in seen and len(exemplars) < MAX_EXEMPLARS:
                seen.add(members[j].family_id)
                exemplars.append(members[j].id)
        firsts: dict[str, Inquiry] = {}
        for member in sorted(members, key=lambda m: (m.occurred_at, m.id)):
            firsts.setdefault(member.family_id, member)
        stems = Counter(s for s in (question_stem(f.text) for f in firsts.values()) if s)
        top = sorted(stems.items(), key=lambda item: (-item[1], item[0]))[:MAX_STEMS]
        days = {m.occurred_at[:10] for m in members}
        ordered = sorted(members, key=lambda m: (m.occurred_at, m.id))
        themes.append(
            ThemeCandidate(
                member_ids=[m.id for m in ordered],
                families=len(family_ids),
                size=len(members),
                distinct_days=len(days),
                first_seen=ordered[0].occurred_at,
                last_seen=ordered[-1].occurred_at,
                projects=sorted({m.project for m in members if m.project}),
                exemplar_ids=exemplars,
                top_stems=[(s, c) for s, c in top if c >= STEM_MIN_COUNT],
                centroid=centroid,
            )
        )
    themes.sort(key=lambda t: (-t.families, -t.size, t.first_seen, t.member_ids[0]))
    return themes, uncategorized


# --- identity ------------------------------------------------------------------------------


def _set_jaccard(a: set[str], b: set[str]) -> float:
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def match_identities(
    old: Sequence[ThemeRecord], new: Sequence[Sequence[str]], scope_ids: set[str]
) -> list[ThemeRecord | None]:
    """Pair new clusters with stored themes by member-set Jaccard >= 0.5, best pairs first.

    Stored members outside the current scope are ignored, so a filtered view keeps the ids and
    labels of the global themes it overlaps.
    """
    old_sets = [set(record.member_ids) & scope_ids for record in old]
    new_sets = [set(members) for members in new]
    pairs = sorted(
        (
            (-score, i, j)
            for i, a in enumerate(old_sets)
            for j, b in enumerate(new_sets)
            if a and (score := _set_jaccard(a, b)) >= IDENTITY_JACCARD
        )
    )
    matched: list[ThemeRecord | None] = [None] * len(new)
    used: set[int] = set()
    for _neg, i, j in pairs:
        if i in used or matched[j] is not None:
            continue
        used.add(i)
        matched[j] = old[i]
    return matched


def ephemeral_theme_id(member_ids: Sequence[str]) -> str:
    digest = hashlib.sha256("|".join(sorted(member_ids)).encode()).hexdigest()
    return f"th-{digest[:8]}"


# --- relations between themes --------------------------------------------------------------


def centroid_distance(a: ThemeCandidate, b: ThemeCandidate) -> float:
    return float(np.clip(1.0 - float(a.centroid @ b.centroid), 0.0, 2.0))


def co_occurrence(a: Sequence[Inquiry], b: Sequence[Inquiry]) -> tuple[int, int]:
    """(co-occurring pairs, shared sessions) of two themes' questions.

    Two questions co-occur when both belong to a known session and it is the same one; when either
    has no session they co-occur if asked at most 7 days apart.
    """
    keys_a = [m.session_key() for m in a]
    keys_b = [m.session_key() for m in b]
    codes: dict[str, int] = {}
    for key in (*keys_a, *keys_b):
        if key is not None:
            codes.setdefault(key, len(codes))
    ca = np.array([-1 if k is None else codes[k] for k in keys_a])
    cb = np.array([-1 if k is None else codes[k] for k in keys_b])
    ta = np.array([m.epoch() for m in a])
    tb = np.array([m.epoch() for m in b])
    both = (ca[:, None] >= 0) & (cb[None, :] >= 0)
    same = both & (ca[:, None] == cb[None, :])
    near = ~both & (np.abs(ta[:, None] - tb[None, :]) <= NEAR_WINDOW_DAYS * 86400)
    shared = len({k for k in keys_a if k is not None} & {k for k in keys_b if k is not None})
    return int(same.sum() + near.sum()), shared


def stem_share(count: int, families: int) -> Measurement:
    return Measurement(
        value=count / families,
        method="share of the theme's families whose first question opens with the stem "
        "(first 2 characters, or first 2 English words); uncalibrated heuristic",
        reference=f"families in this theme (n={families})",
        n=families,
    )
