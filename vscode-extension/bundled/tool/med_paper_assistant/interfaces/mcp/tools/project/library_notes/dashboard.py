"""Handler that builds library dashboards."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..._shared import (
    log_agent_misuse,
    log_tool_call,
    log_tool_result,
)
from .constants import ALLOWED_LIBRARY_SECTIONS
from .context import _resolve_library_project
from .dashboard_views import (
    VIEW_RENDERERS,
    materialize_graph_health,
    summarize_notes,
)
from .index import _collect_notes, _materialize_dashboard_note


def build_library_dashboard(
    view: str = "overview",
    limit: int = 10,
    project: Optional[str] = None,
) -> str:
    """Build a cross-note dashboard for a library-wiki project."""
    log_tool_call(
        "build_library_dashboard",
        {"view": view, "limit": limit, "project": project},
    )

    info, error_msg = _resolve_library_project(project)
    if info is None:
        log_agent_misuse(
            "build_library_dashboard",
            "library-wiki project required",
            {"project": project},
            error_msg,
        )
        return error_msg

    notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
    if not notes:
        return "No library notes yet. Use `write_library_note` or `create_concept_page` first."

    view_name = view.strip().lower() or "overview"
    if view_name not in VIEW_RENDERERS:
        return "❌ Invalid view. Use one of: overview, queues, concepts, links, synthesis, graph-health, unread, metadata, review, assets."

    data = summarize_notes(notes)
    lines = [
        f"# Library Dashboard: {info.get('name', info.get('slug', 'Unknown'))}",
        "",
        f"View: {view_name}",
        f"Total notes: {len(notes)}",
        "",
    ]
    VIEW_RENDERERS[view_name](lines, data, limit)

    repair_path: Optional[Path] = None
    if view_name == "graph-health":
        dashboard_path, repair_path = materialize_graph_health(info, lines, data, limit)
    else:
        dashboard_path = _materialize_dashboard_note(
            info,
            directory="library",
            slug=f"dashboard-{view_name}",
            title=f"{view_name.replace('-', ' ').title()} Dashboard",
            body_lines=lines,
            note_type="library-dashboard",
            tags=["dashboard/library", f"dashboard/{view_name}", "workflow/library-first"],
            extra_fields={"note_class": "library-dashboard", "note_domain": "library"},
        )

    lines.extend(["", f"Materialized note: {dashboard_path}"])
    if repair_path is not None:
        lines.append(f"Repair Worklist: {repair_path}")

    log_tool_result("build_library_dashboard", f"dashboard {view_name}", success=True)
    return "\n".join(lines).strip()
