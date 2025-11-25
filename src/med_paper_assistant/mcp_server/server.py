"""
MedPaper Assistant MCP Server

A Model Context Protocol server for medical paper writing assistance.
This server provides tools for:
- Literature search and reference management
- Draft creation and editing
- Data analysis and visualization
- Word document export with templates

Architecture:
    server.py (this file) - Main entry point, initializes and registers all modules
    config.py - Server configuration and constants
    tools/ - MCP tool definitions organized by functionality
        search_tools.py - Literature search and strategy
        reference_tools.py - Reference and citation management
        draft_tools.py - Draft creation and word counting
        analysis_tools.py - Data analysis and visualization
        export_tools.py - Word document export workflow
    prompts/ - MCP prompt definitions
        prompts.py - Guided workflows for common tasks
"""

from mcp.server.fastmcp import FastMCP

# Core modules
from med_paper_assistant.core.search import LiteratureSearcher
from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.drafter import Drafter
from med_paper_assistant.core.analyzer import Analyzer
from med_paper_assistant.core.formatter import Formatter
from med_paper_assistant.core.template_reader import TemplateReader
from med_paper_assistant.core.word_writer import WordWriter
from med_paper_assistant.core.logger import setup_logger
from med_paper_assistant.core.strategy_manager import StrategyManager

# Server modules
from med_paper_assistant.mcp_server.config import SERVER_INSTRUCTIONS, DEFAULT_EMAIL
from med_paper_assistant.mcp_server.tools import (
    register_search_tools,
    register_reference_tools,
    register_draft_tools,
    register_analysis_tools,
    register_export_tools,
)
from med_paper_assistant.mcp_server.prompts import register_prompts


def create_server() -> FastMCP:
    """
    Create and configure the MedPaper Assistant MCP server.
    
    This function:
    1. Initializes all core modules (searcher, analyzer, etc.)
    2. Creates the FastMCP server instance
    3. Registers all tools and prompts
    
    Returns:
        Configured FastMCP server instance
    """
    # Setup logging
    logger = setup_logger()
    logger.info("Initializing MedPaper Assistant MCP Server...")

    # Initialize core modules
    searcher = LiteratureSearcher(email=DEFAULT_EMAIL)
    analyzer = Analyzer()
    ref_manager = ReferenceManager(searcher)
    drafter = Drafter(ref_manager)
    formatter = Formatter()
    template_reader = TemplateReader()
    word_writer = WordWriter()
    strategy_manager = StrategyManager()

    # Create MCP server
    mcp = FastMCP("MedPaperAssistant", instructions=SERVER_INSTRUCTIONS)

    # Register all tools
    logger.info("Registering search tools...")
    register_search_tools(mcp, searcher, strategy_manager)
    
    logger.info("Registering reference tools...")
    register_reference_tools(mcp, ref_manager, drafter)
    
    logger.info("Registering draft tools...")
    register_draft_tools(mcp, drafter)
    
    logger.info("Registering analysis tools...")
    register_analysis_tools(mcp, analyzer)
    
    logger.info("Registering export tools...")
    register_export_tools(mcp, formatter, template_reader, word_writer)

    # Register prompts
    logger.info("Registering prompts...")
    register_prompts(mcp, template_reader)

    logger.info("MedPaper Assistant MCP Server initialized successfully!")
    return mcp


# Create the server instance
mcp = create_server()


if __name__ == "__main__":
    mcp.run()
