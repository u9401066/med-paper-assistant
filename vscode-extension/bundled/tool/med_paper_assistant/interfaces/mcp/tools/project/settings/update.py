"""Handlers that update project settings and authors."""

import json
from typing import Any

import structlog

from med_paper_assistant.domain.value_objects.author import Author, generate_author_block
from med_paper_assistant.infrastructure.persistence import ProjectManager
from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES

from .._deps import PROJECT_MANAGER


def update_project_settings(
    paper_type: str = "",
    workflow_mode: str = "",
    target_journal: str = "",
    interaction_style: str = "",
    language_preference: str = "",
    writing_style: str = "",
    graph_views_json: str = "",
    memo: str = "",
    status: str = "",
    citation_style: str = "",
) -> str:
    """
    Update project settings (paper type, status, preferences, citation style, memo).

    Args:
        paper_type: Paper type (use get_paper_types)
        workflow_mode: manuscript|library-wiki
        target_journal: Target journal
        interaction_style: AI interaction style
        language_preference: Language notes
        writing_style: Writing style notes
        graph_views_json: JSON array describing custom Foam graph views
        memo: Project notes/reminders
        status: Project status (concept|drafting|review|submitted|published)
        citation_style: Citation style (vancouver|apa|harvard|nature|ama)
    """
    project_manager = PROJECT_MANAGER.get()
    interaction_preferences = _build_interaction_preferences(
        interaction_style, language_preference, writing_style
    )

    # Handle status update
    if status:
        status_result = project_manager.update_project_status(status)
        if not status_result.get("success"):
            return f"❌ Error updating status: {status_result.get('error', 'Unknown error')}"

    # Handle citation style update
    if citation_style:
        _apply_citation_style(citation_style)
        # Also save to project settings
        interaction_preferences["citation_style"] = citation_style

    settings_payload, parse_error = _parse_graph_views(graph_views_json)
    if parse_error:
        return parse_error

    result = project_manager.update_project_settings(
        paper_type=paper_type if paper_type else None,
        workflow_mode=workflow_mode if workflow_mode else None,
        target_journal=target_journal if target_journal else None,
        interaction_preferences=interaction_preferences if interaction_preferences else None,
        memo=memo if memo else None,
        settings=settings_payload,
    )

    if result.get("success"):
        return _render_updated_settings(project_manager, result.get("updated_fields", []))
    else:
        return f"❌ Error: {result.get('error', 'Unknown error')}"


def _build_interaction_preferences(
    interaction_style: str, language_preference: str, writing_style: str
) -> dict[str, str]:
    interaction_preferences: dict[str, str] = {}
    if interaction_style:
        interaction_preferences["interaction_style"] = interaction_style
    if language_preference:
        interaction_preferences["language"] = language_preference
    if writing_style:
        interaction_preferences["writing_style"] = writing_style
    return interaction_preferences


def _apply_citation_style(citation_style: str) -> None:
    try:
        from med_paper_assistant.infrastructure.services import get_drafter

        drafter = get_drafter()
        drafter.set_citation_style(citation_style)
    except Exception:  # nosec B110 - Citation style is best-effort
        structlog.get_logger().debug("Citation style update failed (best-effort)", exc_info=True)


def _parse_graph_views(graph_views_json: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(settings_payload, error_message)`` for the custom graph views input."""
    if not graph_views_json.strip():
        return None, None
    try:
        parsed_graph_views = json.loads(graph_views_json)
    except json.JSONDecodeError as exc:
        return None, f"❌ Error parsing graph_views_json: {exc}"

    if not isinstance(parsed_graph_views, list):
        return None, "❌ graph_views_json must be a JSON array of view specifications."

    return {"custom_graph_views": parsed_graph_views}, None


def _render_updated_settings(project_manager: ProjectManager, updated: list[str]) -> str:
    # Get current project info for display
    info = project_manager.get_project_info()
    prefs = info.get("interaction_preferences", {})
    settings = info.get("settings", {})
    custom_graph_views = settings.get("custom_graph_views", [])
    current_workflow_mode = info.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
    workflow_name = WORKFLOW_MODES.get(current_workflow_mode, {}).get("name", current_workflow_mode)

    output = f"""✅ Project Settings Updated!

**Updated Fields:** {", ".join(updated)}

## Current Settings

| Setting | Value |
|---------|-------|
| Workflow Mode | {workflow_name} |
| Paper Type | {info.get("paper_type", "Not set")} |
| Target Journal | {info.get("target_journal", "Not set")} |

## Interaction Preferences
- **Style:** {prefs.get("interaction_style", "Not set")}
- **Language:** {prefs.get("language", "Not set")}
- **Writing:** {prefs.get("writing_style", "Not set")}

## Foam Graph Views
- **Custom Views:** {len(custom_graph_views)}

## Memo
{info.get("memo", "[No memo]")}

---
These settings are saved in `project.json` and `.memory/activeContext.md`
"""
    return output


def update_authors(authors_json: str) -> str:
    """
    Set or update the author list for the current project.

    Each author entry can be a name string or a structured object.
    Structured format supports affiliations, ORCID, email, and
    corresponding author flag.

    Args:
        authors_json: JSON array of authors. Examples:
            Simple: '["Author One", "Author Two"]'
            Structured: '[{"name": "Tz-Ping Gau", "affiliations": ["Dept of Anesthesiology, Kaohsiung Medical University Hospital, Kaohsiung, Taiwan"], "orcid": "0000-0001-2345-6789", "email": "gau@example.com", "is_corresponding": true, "order": 1}]'
    """
    project_manager = PROJECT_MANAGER.get()
    try:
        authors = json.loads(authors_json)
    except json.JSONDecodeError as e:
        return f"❌ Error parsing authors_json: {e}"

    if not isinstance(authors, list):
        return "❌ Error: authors_json must be a JSON array."

    result = project_manager.update_authors(authors)

    if not result.get("success"):
        return f"❌ Error: {result.get('error', 'Unknown error')}"

    # Display formatted author info
    stored = result.get("authors", [])
    author_objs = [Author.from_dict(a) for a in stored]
    block = generate_author_block(author_objs)

    output = f"✅ Updated {len(stored)} author(s)!\n\n"
    output += "### Author Block Preview\n\n"
    output += block if block else "(No authors)\n"
    output += "\n---\n"
    output += "This info is stored in `project.json` and used for title page generation."

    return output
