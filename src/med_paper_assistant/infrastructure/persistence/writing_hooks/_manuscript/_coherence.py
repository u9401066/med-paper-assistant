"""Deterministic prose coherence & whole-manuscript concept threading analyzer."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.persistence.narrative_thread_store import (
    NarrativeThreadStore,
    split_manuscript_sections,
)

from ._threading import (
    _check_novelty_threading,
    _check_question_answer_and_abstract,
    _check_selling_points,
    _content_terms,
    _issue,
    _paragraphs,
)

_MECHANICAL_OPENER_RE = re.compile(
    r"^(?:Furthermore|Moreover|Additionally|In\s+addition|Besides|Also)\b[, ]",
    re.IGNORECASE,
)


def _boundary_sentences(paragraph: str, *, tail: bool) -> str:
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
    if not sents:
        return paragraph
    chosen = sents[-2:] if tail else sents[:2]
    return " ".join(chosen)


def _ngrams(text: str, n: int = 6) -> set[str]:
    clean = re.sub(r"\[\[[^\]]+\]\]", " ", text.lower())
    tokens = re.findall(r"[a-z0-9]+", clean)
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _check_paragraph_flow(
    sections: dict[str, str], filename: str, slug: str
) -> list[dict[str, Any]]:
    """COH-1: Adjacent paragraph Given->New lexical bridge & mechanical opener audit."""
    issues: list[dict[str, Any]] = []
    for sec in ("introduction", "methods", "results", "discussion"):
        paras = _paragraphs(sections.get(sec, ""))
        for idx in range(len(paras) - 1):
            tail_terms = _content_terms(_boundary_sentences(paras[idx], tail=True))
            head_terms = _content_terms(_boundary_sentences(paras[idx + 1], tail=False))
            overlap = tail_terms & head_terms
            mech = bool(_MECHANICAL_OPENER_RE.match(paras[idx + 1]))
            if not overlap and mech:
                issues.append(
                    _issue(
                        "COH-1",
                        "WARNING",
                        sec,
                        f"{sec.title()} P{idx + 1}->P{idx + 2} opens with a mechanical transition "
                        "and shares zero conceptual bridge terms with the preceding paragraph.",
                        "Replace the generic opener with a Given->New bridge referencing the prior paragraph's concept or mechanism.",
                        filename=filename,
                        slug=slug,
                    )
                )
            elif not overlap and len(tail_terms) >= 5 and len(head_terms) >= 5:
                issues.append(
                    _issue(
                        "COH-1",
                        "INFO",
                        sec,
                        f"{sec.title()} P{idx + 1}->P{idx + 2} shows an abrupt topic shift (0 shared concept terms).",
                        f"Connect P{idx + 2}'s opening sentence back to the closing concept of P{idx + 1}.",
                        filename=filename,
                        slug=slug,
                    )
                )
    return issues


def _check_results_discussion_echo(
    sections: dict[str, str], filename: str, slug: str
) -> list[dict[str, Any]]:
    """COH-2: Catch verbatim copy-paste of Results clauses into Discussion's opening."""
    res_text = sections.get("results", "")
    disc_paras = _paragraphs(sections.get("discussion", ""))
    if not res_text or not disc_paras:
        return []
    shared = _ngrams(res_text, n=8) & _ngrams(" ".join(disc_paras[:2]), n=8)
    if len(shared) < 2:
        return []
    sample = sorted(shared)[0]
    return [
        _issue(
            "COH-2",
            "WARNING",
            "discussion",
            f"Discussion opening repeats {len(shared)} verbatim 8-word clause(s) from Results (e.g., '{sample}').",
            "Open Discussion with scientific interpretation and direct answer to the study aim rather than copying Results sentences.",
            filename=filename,
            slug=slug,
        )
    ]


def _check_terminology_drift(
    sections: dict[str, str],
    canonical_terms: dict[str, list[str]],
    filename: str,
    slug: str,
) -> list[dict[str, Any]]:
    """COH-3: Enforce canonical terminology declared in narrative-thread.yaml."""
    issues: list[dict[str, Any]] = []
    for canonical, variants in canonical_terms.items():
        for variant in variants:
            if not variant or variant.lower() == canonical.lower():
                continue
            pat = re.compile(rf"\b{re.escape(variant)}\b", re.IGNORECASE)
            for sec, body in sections.items():
                if pat.search(body):
                    issues.append(
                        _issue(
                            "COH-3",
                            "WARNING",
                            sec,
                            f"Terminology drift in {sec.title()}: found variant '{variant}' instead of canonical '{canonical}'.",
                            f"Standardize '{variant}' to '{canonical}' across all sections.",
                            filename=filename,
                            slug=slug,
                        )
                    )
    return issues


def analyze_manuscript_coherence(
    project_dir: Path,
    slug: str,
    content: str,
    target_label: str,
) -> dict[str, Any]:
    """Run all COH-1..3 and THR-1..3 checks and return a structured audit dictionary."""
    primary_file = target_label.split(",")[0].strip() or "manuscript.md"
    sections = split_manuscript_sections(content, Path(primary_file).stem)
    thread = NarrativeThreadStore(project_dir).load()

    issues: list[dict[str, Any]] = []
    issues.extend(_check_paragraph_flow(sections, primary_file, slug))
    issues.extend(_check_results_discussion_echo(sections, primary_file, slug))
    issues.extend(
        _check_terminology_drift(sections, thread.get("canonical_terms") or {}, primary_file, slug)
    )
    issues.extend(
        _check_novelty_threading(
            sections, thread.get("novelty_statement") or "", primary_file, slug
        )
    )
    selling_cov, sp_issues = _check_selling_points(
        sections, thread.get("selling_points") or [], primary_file, slug
    )
    issues.extend(sp_issues)
    issues.extend(_check_question_answer_and_abstract(sections, primary_file, slug))

    rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    issues.sort(key=lambda i: (rank.get(i["severity"], 9), i["code"], i["section"]))
    crit = sum(1 for i in issues if i["severity"] == "CRITICAL")
    warn = sum(1 for i in issues if i["severity"] == "WARNING")
    info = sum(1 for i in issues if i["severity"] == "INFO")
    score = max(0, 100 - crit * 25 - warn * 10 - info * 3)

    return {
        "schema": "mdpaper.coherence_audit.v1",
        "status": "clean" if not issues else ("needs_critical_repair" if crit else "needs_polish"),
        "project": slug,
        "target_file": target_label,
        "sections_audited": sorted(sections),
        "coherence_score": score,
        "counts": {"critical": crit, "warning": warn, "info": info, "total": len(issues)},
        "selling_point_coverage": selling_cov,
        "issues": issues[:35],
    }
