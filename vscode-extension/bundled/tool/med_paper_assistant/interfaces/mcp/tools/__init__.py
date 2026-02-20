"""
MCP Tools Module

Provides all tool registration functions for the MedPaper Assistant MCP server.

Structure:
- project/     - Project management (CRUD, settings, exploration, diagrams)
- draft/       - Draft writing and templates
- reference/   - Reference management and citation
- validation/  - Concept and idea validation
- analysis/    - Data analysis and Table 1 generation
- review/      - Manuscript consistency checking
- export/      - Word document export
- _shared/     - Shared utilities

Removed:
- search/      - Moved to pubmed-search MCP server (use MCP protocol)
- diagram/     - Merged into project/ module
"""

# Import register functions from each module
# Shared utilities
from ._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    validate_project_slug,
)
from .analysis import register_analysis_tools
from .draft import register_draft_tools
from .export import register_export_tools
from .project import register_project_tools
from .reference import register_reference_tools
from .review import register_review_tools
from .validation import register_validation_tools

__all__ = [
    "register_project_tools",
    "register_draft_tools",
    "register_reference_tools",
    "register_validation_tools",
    "register_export_tools",
    "register_analysis_tools",
    "register_review_tools",
    # Shared utilities
    "ensure_project_context",
    "validate_project_slug",
    "get_project_list_for_prompt",
]
