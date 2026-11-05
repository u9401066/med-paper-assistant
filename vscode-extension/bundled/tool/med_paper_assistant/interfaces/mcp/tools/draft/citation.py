"""
Citation Tools - 智慧引用助手 MCP 工具

提供用戶選取文字並獲得引用建議的能力。
"""

import os
from collections.abc import Callable
from typing import Any, Optional

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.services.citation_assistant import CitationAssistant
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import resolve_child_path

from .._shared import (
    get_optional_tool_decorator,
    guard_manuscript_tool,
    log_tool_call,
    log_tool_result,
)

# Apply claim type suffix for specialized search
_CLAIM_TYPE_SUFFIXES = {
    "statistical": "epidemiology prevalence incidence",
    "comparison": "randomized controlled trial comparison",
    "guideline": "guideline recommendation",
    "mechanism": "mechanism pharmacology",
    "definition": "definition criteria",
}


def _typed_claim_search(
    citation_assistant: CitationAssistant, text: str, claim_type: str, max_results: int
) -> str:
    search_text = f"{text} {_CLAIM_TYPE_SUFFIXES[claim_type]}".strip()
    result = citation_assistant.analyze_text(
        text=search_text,
        search_local=True,
        generate_queries=True,
    )

    output = f"## 🎯 Citation Search: {claim_type.upper()}\n\n"
    output += f"**Claim**: {text}\n\n"

    if result.local_suggestions:
        output += "### 📚 From Local Library\n\n"
        for sug in result.local_suggestions[:max_results]:
            output += f"- **[[{sug.citation_key}]]**\n"
            output += f"  {sug.title[:80]}...\n"
            output += f"  *Relevance: {sug.relevance_reason}*\n\n"
    else:
        output += "### 📚 Local Library\n*No relevant references found.*\n\n"

    if result.pubmed_search_queries:
        output += "### 🔎 Suggested PubMed Searches\n\n"
        for i, q in enumerate(result.pubmed_search_queries[:3], 1):
            output += f"{i}. `{q}`\n"

    log_tool_result(
        "suggest_citations",
        f"found {len(result.local_suggestions)} local matches",
        success=True,
    )
    return output


def _suggest_citations(
    citation_assistant: CitationAssistant,
    text: str,
    section: str,
    claim_type: str,
    max_results: int,
    search_pubmed: bool,
    project: Optional[str],
) -> str:
    log_tool_call(
        "suggest_citations",
        {
            "text_len": len(text),
            "section": section,
            "claim_type": claim_type,
            "search_pubmed": search_pubmed,
            "project": project,
        },
    )

    error = guard_manuscript_tool("suggest_citations", project)
    if error:
        return error

    if claim_type != "general" and claim_type in _CLAIM_TYPE_SUFFIXES:
        return _typed_claim_search(citation_assistant, text, claim_type, max_results)

    # Default general mode
    result_text = citation_assistant.suggest_for_selection(
        selected_text=text,
        section=section,
    )

    log_tool_result("suggest_citations", f"analyzed {len(text)} chars", success=True)
    return result_text


def _resolve_draft_path(filename: str) -> tuple[str, str]:
    """Resolve the draft file to scan; return (path, error)."""
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()

    try:
        safe_filename = normalize_draft_filename(filename)
        if current_info and current_info.get("project_path"):
            drafts_dir = os.path.join(str(current_info["project_path"]), "drafts")
        else:
            drafts_dir = "drafts"
        draft_path = str(
            resolve_child_path(
                drafts_dir,
                safe_filename,
                field_name="Draft filename",
                allowed_suffixes={".md"},
            )
        )
    except ValueError as e:
        return "", f"❌ Invalid draft filename: {e}"
    return draft_path, ""


def _scan_draft_citations(
    citation_assistant: CitationAssistant, filename: str, project: Optional[str]
) -> str:
    log_tool_call(
        "scan_draft_citations",
        {"filename": filename, "project": project},
    )

    error = guard_manuscript_tool("scan_draft_citations", project)
    if error:
        return error

    # Resolve file path
    draft_path, error = _resolve_draft_path(filename)
    if error:
        return error

    if not os.path.exists(draft_path):
        return f"❌ Draft file not found: {draft_path}"

    result = citation_assistant.scan_draft_for_citations(draft_path)
    log_tool_result("scan_draft_citations", f"scanned {draft_path}", success=True)
    return result


def _register_suggest_tool(
    tool: Callable[..., Any], citation_assistant: CitationAssistant
) -> dict[str, Callable[..., Any]]:
    @tool()
    def suggest_citations(
        text: str,
        section: str = "",
        claim_type: str = "general",
        max_results: int = 5,
        search_pubmed: bool = True,
        project: Optional[str] = None,
    ) -> str:
        """
        Analyze text and suggest citations from local library + PubMed queries.

        Args:
            text: Text passage or specific claim to analyze
            section: Optional context (Introduction/Methods/Results/Discussion)
            claim_type: "general", "statistical", "comparison", "guideline", "mechanism", "definition"
            max_results: Max suggestions (default 5)
            search_pubmed: Generate PubMed search suggestions for gaps
            project: Project slug (uses current if omitted)
        """
        return _suggest_citations(
            citation_assistant, text, section, claim_type, max_results, search_pubmed, project
        )

    return {"suggest_citations": suggest_citations}


def _register_scan_tool(
    tool: Callable[..., Any], citation_assistant: CitationAssistant
) -> dict[str, Callable[..., Any]]:
    @tool()
    def scan_draft_citations(
        filename: str,
        project: Optional[str] = None,
    ) -> str:
        """
        Scan entire draft for uncited statements and suggest citations.

        Args:
            filename: Draft filename (e.g., "introduction.md")
            project: Project slug (uses current if omitted)
        """
        return _scan_draft_citations(citation_assistant, filename, project)

    return {"scan_draft_citations": scan_draft_citations}


def register_citation_tools(
    mcp: MCPServer,
    citation_assistant: CitationAssistant,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register citation-related tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return {
        **_register_suggest_tool(tool, citation_assistant),
        **_register_scan_tool(tool, citation_assistant),
    }


__all__ = ["register_citation_tools"]
