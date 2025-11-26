"""
MCP Prompts Module

All prompt definitions for the MedPaper Assistant.
Prompts provide guided workflows for common tasks.
"""

import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.core.template_reader import TemplateReader
from med_paper_assistant.core.project_manager import get_project_manager


def _get_concept_template() -> str:
    """Load the concept template from internal templates directory."""
    template_path = Path(__file__).parent.parent / "templates" / "concept_template.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return ""


def _get_project_status() -> str:
    """Get current project status for prompt context."""
    pm = get_project_manager()
    current = pm.get_current_project()
    
    if current:
        info = pm.get_project_info(current)
        if info.get("success"):
            paths = info.get("paths", {})
            stats = info.get("stats", {})
            return f"""
📁 **Current Project:** {info.get('name', current)} ({current})
   Status: {info.get('status', 'unknown')} | Drafts: {stats.get('drafts', 0)} | Refs: {stats.get('references', 0)}
   Paths: drafts → `{paths.get('drafts', '')}`, refs → `{paths.get('references', '')}`
"""
    
    # No project selected
    projects = pm.list_projects()
    if projects.get("projects"):
        project_list = ", ".join([p["slug"] for p in projects["projects"]])
        return f"""
⚠️ **No Project Selected!**
   Available: {project_list}
   → Use `switch_project(slug)` to select, or `create_project(name)` to create new.
"""
    else:
        return """
⚠️ **No Projects Found!**
   → Use `create_project(name="Your Research Topic")` to start.
   → This creates isolated directories for drafts, references, data, and results.
"""


