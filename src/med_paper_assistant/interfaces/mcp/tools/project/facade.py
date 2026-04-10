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
):
    """Register stable public verbs for project and workspace state management."""

    @mcp.tool()
    async def project_action(
        action: str,
        name: str = "",
        slug: str = "",
        description: str = "",
        target_journal: str = "",
        paper_type: str = "",
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
        """
        aliases = {
            "get": "current",
            "settings": "update",
            "configure": "setup",
            "explore": "start_exploration",
            "convert": "convert_exploration",
            "authors": "update_authors",
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
        }

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Project facade misconfigured: missing handler '{handler_name}'"

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
            "message": (
                f"Unsupported action '{action}'. Supported actions: checkpoint, get, sync"
            ),
        }

    return {
        "project_action": project_action,
        "workspace_state_action": workspace_state_action,
    }