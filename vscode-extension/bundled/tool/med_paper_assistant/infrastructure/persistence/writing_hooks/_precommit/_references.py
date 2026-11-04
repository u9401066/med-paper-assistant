"""Writing Hooks — P7 reference-integrity check."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from med_paper_assistant.shared.doi import validate_doi

from .._models import HookIssue, HookResult

logger = structlog.get_logger()


@dataclass
class _ReferenceScan:
    total_refs: int = 0
    verified_count: int = 0
    unverified_refs: list[str] = field(default_factory=list)
    doi_present: int = 0
    doi_valid: int = 0
    malformed_dois: list[tuple[str, str, str]] = field(default_factory=list)


def _check_doi(ref_name: str, meta: dict[str, Any], scan: _ReferenceScan) -> None:
    # Offline DOI syntactic validation: only when a DOI is present.
    # Not every legitimate reference has a DOI (books, older papers,
    # PubMed-verified items), so a missing DOI is never an error here
    # — but a *malformed* DOI is a blocking error because it will fail
    # at peer review or break reference resolution.
    raw_doi = str(meta.get("doi") or meta.get("DOI") or "").strip()
    if not raw_doi:
        return
    scan.doi_present += 1
    ok, _normalized, reason = validate_doi(raw_doi)
    if ok:
        scan.doi_valid += 1
    else:
        scan.malformed_dois.append((ref_name, raw_doi, reason))


def _scan_reference_dir(ref_dir: Path, scan: _ReferenceScan) -> None:
    scan.total_refs += 1
    metadata_path = ref_dir / "metadata.json"
    if not metadata_path.is_file():
        scan.unverified_refs.append(ref_dir.name)
        return
    try:
        with open(metadata_path, encoding="utf-8") as f:
            meta = json.load(f)
        data_source = meta.get("_data_source", "")
        if data_source == "pubmed_api" or meta.get("verified", False):
            scan.verified_count += 1
        else:
            scan.unverified_refs.append(ref_dir.name)
        _check_doi(ref_dir.name, meta, scan)
    except Exception:
        scan.unverified_refs.append(ref_dir.name)


def _malformed_doi_issue(ref_name: str, raw_doi: str, reason: str) -> HookIssue:
    return HookIssue(
        hook_id="P7",
        severity="CRITICAL",
        section="references",
        message=f"Reference '{ref_name}' has a malformed DOI '{raw_doi}' ({reason})",
        location=ref_name,
        suggestion=(
            "Fix the DOI to the canonical 10.<registrant>/<suffix> form, "
            "or remove it if no valid DOI exists"
        ),
    )


def _unverified_issue(ref_name: str) -> HookIssue:
    return HookIssue(
        hook_id="P7",
        severity="WARNING",
        section="references",
        message=f"Reference '{ref_name}' is not verified (not from PubMed API)",
        suggestion="Re-save with save_reference_mcp for verified metadata",
    )


def _reference_issues(scan: _ReferenceScan) -> list[HookIssue]:
    # CRITICAL: malformed DOIs must be fixed before the final paper.
    issues = [_malformed_doi_issue(*entry) for entry in scan.malformed_dois]
    issues.extend(_unverified_issue(name) for name in scan.unverified_refs)
    return issues


def _reference_stats(scan: _ReferenceScan) -> dict[str, Any]:
    return {
        "total_refs": scan.total_refs,
        "verified_count": scan.verified_count,
        "unverified_count": len(scan.unverified_refs),
        "unverified_refs": scan.unverified_refs[:10],
        "doi_present": scan.doi_present,
        "doi_valid": scan.doi_valid,
        "doi_malformed": len(scan.malformed_dois),
        "malformed_dois": [name for name, _raw, _reason in scan.malformed_dois[:10]],
    }


class ReferenceIntegrityHooksMixin:
    """P7: saved references must carry verified PubMed metadata and well-formed DOIs."""

    _project_dir: Path

    def check_reference_integrity(
        self,
        content: str | None = None,
    ) -> HookResult:
        """
        Hook P7: Verify saved references have VERIFIED status.

        Checks that each reference directory under references/ has valid
        metadata.json with _data_source == "pubmed_api" or verified == True.
        """
        refs_dir = self._project_dir / "references"
        if not refs_dir.is_dir():
            return HookResult(
                hook_id="P7",
                passed=True,
                stats={"note": "No references directory found"},
            )

        scan = _ReferenceScan()
        for ref_dir in sorted(refs_dir.iterdir()):
            if ref_dir.is_dir():
                _scan_reference_dir(ref_dir, scan)

        issues = _reference_issues(scan)
        passed = len(issues) == 0
        stats = _reference_stats(scan)

        logger.info(
            "Hook P7 complete",
            passed=passed,
            verified=scan.verified_count,
            total=scan.total_refs,
            doi_malformed=len(scan.malformed_dois),
        )
        return HookResult(hook_id="P7", passed=passed, issues=issues, stats=stats)
