"""
Citation Tools - 智慧引用助手 MCP 工具

提供用戶選取文字並獲得引用建議的能力。
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services.citation_assistant import CitationAssistant

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_agent_misuse,
    log_tool_call,
    log_tool_result,
)


def register_citation_tools(mcp: FastMCP, citation_assistant: CitationAssistant):
    """Register citation-related tools."""

    @mcp.tool()
    def suggest_citations(
        text: str,
        section: str = "",
        search_pubmed: bool = True,
        project: Optional[str] = None,
    ) -> str:
        """
        Analyze text and suggest citations from local library + PubMed queries.

        Args:
            text: Text passage to analyze
            section: Optional context (Introduction/Methods/Results/Discussion)
            search_pubmed: Generate PubMed search suggestions for gaps
            project: Project slug (uses current if omitted)
        """
        log_tool_call(
            "suggest_citations",
            {
                "text_len": len(text),
                "section": section,
                "search_pubmed": search_pubmed,
                "project": project,
            },
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "suggest_citations",
                    "valid project context",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        result = citation_assistant.suggest_for_selection(
            selected_text=text,
            section=section,
        )

        log_tool_result("suggest_citations", f"analyzed {len(text)} chars", success=True)
        return result

    @mcp.tool()
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
        log_tool_call(
            "scan_draft_citations",
            {"filename": filename, "project": project},
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "scan_draft_citations",
                    "valid project context",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        # Resolve file path
        from med_paper_assistant.infrastructure.persistence import get_project_manager

        pm = get_project_manager()
        current_info = pm.get_project_info()

        draft_path = filename
        if not os.path.isabs(filename):
            # Try project drafts directory
            if current_info and current_info.get("project_path"):
                draft_path = os.path.join(
                    str(current_info["project_path"]), "drafts", filename
                )
            else:
                draft_path = os.path.join("drafts", filename)

        if not os.path.exists(draft_path):
            return f"❌ Draft file not found: {draft_path}"

        result = citation_assistant.scan_draft_for_citations(draft_path)
        log_tool_result(
            "scan_draft_citations", f"scanned {draft_path}", success=True
        )
        return result

    @mcp.tool()
    def find_citation_for_claim(
        claim: str,
        claim_type: str = "general",
        max_results: int = 5,
        project: Optional[str] = None,
    ) -> str:
        """
        Find citations for a specific claim type.

        Args:
            claim: The claim that needs support
            claim_type: "statistical", "comparison", "guideline", "mechanism", "definition", "general"
            max_results: Max suggestions (default 5)
            project: Project slug (uses current if omitted)
        """
        log_tool_call(
            "find_citation_for_claim",
            {
                "claim": claim[:50],
                "claim_type": claim_type,
                "max_results": max_results,
                "project": project,
            },
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "find_citation_for_claim",
                    "valid project context",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        # Add claim type suffix for better search
        type_suffixes = {
            "statistical": "epidemiology prevalence incidence",
            "comparison": "randomized controlled trial comparison",
            "guideline": "guideline recommendation",
            "mechanism": "mechanism pharmacology",
            "definition": "definition criteria",
        }

        suffix = type_suffixes.get(claim_type, "")
        search_text = f"{claim} {suffix}".strip()

        result = citation_assistant.analyze_text(
            text=search_text,
            search_local=True,
            generate_queries=True,
        )

        # Format output
        output = f"## 🎯 Citation Search: {claim_type.upper()}\n\n"
        output += f"**Claim**: {claim}\n\n"

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
            "find_citation_for_claim",
            f"found {len(result.local_suggestions)} local matches",
            success=True,
        )
        return output


__all__ = ["register_citation_tools"]
