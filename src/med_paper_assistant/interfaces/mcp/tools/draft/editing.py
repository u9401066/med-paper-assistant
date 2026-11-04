"""
Draft Editing Tools — Citation-Aware Partial Editing

Layer 1: get_available_citations — List all valid citation keys before editing
Layer 2: patch_draft — Partial edit with wikilink validation

These tools solve the problem of citation correctness when Agent uses
partial edits (replace_string_in_file) instead of whole-file write_draft().
"""

import os
from collections.abc import Callable
from typing import Any, Optional

from mcp.server import MCPServer

from med_paper_assistant.domain.services.wikilink_validator import find_citation_key_for_pmid
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    get_optional_tool_decorator,
    log_tool_call,
    log_tool_result,
)
from .editing_patch import (
    _get_references_dir,
    _guard_editing_tool,
    _patch_draft,
)


def _first_author(meta: dict) -> str:
    first_author = ""
    authors_full = meta.get("authors_full", [])
    authors = meta.get("authors", [])
    if authors_full and isinstance(authors_full[0], dict):
        first_author = authors_full[0].get("last_name", "")
    elif authors:
        first_author = authors[0].split()[0] if authors[0] else ""
    return first_author


def _citation_row(pmid: str, meta: dict, refs_dir: str) -> str:
    citation_key = meta.get("citation_key", "")
    if not citation_key:
        # Try to find from directory structure
        citation_key = find_citation_key_for_pmid(pmid, refs_dir) or pmid

    title = meta.get("title", "Unknown")
    if len(title) > 50:
        title = title[:47] + "..."

    year = meta.get("year", "")

    return f"| `[[{citation_key}]]` | {pmid} | {_first_author(meta)} | {year} | {title} |\n"


def _citations_table(ref_manager: Any, pmids: list[str], refs_dir: str) -> tuple[str, int]:
    """Build the citation table; return (markdown, number of listed citations)."""
    output = f"📚 **Available Citations ({len(pmids)} references)**\n\n"
    output += "Use these exact `[[citation_key]]` wikilinks in drafts:\n\n"
    output += "| Citation Key | PMID | First Author | Year | Title |\n"
    output += "|-------------|------|--------------|------|-------|\n"

    listed = 0
    for pmid in sorted(pmids):
        meta = ref_manager.get_metadata(pmid)
        if not meta:
            continue
        output += _citation_row(pmid, meta, refs_dir)
        listed += 1
    return output, listed


def _get_available_citations(drafter: Drafter, project: Optional[str]) -> str:
    log_tool_call("get_available_citations", {"project": project})

    guard_error = _guard_editing_tool("get_available_citations", project)
    if guard_error:
        return guard_error

    refs_dir = _get_references_dir()
    if not refs_dir or not os.path.exists(refs_dir):
        result = (
            "📚 **No references found.**\n\n"
            'Save references first using `save_reference_mcp(pmid="...")` '
            "before adding citations to drafts."
        )
        log_tool_result("get_available_citations", "no references dir", success=True)
        return result

    ref_manager = drafter.ref_manager
    pmids = ref_manager.list_references()

    if not pmids:
        result = (
            "📚 **No references saved yet.**\n\n"
            'Save references first using `save_reference_mcp(pmid="...")` '
            "before adding citations to drafts."
        )
        log_tool_result("get_available_citations", "empty", success=True)
        return result

    output, listed = _citations_table(ref_manager, pmids, refs_dir)

    output += "\n---\n"
    output += "💡 **Usage**: Insert `[[citation_key]]` in draft text.\n"
    output += "💡 **Workflow**: Call `get_available_citations` → edit draft with `patch_draft` → `sync_references`\n"

    log_tool_result("get_available_citations", f"listed {listed} citations", success=True)
    return output


def _register_citation_list_tool(
    tool: Callable[..., Any], drafter: Drafter
) -> dict[str, Callable[..., Any]]:
    @tool()
    def get_available_citations(project: Optional[str] = None) -> str:
        """
        List all valid citation keys from saved references.
        ⚠️ MUST call this before editing drafts with citations!

        Returns a table of [[citation_key]] with author, year, title, PMID.
        Use these exact keys when inserting wikilinks in drafts.

        Args:
            project: Project slug (uses current if omitted)
        """
        return _get_available_citations(drafter, project)

    return {"get_available_citations": get_available_citations}


def _register_patch_tool(
    tool: Callable[..., Any], drafter: Drafter
) -> dict[str, Callable[..., Any]]:
    @tool()
    def patch_draft(
        filename: str,
        old_text: str,
        new_text: str,
        project: Optional[str] = None,
    ) -> str:
        """
        Partially edit a draft with citation validation.
        Replaces old_text with new_text, validating all [[wikilinks]] in new_text.

        Use this instead of replace_string_in_file for draft files!

        Args:
            filename: Draft filename (e.g., "introduction.md")
            old_text: Exact text to find and replace (must match uniquely)
            new_text: Replacement text (wikilinks will be validated/auto-fixed)
            project: Project slug (uses current if omitted)
        """
        return _patch_draft(drafter, filename, old_text, new_text, project)

    return {"patch_draft": patch_draft}


def register_editing_tools(
    mcp: MCPServer,
    drafter: Drafter,
    *,
    register_public_verbs: bool = True,
):
    """Register citation-aware editing tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return {
        **_register_citation_list_tool(tool, drafter),
        **_register_patch_tool(tool, drafter),
    }
