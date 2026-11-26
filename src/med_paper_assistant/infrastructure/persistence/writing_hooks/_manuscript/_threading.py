"""Whole-manuscript conceptual threading checks (THR-1..3) and shared text helpers."""

from __future__ import annotations

import re
from typing import Any

_STOPWORDS = frozenset(
    {
        "about",
        "above",
        "after",
        "again",
        "against",
        "among",
        "because",
        "before",
        "being",
        "between",
        "could",
        "during",
        "first",
        "found",
        "further",
        "however",
        "including",
        "into",
        "large",
        "later",
        "least",
        "might",
        "more",
        "most",
        "other",
        "overall",
        "patients",
        "patient",
        "results",
        "result",
        "should",
        "since",
        "study",
        "studies",
        "their",
        "there",
        "these",
        "those",
        "through",
        "under",
        "using",
        "which",
        "while",
        "within",
        "without",
        "would",
        "compared",
        "clinical",
        "significantly",
        "associated",
        "data",
        "analysis",
        "group",
        "groups",
        "showed",
        "demonstrated",
        "observed",
    }
)
_NUMBER_TOKEN_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*%|\bp\s*[<=>]\s*0?\.\d+\b|\b(?:RR|OR|HR|aOR|aHR)\s*[:=]?\s*\d+(?:\.\d+)?\b)",
    re.IGNORECASE,
)


def _content_terms(text: str) -> set[str]:
    clean = re.sub(r"\[\[[^\]]+\]\]", " ", text.lower())
    words = re.findall(r"\b[a-z][a-z0-9\-]{3,}\b", clean)
    return {w for w in words if w not in _STOPWORDS}


def _paragraphs(text: str) -> list[str]:
    no_headings = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.MULTILINE)
    raw = [p.strip() for p in re.split(r"\n\s*\n", no_headings) if p.strip()]
    return [
        p for p in raw if not p.startswith("|") and not p.startswith("![") and len(p.split()) >= 15
    ]


def _term_coverage(source_terms: set[str], target_text: str) -> float:
    if not source_terms:
        return 1.0
    target_terms = _content_terms(target_text)
    return len(source_terms & target_terms) / len(source_terms)


def _issue(
    code: str,
    severity: str,
    section: str,
    message: str,
    suggestion: str,
    *,
    filename: str,
    slug: str,
    tool: str = "draft_action",
) -> dict[str, Any]:
    call = (
        {
            "tool": "draft_action",
            "arguments": {"action": "brief", "section": section, "project": slug},
        }
        if tool == "brief"
        else {
            "tool": "draft_action",
            "arguments": {
                "action": "patch",
                "filename": filename,
                "old_text": "<exact passage>",
                "new_text": "<coherent revision>",
                "project": slug,
            },
        }
    )
    return {
        "code": code,
        "severity": severity,
        "section": section,
        "message": message,
        "suggestion": suggestion,
        "suggested_call": call,
    }


def _check_novelty_threading(
    sections: dict[str, str],
    novelty: str,
    filename: str,
    slug: str,
) -> list[dict[str, Any]]:
    """THR-1: Verify 🔒 NOVELTY STATEMENT concepts actually appear in Intro and Discussion."""
    novelty_terms = _content_terms(novelty)
    if len(novelty_terms) < 2:
        return []
    issues: list[dict[str, Any]] = []
    if (
        "introduction" in sections
        and _term_coverage(novelty_terms, sections["introduction"]) < 0.25
    ):
        issues.append(
            _issue(
                "THR-1",
                "CRITICAL",
                "introduction",
                "🔒 NOVELTY STATEMENT concepts from concept.md are weakly reflected in Introduction (<25% term overlap).",
                "Explicitly weave the core novelty claim into Introduction's gap and rationale paragraphs.",
                filename=filename,
                slug=slug,
            )
        )
    if "discussion" in sections and _term_coverage(novelty_terms, sections["discussion"]) < 0.25:
        issues.append(
            _issue(
                "THR-1",
                "WARNING",
                "discussion",
                "🔒 NOVELTY STATEMENT concepts are weakly revisited in Discussion (<25% term overlap).",
                "Reconnect Discussion's interpretation and contribution explicitly back to the novelty claim.",
                filename=filename,
                slug=slug,
            )
        )
    return issues


def _check_selling_points(
    sections: dict[str, str],
    selling_points: list[str],
    filename: str,
    slug: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """THR-2: Track every 🔒 KEY SELLING POINT across sections and flag evaporated points."""
    coverage: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    body_sections = {
        k: v
        for k, v in sections.items()
        if k in ("introduction", "results", "discussion", "abstract")
    }
    if not body_sections:
        return coverage, issues

    for idx, point in enumerate(selling_points, 1):
        terms = _content_terms(point)
        if len(terms) < 2:
            continue
        sec_scores = {
            sec: round(_term_coverage(terms, text), 2) for sec, text in body_sections.items()
        }
        grounded_in = [sec for sec, sc in sec_scores.items() if sc >= 0.25]
        coverage.append(
            {
                "index": idx,
                "point": point[:160],
                "grounded_in": grounded_in,
                "section_scores": sec_scores,
            }
        )
        if not grounded_in:
            severity = "CRITICAL" if "discussion" in body_sections else "WARNING"
            issues.append(
                _issue(
                    "THR-2",
                    severity,
                    "discussion" if "discussion" in body_sections else next(iter(body_sections)),
                    f"🔒 Selling Point #{idx} evaporated from drafted prose: '{point[:100]}'.",
                    "Ground this selling point with evidence in Results and explicit synthesis in Discussion.",
                    filename=filename,
                    slug=slug,
                )
            )
    return coverage, issues


def _check_question_answer_and_abstract(
    sections: dict[str, str], filename: str, slug: str
) -> list[dict[str, Any]]:
    """THR-3: Intro objective -> Discussion opening answer + Abstract <-> Results numeric parity."""
    issues: list[dict[str, Any]] = []
    intro_paras = _paragraphs(sections.get("introduction", ""))
    disc_paras = _paragraphs(sections.get("discussion", ""))
    if intro_paras and disc_paras:
        aim_terms = _content_terms(intro_paras[-1])
        if len(aim_terms) >= 4 and _term_coverage(aim_terms, disc_paras[0]) < 0.20:
            issues.append(
                _issue(
                    "THR-3",
                    "WARNING",
                    "discussion",
                    "Discussion's opening paragraph does not clearly echo the study objective from Introduction's final paragraph.",
                    "Start Discussion by directly answering the primary aim/hypothesis posed at the end of Introduction.",
                    filename=filename,
                    slug=slug,
                )
            )

    abs_text = sections.get("abstract", "")
    res_text = sections.get("results", "")
    if abs_text and res_text:
        abs_nums = {
            re.sub(r"\s+", "", m.group(0).lower()) for m in _NUMBER_TOKEN_RE.finditer(abs_text)
        }
        res_nums = {
            re.sub(r"\s+", "", m.group(0).lower()) for m in _NUMBER_TOKEN_RE.finditer(res_text)
        }
        unmatched = sorted(n for n in abs_nums if n not in res_nums)
        if unmatched:
            issues.append(
                _issue(
                    "THR-3",
                    "CRITICAL",
                    "abstract",
                    f"Abstract reports statistic(s) not found in Results: {', '.join(unmatched[:6])}.",
                    "Reconcile Abstract and Results numbers so every reported figure matches exactly.",
                    filename=filename,
                    slug=slug,
                )
            )
    return issues
