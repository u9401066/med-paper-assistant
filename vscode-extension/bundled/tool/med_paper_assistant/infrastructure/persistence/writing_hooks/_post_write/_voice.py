"""Writing Hooks — A3c voice-consistency detector.

Per-paragraph readability metrics:
  - avg_sent_len: average words per sentence
  - avg_word_len: average characters per word (vocabulary sophistication)
  - type_token_ratio: unique words / total words (vocabulary diversity)
  - punct_complexity: (em-dashes + semicolons + parentheses) per 100 words

Outliers are detected using z-scores against the document mean.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from .._models import HookIssue, HookResult
from .._text_utils import strip_markdown_prose

logger = structlog.get_logger()

_METRIC_KEYS = ["avg_sent_len", "avg_word_len", "ttr", "punct_complexity"]


def _paragraph_metrics(index: int, para: str) -> dict[str, Any]:
    sentences = [s.strip() for s in re.split(r"[.!?]+", para) if len(s.strip().split()) >= 3]
    words = para.split()
    n_words = len(words)

    avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0.0
    avg_word_len = sum(len(w) for w in words) / n_words if n_words else 0.0

    # Type-token ratio (vocabulary diversity)
    unique_words = {w.lower().strip(".,;:!?\"'()-") for w in words}
    ttr = len(unique_words) / n_words if n_words else 0.0

    # Punctuation complexity (em-dashes, semicolons, parentheses per 100 words)
    punct_hits = para.count("—") + para.count(";") + para.count("(")
    punct_complexity = punct_hits / n_words * 100 if n_words else 0.0

    return {
        "index": index,
        "word_count": n_words,
        "avg_sent_len": avg_sent_len,
        "avg_word_len": avg_word_len,
        "ttr": ttr,
        "punct_complexity": punct_complexity,
        "preview": para[:80] + ("..." if len(para) > 80 else ""),
    }


def _document_baselines(para_metrics: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    baselines: dict[str, dict[str, float]] = {}
    for key in _METRIC_KEYS:
        values = [m[key] for m in para_metrics]
        n = len(values)
        mean_val = sum(values) / n
        std_val = (sum((v - mean_val) ** 2 for v in values) / n) ** 0.5
        baselines[key] = {"mean": mean_val, "std": std_val}
    return baselines


def _outlier_paragraphs(
    para_metrics: list[dict[str, Any]],
    baselines: dict[str, dict[str, float]],
    outlier_z: float,
) -> list[dict]:
    outliers: list[dict] = []
    for m in para_metrics:
        deviations: dict[str, float] = {}
        for key in _METRIC_KEYS:
            std = baselines[key]["std"]
            if std > 0:
                z = abs(m[key] - baselines[key]["mean"]) / std
                if z > outlier_z:
                    deviations[key] = round(z, 2)
        if deviations:
            outliers.append(
                {
                    "paragraph": m["index"] + 1,
                    "preview": m["preview"],
                    "deviations": deviations,
                }
            )
    return outliers


def _outlier_issues(outliers: list[dict], section: str) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for op in outliers:
        deviation_desc = ", ".join(f"{k}: z={v}" for k, v in op["deviations"].items())
        issues.append(
            HookIssue(
                hook_id="A3c",
                severity="WARNING",
                section=section,
                message=f"Voice break at paragraph {op['paragraph']}: "
                f"style deviates from document baseline ({deviation_desc}). "
                f'Preview: "{op["preview"]}"',
                suggestion="This paragraph's writing style differs from the rest of the "
                "manuscript. A human reviewer may notice this shift. Consider "
                "rewriting to match the document's natural voice (e.g. simplify "
                "vocabulary, vary sentence rhythm, reduce punctuation complexity).",
            )
        )
    return issues


def _sophistication_gap(
    para_metrics: list[dict[str, Any]], section: str
) -> tuple[float, list[HookIssue]]:
    # Sophistication gap: max vs min avg_word_len
    word_lens = [m["avg_word_len"] for m in para_metrics]
    gap = max(word_lens) - min(word_lens) if word_lens else 0.0
    if gap <= 1.2:
        return gap, []
    max_p = word_lens.index(max(word_lens)) + 1
    min_p = word_lens.index(min(word_lens)) + 1
    issue = HookIssue(
        hook_id="A3c",
        severity="WARNING",
        section=section,
        message=f"Large vocabulary sophistication gap between paragraphs: "
        f"P{max_p} avg_word_len={max(word_lens):.2f} vs "
        f"P{min_p} avg_word_len={min(word_lens):.2f} "
        f"(gap={gap:.2f}, threshold >1.2). "
        "This ESL-to-polished-prose pattern is a strong AI signal.",
        suggestion="Ensure vocabulary complexity is consistent throughout. "
        "If some paragraphs use simpler words (author's natural voice), "
        "adjust overly polished paragraphs to match.",
    )
    return gap, [issue]


def _voice_stats(
    para_metrics: list[dict[str, Any]],
    baselines: dict[str, dict[str, float]],
    outliers: list[dict],
    gap: float,
) -> dict[str, Any]:
    return {
        "paragraph_count": len(para_metrics),
        "outlier_count": len(outliers),
        "sophistication_gap": round(gap, 3),
        "baselines": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in baselines.items()},
        "paragraph_scores": [
            {
                "p": m["index"] + 1,
                "words": m["word_count"],
                "avg_sl": round(m["avg_sent_len"], 1),
                "avg_wl": round(m["avg_word_len"], 2),
                "ttr": round(m["ttr"], 3),
                "punct": round(m["punct_complexity"], 2),
            }
            for m in para_metrics
        ],
        "outlier_paragraphs": outliers,
    }


def _split_paragraphs(prose: str) -> list[str]:
    # min 20 words to exclude headers/stubs
    return [p.strip() for p in re.split(r"\n\s*\n", prose) if len(p.strip().split()) >= 20]


class VoiceConsistencyHooksMixin:
    """A3c: voice consistency across paragraphs."""

    def check_voice_consistency(
        self,
        content: str,
        section: str = "manuscript",
        outlier_z: float = 1.8,
    ) -> HookResult:
        """
        Hook A3c: Detect voice consistency breaks across paragraphs.

        Flags paragraphs whose style deviates significantly from the document
        baseline (see module docstring for the per-paragraph metrics). Catches
        the #1 risk for human reviewers: ESL paragraphs suddenly switching to
        polished corporate-academic prose.

        Args:
            content: Full manuscript or section text.
            section: Section name for reporting.
            outlier_z: Z-score threshold for flagging (default 1.8).
        """
        prose = strip_markdown_prose(content)
        paragraphs = _split_paragraphs(prose)
        if len(paragraphs) < 4:
            return HookResult(
                hook_id="A3c",
                passed=True,
                issues=[],
                stats={"skipped": True, "reason": "too_few_paragraphs"},
            )

        para_metrics = [_paragraph_metrics(i, para) for i, para in enumerate(paragraphs)]
        baselines = _document_baselines(para_metrics)

        outliers = _outlier_paragraphs(para_metrics, baselines, outlier_z)
        issues = _outlier_issues(outliers, section)
        gap, gap_issues = _sophistication_gap(para_metrics, section)
        issues.extend(gap_issues)

        passed = len(issues) == 0
        stats = _voice_stats(para_metrics, baselines, outliers, gap)
        logger.info(
            "Hook A3c complete",
            passed=passed,
            outlier_count=len(outliers),
            sophistication_gap=round(gap, 3),
        )
        return HookResult(hook_id="A3c", passed=passed, issues=issues, stats=stats)
