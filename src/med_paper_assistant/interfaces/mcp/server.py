"""
MedPaper Assistant MCP Server

A Model Context Protocol server for medical paper writing assistance.
This server provides tools for:
- Literature search and reference management (via pubmed-search-mcp submodule)
- Draft creation and editing
- Word document export with templates

Architecture:
    server.py (this file) - Main entry point, initializes and registers all modules
    config.py - Server configuration and constants
    tools/ - MCP tool definitions organized by functionality
        project/     - Project management (CRUD, settings, exploration, diagrams)
        draft/       - Draft writing and templates
        search/      - Literature search (PubMed) - uses pubmed-search-mcp submodule
        reference/   - Reference management and citation
        validation/  - Concept and idea validation
        export/      - Word document export
        skill/       - Workflow skills management
        _shared/     - Shared utilities
    prompts/ - MCP prompt definitions

Removed:
    analysis/    - Moved to separate data-analysis-mcp project
    diagram/     - Merged into project/ module
"""

from mcp.server.fastmcp import FastMCP

# Infrastructure modules (DDD architecture)
from med_paper_assistant.infrastructure.logging import setup_logger
from med_paper_assistant.infrastructure.persistence import (
    ReferenceManager,
    ProjectManager,
)
from med_paper_assistant.infrastructure.services import (
    Drafter,
    Formatter,
    TemplateReader,
    WordWriter,
    StrategyManager,
)
# Use LiteratureSearcher from pubmed-search-mcp submodule
from pubmed_search.entrez import LiteratureSearcher

# Server modules
from med_paper_assistant.interfaces.mcp.config import SERVER_INSTRUCTIONS, DEFAULT_EMAIL
from med_paper_assistant.interfaces.mcp.tools import (
    register_project_tools,
    register_search_tools,
    register_reference_tools,
    register_draft_tools,
    register_validation_tools,
    register_export_tools,
)
from med_paper_assistant.interfaces.mcp.tools.skill import register_skill_tools
from med_paper_assistant.interfaces.mcp.prompts import register_prompts


def create_server() -> FastMCP:
    """
    Create and configure the MedPaper Assistant MCP server.
    
    This function:
    1. Initializes all core modules (searcher, etc.)
    2. Creates the FastMCP server instance
    3. Registers all tools and prompts
    
    Returns:
        Configured FastMCP server instance
    """
    # Setup logging
    logger = setup_logger()
    logger.info("Initializing MedPaper Assistant MCP Server...")

    # Initialize core modules
    # Use LiteratureSearcher directly from pubmed-search-mcp submodule
    searcher = LiteratureSearcher(email=DEFAULT_EMAIL)
    project_manager = ProjectManager()  # Multi-project support
    ref_manager = ReferenceManager(searcher, project_manager=project_manager)
    drafter = Drafter(ref_manager, project_manager=project_manager)
    formatter = Formatter()
    template_reader = TemplateReader()
    word_writer = WordWriter()
    strategy_manager = StrategyManager()

    # Create MCP server
    mcp = FastMCP("MedPaperAssistant", instructions=SERVER_INSTRUCTIONS)

    # Register all tools
    logger.info("Registering project tools (incl. diagrams)...")
    register_project_tools(mcp, project_manager)
    
    logger.info("Registering search tools...")
    register_search_tools(mcp, searcher, strategy_manager)
    
    logger.info("Registering reference tools...")
    register_reference_tools(mcp, ref_manager, drafter, project_manager)
    
    logger.info("Registering draft tools...")
    register_draft_tools(mcp, drafter)
    
    logger.info("Registering validation tools...")
    register_validation_tools(mcp)
    
    logger.info("Registering export tools...")
    register_export_tools(mcp, formatter, template_reader, word_writer)

    logger.info("Registering skill tools...")
    register_skill_tools(mcp)

    # Register prompts
    logger.info("Registering prompts...")
    register_prompts(mcp, template_reader)

    logger.info("MedPaper Assistant MCP Server initialized successfully!")
    return mcp


# Note: Server instance is created lazily via __main__.py or create_server()
# This avoids RuntimeWarning when running with python -m

if __name__ == "__main__":
    # Direct execution (not recommended, use python -m instead)
    mcp = create_server()
    mcp.run()
