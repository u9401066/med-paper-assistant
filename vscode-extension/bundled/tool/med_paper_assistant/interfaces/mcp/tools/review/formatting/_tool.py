"""MCP handler for the ``check_formatting`` tool."""

from typing import Optional

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from ._checklist import SubmissionFlags
from ._runner import run_check_formatting


class FormattingTool:
    """Holds the manuscript services behind the ``check_formatting`` handler."""

    def __init__(self, drafter: Drafter, ref_manager: ReferenceManager) -> None:
        self._drafter = drafter
        self._ref_manager = ref_manager

    def check_formatting(
        self,
        draft_filename: str,
        journal: str = "generic",
        check_submission: bool = False,
        has_cover_letter: bool = False,
        has_ethics: bool = False,
        has_consent: bool = False,
        has_coi: bool = False,
        has_author_contributions: bool = False,
        has_data_availability: bool = False,
        has_keywords: bool = False,
        has_highlights: bool = False,
        project: Optional[str] = None,
    ) -> str:
        """
        Check manuscript formatting, consistency, and submission readiness.

        Combines formatting checks (word limits, abstract, references), consistency
        checks (citations, numbers, abbreviations, p-values), and optionally
        submission checklist verification.

        Args:
            draft_filename: Draft file to check (or comma-separated for multiple)
            journal: Journal code (bja, anesthesiology, jama, nejm, lancet, ccm, medrxiv, jamia, jbi, generic)
            check_submission: Also check submission readiness (required documents/statements)
            has_cover_letter: Cover letter prepared? (used when check_submission=True)
            has_ethics: Ethics approval included?
            has_consent: Informed consent included?
            has_coi: Conflict of interest included?
            has_author_contributions: Author contributions included?
            has_data_availability: Data availability included?
            has_keywords: Keywords included?
            has_highlights: Highlights included?
            project: Project slug (uses current if omitted)
        """
        flags = SubmissionFlags(
            has_cover_letter,
            has_ethics,
            has_consent,
            has_coi,
            has_author_contributions,
            has_data_availability,
            has_keywords,
            has_highlights,
        )
        return run_check_formatting(
            self._drafter,
            self._ref_manager,
            draft_filename,
            journal,
            check_submission,
            flags,
            project,
        )
