"""Orchestration for the ``check_formatting`` tool."""

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from ..._shared import log_tool_call, log_tool_result, resolve_project_context
from ..submission import JOURNAL_REQUIREMENTS
from ._analysis import analyze_manuscript
from ._checklist import SubmissionFlags, build_submission_items
from ._drafts import read_drafts
from ._report import count_severities, render_report


def run_check_formatting(
    drafter: Drafter,
    ref_manager: ReferenceManager,
    draft_filename: str,
    journal: str,
    check_submission: bool,
    flags: SubmissionFlags,
    project: str | None,
) -> str:
    log_tool_call(
        "check_formatting",
        {
            "draft_filename": draft_filename,
            "journal": journal,
            "check_submission": check_submission,
        },
    )

    _project_info, workflow_error = resolve_project_context(
        project,
        required_mode="manuscript",
    )
    if workflow_error:
        return workflow_error

    journal_key = journal.lower().replace(" ", "_").replace("-", "_")
    reqs = JOURNAL_REQUIREMENTS.get(journal_key, JOURNAL_REQUIREMENTS["generic"])
    filenames = [f.strip() for f in draft_filename.split(",") if f.strip()]
    all_content, read_error = read_drafts(filenames, drafter)
    if read_error:
        return read_error

    issues, passes, medrxiv_report = analyze_manuscript(all_content, reqs, journal_key, ref_manager)
    submission_items = build_submission_items(reqs, check_submission, flags)
    counts = count_severities(issues)
    output = render_report(
        journal_key, filenames, reqs, passes, issues, submission_items, medrxiv_report, counts
    )
    error_count, warning_count, _info_count = counts

    log_tool_result(
        "check_formatting",
        f"errors={error_count}, warnings={warning_count}",
        success=error_count == 0,
    )
    return output
