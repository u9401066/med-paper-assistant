"""
Entrez PDF Module - PMC PDF Download Functionality

Provides functionality to download PDFs from PubMed Central Open Access.
"""

from Bio import Entrez
from typing import Optional
import requests


class PDFMixin:
    """
    Mixin providing PDF download functionality from PMC.
    
    Methods:
        get_pmc_fulltext_url: Get URL for PMC full text PDF
        download_pmc_pdf: Download PDF from PMC Open Access
    """
    
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
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
            record = Entrez.read(handle)
            handle.close()
            
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pmc':
                        links = linkset.get('Link', [])
                        if links:
                            pmc_id = links[0]['Id']
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
            pmc_id = self._get_pmc_id(pmid)
            
            if not pmc_id:
                return False
            
            # Try to get the PDF from PMC
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

    def _get_pmc_id(self, pmid: str) -> Optional[str]:
        """
        Get PMC ID for a given PMID using elink.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            PMC ID if available, None otherwise.
        """
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
            record = Entrez.read(handle)
            handle.close()
            
            if record and record[0].get('LinkSetDb'):
                for linkset in record[0]['LinkSetDb']:
                    if linkset.get('LinkName') == 'pubmed_pmc':
                        links = linkset.get('Link', [])
                        if links:
                            return links[0]['Id']
            return None
        except Exception:
            return None
