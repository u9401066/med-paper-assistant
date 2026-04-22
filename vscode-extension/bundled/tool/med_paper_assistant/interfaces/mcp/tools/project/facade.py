"""Consolidated project/workspace facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP

from .._shared import invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_project_facade_tools(
    mcp: FastMCP,
    crud_tools: ToolMap,
    settings_tools: ToolMap,
    exploration_tools: ToolMap,
    workspace_state_tools: ToolMap,
    library_tools: ToolMap | None = None,
    diagram_tools: ToolMap | None = None,
    workspace_tools: ToolMap | None = None,
):
    """Register stable public verbs for project and workspace state management."""

    library_tools = library_tools or {}
    diagram_tools = diagram_tools or {}
    workspace_tools = workspace_tools or {}

    @mcp.tool()
    async def project_action(
        action: str,
        name: str = "",
        slug: str = "",
        description: str = "",
        target_journal: str = "",
        paper_type: str = "",
        workflow_mode: str = "",
        authors_json: str = "",
        memo: str = "",
        status: str = "",
        citation_style: str = "",
        interaction_style: str = "",
        language_preference: str = "",
        writing_style: str = "",
        keep_exploration: bool = False,
        include_files: bool = False,
        confirm: bool = False,
        filename: str = "",
        content: str = "",
        content_format: str = "xml",
        output_dir: str = "",
        rendered_content: str = "",
        rendered_format: str = "",
        rendered_content_format: str = "auto",
        rendered_filename: str = "",
        ctx: Context | None = None,
    ) -> str:
        """
        Run consolidated project-management actions through one stable entrypoint.

        Actions:
        - create
        - list
        - switch
        - current
        - update
        - setup
        - update_authors
        - start_exploration
        - convert_exploration
        - archive
        - delete
        - save_diagram
        - list_diagrams
        - open_files
        """
        aliases = {
            "get": "current",
            "settings": "update",
            "configure": "setup",
            "explore": "start_exploration",
            "convert": "convert_exploration",
            "authors": "update_authors",
            "diagram_save": "save_diagram",
            "diagram_list": "list_diagrams",
            "open": "open_files",
        }
        normalized = normalize_facade_action(action, aliases)

        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
            "create": (
                crud_tools,
                "create_project",
                {
                    "name": name,
                    "description": description,
                    "target_journal": target_journal,
                    "paper_type": paper_type,
                    "workflow_mode": workflow_mode,
                    "authors_json": authors_json,
                    "memo": memo,
                },
            ),
            "list": (crud_tools, "list_projects", {}),
            "switch": (crud_tools, "switch_project", {"slug": slug}),
            "current": (
                crud_tools,
                "get_current_project",
                {"include_files": include_files},
            ),
            "update": (
                settings_tools,
                "update_project_settings",
                {
                    "paper_type": paper_type,
                    "target_journal": target_journal,
                    "interaction_style": interaction_style,
                    "language_preference": language_preference,
                    "writing_style": writing_style,
                    "memo": memo,
                    "status": status,
                    "citation_style": citation_style,
                    **({"workflow_mode": workflow_mode} if workflow_mode else {}),
                },
            ),
            "setup": (
                settings_tools,
                "setup_project_interactive",
                {"ctx": ctx},
            ),
            "update_authors": (
                settings_tools,
                "update_authors",
                {"authors_json": authors_json},
            ),
            "start_exploration": (exploration_tools, "start_exploration", {}),
            "convert_exploration": (
                exploration_tools,
                "convert_exploration_to_project",
                {
                    "name": name,
                    "description": description,
                    "paper_type": paper_type,
                    "workflow_mode": workflow_mode,
                    "target_journal": target_journal,
                    "keep_exploration": keep_exploration,
                },
            ),
            "archive": (
                crud_tools,
                "archive_project",
                {"slug": slug, "confirm": confirm},
            ),
            "delete": (
                crud_tools,
                "delete_project",
                {"slug": slug, "confirm": confirm},
            ),
            "save_diagram": (
                diagram_tools,
                "save_diagram",
                {
                    "filename": filename,
                    "content": content,
                    "project": slug or None,
                    "content_format": content_format,
                    "description": description,
                    "output_dir": output_dir,
                    "rendered_content": rendered_content,
                    "rendered_format": rendered_format,
                    "rendered_content_format": rendered_content_format,
                    "rendered_filename": rendered_filename,
                },
            ),
            "list_diagrams": (
                diagram_tools,
                "list_diagrams",
                {"project": slug or None},
            ),
            "open_files": (
                workspace_tools,
                "open_project_files",
                {"project_slug": slug or None},
            ),
        }

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Project facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    @mcp.tool()
    async def library_action(
        action: str,
        section: str = "all",
        from_section: str = "",
        to_section: str = "",
        filename: str = "",
        content: str = "",
        title: str = "",
        tags_csv: str = "",
        add_tags_csv: str = "",
        remove_tags_csv: str = "",
        related_notes_csv: str = "",
        note_type: str = "",
        status: str = "",
        query: str = "",
        queue: str = "all",
        view: str = "overview",
        limit: int = 10,
        source_note: str = "",
        target_note: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        Run library-wiki note and dashboard actions through one stable entrypoint.

        Actions:
        - list_notes
        - read_note
        - write_note
        - move_note
        - triage_note
        - update_metadata
        - search_notes
        - show_queues
        - create_concept
        - materialize_concept
        - explain_path
        - build_dashboard
        """
        aliases = {
            "list": "list_notes",
            "read": "read_note",
            "write": "write_note",
            "move": "move_note",
            "triage": "triage_note",
            "metadata": "update_metadata",
            "frontmatter": "update_metadata",
            "search": "search_notes",
            "queues": "show_queues",
            "concept": "create_concept",
            "materialize": "materialize_concept",
            "path": "explain_path",
            "dashboard": "build_dashboard",
        }
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[str, dict[str, Any]]] = {
            "list_notes": (
                "list_library_notes",
                {"section": section, "project": project},
            ),
            "read_note": (
                "read_library_note",
                {"section": section, "filename": filename, "project": project},
            ),
            "write_note": (
                "write_library_note",
                {
                    "section": section,
                    "filename": filename,
                    "content": content,
                    "title": title,
                    "tags_csv": tags_csv,
                    "status": status,
                    "project": project,
                },
            ),
            "move_note": (
                "move_library_note",
                {
                    "filename": filename,
                    "from_section": from_section,
                    "to_section": to_section,
                    "project": project,
                },
            ),
            "triage_note": (
                "triage_library_note",
                {
                    "note_ref": source_note or filename,
                    "target_section": to_section or (section if section != "all" else ""),
                    "status": status,
                    "tags_csv": tags_csv,
                    "related_notes_csv": related_notes_csv,
                    "project": project,
                },
            ),
            "update_metadata": (
                "update_library_note_metadata",
                {
                    "note_ref": source_note or filename,
                    "title": title,
                    "status": status,
                    "tags_csv": tags_csv,
                    "add_tags_csv": add_tags_csv,
                    "remove_tags_csv": remove_tags_csv,
                    "related_notes_csv": related_notes_csv,
                    "note_type": note_type,
                    "project": project,
                },
            ),
            "search_notes": (
                "search_library_notes",
                {"query": query, "section": section, "project": project},
            ),
            "show_queues": (
                "show_reading_queues",
                {"queue": queue, "limit": limit, "project": project},
            ),
            "create_concept": (
                "create_concept_page",
                {
                    "filename": filename,
                    "title": title,
                    "summary": content,
                    "source_notes_csv": query,
                    "tags_csv": tags_csv,
                    "open_questions": status,
                    "project": project,
                },
            ),
            "materialize_concept": (
                "materialize_concept_page",
                {
                    "filename": filename,
                    "title": title,
                    "summary": content,
                    "source_notes_csv": query or source_note or filename,
                    "tags_csv": tags_csv,
                    "open_questions": status,
                    "project": project,
                },
            ),
            "explain_path": (
                "explain_library_path",
                {
                    "source_note": source_note or filename,
                    "target_note": target_note or query,
                    "project": project,
                },
            ),
            "build_dashboard": (
                "build_library_dashboard",
                {"view": view, "limit": limit, "project": project},
            ),
        }

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        handler_name, kwargs = action_specs[normalized]
        handler = library_tools.get(handler_name)
        if handler is None:
            return f"❌ Library facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    @mcp.tool(structured_output=True)
    async def workspace_state_action(
        action: str,
        doing: Optional[str] = None,
        next_action: Optional[str] = None,
        context: Optional[str] = None,
        clear: bool = False,
        section: str = "",
        plan: str = "",
        notes: str = "",
        references_in_use: str = "",
    ) -> dict[str, Any]:
        """
        Manage workspace recovery state through one stable entrypoint.

        Actions:
        - get
        - sync
        - checkpoint
        """
        aliases = {"save": "sync", "recover": "get"}
        normalized = normalize_facade_action(action, aliases)

        if normalized == "get":
            handler = workspace_state_tools.get("get_workspace_state")
            if handler is None:
                return {"status": "error", "message": "Missing handler 'get_workspace_state'"}
            result = await invoke_tool_handler(handler)
            return {"status": "ok", "action": "get", **result}

        if normalized == "sync":
            handler = workspace_state_tools.get("sync_workspace_state")
            if handler is None:
                return {"status": "error", "message": "Missing handler 'sync_workspace_state'"}
            message = await invoke_tool_handler(
                handler,
                doing=doing,
                next_action=next_action,
                context=context,
                clear=clear,
            )
            return {"status": "ok", "action": "sync", "message": message}

        if normalized == "checkpoint":
            handler = workspace_state_tools.get("checkpoint_writing_context")
            if handler is None:
                return {
                    "status": "error",
                    "message": "Missing handler 'checkpoint_writing_context'",
                }
            message = await invoke_tool_handler(
                handler,
                section=section,
                plan=plan,
                notes=notes,
                references_in_use=references_in_use,
            )
            return {"status": "ok", "action": "checkpoint", "message": message}

        return {
            "status": "error",
            "message": (f"Unsupported action '{action}'. Supported actions: checkpoint, get, sync"),
        }

    return {
        "library_action": library_action,
        "project_action": project_action,
        "workspace_state_action": workspace_state_action,
    }
