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

# Infrastructure modules (DDD architecture)
from med_paper_assistant.infrastructure.logging import setup_logger
from med_paper_assistant.infrastructure.persistence import (
    ReferenceManager,
    ProjectManager,
)
from med_paper_assistant.infrastructure.services import (
    Analyzer,
    Drafter,
    Formatter,
    TemplateReader,
    WordWriter,
    StrategyManager,
)
from med_paper_assistant.infrastructure.external.pubmed import PubMedClient

# Server modules
from med_paper_assistant.interfaces.mcp.config import SERVER_INSTRUCTIONS, DEFAULT_EMAIL
from med_paper_assistant.interfaces.mcp.tools import (
    register_search_tools,
    register_reference_tools,
    register_draft_tools,
    register_analysis_tools,
    register_export_tools,
    register_diagram_tools,
)
from med_paper_assistant.interfaces.mcp.tools.project_tools import register_project_tools
from med_paper_assistant.interfaces.mcp.prompts import register_prompts


# Create a LiteratureSearcher-compatible wrapper
class LiteratureSearcher:
    """Wrapper for backward compatibility with existing code."""
    def __init__(self, email: str):
        self._client = PubMedClient(email=email)
        # Also initialize the Entrez searcher for PDF downloads
        from med_paper_assistant.infrastructure.external.entrez import LiteratureSearcher as EntrezSearcher
        self._entrez_searcher = EntrezSearcher(email=email)
    
    def search(self, query, limit=5, min_year=None, max_year=None, article_type=None, strategy="relevance", date_from=None, date_to=None, date_type="edat"):
        # Use Entrez searcher directly for full date support
        results = self._entrez_searcher.search(
            query, limit, min_year, max_year, article_type, strategy,
            date_from=date_from, date_to=date_to, date_type=date_type
        )
        return results
    
    def fetch_details(self, id_list):
        results = self._client.fetch_by_pmids(id_list)
        return [r.to_dict() for r in results]
    
    def find_related_articles(self, pmid, limit=5):
        results = self._client.find_related(pmid, limit)
        return [r.to_dict() for r in results]
    
    def find_citing_articles(self, pmid, limit=10):
        results = self._client.find_citing(pmid, limit)
        return [r.to_dict() for r in results]
    
    def download_pdf(self, pmid):
        return self._client.download_pdf(pmid)
    
    def download_pmc_pdf(self, pmid: str, output_path: str) -> bool:
        """
        Download PDF from PubMed Central if available.
        
        Uses the Entrez searcher's PDF download functionality which:
        1. Finds the PMC ID via elink
        2. Downloads the PDF from PMC Open Access
        
        Args:
            pmid: PubMed ID.
            output_path: Path to save the PDF file.
            
        Returns:
            True if download successful, False otherwise.
        """
        return self._entrez_searcher.download_pmc_pdf(pmid, output_path)


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
    logger.info("Registering project tools...")
    register_project_tools(mcp, project_manager)
    
    logger.info("Registering search tools...")
    register_search_tools(mcp, searcher, strategy_manager)
    
    logger.info("Registering reference tools...")
    register_reference_tools(mcp, ref_manager, drafter)
    
    logger.info("Registering draft tools...")
    register_draft_tools(mcp, drafter)
    
    logger.info("Registering analysis tools...")
    register_analysis_tools(mcp, analyzer)
    
    logger.info("Registering diagram tools...")
    register_diagram_tools(mcp, project_manager)
    
    logger.info("Registering export tools...")
    register_export_tools(mcp, formatter, template_reader, word_writer)

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
