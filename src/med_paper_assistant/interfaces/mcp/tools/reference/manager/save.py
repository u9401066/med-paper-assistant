"""Handlers that save references and attach PDFs."""

import json
from typing import Optional, Union

from ..._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_agent_misuse,
    log_tool_call,
    log_tool_result,
)
from ._deps import REFERENCE, ensure_project_exists, project_context_error

# === GUARDRAIL: Deprecation warning ===
# Always emit warning so even weak models notice
_DEPRECATION_WARNING = (
    "\n\n⚠️ **DEPRECATION WARNING**: `save_reference()` accepts unverified metadata.\n"
    "✅ **Preferred**: `save_reference_mcp(pmid='<PMID>')` — fetches verified data from PubMed API.\n"
    "Only use `save_reference()` when pubmed-search API is confirmed unavailable.\n"
)


def _validate_article(article: Union[dict, str]) -> Union[dict, str]:
    """Return the article dict, or the error message to show the caller."""
    # Handle JSON string input (MCP sometimes passes dict as JSON string)
    if isinstance(article, str):
        try:
            article = json.loads(article)
        except json.JSONDecodeError as e:
            error_msg = (
                f"❌ Invalid JSON string for article parameter: {e}\n\n"
                "**Correct workflow:**\n"
                "1. Use pubmed-search MCP: `fetch_article_details(pmids='12345678')`\n"
                "2. Use mdpaper MCP: `save_reference(article=<metadata from step 1>)`"
            )
            log_agent_misuse(
                "save_reference",
                "valid JSON or dict",
                {"article_type": type(article).__name__},
                error_msg,
            )
            return error_msg

    if not isinstance(article, dict):
        error_msg = (
            f"❌ Invalid input: article must be a dictionary, got {type(article).__name__}.\n\n"
            "**Correct workflow:**\n"
            "1. Use pubmed-search MCP: `fetch_article_details(pmids='12345678')`\n"
            "2. Use mdpaper MCP: `save_reference(article=<metadata from step 1>)`"
        )
        log_agent_misuse(
            "save_reference", "dict type", {"article_type": type(article).__name__}, error_msg
        )
        return error_msg

    if not article.get("pmid"):
        error_msg = (
            "❌ Article metadata must contain 'pmid' field.\n\n"
            "Ensure you're using metadata from pubmed-search MCP's "
            "`fetch_article_details()` or `unified_search()` tools."
        )
        log_agent_misuse(
            "save_reference",
            "article with pmid field",
            {"article_keys": list(article.keys())},
            error_msg,
        )
        return error_msg

    return article


def save_reference(article: Union[dict, str], project: Optional[str] = None) -> str:
    """
    ⚠️ DEPRECATED — Use save_reference_mcp(pmid) instead for verified data.

    This tool accepts unverified metadata that may be fabricated.
    Only use as fallback when pubmed-search API is unavailable.

    Args:
        article: Article metadata dict with 'pmid' field (from pubmed-search)
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    # Log tool call with deprecation warning
    log_tool_call("save_reference", {"article": article, "project": project})

    project_error = project_context_error(project)
    if project_error:
        log_agent_misuse(
            "save_reference",
            "valid project slug",
            {"article": article, "project": project},
            project_error,
        )
        return project_error

    checked_article = _validate_article(article)
    if isinstance(checked_article, str):
        return checked_article

    project_msg = ensure_project_exists()
    result = ref_manager.save_reference(checked_article)
    log_tool_result("save_reference", result)

    # Log as misuse for telemetry tracking
    log_agent_misuse(
        "save_reference",
        "save_reference_mcp(pmid)",
        {"pmid": checked_article.get("pmid", "unknown")},
        "Agent used deprecated save_reference() instead of save_reference_mcp()",
    )

    return result + _DEPRECATION_WARNING + project_msg


def save_reference_mcp(pmid: str, agent_notes: str = "", project: Optional[str] = None) -> str:
    """
    🔒 Save reference by PMID with verified metadata from pubmed-search API (RECOMMENDED).

    Args:
        pmid: PubMed ID (e.g., "12345678")
        agent_notes: Optional AI notes about this reference
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "save_reference_mcp", {"pmid": pmid, "agent_notes": agent_notes, "project": project}
    )

    if project:
        is_valid, msg, project_info = ensure_project_context(project)
        if not is_valid:
            error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
            log_agent_misuse(
                "save_reference_mcp",
                "valid project slug",
                {"pmid": pmid, "project": project},
                error_msg,
            )
            return error_msg

    project_msg = ensure_project_exists()
    result = ref_manager.save_reference_mcp(pmid, agent_notes=agent_notes)
    log_tool_result("save_reference_mcp", result)
    return result + project_msg


def save_reference_pdf(pmid: str, pdf_content: str) -> str:
    """
    Save base64-encoded PDF content for an existing reference.

    Args:
        pmid: PubMed ID
        pdf_content: Base64 encoded PDF
    """
    ref_manager = REFERENCE.get().ref_manager
    import base64

    try:
        decoded = base64.b64decode(pdf_content)
        return ref_manager.save_pdf(pmid, decoded)
    except Exception as e:
        return f"❌ Error decoding PDF: {str(e)}"
