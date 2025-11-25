"""
Search Tools Module

Tools for literature search, search strategy configuration, and result formatting.
"""

import json
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.core.search import LiteratureSearcher, SearchStrategy
from med_paper_assistant.core.strategy_manager import StrategyManager
from med_paper_assistant.core.logger import setup_logger

logger = setup_logger()


def format_search_results(results: list) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."
        
    if "error" in results[0]:
        return f"Error searching PubMed: {results[0]['error']}"
        
    formatted_output = f"Found {len(results)} results:\n\n"
    for i, paper in enumerate(results, 1):
        formatted_output += f"{i}. {paper['title']}\n"
        formatted_output += f"   Authors: {', '.join(paper['authors'][:3])}{' et al.' if len(paper['authors']) > 3 else ''}\n"
        formatted_output += f"   Journal: {paper['journal']} ({paper['year']})\n"
        formatted_output += f"   PMID: {paper['pmid']}\n"
        formatted_output += f"   Abstract: {paper['abstract'][:200]}...\n\n"
        
    return formatted_output


def register_search_tools(mcp: FastMCP, searcher: LiteratureSearcher, strategy_manager: StrategyManager):
    """Register all search-related tools with the MCP server."""
    
    @mcp.tool()
    def configure_search_strategy(criteria_json: str) -> str:
        """
        Save a structured search strategy.
        
        Args:
            criteria_json: JSON string with keys: keywords (list), exclusions (list), 
                          article_types (list), min_sample_size (int), date_range (str).
        """
        try:
            criteria = json.loads(criteria_json)
            return strategy_manager.save_strategy(criteria)
        except Exception as e:
            return f"Error configuring strategy: {str(e)}"

    @mcp.tool()
    def get_search_strategy() -> str:
        """Get the currently saved search strategy."""
        strategy = strategy_manager.load_strategy()
        if not strategy:
            return "No strategy saved."
        return json.dumps(strategy.dict(), indent=2)

    @mcp.tool()
    def search_literature(
        query: str = "", 
        limit: int = 5, 
        min_year: int = None, 
        max_year: int = None, 
        article_type: str = None, 
        strategy: str = "relevance", 
        use_saved_strategy: bool = False
    ) -> str:
        """
        Search for medical literature based on a query using PubMed.
        
        Args:
            query: The search query (e.g., "diabetes treatment guidelines"). 
                   Required if use_saved_strategy is False.
            limit: The maximum number of results to return.
            min_year: Optional minimum publication year (e.g., 2020).
            max_year: Optional maximum publication year.
            article_type: Optional article type (e.g., "Review", "Clinical Trial", "Meta-Analysis").
            strategy: Search strategy ("recent", "most_cited", "relevance", "impact", "agent_decided"). 
                     Default is "relevance".
            use_saved_strategy: If True, uses the criteria from configure_search_strategy.
        """
        logger.info(f"Searching literature: query='{query}', limit={limit}, strategy='{strategy}'")
        try:
            min_sample_size = None
            
            if use_saved_strategy:
                saved_criteria = strategy_manager.load_strategy()
                if saved_criteria:
                    query = strategy_manager.build_pubmed_query(saved_criteria)
                    min_sample_size = saved_criteria.min_sample_size
                    logger.info(f"Using saved strategy. Generated query: {query}")
                else:
                    return "Error: No saved strategy found. Please use configure_search_strategy first."
            
            if not query:
                return "Error: Query is required unless use_saved_strategy is True and a strategy is saved."

            results = searcher.search(query, limit, min_year, max_year, article_type, strategy)
            
            if min_sample_size:
                results = searcher.filter_results(results, min_sample_size)
                
            return format_search_results(results[:limit])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Error: {e}"
