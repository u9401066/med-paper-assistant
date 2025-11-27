"""
Reference Tools Module

Tools for reference management, citation formatting, and bibliography generation.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter, CitationStyle, JOURNAL_CITATION_CONFIGS


def register_reference_tools(mcp: FastMCP, ref_manager: ReferenceManager, drafter: Drafter):
    """Register all reference-related tools with the MCP server."""
    
    @mcp.tool()
    def save_reference(pmid: str, download_pdf: bool = True) -> str:
        """
        Save a reference to the local library with enhanced metadata and optional PDF.
        
        The saved reference includes:
        - Full metadata (authors, journal, volume, pages, DOI, etc.)
        - Pre-formatted citations (Vancouver, APA, Nature styles)
        - Abstract as markdown
        - PDF fulltext if available from PubMed Central (Open Access)
        
        Args:
            pmid: The PubMed ID of the article to save.
            download_pdf: Whether to attempt downloading PDF from PMC (default: True).
        """
        return ref_manager.save_reference(pmid, download_pdf=download_pdf)

    @mcp.tool()
    def list_saved_references() -> str:
        """
        List all saved references in the local library with summary info.
        
        Returns:
            List of PMIDs with title, year, and PDF availability.
        """
        refs = ref_manager.list_references()
        if not refs:
            return "No references saved."
        
        output = f"📚 **Saved References ({len(refs)} total)**\n\n"
        
        for pmid in refs:
            summary = ref_manager.get_reference_summary(pmid)
            title = summary.get('title', 'Unknown')[:60]
            if len(summary.get('title', '')) > 60:
                title += "..."
            year = summary.get('year', '')
            has_pdf = "📄" if summary.get('has_fulltext_pdf') else ""
            
            output += f"- **{pmid}** {has_pdf}: {title} ({year})\n"
        
        output += "\n*📄 = PDF fulltext available*"
        return output

    @mcp.tool()
    def search_local_references(query: str) -> str:
        """
        Search within saved local references by keyword.
        
        Args:
            query: Keyword to search in titles and abstracts.
        """
        results = ref_manager.search_local(query)
        
        if not results:
            return f"No local references found matching '{query}'"
        
        output = f"Found {len(results)} matching references:\n\n"
        for meta in results:
            pmid = meta.get('pmid', '')
            title = meta.get('title', 'Unknown')
            year = meta.get('year', '')
            citation = meta.get('citation', {})
            
            output += f"**PMID:{pmid}** ({year})\n"
            output += f"  {title}\n"
            if citation.get('in_text'):
                output += f"  *Cite as: {citation['in_text']}*\n"
            output += "\n"
            
        return output

    @mcp.tool()
    def get_reference_details(pmid: str) -> str:
        """
        Get detailed information about a saved reference including citation formats.
        
        Args:
            pmid: PubMed ID of the reference.
            
        Returns:
            Comprehensive reference details with pre-formatted citations.
        """
        summary = ref_manager.get_reference_summary(pmid)
        
        if "error" in summary:
            return summary["error"]
        
        output = f"# Reference Details: PMID {pmid}\n\n"
        output += f"**Title**: {summary.get('title', '')}\n\n"
        output += f"**Authors**: {', '.join(summary.get('authors', []))}\n\n"
        output += f"**Journal**: {summary.get('journal', '')} ({summary.get('year', '')})\n\n"
        
        if summary.get('doi'):
            output += f"**DOI**: {summary['doi']}\n\n"
        
        output += f"**Has Abstract**: {'Yes' if summary.get('has_abstract') else 'No'}\n"
        output += f"**Has PDF Fulltext**: {'Yes 📄' if summary.get('has_fulltext_pdf') else 'No'}\n\n"
        
        citation = summary.get('citation', {})
        if citation:
            output += "## Pre-formatted Citations\n\n"
            output += f"**Vancouver**: {citation.get('vancouver', '')}\n\n"
            output += f"**APA**: {citation.get('apa', '')}\n\n"
            output += f"**Nature**: {citation.get('nature', '')}\n\n"
            output += f"**In-text**: {citation.get('in_text', '')}\n"
        
        return output

    @mcp.tool()
    def read_reference_fulltext(pmid: str, max_chars: int = 10000) -> str:
        """
        Read the fulltext PDF content of a saved reference.
        
        Only works if the PDF was downloaded from PubMed Central.
        Use this to get detailed information beyond the abstract.
        
        Args:
            pmid: PubMed ID of the reference.
            max_chars: Maximum characters to return (default 10000).
            
        Returns:
            Extracted text from the PDF, or error message if not available.
        """
        if not ref_manager.has_fulltext(pmid):
            return f"No fulltext PDF available for PMID {pmid}. Only Open Access articles from PMC have downloadable PDFs."
        
        text = ref_manager.read_fulltext(pmid)
        if text is None:
            return f"Could not read fulltext for PMID {pmid}."
        
        if text.startswith("Error"):
            return text
        
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n... [Truncated. Total length: {len(text)} characters]"
        
        return f"# Fulltext: PMID {pmid}\n\n{text}"

    @mcp.tool()
    def retry_pdf_download(pmid: str) -> str:
        """
        Retry downloading PDF for a reference that doesn't have one.
        
        Useful if you saved a reference earlier without PDF download,
        or want to try again for an article that might now be available.
        
        Args:
            pmid: PubMed ID of the reference.
        """
        return ref_manager.retry_pdf_download(pmid)

    @mcp.tool()
    def set_citation_style(style: str) -> str:
        """
        Set the citation style for the current session.
        
        Args:
            style: Citation style ("vancouver", "apa", "harvard", "nature", "ama").
        """
        try:
            drafter.set_citation_style(style)
            return f"Citation style set to: {style}"
        except ValueError as e:
            return str(e)

    @mcp.tool()
    def format_references(pmids: str, style: str = "vancouver", journal: str = None) -> str:
        """
        Format a list of references according to a specific citation style or journal format.
        Uses the pre-formatted citations stored in metadata when available.
        
        Args:
            pmids: Comma-separated list of PMIDs (e.g., "31645286,28924371,33160604").
            style: Citation style ("vancouver", "apa", "harvard", "nature", "ama", "mdpi", "nlm").
                   Default is "vancouver".
            journal: Optional journal name for journal-specific formatting 
                    (e.g., "sensors", "lancet", "bja", "anesthesiology").
                    If provided, overrides the style parameter.
        
        Returns:
            Formatted reference list ready for insertion into the References section.
        """
        pmid_list = [p.strip() for p in pmids.split(",") if p.strip()]
        
        if not pmid_list:
            return "Error: No PMIDs provided."
        
        style_name = journal.upper() if journal else style.upper()
        output = f"📚 **Formatted References ({style_name})**\n\n"
        
        for i, pmid in enumerate(pmid_list, 1):
            metadata = ref_manager.get_metadata(pmid)
            
            if not metadata:
                output += f"[{i}] PMID:{pmid} - Reference not found in local library. Use save_reference first.\n"
                continue
            
            # Use pre-formatted citation if available
            citation = metadata.get('citation', {})
            
            if style.lower() == "vancouver" and citation.get('vancouver'):
                output += f"[{i}] {citation['vancouver']}\n"
            elif style.lower() == "apa" and citation.get('apa'):
                output += f"{citation['apa']}\n"
            elif style.lower() == "nature" and citation.get('nature'):
                output += f"{i}. {citation['nature']}\n"
            else:
                # Fallback to basic format
                authors = metadata.get('authors', [])
                title = metadata.get('title', 'Unknown Title')
                journal_name = metadata.get('journal', 'Unknown Journal')
                year = metadata.get('year', '')
                
                if len(authors) > 3:
                    author_str = f"{authors[0]} et al"
                else:
                    author_str = ", ".join(authors)
                
                output += f"[{i}] {author_str}. {title}. {journal_name}. {year}. PMID:{pmid}\n"
        
        output += f"\n*Total: {len(pmid_list)} references*"
        return output
