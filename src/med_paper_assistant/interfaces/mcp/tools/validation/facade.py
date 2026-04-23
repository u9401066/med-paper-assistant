"""Consolidated validation facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .._shared import invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_validation_facade_tools(
    mcp: FastMCP,
    concept_tools: ToolMap,
    idea_tools: ToolMap,
):
    """Register stable facade verb for validation workflows."""

    @mcp.tool()
    async def validation_action(
        action: str,
        filename: str = "concept.md",
        project: Optional[str] = None,
        run_novelty_check: bool = True,
        target_section: str = "",
        structure_only: bool = False,
        auto_fix: bool = True,
        idea: str = "",
    ) -> str:
        """
        Run validation actions through one stable entrypoint.

        Actions:
        - concept
        - wikilinks
        - literature
        """
        aliases = {
            "actions": "list",
            "help": "list",
            "supported": "list",
            "validate_concept": "concept",
            "concept_validation": "concept",
            "validate_wikilinks": "wikilinks",
            "wikilink": "wikilinks",
            "compare": "literature",
            "compare_with_literature": "literature",
        }
        normalized = normalize_facade_action(action, aliases)

        supported_actions = ("concept", "wikilinks", "literature", "list")
        if normalized == "list":
            return (
                "validation_action supports: "
                "concept, wikilinks, literature. "
                "Aliases: validate_concept, validate_wikilinks, compare, compare_with_literature."
            )

        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
            "concept": (
                concept_tools,
                "validate_concept",
                {
                    "filename": filename,
                    "project": project,
                    "run_novelty_check": run_novelty_check,
                    "target_section": target_section or None,
                    "structure_only": structure_only,
                },
            ),
            "wikilinks": (
                concept_tools,
                "validate_wikilinks",
                {
                    "filename": filename,
                    "project": project,
                    "auto_fix": auto_fix,
                },
            ),
            "literature": (
                idea_tools,
                "compare_with_literature",
                {
                    "idea": idea,
                    "project": project,
                },
            ),
        }

        if normalized not in action_specs:
            supported = ", ".join(supported_actions)
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Validation facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    return {
        "validation_action": validation_action,
    }
