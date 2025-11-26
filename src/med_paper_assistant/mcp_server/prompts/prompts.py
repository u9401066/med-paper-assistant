"""
MCP Prompts Module - Minimal Agent Instructions

DESIGN PRINCIPLE:
- Prompts are instructions FOR THE AGENT, not text for the user to read
- Keep prompts minimal - just tell the agent what to do
- Agent should speak naturally to user, not display the prompt
- Use tools to gather info, then respond conversationally
"""

import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptReference, Completion

from med_paper_assistant.core.template_reader import TemplateReader
from med_paper_assistant.core.project_manager import get_project_manager


def register_prompts(mcp: FastMCP, template_reader: TemplateReader):
    """Register all prompts with the MCP server."""
    
    # ========================================
    # Completion Handler for prompt arguments
    # ========================================
    @mcp.completion()
    async def handle_completion(ref, argument, context):
        """
        Provide autocomplete suggestions for prompt arguments.
        
        This enables IDE-like completion when users type prompt arguments.
        For example, when using /mdpaper.project, suggest existing project names.
        """
        pm = get_project_manager()
        
        # Handle prompt completions
        if isinstance(ref, PromptReference):
            prompt_name = ref.name
            arg_name = argument.name
            partial_value = argument.value or ""
            
            # /mdpaper.project - suggest existing projects
            if prompt_name == "project" and arg_name == "project_name":
                projects = pm.list_projects().get("projects", [])
                suggestions = []
                for p in projects:
                    slug = p.get("slug", "")
                    name = p.get("name", "")
                    # Filter by partial match
                    if partial_value.lower() in slug.lower() or partial_value.lower() in name.lower():
                        suggestions.append(slug)
                return Completion(
                    values=suggestions[:10],  # Max 10 suggestions
                    total=len(suggestions),
                    hasMore=len(suggestions) > 10
                )
            
            # /mdpaper.draft - suggest sections
            if prompt_name == "draft" and arg_name == "section":
                sections = ["Introduction", "Methods", "Results", "Discussion", "Abstract", "Conclusion", "all"]
                suggestions = [s for s in sections if partial_value.lower() in s.lower()]
                return Completion(values=suggestions)
            
            # /mdpaper.concept - no completion needed for topic (free text)
            # /mdpaper.strategy - no completion needed for keywords (free text)
        
        return None
    
    # ========================================
    # /mdpaper.project - Configure project
    # ========================================
    @mcp.prompt(name="project", description="Setup and configure a research project")
    def mdpaper_project(project_name: str = "") -> str:
        pm = get_project_manager()
        
        if project_name:
            # Check if project exists (completion would suggest existing ones)
            projects = pm.list_projects().get("projects", [])
            existing_slugs = [p.get("slug", "") for p in projects]
            
            if project_name in existing_slugs:
                # Existing project selected via completion
                return f"switch_project(slug=\"{project_name}\") then setup_project_interactive()"
            else:
                # New project name
                return f"create_project(name=\"{project_name}\") then setup_project_interactive()"
        
        return "setup_project_interactive()"

    # ========================================
    # /mdpaper.concept - Develop research concept
    # ========================================
    @mcp.prompt(name="concept", description="Develop research concept with literature-based gap analysis")
    def mdpaper_concept(topic: str) -> str:
        return f"""Topic: {topic}
Flow: search_literature() → save_reference() → 確認 research gap → write_draft(concept.md) with 🔒NOVELTY + 🔒KEY SELLING POINTS"""

    # ========================================
    # /mdpaper.strategy - Configure search strategy
    # ========================================
    @mcp.prompt(name="strategy", description="Configure search strategy")
    def mdpaper_strategy(keywords: str) -> str:
        return f"""Keywords: {keywords}
詢問: exclusions, year range, article types, sample size → configure_search_strategy()"""

    # ========================================
    # /mdpaper.draft - Write paper section
    # ========================================
    @mcp.prompt(name="draft", description="Write paper draft")
    def mdpaper_draft(section: str) -> str:
        return f"""Section: {section}
Flow: read_draft(concept.md) → 確保含🔒protected content → get_section_template() → write_draft() → count_words()"""

    # ========================================
    # /mdpaper.analysis - Analyze data
    # ========================================
    @mcp.prompt(name="analysis", description="Analyze data")
    def mdpaper_data_analysis() -> str:
        return """Tools: analyze_dataset(), generate_table_one(), run_statistical_test(), create_plot()
先詢問用戶要分析哪個 CSV 和需要什麼分析"""

    # ========================================
    # /mdpaper.clarify - Refine content
    # ========================================
    @mcp.prompt(name="clarify", description="Refine content")
    def mdpaper_clarify() -> str:
        return """list_drafts() → 詢問要改進哪個 draft → read_draft() → 改進（尊重🔒區塊）→ write_draft()"""

    # ========================================
    # /mdpaper.format - Export to Word
    # ========================================
    @mcp.prompt(name="format", description="Export to Word")
    def mdpaper_format() -> str:
        return """read_template() → read_draft() → start_document_session() → insert_section() per section → verify_document() → save_document()"""
