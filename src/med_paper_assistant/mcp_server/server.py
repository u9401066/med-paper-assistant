from mcp.server.fastmcp import FastMCP
from med_paper_assistant.core.search import LiteratureSearcher
from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.drafter import Drafter

mcp = FastMCP("MedPaperAssistant")
searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
ref_manager = ReferenceManager(searcher)
drafter = Drafter(ref_manager)

@mcp.tool()
def search_literature(query: str, limit: int = 5, min_year: int = None, max_year: int = None, article_type: str = None, sort: str = "relevance") -> str:
    """
    Search for medical literature based on a query using PubMed.
    
    Args:
        query: The search query (e.g., "diabetes treatment guidelines").
        limit: The maximum number of results to return.
        min_year: Optional minimum publication year (e.g., 2020).
        max_year: Optional maximum publication year.
        article_type: Optional article type (e.g., "Review", "Clinical Trial", "Meta-Analysis").
        sort: Sort order ("relevance", "pub_date", "author", "journal"). Default is "relevance".
    """
    results = searcher.search(query, limit, min_year, max_year, article_type, sort)
    
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
def write_draft(filename: str, content: str) -> str:
    """
    Create a draft file with automatic citation formatting.
    Use (PMID:123456) or [PMID:123456] in content to insert citations.
    
    Args:
        filename: Name of the file (e.g., "draft.md").
        content: The text content with citation placeholders.
    """
    try:
        path = drafter.create_draft(filename, content)
        return f"Draft created successfully at: {path}"
    except Exception as e:
        return f"Error creating draft: {str(e)}"

@mcp.tool()
def insert_citation(filename: str, target_text: str, pmid: str) -> str:
    """
    Insert a citation into an existing draft.
    
    Args:
        filename: The draft file name.
        target_text: The text segment after which the citation should be inserted.
        pmid: The PubMed ID to cite.
    """
    try:
        path = drafter.insert_citation(filename, target_text, pmid)
        return f"Citation inserted successfully in: {path}"
    except Exception as e:
        return f"Error inserting citation: {str(e)}"


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