def register_prompts(mcp: FastMCP, template_reader: TemplateReader):
    """Register all prompts with the MCP server."""
    
    @mcp.prompt(name="concept", description="Develop research concept with literature-based gap analysis")
    def mdpaper_concept(topic: str) -> str:
        """
        Develop a research concept with mandatory literature search and user confirmation.
        
        Args:
            topic: Your research topic or hypothesis
        """
        message = f"Help me develop a research concept about: **{topic}**\n\n"
        
        # Project status check
        message += "=" * 60 + "\n"
        message += "📁 **PROJECT STATUS**\n"
        message += "=" * 60 + "\n"
        message += _get_project_status() + "\n"
        
        # If no project, prompt to create one
        pm = get_project_manager()
        if not pm.get_current_project():
            message += "🔴 **ACTION REQUIRED:** Create or select a project first!\n"
            message += "```\n"
            message += f'create_project(name="{topic}", description="Research on {topic}")\n'
            message += "```\n"
            message += "This ensures all your work is organized in one place.\n\n"
        
        message += "=" * 60 + "\n"
        message += "📋 **CONCEPT DEVELOPMENT WORKFLOW**\n"
        message += "=" * 60 + "\n\n"
        
        message += "⚠️ **MANDATORY WORKFLOW** - Complete ALL steps in order:\n\n"
        
        message += "---\n"
        message += "## 📚 STEP 1: Literature Search (REQUIRED)\n"
        message += "---\n"
        message += "You MUST search existing literature FIRST:\n\n"
        message += "```\n"
        message += "1. Use `search_literature` with topic keywords\n"
        message += "2. Find 5-10 relevant recent studies\n"
        message += "3. Use `save_reference` for key papers\n"
        message += "4. Summarize what's been done:\n"
        message += "   - Main findings of existing studies\n"
        message += "   - Methods commonly used\n"
        message += "   - Limitations mentioned in papers\n"
        message += "```\n\n"
        
        message += "---\n"
        message += "## 🔍 STEP 2: Research Gap Identification (REQUIRED)\n"
        message += "---\n"
        message += "Based on literature, identify gaps and **ASK USER TO CONFIRM**:\n\n"
        message += "```\n"
        message += "Present to user:\n"
        message += "┌─────────────────────────────────────────────────────┐\n"
        message += "│ 📊 LITERATURE SUMMARY                               │\n"
        message += "│ • Study 1: [brief finding]                         │\n"
        message += "│ • Study 2: [brief finding]                         │\n"
        message += "│ • Study 3: [brief finding]                         │\n"
        message += "├─────────────────────────────────────────────────────┤\n"
        message += "│ 🔍 IDENTIFIED RESEARCH GAPS                         │\n"
        message += "│ 1. Gap A: [what hasn't been studied]               │\n"
        message += "│ 2. Gap B: [limitation of current methods]          │\n"
        message += "│ 3. Gap C: [unexplored population/setting]          │\n"
        message += "├─────────────────────────────────────────────────────┤\n"
        message += "│ ❓ QUESTIONS FOR USER                               │\n"
        message += "│ • Which gap does your research address?            │\n"
        message += "│ • Any gaps I missed?                               │\n"
        message += "│ • What's your unique approach?                     │\n"
        message += "└─────────────────────────────────────────────────────┘\n"
        message += "```\n\n"
        message += "🛑 **STOP AND WAIT** for user response before proceeding!\n\n"
        
        message += "---\n"
        message += "## ✍️ STEP 3: Concept Writing (After User Confirmation)\n"
        message += "---\n"
        message += "Only after user confirms the gap, write concept using TEMPLATE:\n\n"
        
        message += "### 🔒 PROTECTED Sections (User must approve changes):\n"
        message += "| Section | Content | Status |\n"
        message += "|---------|---------|--------|\n"
        message += "| 🔒 NOVELTY STATEMENT | What's new, why not done before, what will change | ⚠️ REQUIRED |\n"
        message += "| 🔒 KEY SELLING POINTS | 3-5 key differentiators (user-defined) | ⚠️ REQUIRED |\n"
        message += "| 🔒 Author Notes | Personal notes, do not include in paper | Optional |\n\n"
        
        message += "### 📝 EDITABLE Sections (Can freely improve):\n"
        message += "| Section | Content |\n"
        message += "|---------|--------|\n"
        message += "| 📝 Background | Context from literature search |\n"
        message += "| 📝 Research Gap | Gap confirmed by user in Step 2 |\n"
        message += "| 📝 Research Question | Based on confirmed gap |\n"
        message += "| 📝 Methods Overview | Planned methodology |\n"
        message += "| 📝 Expected Outcomes | Anticipated results |\n"
        message += "| 📝 Target Journal | If known |\n\n"
        
        message += "---\n"
        message += "## ⚠️ CRITICAL RULES\n"
        message += "---\n"
        message += "1. **MUST search literature** before writing concept\n"
        message += "2. **MUST present gaps and ASK user** before finalizing\n"
        message += "3. **🔒 Protected content**: Ask user before any modification\n"
        message += "4. **📝 Editable content**: Can improve freely\n"
        message += "5. **Research Gap section**: Must include literature evidence\n\n"
        
        # Check for existing concept files in project or default location
        try:
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
            concept_output = f"`{paths.get('concept', 'concept.md')}`"
        except (ValueError, KeyError):
            drafts_dir = "drafts"
            concept_output = "`drafts/concept_{topic}.md`"
        
        concept_files = []
        if os.path.exists(drafts_dir):
            for f in os.listdir(drafts_dir):
                if f.endswith('.md') and 'concept' in f.lower():
                    concept_files.append(f)
        
        message += "---\n"
        message += "## 📁 CURRENT STATUS\n"
        message += "---\n"
        
        if concept_files:
            message += f"📄 **Existing Concept Files:** {', '.join(concept_files)}\n"
            message += "   → You may read these for reference or create a new one\n"
        else:
            message += "📄 **No existing concept files**\n"
            message += f"   → Will create: {concept_output}\n"
        
        message += f"\n**Output File:** {concept_output}\n"
        message += "\n**After Completion:** Use `validate_concept` to verify all required sections\n"
        
        return message

    @mcp.prompt(name="strategy", description="Configure search strategy")
    def mdpaper_strategy(keywords: str) -> str:
        """
        Configure literature search strategy.
        
        Args:
            keywords: Main keywords for searching (e.g., anesthesia, pain management)
        """
        message = f"Configure a literature search strategy for: {keywords}\n\n"
        message += _get_project_status()
        return message

    @mcp.prompt(name="draft", description="Write paper draft")
    def mdpaper_draft(section: str) -> str:
        """
        Write a paper draft section.
        
        Args:
            section: Which section to write (Introduction, Methods, Results, Discussion, or all)
        """
        pm = get_project_manager()
        
        # Get paths based on current project
        try:
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
            refs_dir = paths.get("references", "references")
        except (ValueError, KeyError):
            drafts_dir = "drafts"
            refs_dir = "references"
        
        # [MANDATORY] Find concept files - innovation and discussion depend on this!
        concept_files = []
        novelty_files = []
        if os.path.exists(drafts_dir):
            for f in os.listdir(drafts_dir):
                if f.endswith('.md'):
                    if 'concept' in f.lower():
                        concept_files.append(f)
                    if 'novelty' in f.lower():
                        novelty_files.append(f)
        
        message = f"Help me write the {section} section of my paper.\n\n"
        
        # Project status
        message += _get_project_status() + "\n"
        
        # [MANDATORY] Concept file section
        message += "=" * 60 + "\n"
        message += "⚠️  **[MANDATORY] CONCEPT FILE REQUIRED** ⚠️\n"
        message += "=" * 60 + "\n\n"
        
        if concept_files:
            message += "📋 **Found Concept Files (MUST USE):**\n"
            for i, cf in enumerate(concept_files, 1):
                message += f"  {i}. {drafts_dir}/{cf}\n"
            message += "\n"
            message += "🔴 **CRITICAL INSTRUCTION:**\n"
            message += "You MUST read the concept file(s) above using `read_draft` tool FIRST!\n"
            message += "The concept file contains:\n"
            message += "  - Research innovation and novelty\n"
            message += "  - Key hypotheses and study design\n"
            message += "  - Literature gaps being addressed\n"
            message += "  - Expected contributions\n"
            message += "\nWithout this, the paper will lack originality and meaningful discussion!\n"
            
            # Add protection reminder for structured concepts
            message += "\n" + "-" * 60 + "\n"
            message += "🔒 **PROTECTED CONTENT WARNING**\n"
            message += "-" * 60 + "\n"
            message += "If the concept file contains `🔒` markers, those sections are PROTECTED:\n"
            message += "- `🔒 NOVELTY STATEMENT` - Core innovation, must preserve in Introduction/Discussion\n"
            message += "- `🔒 KEY SELLING POINTS` - Must highlight throughout the paper\n"
            message += "- `🔒 Author Notes` - Do not include in paper, for reference only\n\n"
            message += "**Rules for Protected Content:**\n"
            message += "1. ✅ You MUST incorporate protected content into the paper\n"
            message += "2. ✅ You CAN refine wording for academic style\n"
            message += "3. ⛔ You MUST ASK before making substantial changes\n"
            message += "4. ⛔ NEVER delete or weaken protected selling points\n"
        else:
            message += "❌ **NO CONCEPT FILE FOUND!**\n\n"
            message += "🚨 **ACTION REQUIRED:**\n"
            message += "Before writing any section, you MUST first:\n"
            message += "  1. Use `/mdpaper.concept` prompt to develop research concept\n"
            message += "  2. OR use `write_draft` tool to create a concept file\n"
            message += "  3. The concept file should be named with 'concept' in the filename\n"
            message += "     (e.g., 'concept_study_topic.md')\n\n"
            message += "⛔ **DO NOT proceed with writing until a concept file exists!**\n"
        
        # Show novelty analysis if exists
        if novelty_files:
            message += "\n📊 **Novelty Analysis Available:**\n"
            for nf in novelty_files:
                message += f"  - {drafts_dir}/{nf}\n"
            message += "  (Contains literature gaps and innovation rationale)\n"
        
        message += "\n" + "-" * 60 + "\n"
        
        # Also list saved references
        saved_refs = []
        if os.path.exists(refs_dir):
            saved_refs = [d for d in os.listdir(refs_dir) if os.path.isdir(os.path.join(refs_dir, d))]
        
        message += "\n📚 **Saved References:** "
        if saved_refs:
            message += f"{len(saved_refs)} references available\n"
            message += "  Use `list_saved_references` to see details\n"
        else:
            message += "None (use `search_literature` and `save_reference` first)\n"
        
        message += "\n**Writing Workflow:**\n"
        message += "1. 📖 Read concept file (MANDATORY) - Note 🔒 protected sections\n"
        message += "2. 📚 Review saved references\n"
        message += "3. 📝 Get section template with `get_section_template`\n"
        message += "4. ✍️  Write section with `write_draft` or `draft_section`\n"
        message += "5. 🔢 Check word count with `count_words`\n"
        message += "6. ✅ Verify protected content is preserved\n"
        
        return message

    @mcp.prompt(name="analysis", description="Analyze data")
    def mdpaper_data_analysis() -> str:
        """
        Analyze research data.
        
        This prompt automatically lists available data files for analysis.
        """
        pm = get_project_manager()
        
        # Get data directory based on current project
        try:
            paths = pm.get_project_paths()
            data_dir = paths.get("data", "data")
        except (ValueError, KeyError):
            data_dir = "data"
        
        data_files = []
        if os.path.exists(data_dir):
            data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        
        message = "Analyze research data.\n\n"
        message += _get_project_status() + "\n"
        
        message += "📊 **Available Data Files:**\n"
        if data_files:
            for i, f in enumerate(data_files, 1):
                message += f"  {i}. {data_dir}/{f}\n"
        else:
            message += f"  (No CSV files found in {data_dir}/ folder)\n"
        
        message += "\n**Available Analysis Tools:**\n"
        message += "- `analyze_dataset` - Get descriptive statistics\n"
        message += "- `generate_table_one` - Create Table 1 (baseline characteristics)\n"
        message += "- `run_statistical_test` - Run t-test, correlation, etc.\n"
        message += "- `create_plot` - Create scatter, bar, box, histogram plots\n"
        
        message += "\nPlease help me analyze my data."
        
        return message

    @mcp.prompt(name="clarify", description="Refine content")
    def mdpaper_clarify() -> str:
        """
        Refine paper content.
        
        This prompt lists available drafts for refinement.
        """
        pm = get_project_manager()
        
        # Get drafts directory based on current project
        try:
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
        except (ValueError, KeyError):
            drafts_dir = "drafts"
        
        drafts = []
        if os.path.exists(drafts_dir):
            drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
        
        message = "Refine paper content.\n\n"
        message += _get_project_status() + "\n"
        
        message += "📄 **Available Drafts:**\n"
        if drafts:
            for i, d in enumerate(drafts, 1):
                message += f"  {i}. {drafts_dir}/{d}\n"
        else:
            message += "  (No drafts found)\n"
        
        message += "\n**Refinement Options:**\n"
        message += "- Make language more formal/academic\n"
        message += "- Shorten to meet word limits\n"
        message += "- Add more citations\n"
        message += "- Improve clarity and flow\n"
        message += "- Check grammar and style\n"
        
        message += "\nWhich draft would you like to refine, and what changes do you need?"
        
        return message

    @mcp.prompt(name="format", description="Export to Word")
    def mdpaper_format() -> str:
        """
        Export draft to Word document.
        
        This prompt automatically lists available drafts and templates.
        """
        pm = get_project_manager()
        
        # Get directories based on current project
        try:
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
            results_dir = paths.get("results", "results")
        except (ValueError, KeyError):
            drafts_dir = "drafts"
            results_dir = "results"
        
        # Get available drafts
        drafts = []
        if os.path.exists(drafts_dir):
            drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
        
        # Get available templates
        templates = template_reader.list_templates()
        
        message = "Export a draft to Word format.\n\n"
        message += _get_project_status() + "\n"
        
        message += "📄 **Available Drafts:**\n"
        if drafts:
            for i, d in enumerate(drafts, 1):
                message += f"  {i}. {drafts_dir}/{d}\n"
        else:
            message += f"  (No drafts found in {drafts_dir}/ folder)\n"
        
        message += "\n📋 **Available Templates:**\n"
        if templates:
            for i, t in enumerate(templates, 1):
                message += f"  {i}. {t}\n"
        else:
            message += "  (No templates found)\n"
        
        message += f"\n**Output Location:** `{results_dir}/`\n"
        message += "\nPlease help me export a draft to Word. "
        message += "Use the 8-step workflow: read_template → read_draft → start_document_session → "
        message += "insert_section (for each section) → verify_document → check_word_limits → save_document"
        
        return message
