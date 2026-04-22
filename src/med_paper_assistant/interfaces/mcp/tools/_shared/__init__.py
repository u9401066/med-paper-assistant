"""
Shared utilities for MCP tools.
"""

from .checkpoint import auto_checkpoint_writing
from .facade_dispatch import (
    get_optional_tool_decorator,
    invoke_tool_handler,
    normalize_facade_action,
)
from .progress import report_tool_progress
from .project_context import (
    ensure_project_context,
    get_concept_path,
    get_drafts_dir,
    get_project_list_for_prompt,
    get_project_path,
    resolve_project_context,
    validate_project_for_tool,
    validate_project_for_workflow,
    validate_project_slug,
)
from .tool_logging import (
    get_tool_logger,
    initialize_tool_tracking,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    with_tool_logging,
)

__all__ = [
    "auto_checkpoint_writing",
    "get_optional_tool_decorator",
    "invoke_tool_handler",
    "normalize_facade_action",
    "report_tool_progress",
    "ensure_project_context",
    "validate_project_slug",
    "get_project_list_for_prompt",
    "resolve_project_context",
    # Project path helpers
    "get_project_path",
    "get_drafts_dir",
    "get_concept_path",
    "validate_project_for_tool",
    "validate_project_for_workflow",
    # Logging utilities
    "get_tool_logger",
    "initialize_tool_tracking",
    "log_tool_call",
    "log_tool_result",
    "log_tool_error",
    "log_agent_misuse",
    "with_tool_logging",
]
