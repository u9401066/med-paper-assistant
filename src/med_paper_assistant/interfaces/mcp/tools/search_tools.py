"""
Search Tools Module

Tools for literature search, search strategy configuration, and result formatting.
"""

import json
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.external.pubmed.client import SearchStrategy
from med_paper_assistant.infrastructure.services import StrategyManager
from med_paper_assistant.infrastructure.logging import setup_logger

logger = setup_logger()


def format_search_results(results: list, include_doi: bool = True) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."
        
    if "error" in results[0]:
        return f"Error searching PubMed: {results[0]['error']}"
        
    formatted_output = f"Found {len(results)} results:\n\n"
    for i, paper in enumerate(results, 1):
        formatted_output += f"{i}. **{paper['title']}**\n"
        authors = paper.get('authors', [])
        formatted_output += f"   Authors: {', '.join(authors[:3])}{' et al.' if len(authors) > 3 else ''}\n"
        journal = paper.get('journal', 'Unknown Journal')
        year = paper.get('year', '')
        volume = paper.get('volume', '')
        pages = paper.get('pages', '')
        
        journal_info = f"{journal} ({year})"
        if volume:
            journal_info += f"; {volume}"
            if pages:
                journal_info += f": {pages}"
        formatted_output += f"   Journal: {journal_info}\n"
        formatted_output += f"   PMID: {paper.get('pmid', '')}"
        
        if include_doi and paper.get('doi'):
            formatted_output += f" | DOI: {paper['doi']}"
        if paper.get('pmc_id'):
            formatted_output += f" | PMC: {paper['pmc_id']} 📄"
        
        formatted_output += "\n"
        
        abstract = paper.get('abstract', '')
        if abstract:
            formatted_output += f"   Abstract: {abstract[:200]}...\n"
        formatted_output += "\n"
        
    return formatted_output


def register_search_tools(mcp: FastMCP, searcher, strategy_manager: StrategyManager):
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

    @mcp.tool()
    def find_related_articles(pmid: str, limit: int = 5) -> str:
        """
        Find articles related to a given PubMed article.
        Uses PubMed's "Related Articles" feature to find similar papers.
        
        Args:
            pmid: PubMed ID of the source article.
            limit: Maximum number of related articles to return.
            
        Returns:
            List of related articles with details.
        """
        logger.info(f"Finding related articles for PMID: {pmid}")
        try:
            results = searcher.get_related_articles(pmid, limit)
            
            if not results:
                return f"No related articles found for PMID {pmid}."
            
            if "error" in results[0]:
                return f"Error finding related articles: {results[0]['error']}"
            
            output = f"📚 **Related Articles for PMID {pmid}** ({len(results)} found)\n\n"
            output += format_search_results(results)
            return output
        except Exception as e:
            logger.error(f"Find related articles failed: {e}")
            return f"Error: {e}"

    @mcp.tool()
    def find_citing_articles(pmid: str, limit: int = 10) -> str:
        """
        Find articles that cite a given PubMed article.
        Uses PubMed Central's citation data to find papers that reference this article.
        
        Args:
            pmid: PubMed ID of the source article.
            limit: Maximum number of citing articles to return.
            
        Returns:
            List of citing articles with details.
        """
        logger.info(f"Finding citing articles for PMID: {pmid}")
        try:
            results = searcher.get_citing_articles(pmid, limit)
            
            if not results:
                return f"No citing articles found for PMID {pmid}. (Article may not be indexed in PMC or has no citations yet.)"
            
            if "error" in results[0]:
                return f"Error finding citing articles: {results[0]['error']}"
            
            output = f"📖 **Articles Citing PMID {pmid}** ({len(results)} found)\n\n"
            output += format_search_results(results)
            return output
        except Exception as e:
            logger.error(f"Find citing articles failed: {e}")
            return f"Error: {e}"
