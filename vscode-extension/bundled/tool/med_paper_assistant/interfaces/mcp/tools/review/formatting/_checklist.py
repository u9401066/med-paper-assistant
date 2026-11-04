"""Submission checklist items for the formatting check."""

from typing import Any, NamedTuple


class SubmissionFlags(NamedTuple):
    """Which submission documents/statements the author reports as ready."""

    has_cover_letter: bool
    has_ethics: bool
    has_consent: bool
    has_coi: bool
    has_author_contributions: bool
    has_data_availability: bool
    has_keywords: bool
    has_highlights: bool


def _document_items(reqs: dict[str, Any], flags: SubmissionFlags) -> list[dict[str, str]]:
    """Cover letter, highlights, ethics approval and informed consent."""
    submission_items: list[dict[str, str]] = []
    if reqs.get("cover_letter"):
        submission_items.append(
            {
                "item": "Cover letter",
                "status": "pass" if flags.has_cover_letter else "fail",
                "detail": "" if flags.has_cover_letter else "Required for this journal",
            }
        )
    if reqs.get("highlights"):
        submission_items.append(
            {
                "item": "Highlights/Key Points",
                "status": "pass" if flags.has_highlights else "fail",
                "detail": "" if flags.has_highlights else "Required for this journal",
            }
        )
    if reqs.get("ethics_statement"):
        submission_items.append(
            {
                "item": "Ethics approval",
                "status": "pass" if flags.has_ethics else "fail",
                "detail": "" if flags.has_ethics else "Include IRB/Ethics approval number",
            }
        )
    submission_items.append(
        {
            "item": "Informed consent",
            "status": "pass" if flags.has_consent else "warning",
            "detail": "" if flags.has_consent else "Verify consent statement",
        }
    )
    return submission_items


def _statement_items(reqs: dict[str, Any], flags: SubmissionFlags) -> list[dict[str, str]]:
    """Conflict of interest, author contributions, data availability and keywords."""
    submission_items: list[dict[str, str]] = []
    if reqs.get("conflict_of_interest"):
        submission_items.append(
            {
                "item": "Conflict of interest",
                "status": "pass" if flags.has_coi else "fail",
                "detail": "" if flags.has_coi else "Required — even if 'None'",
            }
        )
    if reqs.get("author_contributions"):
        submission_items.append(
            {
                "item": "Author contributions",
                "status": "pass" if flags.has_author_contributions else "fail",
                "detail": "" if flags.has_author_contributions else "Use CRediT taxonomy",
            }
        )
    if reqs.get("data_availability"):
        submission_items.append(
            {
                "item": "Data availability",
                "status": "pass" if flags.has_data_availability else "fail",
                "detail": ""
                if flags.has_data_availability
                else "State if data available on request",
            }
        )
    if reqs.get("keywords"):
        submission_items.append(
            {
                "item": "Keywords",
                "status": "pass" if flags.has_keywords else "warning",
                "detail": f"Required: {reqs['keywords']}" if not flags.has_keywords else "",
            }
        )
    return submission_items


def build_submission_items(
    reqs: dict[str, Any], check_submission: bool, flags: SubmissionFlags
) -> list[dict[str, str]]:
    """Build the submission checklist (empty unless ``check_submission`` is set)."""
    if not check_submission:
        return []
    return _document_items(reqs, flags) + _statement_items(reqs, flags)
