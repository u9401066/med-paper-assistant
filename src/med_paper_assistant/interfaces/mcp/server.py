"""
MedPaper Assistant MCP Server

A Model Context Protocol server for medical paper writing assistance.
This server provides tools for:
- Project and concept management
- Draft creation and editing
- Reference management
- Data analysis and Table 1 generation
- Word document export with templates

Architecture:
    server.py (this file) - Main entry point, initializes and registers all modules
    config.py - Server configuration and constants
    tools/ - MCP tool definitions organized by functionality
        project/     - Project management (CRUD, settings, exploration, diagrams)
        draft/       - Draft writing and templates
        reference/   - Reference management and citation
        validation/  - Concept and idea validation
        analysis/    - Data analysis and Table 1 generation
        export/      - Word document export
        _shared/     - Shared utilities
    prompts/ - MCP prompt definitions

External MCP Services (use via VS Code Copilot):
    pubmed-search  - Literature search (PubMed/Entrez)
    cgu            - Creativity generation for research ideas
    zotero-keeper  - Bibliography management
    drawio         - Diagram generation

Note: Skill tools removed (2025-12-17) - VS Code Copilot now has built-in
      support for .claude/skills/ via the skills attachment system.
"""

from mcp.server.fastmcp import FastMCP

# Infrastructure modules (DDD architecture)
from med_paper_assistant.infrastructure.logging import setup_logger
from med_paper_assistant.infrastructure.persistence import (
    ProjectManager,
    ReferenceManager,
)
from med_paper_assistant.infrastructure.services import (
    Analyzer,
    Drafter,
    Formatter,
    TemplateReader,
    WordWriter,
)

# Server modules
from med_paper_assistant.interfaces.mcp.config import SERVER_INSTRUCTIONS
from med_paper_assistant.interfaces.mcp.prompts import register_prompts
from med_paper_assistant.interfaces.mcp.tools import (
    register_analysis_tools,
    register_draft_tools,
    register_export_tools,
    register_project_tools,
    register_reference_tools,
    register_review_tools,
    register_validation_tools,
)


def create_server() -> FastMCP:
    """
    Create and configure the MedPaper Assistant MCP server.

    This function:
    1. Initializes all core modules
    2. Creates the FastMCP server instance
    3. Registers all tools and prompts

    Note: Literature search is now handled by pubmed-search MCP server.
    Use VS Code Copilot to orchestrate cross-MCP calls.

    Returns:
        Configured FastMCP server instance
    """
    # Setup logging
    logger = setup_logger()
    logger.info("Initializing MedPaper Assistant MCP Server...")

    # Initialize core modules
    project_manager = ProjectManager()  # Multi-project support
    ref_manager = ReferenceManager(project_manager=project_manager)
    drafter = Drafter(ref_manager, project_manager=project_manager)
    formatter = Formatter()
    template_reader = TemplateReader()
    word_writer = WordWriter()
    analyzer = Analyzer()

    # Create MCP server
    mcp = FastMCP("MedPaperAssistant", instructions=SERVER_INSTRUCTIONS)

    # Register all tools
    logger.info("Registering project tools (incl. diagrams)...")
    register_project_tools(mcp, project_manager)

    logger.info("Registering reference tools...")
    register_reference_tools(mcp, ref_manager, drafter, project_manager)

    logger.info("Registering draft tools...")
    register_draft_tools(mcp, drafter)

    logger.info("Registering validation tools...")
    register_validation_tools(mcp)

    logger.info("Registering analysis tools...")
    register_analysis_tools(mcp, analyzer)

    logger.info("Registering review tools...")
    register_review_tools(mcp, drafter, ref_manager, project_manager)

    logger.info("Registering export tools...")
    register_export_tools(mcp, formatter, template_reader, word_writer)

    # Note: Skill tools removed - VS Code Copilot has built-in skill support
    # via .claude/skills/ directory attachment system

    # Register prompts
    logger.info("Registering prompts...")
    register_prompts(mcp, template_reader)

    logger.info("MedPaper Assistant MCP Server initialized successfully!")
    logger.info("Note: Use pubmed-search MCP for literature search.")
    return mcp


# Note: Server instance is created lazily via __main__.py or create_server()
# This avoids RuntimeWarning when running with python -m

if __name__ == "__main__":
    # Direct execution (not recommended, use python -m instead)
    mcp = create_server()
    mcp.run()
