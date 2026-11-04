"""
Draft Writing Tools

write_draft, draft_section, read_draft, list_drafts
"""

from collections.abc import Callable
from typing import Any, Optional

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    get_optional_tool_decorator,
    get_project_path,
)
from .writing_context import _check_writing_order, _draft_section
from .writing_files import _delete_draft, _list_drafts, _read_draft, _write_draft


def _run_embedded_post_write_hooks(content: str, section_name: str = "manuscript") -> str:
    """
    Run post-write hooks automatically after write_draft/patch_draft.

    Non-blocking: returns a report string (never raises). Agent cannot skip
    this because it's embedded in the write path, not a separate tool call.

    Returns:
        Formatted report string, or empty string if no issues or on error.
    """
    project_path = get_project_path()
    if not project_path:
        return ""

    try:
        from med_paper_assistant.infrastructure.persistence.writing_hooks import (
            WritingHooksEngine,
        )

        engine = WritingHooksEngine(project_path)
        results = engine.run_post_write_hooks(content, section=section_name)

        criticals: list[str] = []
        warnings: list[str] = []

        for hook_id, hook_result in results.items():
            for issue in hook_result.issues:
                line = f"[{hook_id}] {issue.message}"
                if issue.severity == "CRITICAL":
                    criticals.append(f"❌ {line}")
                elif issue.severity == "WARNING":
                    warnings.append(f"⚠️  {line}")

        if not criticals and not warnings:
            return "\n\n✅ **Post-write hooks**: All checks passed."

        parts = ["\n\n📋 **Post-write hooks (auto-run)**:"]
        if criticals:
            parts.append(f"\n**CRITICAL ({len(criticals)}):**")
            parts.extend(f"\n- {c}" for c in criticals)
        if warnings:
            parts.append(f"\n**Warnings ({len(warnings)}):**")
            parts.extend(f"\n- {w}" for w in warnings[:10])  # Cap at 10 to avoid token bloat
            if len(warnings) > 10:
                parts.append(f"\n- ... and {len(warnings) - 10} more")

        return "".join(parts)
    except Exception:
        return ""  # Silently fail — don't block writing due to hook errors


def _register_planning_tools(
    tool: Callable[..., Any], drafter: Drafter
) -> dict[str, Callable[..., Any]]:
    @tool()
    def check_writing_order(project: Optional[str] = None) -> str:
        """
        Check the recommended writing order and current progress for the active project.

        Shows which sections have been written and which prerequisites remain.
        Advisory only — CONSTITUTION §22 allows reordering phases.

        Args:
            project: Project slug (uses current if omitted)
        """
        return _check_writing_order(project)

    @tool()
    def draft_section(
        topic: str, notes: str, project: Optional[str] = None, skip_validation: bool = False
    ) -> str:
        """
        Draft a paper section using concept.md and saved references as context.

        Args:
            topic: Section name (e.g., "Introduction")
            notes: Raw notes/bullet points to convert
            project: Project slug (uses current if omitted)
            skip_validation: Internal use only
        """
        return _draft_section(drafter, topic, notes, project, skip_validation)

    return {"check_writing_order": check_writing_order, "draft_section": draft_section}


def _register_write_tool(
    tool: Callable[..., Any], drafter: Drafter
) -> dict[str, Callable[..., Any]]:
    @tool()
    def write_draft(
        filename: str = "",
        content: str = "",
        project: Optional[str] = None,
        skip_validation: bool = False,
        section: Optional[str] = None,
    ) -> str:
        """
        Create/update a draft file with auto citation formatting.
        Use (PMID:123456) or [PMID:123456] for citations.

        Args:
            filename: Draft filename (e.g., "draft.md")
            content: Text content with citation placeholders
            project: Project slug (uses current if omitted)
            skip_validation: Internal use only
            section: Optional section label used to derive filename when omitted
        """
        return _write_draft(
            drafter,
            _run_embedded_post_write_hooks,
            filename,
            content,
            project,
            skip_validation,
            section,
        )

    return {"write_draft": write_draft}


def _register_file_tools(tool: Callable[..., Any]) -> dict[str, Callable[..., Any]]:
    @tool()
    def list_drafts(project: Optional[str] = None) -> str:
        """
        List all draft files in drafts/ with section and word counts.

        Args:
            project: Project slug (uses current if omitted)
        """
        return _list_drafts(project)

    @tool()
    def read_draft(filename: str, project: Optional[str] = None) -> str:
        """
        Read a draft file's structure and content by sections.

        Args:
            filename: Draft filename (in drafts/ directory)
            project: Project slug (uses current if omitted)
        """
        return _read_draft(filename, project)

    @tool()
    def delete_draft(filename: str, confirm: bool = False, project: Optional[str] = None) -> str:
        """
        ⚠️ DESTRUCTIVE: Delete a draft file permanently.

        Args:
            filename: Draft filename (e.g., "draft.md")
            confirm: False=preview, True=actually delete
            project: Project slug (uses current if omitted)
        """
        return _delete_draft(filename, confirm, project)

    return {"list_drafts": list_drafts, "read_draft": read_draft, "delete_draft": delete_draft}


def register_writing_tools(
    mcp: MCPServer,
    drafter: Drafter,
    *,
    register_public_verbs: bool = True,
):
    """Register draft writing tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return {
        **_register_planning_tools(tool, drafter),
        **_register_write_tool(tool, drafter),
        **_register_file_tools(tool),
    }
