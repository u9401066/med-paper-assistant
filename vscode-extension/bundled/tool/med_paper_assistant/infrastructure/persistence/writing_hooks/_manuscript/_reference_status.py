"""Writing Hooks — C5 wikilink resolvability and C10 reference fulltext status."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from med_paper_assistant.domain.services.citation_converter import (
    extract_reference_wikilink_keys,
)

from .._models import HookIssue, HookResult

logger = structlog.get_logger()


def _existing_reference_names(refs_dir: Path) -> set[str]:
    existing_refs: set[str] = set()
    if refs_dir.is_dir():
        for entry in refs_dir.iterdir():
            if entry.is_dir():
                existing_refs.add(entry.name)
            elif entry.is_file() and entry.suffix.lower() == ".md":
                existing_refs.add(entry.stem)
    return existing_refs


def _is_resolved(wikilink: str, existing_refs: set[str]) -> bool:
    if wikilink in existing_refs:
        return True
    pmid_match = re.search(r"(\d{7,8})", wikilink)
    if pmid_match:
        pmid = pmid_match.group(1)
        return any(pmid in ref_name for ref_name in existing_refs)
    return False


def _load_metadata(meta_path: Path) -> dict[str, Any] | None:
    if not meta_path.is_file():
        return None
    try:
        meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return meta


def _audit_reference(
    ref_key: str, refs_dir: Path, issues: list[HookIssue]
) -> tuple[bool, bool] | None:
    """Return (ingested, analyzed) for a cited reference, or None if metadata is unusable."""
    meta = _load_metadata(refs_dir / ref_key / "metadata.json")
    if meta is None:
        return None

    ingested = bool(meta.get("fulltext_ingested", False))
    if not ingested:
        reason = meta.get("fulltext_unavailable_reason", "not attempted")
        issues.append(
            HookIssue(
                hook_id="C10",
                severity="WARNING",
                section="References",
                message=f"Reference [[{ref_key}]] cited without fulltext ingestion",
                location=ref_key,
                suggestion=f"Run asset-aware fulltext ingestion or note reason: {reason}",
            )
        )

    analyzed = bool(meta.get("analysis_completed", False))
    if not analyzed:
        issues.append(
            HookIssue(
                hook_id="C10",
                severity="WARNING",
                section="References",
                message=f"Reference [[{ref_key}]] cited without subagent analysis",
                location=ref_key,
                suggestion="Run get_reference_for_analysis → subagent → save_reference_analysis before citing",
            )
        )
    return ingested, analyzed


def _fulltext_stats(
    total_cited: int,
    ingested: int,
    not_ingested: int,
    analyzed: int,
    not_analyzed: int,
    missing_metadata: int,
) -> dict[str, Any]:
    total = ingested + not_ingested + missing_metadata
    return {
        "total_cited": total_cited,
        "fulltext_ingested": ingested,
        "fulltext_missing": not_ingested,
        "analysis_completed": analyzed,
        "analysis_missing": not_analyzed,
        "metadata_missing": missing_metadata,
        "fulltext_pct": round(ingested / total * 100, 1) if total > 0 else 0,
        "analysis_pct": round(analyzed / total * 100, 1) if total > 0 else 0,
    }


class ReferenceStatusHooksMixin:
    """C5 / C10: cited references must exist and carry fulltext + analysis."""

    # ── Hook C5: Wikilink Resolvable ───────────────────────────────

    def check_wikilink_resolvable(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C5: Verify all wikilinks resolve to saved references.
        """
        issues: list[HookIssue] = []

        reference_keys = extract_reference_wikilink_keys(content)
        if not reference_keys:
            return HookResult(
                hook_id="C5",
                passed=True,
                stats={"total_reference_wikilinks": 0, "resolved": 0, "unresolved": 0},
            )

        existing_refs = _existing_reference_names(self._project_dir / "references")

        resolved = 0
        unresolved = 0

        for wl in reference_keys:
            if _is_resolved(wl, existing_refs):
                resolved += 1
                continue
            unresolved += 1
            issues.append(
                HookIssue(
                    hook_id="C5",
                    severity="CRITICAL",
                    section="manuscript",
                    message=f"Wikilink [[{wl}]] cannot be resolved to a saved reference",
                    suggestion="Save this reference with save_reference_mcp or fix the wikilink",
                )
            )

        passed = unresolved == 0
        stats = {
            "total_wikilinks": len(reference_keys),
            "total_reference_wikilinks": len(reference_keys),
            "resolved": resolved,
            "unresolved": unresolved,
        }

        logger.info("Hook C5 complete", passed=passed, unresolved=unresolved)
        return HookResult(hook_id="C5", passed=passed, issues=issues, stats=stats)

    # ── Hook C10: Reference Fulltext Verification ──────────────────

    def check_reference_fulltext_status(
        self,
        content: str,
    ) -> HookResult:
        """
        C10: Verify that cited references have fulltext + analysis status.
        """
        issues: list[HookIssue] = []

        unique_refs = set(extract_reference_wikilink_keys(content))

        if not unique_refs:
            return HookResult(
                hook_id="C10",
                passed=True,
                stats={"note": "No wikilink citations found"},
            )

        refs_dir = self._project_dir / "references"
        ingested = 0
        not_ingested = 0
        analyzed = 0
        not_analyzed = 0
        missing_metadata = 0

        for ref_key in sorted(unique_refs):
            status = _audit_reference(ref_key, refs_dir, issues)
            if status is None:
                missing_metadata += 1
                continue
            is_ingested, is_analyzed = status
            ingested += is_ingested
            not_ingested += not is_ingested
            analyzed += is_analyzed
            not_analyzed += not is_analyzed

        stats = _fulltext_stats(
            len(unique_refs), ingested, not_ingested, analyzed, not_analyzed, missing_metadata
        )

        passed = not_ingested == 0 and missing_metadata == 0 and not_analyzed == 0
        logger.info(
            "Hook C10 (Reference Fulltext+Analysis) complete",
            passed=passed,
            ingested=ingested,
            analyzed=analyzed,
            missing_fulltext=not_ingested,
            missing_analysis=not_analyzed,
        )
        return HookResult(hook_id="C10", passed=passed, issues=issues, stats=stats)
