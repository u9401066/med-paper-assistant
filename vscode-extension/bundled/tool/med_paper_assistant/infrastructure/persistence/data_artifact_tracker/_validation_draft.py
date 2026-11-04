"""Data Artifact Tracker — draft cross-reference checks and summary for validation."""

from __future__ import annotations

import re
from typing import Any

from ._review import _ReviewMixin
from ._validation_checks import issue

_STAT_PATTERNS = [
    r"p\s*[<>=]\s*0\.\d+",
    r"p\s*-\s*value",
    r"statistically\s+significant",
    r"CI\s*[:\s]*\d+",
    r"odds\s+ratio",
    r"hazard\s+ratio",
    r"relative\s+risk",
]


def _caption_issues(
    tracker: _ReviewMixin,
    entries: list[dict[str, Any]],
    asset_type: str,
    label: str,
) -> list[dict[str, str]]:
    """Manifest entries also need review receipts for caption trustworthiness."""
    issues: list[dict[str, str]] = []
    for entry in entries:
        fname = entry.get("filename")
        if not fname:
            continue
        asset_path = f"results/{asset_type}s/{fname}"
        ok, detail = tracker.review_satisfies_caption(
            asset_path,
            str(entry.get("caption", "")),
            asset_type=asset_type,
        )
        if not ok:
            issues.append(
                issue(
                    "CRITICAL",
                    "caption_unreviewed",
                    f"{label} {entry.get('number')} caption is not backed by a matching review receipt: {detail}",
                )
            )
    return issues


def _phantom_reference_issues(label: str, refs: set[str]) -> list[dict[str, str]]:
    return [
        issue(
            "CRITICAL",
            "phantom_reference",
            f"Draft references '{label} {ref}' but no such entry in manifest",
        )
        for ref in refs
    ]


def _orphan_asset_issues(label: str, numbers: set[str]) -> list[dict[str, str]]:
    return [
        issue(
            "WARNING",
            "orphan_asset",
            f"{label} {num} is in manifest but never referenced in draft",
        )
        for num in numbers
    ]


def _unverified_stats_issues(
    draft_content: str, artifacts: list[dict[str, Any]]
) -> list[dict[str, str]]:
    has_stat_claims = any(re.search(pat, draft_content, re.IGNORECASE) for pat in _STAT_PATTERNS)
    stat_artifacts = [a for a in artifacts if a.get("artifact_type") == "statistics"]
    if has_stat_claims and not stat_artifacts:
        return [
            issue(
                "CRITICAL",
                "unverified_stats",
                "Draft contains statistical claims but no statistical test artifacts recorded",
            )
        ]
    return []


def check_draft_references(
    tracker: _ReviewMixin,
    draft_content: str,
    manifest: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Check 5: draft Figure/Table references map to manifest entries and reviews."""
    fig_refs = set(re.findall(r"Figure\s+(\d+)", draft_content, re.IGNORECASE))
    tbl_refs = set(re.findall(r"Table\s+(\d+)", draft_content, re.IGNORECASE))

    manifest_fig_nums = {str(e.get("number")) for e in manifest.get("figures", [])}
    manifest_tbl_nums = {str(e.get("number")) for e in manifest.get("tables", [])}

    issues = _phantom_reference_issues("Figure", fig_refs - manifest_fig_nums)
    issues.extend(_caption_issues(tracker, manifest.get("figures", []), "figure", "Figure"))
    issues.extend(_caption_issues(tracker, manifest.get("tables", []), "table", "Table"))
    issues.extend(_phantom_reference_issues("Table", tbl_refs - manifest_tbl_nums))
    issues.extend(_orphan_asset_issues("Figure", manifest_fig_nums - fig_refs))
    issues.extend(_orphan_asset_issues("Table", manifest_tbl_nums - tbl_refs))
    issues.extend(_unverified_stats_issues(draft_content, artifacts))
    return issues


def build_validation_result(
    issues: list[dict[str, str]],
    artifacts: list[dict[str, Any]],
    data_anchors: list[dict[str, Any]],
    manifest_figures: dict[Any, Any],
    manifest_tables: dict[Any, Any],
) -> dict[str, Any]:
    """Assemble the pass/fail result with summary counts."""
    critical_count = sum(1 for i in issues if i["severity"] == "CRITICAL")
    warning_count = sum(1 for i in issues if i["severity"] == "WARNING")

    return {
        "passed": critical_count == 0,
        "issues": issues,
        "summary": {
            "total_artifacts": len(artifacts),
            "figures_tracked": len([a for a in artifacts if a["artifact_type"] == "figure"]),
            "tables_tracked": len([a for a in artifacts if a["artifact_type"] == "table"]),
            "stats_tracked": len([a for a in artifacts if a["artifact_type"] == "statistics"]),
            "data_anchors": len(data_anchors),
            "critical_issues": critical_count,
            "warning_issues": warning_count,
            "manifest_figures": len(manifest_figures),
            "manifest_tables": len(manifest_tables),
        },
    }
