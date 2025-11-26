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
        current = pm.get_current_project()
        
        if current:
            # Direct instruction to call the elicitation tool
            return f"Call setup_project_interactive() now to configure project '{current}' with interactive prompts."
        elif project_name:
            return f"First call create_project(name=\"{project_name}\"), then call setup_project_interactive() to configure it."
        else:
            return "Call list_projects() to see available projects, then ask user which to configure."

    # ========================================
    # /mdpaper.concept - Develop research concept
    # ========================================
    @mcp.prompt(name="concept", description="Develop research concept with literature-based gap analysis")
    def mdpaper_concept(topic: str) -> str:
        pm = get_project_manager()
        current = pm.get_current_project()
        
        if not current:
            return f"""[AGENT INSTRUCTION] Develop concept for "{topic}" but NO PROJECT SELECTED.
First ask: "I'll help you develop this concept. Should I create a new project for '{topic}'?"
If yes: create_project(name="{topic}") then proceed with concept development."""
        
        return f"""[AGENT INSTRUCTION] Develop research concept for "{topic}" in project "{current}".

WORKFLOW (do these steps, don't show them to user):
1. search_literature() for the topic - find 5-10 recent papers
2. save_reference() for key papers
3. Present findings to user: "I found these key studies..." 
4. Identify research gaps and ASK user: "Based on the literature, I see these gaps... Which one does your research address?"
5. WAIT for user confirmation
6. After confirmation, write concept with write_draft() including:
   - 🔒 NOVELTY STATEMENT (ask user to define)
   - 🔒 KEY SELLING POINTS (ask user for 3-5 points)
   - Background, Research Gap, Methods, Expected Outcomes

Start by saying: "I'll search the literature on {topic} to identify research gaps. One moment..."
Then call search_literature()."""

    # ========================================
    # /mdpaper.strategy - Configure search strategy
    # ========================================
    @mcp.prompt(name="strategy", description="Configure search strategy")
    def mdpaper_strategy(keywords: str) -> str:
        return f"""[AGENT INSTRUCTION] Configure literature search strategy for "{keywords}".

Ask user these questions ONE AT A TIME:
1. "What specific keywords should I search for?" (suggest: {keywords})
2. "Any terms to exclude?"
3. "What year range? (e.g., 2020-2024)"
4. "Article types? (e.g., Clinical Trial, Review, Meta-Analysis)"
5. "Minimum sample size if applicable?"

After collecting answers, call configure_search_strategy() with the criteria.
Start by asking about keywords."""

    # ========================================
    # /mdpaper.draft - Write paper section
    # ========================================
    @mcp.prompt(name="draft", description="Write paper draft")
    def mdpaper_draft(section: str) -> str:
        pm = get_project_manager()
        current = pm.get_current_project()
        
        if not current:
            return f"""[AGENT INSTRUCTION] Write {section} but NO PROJECT SELECTED.
Call list_projects() and ask user which project to work on."""
        
        return f"""[AGENT INSTRUCTION] Write the {section} section for project "{current}".

WORKFLOW (internal, don't display):
1. FIRST: Check for concept file using list_drafts() - concept file is MANDATORY
2. If no concept: Tell user "I need to understand your research concept first. Let's develop it." Then use /mdpaper.concept workflow
3. If concept exists: Read it with read_draft() to understand the research
4. Note any 🔒 protected sections - these MUST be incorporated
5. Check list_saved_references() for available citations
6. Get section guidelines with get_section_template("{section}")
7. Write with write_draft() or draft_section()
8. Check word count with count_words()

Start by saying: "I'll write the {section} section. Let me first review your research concept..."
Then call list_drafts() to find the concept file."""

    # ========================================
    # /mdpaper.analysis - Analyze data
    # ========================================
    @mcp.prompt(name="analysis", description="Analyze data")
    def mdpaper_data_analysis() -> str:
        pm = get_project_manager()
        
        try:
            paths = pm.get_project_paths()
            data_dir = paths.get("data", "data")
        except:
            data_dir = "data"
        
        return f"""[AGENT INSTRUCTION] Analyze research data in "{data_dir}/".

WORKFLOW:
1. List files in data directory
2. Ask user: "Which dataset would you like to analyze?"
3. Once selected, ask: "What analysis do you need?"
   - Descriptive statistics (analyze_dataset)
   - Table 1 baseline characteristics (generate_table_one) 
   - Statistical tests (run_statistical_test)
   - Visualizations (create_plot)
4. Run the appropriate analysis tool
5. Present results and ask if they need more analysis

Start by saying: "Let me check what data files are available..."
Then list the data directory contents."""

    # ========================================
    # /mdpaper.clarify - Refine content
    # ========================================
    @mcp.prompt(name="clarify", description="Refine content")
    def mdpaper_clarify() -> str:
        pm = get_project_manager()
        
        try:
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
        except:
            drafts_dir = "drafts"
        
        return f"""[AGENT INSTRUCTION] Refine paper content in "{drafts_dir}/".

WORKFLOW:
1. Call list_drafts() to see available drafts
2. Ask user: "Which draft would you like to refine?"
3. Ask: "What kind of refinement?"
   - Make more formal/academic
   - Shorten for word limits
   - Add citations
   - Improve clarity
   - Grammar and style check
4. Read the draft with read_draft()
5. Make improvements (respecting 🔒 protected sections)
6. Save with write_draft()

Start by saying: "I'll help refine your draft. Let me see what's available..."
Then call list_drafts()."""

    # ========================================
    # /mdpaper.format - Export to Word
    # ========================================
    @mcp.prompt(name="format", description="Export to Word")
    def mdpaper_format() -> str:
        return """[AGENT INSTRUCTION] Export draft to Word document.

WORKFLOW (8 steps):
1. list_drafts() - find available drafts
2. list_templates() - find available Word templates
3. Ask user which draft and template to use
4. read_template() - understand template structure
5. read_draft() - get draft content
6. start_document_session() - begin export
7. insert_section() - for each section, map draft content to template sections
8. verify_document() - check all content inserted
9. check_word_limits() - verify limits met
10. save_document() - export final file

Start by saying: "I'll export your draft to Word. Let me check available drafts and templates..."
Then call list_drafts() and list_templates()."""
