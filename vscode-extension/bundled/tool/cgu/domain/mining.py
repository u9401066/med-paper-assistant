"""Mining creative sources from a person's own question history, plus the funnel and coverage gauges.

Every trigger is a deterministic condition over counts and uncalibrated similarity measurements.
Titles are fixed templates over facts; nothing here invents prose or a combined creativity score.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field

from cgu.domain.capture import CHANNELS, parse_time
from cgu.domain.common import Measurement
from cgu.domain.inquiry import (
    NEAR_WINDOW_DAYS,
    Inquiry,
    SourceRecord,
    ThemeCandidate,
    centroid_distance,
    co_occurrence,
    stem_share,
)
from cgu.domain.measure import band_from_distance

MineKind = Literal["frame", "bridge", "stalled", "dormant"]
KINDS: tuple[MineKind, ...] = ("frame", "bridge", "stalled", "dormant")
DECISIONS = ("adopt", "modify", "abandon")
DEFAULT_LIMIT = 3
STALLED_MIN_DAYS = 3
STALLED_MIN_FAMILIES = 3
EVIDENCE_WEAK_BELOW = 0.5
DORMANT_WINDOW_DAYS = 14
DORMANT_MIN_SIMILARITY_LEXICAL = 0.2
DORMANT_MIN_SIMILARITY_SEMANTIC = 0.6
RELATED_MIN_SIMILARITY_LEXICAL = 0.25
RELATED_MIN_SIMILARITY_SEMANTIC = 0.5

ECHO_CHAMBER_WARNING = (
    "這些來源只反映你已在想的事（取材自你自己的提問歷史）；外部視角請搭配 cgu_material 或文獻工具。"
)
LEXICAL_WARNING = (
    "semantic=false：主題是詞面（字元 n-gram）群聚，不是語意主題；相似不代表意思相近。"
)
RANK_RULES: dict[str, str] = {
    "frame": "最常見問句開頭的占比由高到低；其次主題的 family 數由多到少；最後依 theme_id。",
    "bridge": (
        "co_occurrence（兩主題的提問在同一個 session，或在無 session 時相隔 7 天內的配對數）由多到少；"
        "其次 mid 先於 far；其次兩主題 family 數之和由多到少。"
    ),
    "stalled": "distinct_days 由多到少；其次 families 由多到少；最後依 theme_id。",
    "dormant": "相似度由高到低；其次被放棄的先於被修改的；最後依 idea_id。",
}
_BAND_NAME = {"mid": "中等距離", "far": "遙遠"}
Safe = Callable[[str], str]


@dataclass
class ThemeView:
    theme_id: str
    label: str | None
    labeled_by: str | None
    persisted: bool
    candidate: ThemeCandidate


class MinedSource(BaseModel):
    source_id: str
    kind: MineKind
    title: str
    evidence: list[dict[str, str]]
    measures: dict[str, Measurement] = Field(default_factory=dict)
    facts: dict[str, Any] = Field(default_factory=dict)
    next: list[dict[str, Any]] = Field(default_factory=list)


class FeedbackIdea(BaseModel):
    idea_id: str
    session_id: str
    session_topic: str
    text: str
    decision: str
    decided_at: str


def make_source_id(kind: str, evidence_ids: Sequence[str], extra: str = "") -> str:
    """The same evidence always yields the same id."""
    digest = hashlib.sha256("|".join([kind, extra, *sorted(evidence_ids)]).encode()).hexdigest()
    return f"src-{digest[:12]}"


def _evidence(ids: Sequence[str], by_id: dict[str, Inquiry], safe: Safe) -> list[dict[str, str]]:
    return [
        {
            "inquiry_id": i,
            "text": safe(by_id[i].text),
            "occurred_at": by_id[i].occurred_at,
        }
        for i in ids
        if i in by_id
    ]


def display_name(view: ThemeView, by_id: dict[str, Inquiry], safe: Safe) -> str:
    if view.label:
        return f"「{view.label}」"
    first = by_id.get(view.candidate.exemplar_ids[0]) if view.candidate.exemplar_ids else None
    snippet = safe(first.text)[:20] if first else ""
    return f"（未命名主題：{snippet}…）"


def _after(session: str) -> dict[str, Any]:
    return {
        "tool": "cgu_ideas",
        "action": "add",
        "args": {
            "session_id": session,
            "ideas": [
                {
                    "text": "<點子>",
                    "kind": "candidate",
                    "meta": {"from_source": "<此來源的 source_id>"},
                }
            ],
        },
    }


def _open(topic: str) -> dict[str, Any]:
    return {"tool": "cgu_session", "action": "open", "args": {"topic": topic}}


SESSION_REF = "<上一步回傳的 session_id>"


# --- frame ---------------------------------------------------------------------------------


def mine_frames(
    themes: Sequence[ThemeView], by_id: dict[str, Inquiry], *, limit: int, safe: Safe
) -> list[MinedSource]:
    def key(view: ThemeView) -> tuple[float, int, str]:
        c = view.candidate
        share = c.top_stems[0][1] / c.families if c.top_stems else 0.0
        return (-share, -c.families, view.theme_id)

    sources: list[MinedSource] = []
    for view in sorted(themes, key=key)[:limit]:
        c = view.candidate
        name = display_name(view, by_id, safe)
        stem, count = c.top_stems[0] if c.top_stems else (None, 0)
        if stem is None:
            title = f"{name} 這個主題有 {c.families} 個不同的問題；可以溯因這些提問默默依賴的假設"
        else:
            title = (
                f"{name} 這個主題裡，{count}/{c.families} 個不同的問題都以「{stem}」開頭；"
                "可以溯因這些提問默默依賴的假設"
            )
        sid = make_source_id("frame", c.exemplar_ids, extra=view.theme_id)
        sources.append(
            MinedSource(
                source_id=sid,
                kind="frame",
                title=title,
                evidence=_evidence(c.exemplar_ids, by_id, safe),
                measures={"top_stem_share": stem_share(count, c.families)} if stem else {},
                facts={
                    "theme_id": view.theme_id,
                    "label": view.label,
                    "families": c.families,
                    "size": c.size,
                    "distinct_days": c.distinct_days,
                    "top_stem": stem,
                    "top_stem_count": count,
                },
                next=[
                    _open("<把這個主題改寫成一個探究題>"),
                    {
                        "tool": "cgu_frame",
                        "action": "create",
                        "args": {
                            "session_id": SESSION_REF,
                            "problem": "<同上>",
                            "assumptions": [
                                {
                                    "text": "<溯因出的假設>",
                                    "kind": "belt",
                                    "source": "abduced_from_user_questions",
                                }
                            ],
                        },
                    },
                    {
                        "tool": "cgu_frame",
                        "action": "operate",
                        "args": {
                            "session_id": SESSION_REF,
                            "frame_id": "<上一步回傳的 frame_id>",
                            "operator": "negate",
                            "target": "assumption",
                        },
                    },
                    _after(SESSION_REF),
                ],
            )
        )
    return sources


# --- bridge --------------------------------------------------------------------------------


def band_counts(themes: Sequence[ThemeView]) -> dict[str, int]:
    counts = {"near": 0, "mid": 0, "far": 0}
    for i, a in enumerate(themes):
        for b in themes[i + 1 :]:
            counts[band_from_distance(centroid_distance(a.candidate, b.candidate))] += 1
    return counts


def mine_bridges(
    themes: Sequence[ThemeView], by_id: dict[str, Inquiry], *, limit: int, safe: Safe
) -> list[MinedSource]:
    found: list[tuple[tuple[int, int, int, str, str], MinedSource]] = []
    for i, a in enumerate(themes):
        for b in themes[i + 1 :]:
            distance = centroid_distance(a.candidate, b.candidate)
            band = band_from_distance(distance)
            if band == "near":
                continue
            co, shared = co_occurrence(
                [by_id[m] for m in a.candidate.member_ids if m in by_id],
                [by_id[m] for m in b.candidate.member_ids if m in by_id],
            )
            ids_a = a.candidate.exemplar_ids[:3]
            ids_b = b.candidate.exemplar_ids[:3]
            evidence = [
                {**row, "theme_id": a.theme_id} for row in _evidence(ids_a, by_id, safe)
            ] + [{**row, "theme_id": b.theme_id} for row in _evidence(ids_b, by_id, safe)]
            name_a = display_name(a, by_id, safe)
            name_b = display_name(b, by_id, safe)
            title = (
                f"{name_a} 與 {name_b} 是兩個{_BAND_NAME[band]}的主題，"
                f"共同出現 {co} 次（同一個 session，或無 session 時相隔 {NEAR_WINDOW_DAYS} 天內）；"
                "可以當碰撞素材"
            )
            sid = make_source_id(
                "bridge", [*ids_a, *ids_b], extra="|".join(sorted([a.theme_id, b.theme_id]))
            )
            text_a = safe(by_id[ids_a[0]].text) if ids_a and ids_a[0] in by_id else "<A>"
            text_b = safe(by_id[ids_b[0]].text) if ids_b and ids_b[0] in by_id else "<B>"
            source = MinedSource(
                source_id=sid,
                kind="bridge",
                title=title,
                evidence=evidence,
                measures={
                    "centroid_distance": Measurement(
                        value=distance,
                        method="cosine distance between the two themes' centroids; "
                        "band cut-offs are uncalibrated",
                        reference="the two themes' member questions",
                        n=len(a.candidate.member_ids) + len(b.candidate.member_ids),
                    )
                },
                facts={
                    "theme_a": a.theme_id,
                    "theme_b": b.theme_id,
                    "label_a": a.label,
                    "label_b": b.label,
                    "band": band,
                    "co_occurrence": co,
                    "shared_sessions": shared,
                    "families_a": a.candidate.families,
                    "families_b": b.candidate.families,
                },
                next=[
                    _open("<兩個主題之間的橋接探究題>"),
                    {
                        "tool": "cgu_material",
                        "action": "add",
                        "args": {
                            "session_id": SESSION_REF,
                            "fragments": [
                                {"text": e["text"], "source_type": "user_inquiry"} for e in evidence
                            ],
                        },
                    },
                    {
                        "tool": "cgu_diverge",
                        "action": "collide",
                        "args": {
                            "session_id": SESSION_REF,
                            "a": text_a,
                            "b": text_b,
                            "mode": "bridge",
                        },
                    },
                    _after(SESSION_REF),
                ],
            )
            rank = (
                -co,
                0 if band == "mid" else 1,
                -(a.candidate.families + b.candidate.families),
                a.theme_id,
                b.theme_id,
            )
            found.append((rank, source))
    found.sort(key=lambda item: item[0])
    return [source for _rank, source in found[:limit]]


# --- stalled -------------------------------------------------------------------------------


def mine_stalled(
    themes: Sequence[ThemeView],
    by_id: dict[str, Inquiry],
    adopted_sessions: set[str],
    *,
    limit: int,
    safe: Safe,
) -> list[MinedSource]:
    found: list[tuple[tuple[int, int, str], MinedSource]] = []
    for view in themes:
        c = view.candidate
        if c.distinct_days < STALLED_MIN_DAYS or c.families < STALLED_MIN_FAMILIES:
            continue
        members = [by_id[m] for m in c.member_ids if m in by_id]
        sessions = {m.session_id for m in members if m.session_id}
        if sessions & adopted_sessions:
            continue
        linked = sum(1 for m in members if m.session_id)
        quality = linked / len(members) if members else 0.0
        weak = quality < EVIDENCE_WEAK_BELOW
        name = display_name(view, by_id, safe)
        note = (
            f"證據弱：只有 {linked}/{len(members)} 筆提問連結到 session"
            if weak
            else f"{linked}/{len(members)} 筆提問連結到 session"
        )
        title = (
            f"{name} 在 {c.distinct_days} 天裡出現 {c.families} 種問法，"
            f"所連結的 session 沒有任何被採用的點子（{note}）"
        )
        source = MinedSource(
            source_id=make_source_id("stalled", c.exemplar_ids, extra=view.theme_id),
            kind="stalled",
            title=title,
            evidence=_evidence(c.exemplar_ids, by_id, safe),
            measures={
                "evidence_quality": Measurement(
                    value=quality,
                    method="share of the theme's questions captured with a CGU session link "
                    f"(weak evidence below {EVIDENCE_WEAK_BELOW}); uncalibrated",
                    reference=f"questions in this theme (n={len(members)})",
                    n=len(members),
                )
            },
            facts={
                "theme_id": view.theme_id,
                "label": view.label,
                "distinct_days": c.distinct_days,
                "families": c.families,
                "size": c.size,
                "linked_inquiries": linked,
                "linked_sessions": len(sessions),
                "weak_evidence": weak,
                "stalled_rounds_suggested": c.distinct_days,
            },
            next=[
                _open("<把這個主題改寫成一個探究題>"),
                {
                    "tool": "cgu_frame",
                    "action": "create",
                    "args": {"session_id": SESSION_REF, "problem": "<同上>"},
                },
                {
                    "tool": "cgu_frame",
                    "action": "doubt",
                    "args": {
                        "session_id": SESSION_REF,
                        "frame_id": "<上一步回傳的 frame_id>",
                        "signals": {"stalled_rounds": c.distinct_days},
                    },
                },
            ],
        )
        found.append(((-c.distinct_days, -c.families, view.theme_id), source))
    found.sort(key=lambda item: item[0])
    return [source for _rank, source in found[:limit]]


# --- dormant -------------------------------------------------------------------------------


def latest_feedback_ideas(rows: Sequence[dict[str, Any]]) -> list[FeedbackIdea]:
    """The latest decision per idea (rows are in the order the feedback was recorded)."""
    latest: dict[str, FeedbackIdea] = {}
    for row in rows:
        if not row.get("text"):
            continue
        latest[row["idea_id"]] = FeedbackIdea(
            idea_id=row["idea_id"],
            session_id=row["session_id"],
            session_topic=row.get("session_topic") or "",
            text=row["text"],
            decision=row["decision"],
            decided_at=row.get("at") or "",
        )
    return list(latest.values())


def recent_window(inquiries: Sequence[Inquiry], now: datetime) -> list[Inquiry]:
    floor = now - timedelta(days=DORMANT_WINDOW_DAYS)
    return [i for i in inquiries if parse_time(i.occurred_at) >= floor]


def mine_dormant(
    ideas: Sequence[FeedbackIdea],
    idea_matrix: np.ndarray,
    recent: Sequence[Inquiry],
    recent_matrix: np.ndarray,
    *,
    now: datetime,
    min_similarity: float,
    method: str,
    limit: int,
    safe: Safe,
) -> list[MinedSource]:
    if not ideas or not recent:
        return []
    sims = idea_matrix @ recent_matrix.T
    found: list[tuple[tuple[float, int, str], MinedSource]] = []
    for i, idea in enumerate(ideas):
        if idea.decision not in ("abandon", "modify"):
            continue
        row = sims[i].copy()
        for j, inquiry in enumerate(recent):
            if inquiry.session_id == idea.session_id:
                row[j] = -np.inf
        j = int(np.argmax(row))
        score = float(row[j])
        if score < min_similarity:
            continue
        inquiry = recent[j]
        days_ago = max(0, int((now - parse_time(inquiry.occurred_at)).total_seconds() // 86400))
        verb = "放棄" if idea.decision == "abandon" else "修改"
        snippet = safe(idea.text)[:40]
        sid = make_source_id("dormant", [inquiry.id], extra=idea.idea_id)
        source = MinedSource(
            source_id=sid,
            kind="dormant",
            title=(
                f"你在「{safe(idea.session_topic)[:30]}」{verb}過的點子「{snippet}」，"
                f"和你 {days_ago} 天前的提問相似；可以重新啟動"
            ),
            evidence=_evidence([inquiry.id], {inquiry.id: inquiry}, safe),
            measures={
                "similarity": Measurement(
                    value=score,
                    method=f"{method}; threshold {min_similarity} is uncalibrated",
                    reference=f"your questions in the last {DORMANT_WINDOW_DAYS} days "
                    f"(n={len(recent)})",
                    n=len(recent),
                )
            },
            facts={
                "idea_id": idea.idea_id,
                "idea_text": safe(idea.text),
                "idea_decision": idea.decision,
                "session_id": idea.session_id,
                "session_topic": safe(idea.session_topic),
                "inquiry_id": inquiry.id,
                "days_ago": days_ago,
            },
            next=[
                _open(safe(inquiry.text)[:80]),
                {
                    "tool": "cgu_ideas",
                    "action": "add",
                    "args": {
                        "session_id": SESSION_REF,
                        "ideas": [
                            {
                                "text": safe(idea.text),
                                "kind": "human",
                                "meta": {"from_dormant_idea": idea.idea_id},
                            }
                        ],
                    },
                },
                _after(SESSION_REF),
            ],
        )
        found.append(((-score, 0 if idea.decision == "abandon" else 1, idea.idea_id), source))
    found.sort(key=lambda item: item[0])
    return [source for _rank, source in found[:limit]]


# --- funnel and coverage -------------------------------------------------------------------


def _funnel_row() -> dict[str, int]:
    return {
        "surfaced": 0,
        "times_surfaced": 0,
        "turned_into_ideas": 0,
        "sources_with_ideas": 0,
        "adopted": 0,
        "modified": 0,
        "abandoned": 0,
        "undecided": 0,
        "surfaced_unused": 0,
    }


_DECISION_FIELD = {"adopt": "adopted", "modify": "modified", "abandon": "abandoned"}


def build_funnel(
    sources: Sequence[SourceRecord],
    ideas: Sequence[tuple[str, str]],
    decisions: dict[str, str],
) -> dict[str, Any]:
    """surfaced -> turned into ideas -> adopted / modified / abandoned, by source kind.

    `ideas` are (idea_id, source_id) pairs from meta.from_source; `decisions` the latest feedback
    per idea. Surfaced sources that nobody used are the baseline.
    """
    by_kind: dict[str, dict[str, int]] = {kind: _funnel_row() for kind in KINDS}
    kind_of = {s.id: s.kind for s in sources}
    used: set[str] = set()
    for source in sources:
        row = by_kind.setdefault(source.kind, _funnel_row())
        row["surfaced"] += 1
        row["times_surfaced"] += source.times_surfaced
    for idea_id, source_id in ideas:
        kind = kind_of.get(source_id)
        if kind is None:
            continue
        row = by_kind[kind]
        row["turned_into_ideas"] += 1
        used.add(source_id)
        decision = decisions.get(idea_id)
        if decision in _DECISION_FIELD:
            row[_DECISION_FIELD[decision]] += 1
        else:
            row["undecided"] += 1
    for source in sources:
        if source.id in used:
            by_kind[source.kind]["sources_with_ideas"] += 1
    total = _funnel_row()
    for row in by_kind.values():
        row["surfaced_unused"] = row["surfaced"] - row["sources_with_ideas"]
        for key, value in row.items():
            total[key] += value
    return {
        "total": total,
        "by_kind": by_kind,
        "note": "surfaced_unused is the baseline: sources shown but never turned into an idea. "
        "Counts only; no preference model, no prediction.",
    }


def build_coverage(
    inquiries: Sequence[Inquiry], themes: int, bridges: dict[str, int]
) -> dict[str, Any]:
    channels = dict.fromkeys(CHANNELS, 0)
    for inquiry in inquiries:
        channels[inquiry.source] = channels.get(inquiry.source, 0) + 1
    return {
        "inquiries": len(inquiries),
        "families": len({i.family_id for i in inquiries}),
        "themes_min_size": themes,
        "distinct_days": len({i.occurred_at[:10] for i in inquiries}),
        "projects": len({i.project for i in inquiries if i.project}),
        "sources_by_channel": channels,
        "bridge_candidates": bridges,
        "note": "more material, not more creativity",
    }
