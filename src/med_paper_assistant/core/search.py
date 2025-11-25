from Bio import Entrez
from typing import List, Dict, Any

class LiteratureSearcher:
    def __init__(self, email: str = "your.email@example.com"):
        """
        Initialize the LiteratureSearcher.
        
        Args:
            email: Email address required by NCBI Entrez API.
        """
        Entrez.email = email

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search PubMed for articles.
        
        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            
        Returns:
            List of dictionaries containing article details.
        """
        try:
            # Step 1: Search for IDs
            handle = Entrez.esearch(db="pubmed", term=query, retmax=limit)
            record = Entrez.read(handle)
            handle.close()
            
            id_list = record["IdList"]
            
            if not id_list:
                return []

            # Step 2: Fetch details
            handle = Entrez.efetch(db="pubmed", id=id_list, rettype="medline", retmode="text")
            # We can parse MEDLINE format or XML. XML is easier for structured data.
            # Let's re-fetch as XML for easier parsing with Biopython
            handle.close()
            
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
