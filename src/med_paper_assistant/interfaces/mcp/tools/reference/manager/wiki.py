"""Handlers that upgrade reference identity and materialize wiki pages."""

import json
from typing import Optional

from ..._shared import log_tool_call, log_tool_result
from ._deps import (
    REFERENCE,
    ensure_project_exists,
    parse_reference_ids,
    project_context_error,
)


def _parse_verified_article(
    verified_metadata_json: str,
) -> tuple[Optional[dict], Optional[str]]:
    """Return the verified article (``None`` when absent), or the error message."""
    if not verified_metadata_json.strip():
        return None, None

    try:
        verified_article = json.loads(verified_metadata_json)
    except json.JSONDecodeError as exc:
        return None, f"❌ Invalid verified_metadata_json: {exc}"

    if not isinstance(verified_article, dict):
        return None, "❌ verified_metadata_json must decode to a JSON object."
    return verified_article, None


def resolve_reference_identity(
    reference_id: str,
    pmid: str = "",
    verified_metadata_json: str = "",
    agent_notes: str = "",
    project: Optional[str] = None,
) -> str:
    """
    Upgrade a local/extracted reference to a canonical verified identity.

    Args:
        reference_id: Existing local reference id (for example local_abcd1234)
        pmid: Optional PubMed ID if MedPaper should fetch verified metadata directly
        verified_metadata_json: Optional verified metadata JSON supplied by the harness
        agent_notes: Optional notes to persist with the canonical record
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "resolve_reference_identity",
        {
            "reference_id": reference_id,
            "pmid": pmid,
            "project": project,
            "has_verified_metadata_json": bool(verified_metadata_json.strip()),
        },
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    verified_article, parse_error = _parse_verified_article(verified_metadata_json)
    if parse_error:
        return parse_error

    if not pmid and verified_article is None:
        return "❌ Provide either pmid or verified_metadata_json."

    result = ref_manager.resolve_reference_identity(
        reference_id,
        verified_article=verified_article,
        pmid=pmid or None,
        agent_notes=agent_notes,
    )
    log_tool_result("resolve_reference_identity", result)
    return result


def build_knowledge_map(
    title: str,
    reference_ids: str = "",
    query: str = "",
    limit: int = 12,
    project: Optional[str] = None,
) -> str:
    """
    Build a materialized knowledge map page from saved references.

    Args:
        title: Title of the map page
        reference_ids: Optional comma/newline-separated reference ids
        query: Optional local search query when reference_ids omitted
        limit: Max references to include when selecting automatically
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "build_knowledge_map",
        {
            "title": title,
            "reference_ids": reference_ids,
            "query": query,
            "limit": limit,
            "project": project,
        },
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    project_msg = ensure_project_exists()
    result = ref_manager.build_knowledge_map(
        title,
        reference_ids=parse_reference_ids(reference_ids),
        query=query,
        limit=limit,
    )
    log_tool_result("build_knowledge_map", result)
    return result + project_msg


def build_synthesis_page(
    title: str,
    reference_ids: str = "",
    query: str = "",
    focus: str = "",
    summary_markdown: str = "",
    limit: int = 12,
    project: Optional[str] = None,
) -> str:
    """
    Build a materialized synthesis page from saved references.

    Args:
        title: Title of the synthesis page
        reference_ids: Optional comma/newline-separated reference ids
        query: Optional local search query when reference_ids omitted
        focus: Optional synthesis focus
        summary_markdown: Optional prewritten synthesis markdown
        limit: Max references to include when selecting automatically
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "build_synthesis_page",
        {
            "title": title,
            "reference_ids": reference_ids,
            "query": query,
            "focus": focus,
            "has_summary_markdown": bool(summary_markdown.strip()),
            "limit": limit,
            "project": project,
        },
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    project_msg = ensure_project_exists()
    result = ref_manager.build_synthesis_page(
        title,
        reference_ids=parse_reference_ids(reference_ids),
        query=query,
        focus=focus,
        summary_markdown=summary_markdown,
        limit=limit,
    )
    log_tool_result("build_synthesis_page", result)
    return result + project_msg


def materialize_agent_wiki(
    knowledge_map_title: str,
    synthesis_title: str = "",
    reference_ids: str = "",
    query: str = "",
    focus: str = "",
    summary_markdown: str = "",
    limit: int = 12,
    project: Optional[str] = None,
) -> str:
    """
    Materialize the second-stage agent wiki bundle in one step.

    Args:
        knowledge_map_title: Title for the knowledge map page
        synthesis_title: Optional title for the synthesis page
        reference_ids: Optional comma/newline-separated reference ids
        query: Optional local search query when reference_ids omitted
        focus: Optional synthesis focus
        summary_markdown: Optional prewritten synthesis markdown
        limit: Max references to include when selecting automatically
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "materialize_agent_wiki",
        {
            "knowledge_map_title": knowledge_map_title,
            "synthesis_title": synthesis_title,
            "reference_ids": reference_ids,
            "query": query,
            "focus": focus,
            "has_summary_markdown": bool(summary_markdown.strip()),
            "limit": limit,
            "project": project,
        },
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    project_msg = ensure_project_exists()
    result = ref_manager.materialize_agent_wiki(
        knowledge_map_title=knowledge_map_title,
        synthesis_title=synthesis_title,
        reference_ids=parse_reference_ids(reference_ids),
        query=query,
        focus=focus,
        summary_markdown=summary_markdown,
        limit=limit,
    )
    log_tool_result("materialize_agent_wiki", result)
    return result + project_msg
