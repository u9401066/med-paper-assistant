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
    get_optional_tool_decorator,
    log_agent_misuse,
    log_tool_call,
    log_tool_result,
    validate_project_for_workflow,
)


def register_citation_tools(
    mcp: FastMCP,
    citation_assistant: CitationAssistant,
    *,
    register_public_verbs: bool = True,
):
    """Register citation-related tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    def _require_manuscript_project(project: Optional[str]) -> Optional[str]:
        is_valid, error_msg = validate_project_for_workflow(
            project,
            required_mode="manuscript",
        )
        if is_valid:
            return None
        return error_msg

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

        workflow_error = _require_manuscript_project(project)
        if workflow_error:
            log_agent_misuse(
                "suggest_citations",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

        # Apply claim type suffix for specialized search
        type_suffixes = {
            "statistical": "epidemiology prevalence incidence",
            "comparison": "randomized controlled trial comparison",
            "guideline": "guideline recommendation",
            "mechanism": "mechanism pharmacology",
            "definition": "definition criteria",
        }

        if claim_type != "general" and claim_type in type_suffixes:
            search_text = f"{text} {type_suffixes[claim_type]}".strip()
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

        # Default general mode
        result_text = citation_assistant.suggest_for_selection(
            selected_text=text,
            section=section,
        )

        log_tool_result("suggest_citations", f"analyzed {len(text)} chars", success=True)
        return result_text

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

        workflow_error = _require_manuscript_project(project)
        if workflow_error:
            log_agent_misuse(
                "scan_draft_citations",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

        # Resolve file path
        from med_paper_assistant.infrastructure.persistence import get_project_manager

        pm = get_project_manager()
        current_info = pm.get_project_info()

        draft_path = filename
        if not os.path.isabs(filename):
            # Try project drafts directory
            if current_info and current_info.get("project_path"):
                draft_path = os.path.join(str(current_info["project_path"]), "drafts", filename)
            else:
                draft_path = os.path.join("drafts", filename)

        if not os.path.exists(draft_path):
            return f"❌ Draft file not found: {draft_path}"

        result = citation_assistant.scan_draft_for_citations(draft_path)
        log_tool_result("scan_draft_citations", f"scanned {draft_path}", success=True)
        return result

    return {
        "suggest_citations": suggest_citations,
        "scan_draft_citations": scan_draft_citations,
    }


__all__ = ["register_citation_tools"]
