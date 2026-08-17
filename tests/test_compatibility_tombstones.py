"""Keep intentional compatibility tombstones explicit and inert."""

from __future__ import annotations

import importlib

import pytest

COMPATIBILITY_TOMBSTONES = {
    "med_paper_assistant.application.use_cases.save_reference": (
        "legacy save-reference imports; runtime moved to the reference manager"
    ),
    "med_paper_assistant.interfaces.mcp.tools.review.response": (
        "legacy reviewer-response imports; workflow moved to the submission skill"
    ),
}


@pytest.mark.parametrize("module_name", COMPATIBILITY_TOMBSTONES)
def test_compatibility_tombstone_is_documented_and_inert(module_name: str) -> None:
    module = importlib.import_module(module_name)
    doc = (module.__doc__ or "").lower()
    public_names = {name for name in vars(module) if not name.startswith("_")}

    assert "tombstone" in doc or "stub" in doc
    assert public_names == set()


def test_removed_orphans_are_not_reintroduced() -> None:
    project_context = importlib.import_module(
        "med_paper_assistant.interfaces.mcp.tools._shared.project_context"
    )
    submission = importlib.import_module(
        "med_paper_assistant.interfaces.mcp.tools.review.submission"
    )

    for name in (
        "ProjectContextError",
        "get_current_project_info",
        "format_project_context_error",
    ):
        assert not hasattr(project_context, name)
    for name in ("ChecklistItem", "SubmissionChecklist"):
        assert not hasattr(submission, name)
