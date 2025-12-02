"""
MCP Tools Module

Provides all tool registration functions for the MedPaper Assistant MCP server.

Structure:
- project/     - Project management (CRUD, settings, exploration, diagrams)
- draft/       - Draft writing and templates
- search/      - Literature search (PubMed) - uses pubmed-search-mcp submodule
- reference/   - Reference management and citation
- validation/  - Concept and idea validation
- export/      - Word document export
- skill/       - Workflow skills management
- _shared/     - Shared utilities

Removed:
- analysis/    - Moved to separate project (data-analysis-mcp)
- diagram/     - Merged into project/ module
"""

# Import register functions from each module
from .project import register_project_tools
from .draft import register_draft_tools
from .search import register_search_tools
from .reference import register_reference_tools
from .validation import register_validation_tools
from .export import register_export_tools

# Shared utilities
from ._shared import (
    ensure_project_context,
    validate_project_slug,
    get_project_list_for_prompt,
)

# Future modules (placeholder - not registered yet)
# from .discussion import register_discussion_tools
# from .review import register_review_tools

__all__ = [
    "register_project_tools",
    "register_draft_tools",
    "register_search_tools",
    "register_reference_tools",
    "register_validation_tools",
    "register_export_tools",
    # Shared utilities
    "ensure_project_context",
    "validate_project_slug",
    "get_project_list_for_prompt",
    # Future:
    # "register_discussion_tools",
    # "register_review_tools",
]
