from mcp.server.fastmcp import FastMCP
from med_paper_assistant.core.search import LiteratureSearcher
from med_paper_assistant.core.reference_manager import ReferenceManager

mcp = FastMCP("MedPaperAssistant")
searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
ref_manager = ReferenceManager(searcher)

@mcp.tool()
def search_literature(query: str, limit: int = 5) -> str:
    """
    Search for medical literature based on a query using PubMed.
    
    Args:
        query: The search query (e.g., "diabetes treatment guidelines").
        limit: The maximum number of results to return.
    """
    results = searcher.search(query, limit)
    
    if not results:
        return "No results found."
        
    if "error" in results[0]:
        return f"Error searching PubMed: {results[0]['error']}"
        
    formatted_output = f"Found {len(results)} results for '{query}':\n\n"
    for i, paper in enumerate(results, 1):
        formatted_output += f"{i}. {paper['title']}\n"
        formatted_output += f"   Authors: {', '.join(paper['authors'][:3])}{' et al.' if len(paper['authors']) > 3 else ''}\n"
        formatted_output += f"   Journal: {paper['journal']} ({paper['year']})\n"
        formatted_output += f"   PMID: {paper['pmid']}\n"
        formatted_output += f"   Abstract: {paper['abstract'][:200]}...\n\n"
        
    return formatted_output

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
    """
    List all saved references in the local library.
    """
    refs = ref_manager.list_references()
    if not refs:
        return "No references saved."
    return f"Saved references (PMIDs): {', '.join(refs)}"


@mcp.tool()
def draft_section(topic: str, notes: str) -> str:
    """
    Draft a section of a medical paper based on notes.
    
    Args:
        topic: The topic of the section (e.g., "Introduction").
        notes: Raw notes or bullet points to convert into text.
    """
    # Placeholder for drafting logic
    return f"Drafting section '{topic}' based on notes..."

@mcp.tool()
def apply_template(content: str, journal_name: str) -> str:
    """
    Apply a specific journal template to the content.
    
    Args:
        content: The content to format.
        journal_name: The name of the journal template (e.g., "NEJM").
    """
    # Placeholder for formatting logic
    return f"Applying template '{journal_name}' to content..."

if __name__ == "__main__":
    mcp.run()
