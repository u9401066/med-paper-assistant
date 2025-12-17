"""
Shared utilities for MCP tools.
"""

from .project_context import (
    ensure_project_context,
    validate_project_slug,
    get_project_list_for_prompt
)

from .tool_logging import (
    get_tool_logger,
    log_tool_call,
    log_tool_result,
    log_tool_error,
    log_agent_misuse,
    with_tool_logging,
)

__all__ = [
    "ensure_project_context",
    "validate_project_slug", 
    "get_project_list_for_prompt",
    # Logging utilities
    "get_tool_logger",
    "log_tool_call",
    "log_tool_result",
    "log_tool_error",
    "log_agent_misuse",
    "with_tool_logging",
]
