"""
MCP Prompts Module

All prompt definitions for the MedPaper Assistant.
Prompts provide guided workflows for common tasks.
"""

import os
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.core.template_reader import TemplateReader


def register_prompts(mcp: FastMCP, template_reader: TemplateReader):
    """Register all prompts with the MCP server."""
    
    @mcp.prompt(name="concept", description="Develop research concept")
    def mdpaper_concept(topic: str) -> str:
        """
        Develop a research concept.
        
        Args:
            topic: Your research topic or hypothesis
        """
        return f"Help me develop a research concept about: {topic}"

    @mcp.prompt(name="strategy", description="Configure search strategy")
    def mdpaper_strategy(keywords: str) -> str:
        """
        Configure literature search strategy.
        
        Args:
            keywords: Main keywords for searching (e.g., anesthesia, pain management)
        """
        return f"Configure a literature search strategy for: {keywords}"

    @mcp.prompt(name="draft", description="Write paper draft")
    def mdpaper_draft(section: str) -> str:
        """
        Write a paper draft section.
        
        Args:
            section: Which section to write (Introduction, Methods, Results, Discussion, or all)
        """
        return f"Help me write the {section} section of my paper."

    @mcp.prompt(name="analysis", description="Analyze data")
    def mdpaper_data_analysis() -> str:
        """
        Analyze research data.
        
        This prompt automatically lists available data files for analysis.
        """
        data_dir = "data"
        data_files = []
        if os.path.exists(data_dir):
            data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        
        message = "Analyze research data.\n\n"
        
        message += "📊 **Available Data Files:**\n"
        if data_files:
            for i, f in enumerate(data_files, 1):
                message += f"  {i}. {f}\n"
        else:
            message += "  (No CSV files found in data/ folder)\n"
        
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
        drafts_dir = "drafts"
        drafts = []
        if os.path.exists(drafts_dir):
            drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
        
        message = "Refine paper content.\n\n"
        
        message += "📄 **Available Drafts:**\n"
        if drafts:
            for i, d in enumerate(drafts, 1):
                message += f"  {i}. {d}\n"
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
        # Get available drafts
        drafts_dir = "drafts"
        drafts = []
        if os.path.exists(drafts_dir):
            drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
        
        # Get available templates
        templates = template_reader.list_templates()
        
        message = "Export a draft to Word format.\n\n"
        
        message += "📄 **Available Drafts:**\n"
        if drafts:
            for i, d in enumerate(drafts, 1):
                message += f"  {i}. {d}\n"
        else:
            message += "  (No drafts found in drafts/ folder)\n"
        
        message += "\n📋 **Available Templates:**\n"
        if templates:
            for i, t in enumerate(templates, 1):
                message += f"  {i}. {t}\n"
        else:
            message += "  (No templates found)\n"
        
        message += "\nPlease help me export a draft to Word. "
        message += "Use the 8-step workflow: read_template → read_draft → start_document_session → "
        message += "insert_section (for each section) → verify_document → check_word_limits → save_document"
        
        return message
