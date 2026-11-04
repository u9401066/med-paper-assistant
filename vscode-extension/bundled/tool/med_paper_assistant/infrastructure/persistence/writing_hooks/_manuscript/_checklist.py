"""Writing Hooks — C2 submission checklist."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()

# Map document types to file patterns and content patterns
_DOC_CHECKS: dict[str, dict] = {
    "cover_letter": {
        "files": ["cover-letter.md", "cover_letter.md", "cover-letter.docx"],
        "content_pattern": None,
    },
    "highlights": {
        "files": ["highlights.md", "highlights.txt"],
        "content_pattern": r"(?i)(?:highlight|key\s*finding)",
    },
    "graphical_abstract": {
        "files": [
            "graphical-abstract.png",
            "graphical-abstract.jpg",
            "graphical-abstract.pdf",
            "graphical_abstract.*",
        ],
        "content_pattern": None,
    },
    "author_contributions": {
        "files": [],
        "content_pattern": r"(?i)(?:author\s*contribution|CRediT|contributor)",
    },
    "conflict_of_interest": {
        "files": [],
        "content_pattern": r"(?i)(?:conflict\s*of\s*interest|competing\s*interest|disclosure|COI)",
    },
    "funding_statement": {
        "files": [],
        "content_pattern": r"(?i)(?:funding|grant|financial\s*support|supported\s*by)",
    },
    "ethics_statement": {
        "files": [],
        "content_pattern": r"(?i)(?:ethic|IRB|institutional\s*review\s*board|informed\s*consent|Helsinki)",
    },
    "data_availability": {
        "files": [],
        "content_pattern": r"(?i)(?:data\s*availab|data\s*sharing|data\s*access)",
    },
}


def _document_file_exists(project_dir: Path, patterns: list[str]) -> bool:
    file_found = False
    for pattern in patterns:
        if "*" in pattern:
            file_found = bool(list(project_dir.glob(pattern)))
        else:
            file_found = (project_dir / pattern).is_file()
        if file_found:
            break
    return file_found


def _document_present(project_dir: Path, check: dict, content: str) -> bool:
    if _document_file_exists(project_dir, check["files"]):
        return True
    return bool(
        check["content_pattern"] and content and re.search(check["content_pattern"], content)
    )


def _missing_document_issue(doc_type: str) -> HookIssue:
    return HookIssue(
        hook_id="C2",
        severity="WARNING",
        section="submission",
        message=f"Required document '{doc_type}' not found",
        suggestion=(
            f"Add {doc_type.replace('_', ' ')} to the manuscript or "
            f"create a separate file in the project directory"
        ),
    )


def _skipped_result(note: str) -> HookResult:
    return HookResult(hook_id="C2", passed=True, stats={"note": note})


class SubmissionChecklistHooksMixin:
    """C2: required submission documents."""

    def _audit_required_documents(
        self, required_docs: dict[str, Any], content: str
    ) -> tuple[int, list[str], list[str], list[HookIssue]]:
        checked = 0
        missing: list[str] = []
        found: list[str] = []
        issues: list[HookIssue] = []

        for doc_type, is_required in required_docs.items():
            # Skip non-boolean or false entries
            if isinstance(is_required, dict):
                is_required = is_required.get("required", False)
            if not is_required:
                continue

            checked += 1
            check = _DOC_CHECKS.get(doc_type)
            if not check:
                continue

            if _document_present(self._project_dir, check, content):
                found.append(doc_type)
            else:
                missing.append(doc_type)
                issues.append(_missing_document_issue(doc_type))
        return checked, found, missing, issues

    def check_submission_checklist(self, content: str) -> HookResult:
        """Hook C2: Verify required submission documents exist.

        Code-Enforced check that reads journal-profile.yaml required_documents
        and verifies each required item is present in the project directory
        or mentioned in the manuscript content.

        Previously Agent-Driven (relied on Agent reading SKILL.md).
        Now partially Code-Enforced for weak model resilience.

        Args:
            content: Full manuscript text.
        """
        if not self._journal_profile:
            return _skipped_result("No journal-profile.yaml — skipping checklist")

        required_docs = self._journal_profile.get("required_documents", {})
        if not required_docs:
            return _skipped_result("No required_documents in journal profile")

        checked, found, missing, issues = self._audit_required_documents(required_docs, content)

        passed = len(missing) == 0
        stats = {
            "required_count": checked,
            "found_count": len(found),
            "missing_count": len(missing),
            "missing_docs": missing,
            "found_docs": found,
        }

        logger.info(
            "Hook C2 (Submission Checklist) complete",
            passed=passed,
            found=len(found),
            missing=len(missing),
        )
        return HookResult(hook_id="C2", passed=passed, issues=issues, stats=stats)
