"""
MCP Server Tools Package

This package contains all MCP tool definitions organized by functionality:
- search_tools: Literature search and strategy management
- reference_tools: Reference management and citation formatting
- draft_tools: Draft creation and editing
- analysis_tools: Data analysis, statistics, and visualization
- export_tools: Word document export workflow
"""

from .search_tools import register_search_tools
from .reference_tools import register_reference_tools
from .draft_tools import register_draft_tools
from .analysis_tools import register_analysis_tools
from .export_tools import register_export_tools

__all__ = [
    "register_search_tools",
    "register_reference_tools",
    "register_draft_tools",
    "register_analysis_tools",
    "register_export_tools",
]
