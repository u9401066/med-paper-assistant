"""Handlers that list, search, read and format saved references."""

from typing import Optional

from ._deps import REFERENCE, project_context_error


def list_saved_references(project: Optional[str] = None) -> str:
    """
    List saved references with title, year, and PDF availability.

    Args:
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    project_error = project_context_error(project)
    if project_error:
        return project_error

    refs = ref_manager.list_references()
    if not refs:
        return "No references saved."

    output = f"📚 **Saved References ({len(refs)} total)**\n\n"

    for pmid in refs:
        summary = ref_manager.get_reference_summary(pmid)
        title = summary.get("title", "Unknown")[:60]
        if len(summary.get("title", "")) > 60:
            title += "..."
        year = summary.get("year", "")
        has_pdf = "📄" if summary.get("has_fulltext_pdf") else ""

        output += f"- **{pmid}** {has_pdf}: {title} ({year})\n"

    output += "\n*📄 = PDF fulltext available*"
    return output


def search_local_references(query: str) -> str:
    """
    Search within saved references by keyword in titles and abstracts.

    Args:
        query: Search keyword
    """
    ref_manager = REFERENCE.get().ref_manager
    results = ref_manager.search_local(query)

    if not results:
        return f"No local references found matching '{query}'"

    output = f"Found {len(results)} matching references:\n\n"
    for meta in results:
        pmid = meta.get("pmid", "")
        title = meta.get("title", "Unknown")
        year = meta.get("year", "")
        citation = meta.get("citation", {})

        output += f"**PMID:{pmid}** ({year})\n"
        output += f"  {title}\n"
        if citation.get("in_text"):
            output += f"  *Cite as: {citation['in_text']}*\n"
        output += "\n"

    return output


def get_reference_details(pmid: str) -> str:
    """
    Get detailed info and pre-formatted citations for a saved reference.

    Args:
        pmid: PubMed ID
    """
    ref_manager = REFERENCE.get().ref_manager
    summary = ref_manager.get_reference_summary(pmid)

    if "error" in summary:
        return summary["error"]

    output = f"# Reference Details: PMID {pmid}\n\n"
    output += f"**Title**: {summary.get('title', '')}\n\n"
    output += f"**Authors**: {', '.join(summary.get('authors', []))}\n\n"
    output += f"**Journal**: {summary.get('journal', '')} ({summary.get('year', '')})\n\n"

    if summary.get("doi"):
        output += f"**DOI**: {summary['doi']}\n\n"

    output += f"**Has Abstract**: {'Yes' if summary.get('has_abstract') else 'No'}\n"
    output += f"**Has PDF Fulltext**: {'Yes 📄' if summary.get('has_fulltext_pdf') else 'No'}\n\n"

    citation = summary.get("citation", {})
    if citation:
        output += "## Pre-formatted Citations\n\n"
        output += f"**Vancouver**: {citation.get('vancouver', '')}\n\n"
        output += f"**APA**: {citation.get('apa', '')}\n\n"
        output += f"**Nature**: {citation.get('nature', '')}\n\n"
        output += f"**In-text**: {citation.get('in_text', '')}\n"

    return output


def read_reference_fulltext(pmid: str, max_chars: int = 10000) -> str:
    """
    Read PDF fulltext of a saved reference (PMC Open Access only).

    Args:
        pmid: PubMed ID
        max_chars: Max characters to return (default 10000)
    """
    ref_manager = REFERENCE.get().ref_manager
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


def format_references(pmids: str, style: str = "vancouver", journal: Optional[str] = None) -> str:
    """
    Format references for insertion into manuscript.

    Args:
        pmids: Comma-separated PMIDs (e.g., "31645286,28924371")
        style: "vancouver", "apa", "harvard", "nature", "ama", "mdpi", "nlm"
        journal: Optional journal name for specific formatting
    """
    ref_manager = REFERENCE.get().ref_manager
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

        citation = metadata.get("citation", {})

        if style.lower() == "vancouver" and citation.get("vancouver"):
            output += f"[{i}] {citation['vancouver']}\n"
        elif style.lower() == "apa" and citation.get("apa"):
            output += f"{citation['apa']}\n"
        elif style.lower() == "nature" and citation.get("nature"):
            output += f"{i}. {citation['nature']}\n"
        else:
            authors = metadata.get("authors", [])
            title = metadata.get("title", "Unknown Title")
            journal_name = metadata.get("journal", "Unknown Journal")
            year = metadata.get("year", "")

            if len(authors) > 3:
                author_str = f"{authors[0]} et al"
            else:
                author_str = ", ".join(authors)

            output += f"[{i}] {author_str}. {title}. {journal_name}. {year}. PMID:{pmid}\n"

    output += f"\n*Total: {len(pmid_list)} references*"
    return output
