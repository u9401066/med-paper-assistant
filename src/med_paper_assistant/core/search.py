from Bio import Entrez
from typing import List, Dict, Any, Optional
import re
import os
import requests

from enum import Enum

class SearchStrategy(Enum):
    RECENT = "recent"
    MOST_CITED = "most_cited"  # Proxy: Relevance (PubMed doesn't support citation sort directly without PMC)
    RELEVANCE = "relevance"
    IMPACT = "impact"          # Proxy: Journal (or Relevance)
    AGENT_DECIDED = "agent_decided"

class LiteratureSearcher:
    def __init__(self, email: str = "your.email@example.com", api_key: str = None):
        """
        Initialize the LiteratureSearcher.
        
        Args:
            email: Email address required by NCBI Entrez API.
            api_key: Optional NCBI API key for higher rate limits (10/sec vs 3/sec).
        """
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
        Entrez.max_tries = 3
        Entrez.sleep_between_tries = 15

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
                    pubmed_data = article.get('PubmedData', {})
                    
                    title = article_data.get('ArticleTitle', 'No title')
                    
                    # Extract authors with full details
                    authors = []
                    authors_full = []  # For citation formatting
                    if 'AuthorList' in article_data:
                        for author in article_data['AuthorList']:
                            if 'LastName' in author:
                                last_name = author['LastName']
                                fore_name = author.get('ForeName', '')
                                initials = author.get('Initials', '')
                                authors.append(f"{last_name} {fore_name}".strip())
                                authors_full.append({
                                    "last_name": last_name,
                                    "fore_name": fore_name,
                                    "initials": initials
                                })
                            elif 'CollectiveName' in author:
                                authors.append(author['CollectiveName'])
                                authors_full.append({"collective_name": author['CollectiveName']})
                    
                    # Extract abstract
                    abstract_text = ""
                    if 'Abstract' in article_data and 'AbstractText' in article_data['Abstract']:
                        abstract_parts = article_data['Abstract']['AbstractText']
                        if isinstance(abstract_parts, list):
                            abstract_text = " ".join([str(part) for part in abstract_parts])
                        else:
                            abstract_text = str(abstract_parts)
                            
                    # Extract Journal info with more details
                    journal_data = article_data.get('Journal', {})
                    journal = journal_data.get('Title', 'Unknown Journal')
                    journal_abbrev = journal_data.get('ISOAbbreviation', '')
                    journal_issue = journal_data.get('JournalIssue', {})
                    volume = journal_issue.get('Volume', '')
                    issue = journal_issue.get('Issue', '')
                    pub_date = journal_issue.get('PubDate', {})
                    year = pub_date.get('Year', '')
                    month = pub_date.get('Month', '')
                    day = pub_date.get('Day', '')
                    
                    # If year is missing, try MedlineDate
                    if not year and 'MedlineDate' in pub_date:
                        medline_date = pub_date['MedlineDate']
                        year_match = re.search(r'(\d{4})', medline_date)
                        if year_match:
                            year = year_match.group(1)
                    
                    # Extract pagination
                    pagination = article_data.get('Pagination', {})
                    pages = pagination.get('MedlinePgn', '')
                    
                    # Extract DOI and PMC ID from ArticleIdList
                    doi = ''
                    pmc_id = ''
                    article_ids = pubmed_data.get('ArticleIdList', [])
                    for aid in article_ids:
                        if hasattr(aid, 'attributes'):
                            if aid.attributes.get('IdType') == 'doi':
                                doi = str(aid)
                            elif aid.attributes.get('IdType') == 'pmc':
                                pmc_id = str(aid)
                    
                    # Extract PMID
                    pmid = str(medline_citation.get('PMID', ''))
                    
                    # Extract keywords
                    keywords = []
                    if 'KeywordList' in medline_citation:
                        for kw_list in medline_citation['KeywordList']:
                            keywords.extend([str(kw) for kw in kw_list])
                    
                    # Extract MeSH terms
                    mesh_terms = []
                    if 'MeshHeadingList' in medline_citation:
                        for mesh in medline_citation['MeshHeadingList']:
                            if 'DescriptorName' in mesh:
                                mesh_terms.append(str(mesh['DescriptorName']))

                    results.append({
                        "pmid": pmid,
                        "title": title,
                        "authors": authors,
                        "authors_full": authors_full,
                        "journal": journal,
                        "journal_abbrev": journal_abbrev,
                        "year": year,
                        "month": month,
                        "day": day,
                        "volume": volume,
                        "issue": issue,
                        "pages": pages,
                        "doi": doi,
                        "pmc_id": pmc_id,
                        "abstract": abstract_text,
                        "keywords": keywords,
                        "mesh_terms": mesh_terms
                    })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def get_pmc_fulltext_url(self, pmid: str) -> Optional[str]:
        """
        Get the PubMed Central full text URL if available (Open Access).
        Uses elink to find PMC ID and constructs the download URL.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            URL to download full text PDF, or None if not available.
        """
        try:
            # Use elink to find PMC ID
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
            record = Entrez.read(handle)
            handle.close()
            
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pmc':
                        links = linkset.get('Link', [])
                        if links:
                            pmc_id = links[0]['Id']
                            # PMC PDF URL format
                            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
            return None
        except Exception as e:
            print(f"Error getting PMC URL: {e}")
            return None

    def download_pmc_pdf(self, pmid: str, output_path: str) -> bool:
        """
        Download PDF from PubMed Central if available.
        
        Args:
            pmid: PubMed ID.
            output_path: Path to save the PDF file.
            
        Returns:
            True if download successful, False otherwise.
        """
        try:
            # First, get PMC ID via elink
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
            record = Entrez.read(handle)
            handle.close()
            
            pmc_id = None
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pmc':
                        links = linkset.get('Link', [])
                        if links:
                            pmc_id = links[0]['Id']
                            break
            
            if not pmc_id:
                return False
            
            # Try to get the PDF from PMC
            # First, try the OA service
            oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; med-paper-assistant/1.0)'
            }
            
            response = requests.get(oa_url, headers=headers, allow_redirects=True, timeout=30)
            
            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            
            return False
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return False

    def get_related_articles(self, pmid: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find related articles using PubMed's related articles feature.
        
        Args:
            pmid: PubMed ID to find related articles for.
            limit: Maximum number of related articles to return.
            
        Returns:
            List of related article details.
        """
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pubmed", id=pmid, linkname="pubmed_pubmed")
            record = Entrez.read(handle)
            handle.close()
            
            related_ids = []
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pubmed':
                        links = linkset.get('Link', [])
                        related_ids = [link['Id'] for link in links[:limit]]
                        break
            
            if related_ids:
                return self.fetch_details(related_ids)
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def get_citing_articles(self, pmid: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find articles that cite this article (via PMC).
        
        Args:
            pmid: PubMed ID.
            limit: Maximum number of citing articles to return.
            
        Returns:
            List of citing article details.
        """
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pubmed", id=pmid, linkname="pubmed_pubmed_citedin")
            record = Entrez.read(handle)
            handle.close()
            
            citing_ids = []
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pubmed_citedin':
                        links = linkset.get('Link', [])
                        citing_ids = [link['Id'] for link in links[:limit]]
                        break
            
            if citing_ids:
                return self.fetch_details(citing_ids)
            return []
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
            handle = Entrez.esearch(db="pubmed", term=full_query, retmax=limit*2, sort=sort_param) # Fetch more to allow for filtering
            record = Entrez.read(handle)
            handle.close()
            
            id_list = record["IdList"]
            
            results = self.fetch_details(id_list)
            
            # Step 2: Post-processing Filter (e.g. Sample Size)
            # This is where we would use the StrategyManager criteria if passed, 
            # but for now we'll keep it simple or let the caller handle it.
            # To support the user request "trial > 100", we need to look at the abstract.
            
            return results[:limit]

        except Exception as e:
            return [{"error": str(e)}]

    def filter_results(self, results: List[Dict[str, Any]], min_sample_size: int = None) -> List[Dict[str, Any]]:
        """
        Filter results based on abstract content.
        
        Args:
            results: List of paper details.
            min_sample_size: Minimum number of participants mentioned.
        """
        if not min_sample_size:
            return results
            
        filtered = []
        import re
        
        for paper in results:
            abstract = paper.get('abstract', '').lower()
            # Simple regex to find "n = 123" or "123 patients"
            # This is a heuristic and not perfect.
            # Patterns: "n = 123", "n=123", "123 patients", "123 participants", "123 subjects"
            patterns = [
                r"n\s*=\s*(\d+)",
                r"(\d+)\s*patients",
                r"(\d+)\s*participants",
                r"(\d+)\s*subjects"
            ]
            
            max_n = 0
            for p in patterns:
                matches = re.findall(p, abstract)
                for m in matches:
                    try:
                        val = int(m)
                        if val > max_n:
                            max_n = val
                    except:
                        pass
            
            if max_n >= min_sample_size:
                filtered.append(paper)
                
        return filtered

    def quick_fetch_summary(self, id_list: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch article summaries using ESummary (faster than EFetch for metadata only).
        
        Args:
            id_list: List of PubMed IDs.
            
        Returns:
            List of article summaries with basic metadata.
        """
        if not id_list:
            return []
        
        try:
            handle = Entrez.esummary(db="pubmed", id=",".join(id_list))
            summaries = Entrez.read(handle)
            handle.close()
            
            results = []
            for summary in summaries:
                if isinstance(summary, dict):
                    results.append({
                        "pmid": summary.get('Id', ''),
                        "title": summary.get('Title', ''),
                        "authors": [author.get('Name', '') for author in summary.get('AuthorList', [])],
                        "journal": summary.get('Source', ''),
                        "year": summary.get('PubDate', '').split()[0] if summary.get('PubDate') else '',
                        "doi": summary.get('DOI', ''),
                        "pmc_id": summary.get('PMCID', '')
                    })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def spell_check_query(self, query: str) -> str:
        """
        Get spelling suggestions for search queries using ESpell.
        
        Args:
            query: The search query to check.
            
        Returns:
            Corrected query string if suggestions found, original query otherwise.
        """
        try:
            handle = Entrez.espell(db="pubmed", term=query)
            result = Entrez.read(handle)
            handle.close()
            
            corrected = result.get("CorrectedQuery", "")
            return corrected if corrected else query
        except Exception as e:
            print(f"Error in spell check: {e}")
            return query

    def get_database_counts(self, query: str) -> Dict[str, int]:
        """
        Get result counts across multiple NCBI databases using EGQuery.
        
        Args:
            query: The search query.
            
        Returns:
            Dictionary mapping database names to result counts.
        """
        try:
            handle = Entrez.egquery(term=query)
            result = Entrez.read(handle)
            handle.close()
            
            counts = {}
            for db_result in result["eGQueryResult"]:
                db_name = db_result.get("DbName", "")
                count = db_result.get("Count", "0")
                try:
                    counts[db_name] = int(count)
                except ValueError:
                    counts[db_name] = 0
            
            return counts
        except Exception as e:
            return {"error": str(e)}

    def validate_mesh_terms(self, terms: List[str]) -> Dict[str, Any]:
        """
        Validate MeSH terms and get their IDs using MeSH database.
        
        Args:
            terms: List of potential MeSH terms to validate.
            
        Returns:
            Dictionary with valid terms and their IDs.
        """
        try:
            query = " OR ".join([f'"{term}"[MeSH Terms]' for term in terms])
            handle = Entrez.esearch(db="mesh", term=query, retmax=len(terms))
            result = Entrez.read(handle)
            handle.close()
            
            mesh_ids = result.get("IdList", [])
            
            if mesh_ids:
                handle = Entrez.esummary(db="mesh", id=",".join(mesh_ids))
                summaries = Entrez.read(handle)
                handle.close()
                
                validated_terms = []
                for summary in summaries:
                    if isinstance(summary, dict):
                        validated_terms.append({
                            "mesh_id": summary.get("Id", ""),
                            "term": summary.get("DS_MeshTerms", [""])[0] if summary.get("DS_MeshTerms") else "",
                            "tree_numbers": summary.get("DS_IdxLinks", [])
                        })
                
                return {
                    "valid_count": len(validated_terms),
                    "terms": validated_terms
                }
            
            return {"valid_count": 0, "terms": []}
        except Exception as e:
            return {"error": str(e)}

    def find_by_citation(self, journal: str, year: str, volume: str = "", 
                        first_page: str = "", author: str = "", title: str = "") -> Optional[str]:
        """
        Find article by citation details using ECitMatch.
        
        Args:
            journal: Journal name or abbreviation.
            year: Publication year.
            volume: Volume number (optional).
            first_page: First page number (optional).
            author: First author last name (optional).
            title: Article title (optional).
            
        Returns:
            PMID if found, None otherwise.
        """
        try:
            # Format: journal|year|volume|first_page|author|key|
            citation_string = f"{journal}|{year}|{volume}|{first_page}|{author}||"
            
            handle = Entrez.ecitmatch(db="pubmed", bdata=citation_string)
            result = handle.read().strip()
            handle.close()
            
            # Parse result: format is "citation_string\tPMID" or "citation_string\tNOT_FOUND"
            if result and '\t' in result:
                parts = result.split('\t')
                if len(parts) > 1 and parts[1].isdigit():
                    return parts[1]
            
            return None
        except Exception as e:
            print(f"Error in citation match: {e}")
            return None

    def search_with_history(self, query: str, batch_size: int = 500) -> Dict[str, Any]:
        """
        Search large result sets efficiently using NCBI History Server.
        Returns WebEnv and QueryKey for batch processing.
        
        Args:
            query: Search query string.
            batch_size: Number of results to process per batch.
            
        Returns:
            Dictionary with search metadata for batch processing.
        """
        try:
            handle = Entrez.esearch(db="pubmed", term=query, usehistory="y", retmax=0)
            search_results = Entrez.read(handle)
            handle.close()
            
            return {
                "webenv": search_results.get("WebEnv", ""),
                "query_key": search_results.get("QueryKey", ""),
                "count": int(search_results.get("Count", 0)),
                "batch_size": batch_size
            }
        except Exception as e:
            return {"error": str(e)}

    def fetch_batch_from_history(self, webenv: str, query_key: str, 
                                 start: int, batch_size: int) -> List[Dict[str, Any]]:
        """
        Fetch a batch of results using History Server credentials.
        
        Args:
            webenv: WebEnv from search_with_history.
            query_key: QueryKey from search_with_history.
            start: Starting index (0-based).
            batch_size: Number of results to fetch.
            
        Returns:
            List of article details for this batch.
        """
        try:
            handle = Entrez.efetch(db="pubmed", retstart=start, retmax=batch_size,
                                  webenv=webenv, query_key=query_key, retmode="xml")
            papers = Entrez.read(handle)
            handle.close()
            
            results = []
            if 'PubmedArticle' in papers:
                for article in papers['PubmedArticle']:
                    medline_citation = article['MedlineCitation']
                    article_data = medline_citation['Article']
                    
                    title = article_data.get('ArticleTitle', 'No title')
                    pmid = str(medline_citation.get('PMID', ''))
                    
                    # Extract basic info
                    authors = []
                    if 'AuthorList' in article_data:
                        for author in article_data['AuthorList']:
                            if 'LastName' in author:
                                authors.append(f"{author['LastName']} {author.get('ForeName', '')}".strip())
                    
                    journal = article_data.get('Journal', {}).get('Title', 'Unknown')
                    year = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', '')
                    
                    results.append({
                        "pmid": pmid,
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "year": year
                    })
            
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def export_citations(self, id_list: List[str], format: str = "medline") -> str:
        """
        Export citations in various formats.
        
        Args:
            id_list: List of PubMed IDs.
            format: Output format - "medline", "pubmed" (XML), "abstract", or "bibtex" (via pubmed).
            
        Returns:
            Formatted citation text.
        """
        if not id_list:
            return ""
        
        try:
            valid_formats = {
                "medline": ("medline", "text"),
                "pubmed": ("pubmed", "xml"),
                "abstract": ("abstract", "text")
            }
            
            if format not in valid_formats:
                format = "medline"
            
            rettype, retmode = valid_formats[format]
            
            handle = Entrez.efetch(db="pubmed", id=id_list, 
                                  rettype=rettype, retmode=retmode)
            result = handle.read()
            handle.close()
            
            return result
        except Exception as e:
            return f"Error exporting citations: {str(e)}"

    def get_article_references(self, pmid: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get references (bibliography) of an article via PMC.
        
        Args:
            pmid: PubMed ID.
            limit: Maximum number of references to return.
            
        Returns:
            List of referenced article details.
        """
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pubmed", 
                                 id=pmid, linkname="pubmed_pubmed_refs")
            record = Entrez.read(handle)
            handle.close()
            
            ref_ids = []
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pubmed_refs':
                        links = linkset.get('Link', [])
                        ref_ids = [link['Id'] for link in links[:limit]]
                        break
            
            if ref_ids:
                return self.fetch_details(ref_ids)
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def get_database_info(self, db: str = "pubmed") -> Dict[str, Any]:
        """
        Get database statistics and field information using EInfo.
        
        Args:
            db: Database name (default: pubmed).
            
        Returns:
            Dictionary with database information.
        """
        try:
            handle = Entrez.einfo(db=db)
            result = Entrez.read(handle)
            handle.close()
            
            db_info = result.get("DbInfo", {})
            
            return {
                "name": db_info.get("DbName", ""),
                "menu_name": db_info.get("MenuName", ""),
                "description": db_info.get("Description", ""),
                "count": db_info.get("Count", "0"),
                "last_update": db_info.get("LastUpdate", ""),
                "fields": [
                    {
                        "name": field.get("Name", ""),
                        "full_name": field.get("FullName", ""),
                        "description": field.get("Description", "")
                    }
                    for field in db_info.get("FieldList", [])
                ]
            }
        except Exception as e:
            return {"error": str(e)}
