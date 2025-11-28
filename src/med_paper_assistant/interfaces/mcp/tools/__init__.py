"""
MCP Server Tools Package

This package contains all MCP tool definitions organized by functionality:
- search_tools: Literature search and strategy management
- reference_tools: Reference management and citation formatting
- draft_tools: Draft creation and editing
- analysis_tools: Data analysis, statistics, and visualization
- export_tools: Word document export workflow
- diagram_tools: Diagram saving and management
- project_context: Project context validation utilities
"""

from .search_tools import register_search_tools
from .reference_tools import register_reference_tools
from .draft_tools import register_draft_tools
from .analysis_tools import register_analysis_tools
from .export_tools import register_export_tools
from .diagram_tools import register_diagram_tools
from .project_context import (
    ensure_project_context,
    validate_project_slug,
    get_project_list_for_prompt,
    ProjectContextError,
)

__all__ = [
    "register_search_tools",
    "register_reference_tools",
    "register_draft_tools",
    "register_analysis_tools",
    "register_export_tools",
    "register_diagram_tools",
    "ensure_project_context",
    "validate_project_slug",
    "get_project_list_for_prompt",
    "ProjectContextError",
]
