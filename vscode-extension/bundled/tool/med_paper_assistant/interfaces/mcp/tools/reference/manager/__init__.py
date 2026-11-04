"""
Reference Manager Tools

save_reference, list, search, format, citation management, analysis
"""

from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from ..._binding import register_handlers
from ..._shared import get_optional_tool_decorator
from ._deps import REFERENCE, ReferenceDeps
from .analysis import get_reference_for_analysis, save_reference_analysis
from .intake import import_local_papers, ingest_markdown_source, ingest_web_source
from .maintenance import delete_reference, rebuild_foam_aliases
from .query import (
    format_references,
    get_reference_details,
    list_saved_references,
    read_reference_fulltext,
    search_local_references,
)
from .save import save_reference, save_reference_mcp, save_reference_pdf
from .wiki import (
    build_knowledge_map,
    build_synthesis_page,
    materialize_agent_wiki,
    resolve_reference_identity,
)

WIKI_HANDLERS = (
    import_local_papers,
    ingest_web_source,
    ingest_markdown_source,
    resolve_reference_identity,
    build_knowledge_map,
    build_synthesis_page,
    materialize_agent_wiki,
)

STANDARD_HANDLERS = (
    list_saved_references,
    search_local_references,
    get_reference_details,
    read_reference_fulltext,
    save_reference_pdf,
    format_references,
    rebuild_foam_aliases,
    delete_reference,
    get_reference_for_analysis,
    save_reference_analysis,
)

__all__ = ["STANDARD_HANDLERS", "WIKI_HANDLERS", "register_reference_manager_tools"]


def register_reference_manager_tools(
    mcp: MCPServer,
    ref_manager: ReferenceManager,
    drafter: Drafter,
    project_manager,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register reference management tools."""

    tool = get_optional_tool_decorator(
        mcp,
        register_public_verbs=register_public_verbs,
    )

    # Get project manager for auto-project creation
    deps = ReferenceDeps(ref_manager, ref_manager._project_manager)

    registered_save = register_handlers(tool, REFERENCE.bind(deps, (save_reference,)))
    registered_verified = register_handlers(mcp.tool, REFERENCE.bind(deps, (save_reference_mcp,)))
    registered_wiki: dict[str, Callable[..., Any]] = {}
    if register_public_verbs:
        # These handlers used to be nested one level deeper, inside an ``if`` block.
        registered_wiki = register_handlers(
            mcp.tool, REFERENCE.bind(deps, WIKI_HANDLERS, doc_levels=2)
        )
    registered_standard = register_handlers(tool, REFERENCE.bind(deps, STANDARD_HANDLERS))

    handlers: dict[str, Callable[..., Any]] = {
        **registered_save,
        **registered_verified,
        **registered_standard,
    }
    handlers.update(registered_wiki)
    return handlers
