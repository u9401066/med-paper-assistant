"""
Idea Validation Tools

Provides tools that require service access for idea validation.

MCP Tool (legitimate, needs ref_manager):
- compare_with_literature: Search saved references to find overlaps/gaps

Moved to Skills (no hard-coded logic needed):
- validate_hypothesis → .claude/skills/idea-validation/SKILL.md
- check_feasibility   → .claude/skills/idea-validation/SKILL.md
"""

import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_result,
)


def register_idea_validation_tools(mcp: FastMCP, ref_manager=None):
    """Register idea validation tools that require service access.

    Only `compare_with_literature` remains as an MCP tool because it needs
    ref_manager to query the saved reference database. The former
    `validate_hypothesis` and `check_feasibility` tools were pure text
    templates and are now handled by the `idea-validation` skill, where
    LLM reasoning produces better results than hard-coded regex.

    Args:
        mcp: FastMCP server instance to register tools on.
        ref_manager: ReferenceManager for querying saved references.
            Optional — tool degrades gracefully if None.
    """

    @mcp.tool()
    def compare_with_literature(
        idea: str,
        project: Optional[str] = None,
    ) -> str:
        """
        Compare a research idea against saved project references to identify gaps and overlaps.

        Args:
            idea: Research idea or hypothesis to compare
            project: Project slug (uses current if omitted)
        """
        log_tool_call("compare_with_literature", {"idea": idea[:80], "project": project})

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        output = "# 📚 Literature Comparison\n\n"
        output += f"**Research Idea:** {idea}\n\n"

        # Extract keywords from idea
        idea_lower = idea.lower()
        # Remove common words
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "shall",
            "of",
            "in",
            "to",
            "for",
            "with",
            "on",
            "at",
            "by",
            "from",
            "and",
            "or",
            "but",
            "not",
            "if",
            "than",
            "that",
            "this",
            "these",
            "those",
            "it",
            "its",
            "we",
            "our",
            "their",
        }
        words = re.findall(r"\b[a-z]{3,}\b", idea_lower)
        keywords = [w for w in words if w not in stop_words]
        unique_keywords = list(dict.fromkeys(keywords))[:10]  # Dedupe, keep order

        output += f"**Extracted Keywords:** {', '.join(unique_keywords)}\n\n"
        output += "---\n\n"

        # Search saved references
        if ref_manager is None:
            output += "⚠️ Reference manager not available. Cannot search saved references.\n"
            output += "Use `search_local_references` to manually search.\n\n"
        else:
            try:
                saved_refs = ref_manager.list_references()

                if not saved_refs:
                    output += "ℹ️ No saved references in current project.\n"
                    output += "Use `save_reference_mcp` to save relevant references first.\n\n"
                else:
                    output += f"## Saved References ({len(saved_refs)} total)\n\n"

                    # Search for keyword matches
                    matching_refs = []
                    for ref_item in saved_refs:
                        if isinstance(ref_item, dict):
                            ref_text = f"{ref_item.get('title', '')} {ref_item.get('abstract', '')}".lower()
                            pmid = str(ref_item.get("pmid", ""))
                        elif isinstance(ref_item, str):
                            # Might be a PMID string
                            pmid = ref_item
                            try:
                                meta = ref_manager.get_metadata(pmid)
                                ref_text = (
                                    f"{meta.get('title', '')} {meta.get('abstract', '')}".lower()
                                )
                                ref_item = meta
                            except Exception:
                                ref_text = ""
                                ref_item = {"pmid": pmid}
                        else:
                            continue

                        match_count = sum(1 for kw in unique_keywords if kw in ref_text)
                        if match_count > 0:
                            matching_refs.append((ref_item, match_count, pmid))

                    # Sort by match count
                    matching_refs.sort(key=lambda x: x[1], reverse=True)

                    if matching_refs:
                        output += "### Related References (by keyword overlap)\n\n"
                        output += "| # | PMID | Title | Keyword Matches | Overlap |\n"
                        output += "|---|------|-------|-----------------|--------|\n"

                        for i, (ref_data, count, pmid) in enumerate(matching_refs[:10], 1):
                            title = ref_data.get("title", "Unknown")[:60]
                            if len(ref_data.get("title", "")) > 60:
                                title += "..."
                            overlap = (
                                "🔴 High" if count >= 4 else "🟡 Medium" if count >= 2 else "🟢 Low"
                            )
                            output += f"| {i} | {pmid} | {title} | {count}/{len(unique_keywords)} | {overlap} |\n"

                        output += "\n"

                        # Novelty assessment
                        high_overlap = sum(1 for _, c, _ in matching_refs if c >= 4)
                        output += "### Novelty Assessment\n\n"
                        if high_overlap > 3:
                            output += "⚠️ **High overlap** with existing references. "
                            output += "Consider:\n"
                            output += "- Narrowing your research question\n"
                            output += "- Focusing on a specific subpopulation\n"
                            output += "- Adding a novel methodology or outcome\n\n"
                        elif high_overlap > 0:
                            output += "🟡 **Moderate overlap** — Related work exists but your idea may offer new insights.\n"
                            output += "Ensure your concept.md clearly articulates the NOVELTY STATEMENT.\n\n"
                        else:
                            output += "✅ **Low overlap** — Your idea appears to address a gap in saved references.\n"
                            output += (
                                "Verify with broader PubMed search using `search_literature`.\n\n"
                            )
                    else:
                        output += "ℹ️ No saved references match the idea keywords.\n"
                        output += (
                            "This could mean a genuine gap OR insufficient references saved.\n\n"
                        )

            except Exception as e:
                output += f"⚠️ Error searching references: {e}\n\n"

        # Gap analysis template
        output += "## Gap Analysis\n\n"
        output += "| What's Known | What's Missing | Your Contribution |\n"
        output += "|-------------|----------------|-------------------|\n"
        output += "| [Existing finding 1] | [Gap] | [How your study fills this] |\n"
        output += "| [Existing finding 2] | [Gap] | [How your study fills this] |\n\n"

        output += "---\n"
        output += (
            "💡 Use `search_literature` for comprehensive PubMed search beyond saved references.\n"
        )

        log_tool_result("compare_with_literature", "comparison generated", success=True)
        return output
