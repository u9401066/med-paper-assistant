"""
Shared utilities for MCP tools.
"""

from .project_context import (
    ensure_project_context,
    get_concept_path,
    get_drafts_dir,
    get_project_list_for_prompt,
    get_project_path,
    validate_project_for_tool,
    validate_project_slug,
)
from .tool_logging import (
    get_tool_logger,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    with_tool_logging,
)

__all__ = [
    "ensure_project_context",
    "validate_project_slug",
    "get_project_list_for_prompt",
    # Project path helpers
    "get_project_path",
    "get_drafts_dir",
    "get_concept_path",
    "validate_project_for_tool",
    # Logging utilities
    "get_tool_logger",
    "log_tool_call",
    "log_tool_result",
    "log_tool_error",
    "log_agent_misuse",
    "with_tool_logging",
]
