from Bio import Entrez
from typing import List, Dict, Any

from enum import Enum

class SearchStrategy(Enum):
    RECENT = "recent"
    MOST_CITED = "most_cited"  # Proxy: Relevance (PubMed doesn't support citation sort directly without PMC)
    RELEVANCE = "relevance"
    IMPACT = "impact"          # Proxy: Journal (or Relevance)
    AGENT_DECIDED = "agent_decided"

class LiteratureSearcher:
    def __init__(self, email: str = "your.email@example.com"):
        """
        Initialize the LiteratureSearcher.
        
        Args:
            email: Email address required by NCBI Entrez API.
        """
        Entrez.email = email

    def fetch_details(self, id_list: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch details for a list of PMIDs.
        
        Args:
            id_list: List of PubMed IDs.
            
        Returns:
            List of dictionaries containing article details.
        """
        if not id_list:
            return []

        try:
            handle = Entrez.efetch(db="pubmed", id=id_list, retmode="xml")
            papers = Entrez.read(handle)
            handle.close()
            
            results = []
            if 'PubmedArticle' in papers:
                for article in papers['PubmedArticle']:
                    medline_citation = article['MedlineCitation']
                    article_data = medline_citation['Article']
                    
                    title = article_data.get('ArticleTitle', 'No title')
                    
                    # Extract authors
                    authors = []
                    if 'AuthorList' in article_data:
                        for author in article_data['AuthorList']:
                            if 'LastName' in author and 'ForeName' in author:
                                authors.append(f"{author['LastName']} {author['ForeName']}")
                    
                    # Extract abstract
                    abstract_text = ""
                    if 'Abstract' in article_data and 'AbstractText' in article_data['Abstract']:
                        abstract_parts = article_data['Abstract']['AbstractText']
                        if isinstance(abstract_parts, list):
                            abstract_text = " ".join([str(part) for part in abstract_parts])
                        else:
                            abstract_text = str(abstract_parts)
                            
                    # Extract Journal info
                    journal = article_data.get('Journal', {}).get('Title', 'Unknown Journal')
                    pub_date = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
                    year = pub_date.get('Year', 'Unknown Year')

                    results.append({
                        "pmid": medline_citation.get('PMID', ''),
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                        "abstract": abstract_text
                    })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def search(self, query: str, limit: int = 5, min_year: int = None, max_year: int = None, article_type: str = None, strategy: str = "relevance") -> List[Dict[str, Any]]:
        """
        Search PubMed for articles using a specific strategy.
        
        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            min_year: Minimum publication year.
            max_year: Maximum publication year.
            article_type: Type of article (e.g., "Review", "Clinical Trial").
            strategy: Search strategy ("recent", "most_cited", "relevance", "impact", "agent_decided").
            
        Returns:
            List of dictionaries containing article details.
        """
        try:
            # Map strategy to PubMed sort parameter
            sort_param = "relevance" # Default
            
            if strategy == SearchStrategy.RECENT.value:
                sort_param = "pub_date"
            elif strategy == SearchStrategy.MOST_CITED.value:
                sort_param = "relevance" # Best proxy
            elif strategy == SearchStrategy.RELEVANCE.value:
                sort_param = "relevance"
            elif strategy == SearchStrategy.IMPACT.value:
                sort_param = "relevance" # Best proxy without IF data
            elif strategy == SearchStrategy.AGENT_DECIDED.value:
                # Agent logic could go here, but for now we default to relevance
                # In a real agentic loop, the agent would choose the strategy *before* calling this tool.
                # If passed here, we treat it as relevance.
                sort_param = "relevance"
            
            # Construct advanced query
            full_query = query
            
            if min_year or max_year:
                date_range = f"{min_year or 1900}/{'01/01'}:{max_year or 3000}/{'12/31'}[dp]"
                full_query += f" AND {date_range}"
                
            if article_type:
                full_query += f" AND \"{article_type}\"[pt]"
            
            # Step 1: Search for IDs
            handle = Entrez.esearch(db="pubmed", term=full_query, retmax=limit, sort=sort_param)
            record = Entrez.read(handle)
            handle.close()
            
            id_list = record["IdList"]
            
            return self.fetch_details(id_list)

        except Exception as e:
            return [{"error": str(e)}]
