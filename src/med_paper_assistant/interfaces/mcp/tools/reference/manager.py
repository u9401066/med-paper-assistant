"""
Reference Manager Tools

save_reference, list, search, format, citation management
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter
from .._shared import ensure_project_context, get_project_list_for_prompt


def register_reference_manager_tools(mcp: FastMCP, ref_manager: ReferenceManager, drafter: Drafter):
    """Register reference management tools."""
    
    # Get project manager for auto-project creation
    project_manager = ref_manager._project_manager
    
    def _ensure_project_exists() -> str:
        """Ensure a project exists for saving references."""
        if project_manager is None:
            return ""
        
        current = project_manager.get_current_project()
        if current:
            return ""
        
        result = project_manager.get_or_create_temp_project()
        if result.get("success"):
            return "\n\n💡 *已自動建立文獻探索工作區。找到研究方向後，使用 `convert_exploration_to_project` 轉換為正式專案。*"
        return ""
    
    @mcp.tool()
    def save_reference(pmid: str, download_pdf: bool = True, project: Optional[str] = None) -> str:
        """
        Save a reference to the local library with enhanced metadata and optional PDF.
        
        The saved reference includes:
        - Full metadata (authors, journal, volume, pages, DOI, etc.)
        - Pre-formatted citations (Vancouver, APA, Nature styles)
        - Abstract as markdown
        - PDF fulltext if available from PubMed Central (Open Access)
        
        If no project is active, automatically creates an exploration workspace.
        
        Args:
            pmid: The PubMed ID of the article to save.
            download_pdf: Whether to attempt downloading PDF from PMC (default: True).
            project: Project slug to save to. Agent should confirm with user.
        """
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
        
        project_msg = _ensure_project_exists()
        result = ref_manager.save_reference(pmid, download_pdf=download_pdf)
        return result + project_msg

    @mcp.tool()
    def list_saved_references(project: Optional[str] = None) -> str:
        """
        List all saved references in the local library with summary info.
        
        Args:
            project: Project slug to list from. If not specified, uses current project.
        
        Returns:
            List of PMIDs with title, year, and PDF availability.
        """
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
        
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
        Format a list of references according to a specific citation style.
        
        Args:
            pmids: Comma-separated list of PMIDs (e.g., "31645286,28924371,33160604").
            style: Citation style ("vancouver", "apa", "harvard", "nature", "ama", "mdpi", "nlm").
            journal: Optional journal name for journal-specific formatting.
        
        Returns:
            Formatted reference list ready for insertion.
        """
        pmid_list = [p.strip() for p in pmids.split(",") if p.strip()]
        
        if not pmid_list:
            return "Error: No PMIDs provided."
        
        style_name = journal.upper() if journal else style.upper()
        output = f"📚 **Formatted References ({style_name})**\n\n"
        
        for i, pmid in enumerate(pmid_list, 1):
            metadata = ref_manager.get_metadata(pmid)
            
            if not metadata:
                output += f"[{i}] PMID:{pmid} - Reference not found. Use save_reference first.\n"
                continue
            
            citation = metadata.get('citation', {})
            
            if style.lower() == "vancouver" and citation.get('vancouver'):
                output += f"[{i}] {citation['vancouver']}\n"
            elif style.lower() == "apa" and citation.get('apa'):
                output += f"{citation['apa']}\n"
            elif style.lower() == "nature" and citation.get('nature'):
                output += f"{i}. {citation['nature']}\n"
            else:
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
