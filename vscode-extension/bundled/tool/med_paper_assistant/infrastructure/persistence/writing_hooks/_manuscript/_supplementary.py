"""Writing Hooks — C9 supplementary material cross-references."""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()

_SUPP_PATTERNS = [
    (r"[Ss]upplementary\s+(?:Table|Tbl\.?)\s+(\w+)", "Supplementary Table"),
    (r"[Ss]upplementary\s+(?:Figure|Fig\.?)\s+(\w+)", "Supplementary Figure"),
    (
        r"[Ss]upplementary\s+(?:Material|Data|File|Appendix)\s+(\w+)",
        "Supplementary Material",
    ),
    (r"[Ss]\d+\s+(?:Table|Fig)", "S-prefix reference"),
    (r"\bAppendix\s+([A-Z]\d*|S\d+|\d+)\b", "Appendix"),
    (r"[Oo]nline\s+[Ss]upplement(?:ary)?\s+(\w+)", "Online Supplement"),
    (r"e(?:Table|Figure|Appendix)\s*(\d+)", "e-prefix reference"),
]


def _collect_text_refs(content: str) -> dict[str, list[str]]:
    text_refs: dict[str, list[str]] = {}
    for pattern, ref_type in _SUPP_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            text_refs.setdefault(ref_type, []).extend(matches)
    return text_refs


def _collect_supp_files(project_dir: Path) -> set[str]:
    supp_files: set[str] = set()
    for supp_dir in (project_dir / "supplementary", project_dir / "exports" / "supplementary"):
        if supp_dir.is_dir():
            for f in supp_dir.rglob("*"):
                if f.is_file():
                    supp_files.add(f.name)
    return supp_files


def _no_files_issue(total_refs: int, text_refs: dict[str, list[str]]) -> HookIssue:
    return HookIssue(
        hook_id="C9",
        severity="CRITICAL",
        section="Supplementary",
        message=(
            f"Main text references {total_refs} supplementary item(s) "
            f"but no supplementary files exist"
        ),
        location=", ".join(f"{rtype} {', '.join(ids[:3])}" for rtype, ids in text_refs.items()),
        suggestion="Create supplementary files in 'supplementary/' directory, or remove references from main text",
    )


def _unmatched_ref_issues(text_refs: dict[str, list[str]], supp_files: set[str]) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for ref_type, ids in text_refs.items():
        for ref_id in ids:
            ref_escaped = re.escape(ref_id.lower())
            has_match = any(
                re.search(rf"(?:^|[_\-.]){ref_escaped}(?:[_\-.]|$)", fname.lower())
                for fname in supp_files
            )
            if not has_match:
                issues.append(
                    HookIssue(
                        hook_id="C9",
                        severity="WARNING",
                        section="Supplementary",
                        message=f"'{ref_type} {ref_id}' referenced in text but no matching supplementary file found",
                        suggestion=f"Create supplementary file for {ref_type} {ref_id}, or verify the reference identifier",
                    )
                )
    return issues


class SupplementaryHooksMixin:
    """C9: supplementary material cross-references."""

    def check_supplementary_crossref(
        self,
        content: str,
    ) -> HookResult:
        """Hook C9: Verify supplementary material cross-references."""
        issues: list[HookIssue] = []

        text_refs = _collect_text_refs(content)
        supp_files = _collect_supp_files(self._project_dir)

        total_refs = sum(len(v) for v in text_refs.values())
        if total_refs > 0 and not supp_files:
            issues.append(_no_files_issue(total_refs, text_refs))

        if supp_files and total_refs > 0:
            issues.extend(_unmatched_ref_issues(text_refs, supp_files))

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "text_references": total_refs,
            "supplementary_files": len(supp_files),
            "reference_types": {k: len(v) for k, v in text_refs.items()},
        }

        logger.info(
            "Hook C9 complete",
            passed=passed,
            text_refs=total_refs,
            supp_files=len(supp_files),
        )
        return HookResult(hook_id="C9", passed=passed, issues=issues, stats=stats)
