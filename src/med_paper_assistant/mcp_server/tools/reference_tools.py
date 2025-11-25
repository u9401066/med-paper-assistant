"""
Reference Tools Module

Tools for reference management, citation formatting, and bibliography generation.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.drafter import Drafter, CitationStyle, JOURNAL_CITATION_CONFIGS


# Style-specific configurations for reference formatting
STYLE_CONFIGS = {
    "vancouver": {"author_format": "last_initials", "max_authors": 6, "et_al_threshold": 3},
    "apa": {"author_format": "last_comma_initials", "max_authors": 7, "et_al_threshold": 6},
    "harvard": {"author_format": "last_comma_initials", "max_authors": 3, "et_al_threshold": 3},
    "nature": {"author_format": "last_initials", "max_authors": 5, "et_al_threshold": 5},
    "ama": {"author_format": "last_initials", "max_authors": 6, "et_al_threshold": 6},
    "mdpi": {"author_format": "last_comma_initials", "max_authors": 6, "et_al_threshold": 6},
    "nlm": {"author_format": "last_initials", "max_authors": 6, "et_al_threshold": 6},
}


def format_authors(authors: list, format_type: str, max_authors: int, et_al_threshold: int) -> str:
    """
    Format author names according to citation style.
    
    PubMed returns author names as "Lastname Firstname" (e.g., "Cho Sang-Hyeon").
    
    Args:
        authors: List of author names from PubMed.
        format_type: One of "last_initials", "last_initials_space", "last_comma_initials", 
                     "initials_last", or "full".
        max_authors: Maximum number of authors to display.
        et_al_threshold: Number of authors above which to use "et al."
    
    Returns:
        Formatted author string.
    """
    if not authors:
        return "Unknown Author"
    
    use_et_al = len(authors) > et_al_threshold
    display_authors = authors[:max_authors] if not use_et_al else authors[:et_al_threshold]
    
    formatted = []
    for author in display_authors:
        parts = author.split()
        if len(parts) >= 2:
            last_name = parts[0]
            first_parts = parts[1:]
            
            if format_type == "last_initials":
                initials = "".join([p[0].upper() for p in first_parts if p])
                formatted.append(f"{last_name} {initials}")
            elif format_type == "last_initials_space":
                initials = " ".join([p[0].upper() for p in first_parts if p])
                formatted.append(f"{last_name} {initials}")
            elif format_type == "last_comma_initials":
                initials = ".".join([p[0].upper() for p in first_parts if p]) + "."
                formatted.append(f"{last_name}, {initials}")
            elif format_type == "initials_last":
                initials = ".".join([p[0].upper() for p in first_parts if p]) + "."
                formatted.append(f"{initials} {last_name}")
            else:
                formatted.append(author)
        else:
            formatted.append(author)
    
    if len(formatted) == 1:
        result = formatted[0]
    elif len(formatted) == 2:
        result = f"{formatted[0]}, {formatted[1]}"
    else:
        result = ", ".join(formatted)
    
    if use_et_al:
        result += ", et al."
    
    return result


def build_reference_string(
    index: int,
    metadata: dict,
    formatted_authors: str,
    style: str,
    journal: str = None,
    config: dict = None
) -> str:
    """Build a formatted reference string based on citation style."""
    title = metadata.get('title', 'Unknown Title').rstrip('.')
    journal_name = metadata.get('journal', 'Unknown Journal')
    year = metadata.get('year', 'Unknown')
    volume = metadata.get('volume', '')
    pages = metadata.get('pages', '')
    pmid = metadata.get('pmid', '')
    
    # Helper function to add separator after authors
    def author_separator(authors_text):
        if authors_text.endswith('.') or authors_text.endswith(','):
            return authors_text + " "
        else:
            return authors_text + ". "
    
    author_block = author_separator(formatted_authors)
    
    if style.lower() == "vancouver" or (journal and config and config.get('style') == 'vancouver'):
        ref_str = f"[{index}] {author_block}{title}. {journal_name} ({year})."
        if volume:
            ref_str = f"[{index}] {author_block}{title}. {journal_name} {year}; {volume}"
            if pages:
                ref_str += f": {pages}"
            ref_str += "."
    elif style.lower() == "apa":
        ref_str = f"{formatted_authors} ({year}). {title}. *{journal_name}*"
        if volume:
            ref_str += f", {volume}"
            if pages:
                ref_str += f", {pages}"
        ref_str += "."
    elif style.lower() == "harvard":
        ref_str = f"{formatted_authors} ({year}) '{title}', *{journal_name}*"
        if volume:
            ref_str += f", vol. {volume}"
            if pages:
                ref_str += f", pp. {pages}"
        ref_str += "."
    elif style.lower() == "nature" or style.lower() == "ama":
        ref_str = f"{index}. {author_block}{title}. {journal_name}"
        if volume:
            ref_str += f" {volume}"
            if pages:
                ref_str += f", {pages}"
        ref_str += f" ({year})."
    elif style.lower() == "mdpi":
        ref_str = f"{index}. {author_block}{title}. *{journal_name}* **{year}**"
        if volume:
            ref_str += f", *{volume}*"
            if pages:
                ref_str += f", {pages}"
        ref_str += "."
    else:
        ref_str = f"[{index}] {author_block}{title}. {journal_name} ({year}). PMID:{pmid}."
    
    return ref_str


def register_reference_tools(mcp: FastMCP, ref_manager: ReferenceManager, drafter: Drafter):
    """Register all reference-related tools with the MCP server."""
    
    @mcp.tool()
    def save_reference(pmid: str) -> str:
        """
        Save a reference to the local library.
        
        Args:
            pmid: The PubMed ID of the article to save.
        """
        return ref_manager.save_reference(pmid)

    @mcp.tool()
    def list_saved_references() -> str:
        """List all saved references in the local library."""
        refs = ref_manager.list_references()
        if not refs:
            return "No references saved."
        return f"Saved references (PMIDs): {', '.join(refs)}"

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
        
        output = f"Found {len(results)} matching references:\n"
        for meta in results:
            output += f"- PMID:{meta.get('pmid')} | {meta.get('title', 'Unknown')}\n"
            
        return output

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
        Use this to get properly formatted references for the References section.
        
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
        
        # Get configuration
        if journal and journal.lower() in JOURNAL_CITATION_CONFIGS:
            config = JOURNAL_CITATION_CONFIGS[journal.lower()]
            style_name = f"{journal.upper()} format"
        else:
            config = STYLE_CONFIGS.get(style.lower(), STYLE_CONFIGS["vancouver"])
            style_name = style.upper()
        
        output = f"📚 **Formatted References ({style_name})**\n\n"
        
        for i, pmid in enumerate(pmid_list, 1):
            metadata = ref_manager.get_metadata(pmid)
            
            if not metadata:
                output += f"[{i}] PMID:{pmid} - Reference not found in local library. Use save_reference first.\n"
                continue
            
            authors = metadata.get('authors', [])
            author_format = config.get('author_format', 'full')
            max_authors = config.get('max_authors', 6)
            et_al_threshold = config.get('et_al_threshold', 3)
            
            formatted_authors = format_authors(authors, author_format, max_authors, et_al_threshold)
            ref_str = build_reference_string(i, metadata, formatted_authors, style, journal, config)
            
            output += ref_str + "\n"
        
        output += f"\n*Total: {len(pmid_list)} references*"
        return output
