"""
HTTP Client for MCP-to-MCP communication.

This module provides a client for mdpaper to communicate directly
with pubmed-search MCP via HTTP API, bypassing the Agent.

Author: u9401066@gap.kmu.edu.tw
"""

import logging
import os
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_PUBMED_API_URL = "http://127.0.0.1:8765"


class PubMedAPIClient:
    """
    HTTP client for communicating with pubmed-search MCP's HTTP API.
    
    This enables MCP-to-MCP direct communication for verified data:
    - mdpaper only receives PMID from Agent
    - mdpaper fetches verified metadata directly from pubmed-search
    - Prevents Agent from modifying/hallucinating bibliographic data
    """
    
    def __init__(
        self, 
        base_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: pubmed-search API URL (default from env or localhost:8765)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.environ.get(
            "PUBMED_MCP_API_URL", 
            DEFAULT_PUBMED_API_URL
        )
        self.timeout = timeout
        logger.info(f"PubMedAPIClient initialized with URL: {self.base_url}")
    
    def get_cached_article(
        self, 
        pmid: str, 
        fetch_if_missing: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get article metadata from pubmed-search cache.
        
        This is the primary method for MCP-to-MCP data retrieval.
        
        Args:
            pmid: PubMed ID
            fetch_if_missing: If True, pubmed-search will fetch from NCBI if not cached
            
        Returns:
            Article metadata dict with verified=True, or None if not found
        """
        try:
            url = f"{self.base_url}/api/cached_article/{pmid}"
            params = {"fetch_if_missing": str(fetch_if_missing).lower()}
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("verified"):
                        logger.info(f"[MCP-to-MCP] Retrieved verified article PMID:{pmid}")
                        return data.get("data")
                    else:
                        logger.warning(f"[MCP-to-MCP] Article not marked as verified: {pmid}")
                        return data.get("data")
                        
                elif response.status_code == 404:
                    logger.warning(f"[MCP-to-MCP] Article not found: PMID:{pmid}")
                    return None
                    
                else:
                    logger.error(f"[MCP-to-MCP] HTTP error {response.status_code}: {response.text}")
                    return None
                    
        except httpx.ConnectError:
            logger.error(
                f"[MCP-to-MCP] Cannot connect to pubmed-search API at {self.base_url}. "
                f"Is pubmed-search MCP running?"
            )
            return None
        except Exception as e:
            logger.error(f"[MCP-to-MCP] Error fetching article: {e}")
            return None
    
    def get_multiple_articles(
        self, 
        pmids: List[str], 
        fetch_if_missing: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple articles from pubmed-search cache.
        
        Args:
            pmids: List of PubMed IDs
            fetch_if_missing: If True, fetch missing articles from NCBI
            
        Returns:
            Dict mapping PMID to article metadata
        """
        try:
            url = f"{self.base_url}/api/cached_articles"
            params = {
                "pmids": ",".join(pmids),
                "fetch_if_missing": str(fetch_if_missing).lower()
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    found = data.get("found", {})
                    missing = data.get("missing", [])
                    
                    if missing:
                        logger.warning(f"[MCP-to-MCP] Missing articles: {missing}")
                    
                    logger.info(
                        f"[MCP-to-MCP] Retrieved {len(found)}/{len(pmids)} articles"
                    )
                    return found
                else:
                    logger.error(f"[MCP-to-MCP] HTTP error {response.status_code}")
                    return {}
                    
        except httpx.ConnectError:
            logger.error(f"[MCP-to-MCP] Cannot connect to pubmed-search API")
            return {}
        except Exception as e:
            logger.error(f"[MCP-to-MCP] Error: {e}")
            return {}
    
    def check_health(self) -> bool:
        """
        Check if pubmed-search API is available.
        
        Returns:
            True if API is healthy
        """
        try:
            url = f"{self.base_url}/health"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                return response.status_code == 200
        except:
            return False
    
    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get pubmed-search session summary.
        
        Returns:
            Session summary dict or None
        """
        try:
            url = f"{self.base_url}/api/session/summary"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return response.json()
                return None
        except:
            return None


# Singleton instance for convenience
_client: Optional[PubMedAPIClient] = None


def get_pubmed_api_client(
    base_url: Optional[str] = None,
    force_new: bool = False
) -> PubMedAPIClient:
    """
    Get or create the PubMed API client singleton.
    
    Args:
        base_url: Optional custom API URL
        force_new: If True, create a new instance
        
    Returns:
        PubMedAPIClient instance
    """
    global _client
    
    if _client is None or force_new:
        _client = PubMedAPIClient(base_url=base_url)
    
    return _client
