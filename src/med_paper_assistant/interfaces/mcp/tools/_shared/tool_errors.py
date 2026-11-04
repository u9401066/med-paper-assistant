"""Convert "❌ ..." failure strings into MCP tool errors (``isError=True``).

Handlers keep returning human-readable strings so direct calls and unit tests are
unchanged. Only the callable registered with the MCP server is wrapped, so clients
receive ``isError=True`` with the same text.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

FAILURE_PREFIX = "❌"


def is_failure_result(result: Any) -> bool:
    """Return True when a handler result is a textual failure report."""
    return isinstance(result, str) and result.lstrip().startswith(FAILURE_PREFIX)


def raise_for_failure(result: Any) -> Any:
    """Raise ``ToolError`` for failure strings; pass every other result through."""
    if is_failure_result(result):
        raise ToolError(result.strip())
    return result


def wrap_tool_function(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap ``fn`` so failure strings raise ``ToolError`` (signature preserved)."""
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return raise_for_failure(await fn(*args, **kwargs))

        return async_wrapper

    @functools.wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        return raise_for_failure(fn(*args, **kwargs))

    return sync_wrapper


def enable_failure_errors(mcp: MCPServer) -> MCPServer:
    """Make every tool added to ``mcp`` report "❌" results as MCP errors.

    ``@mcp.tool()`` still returns the original function, so callers that use the
    returned handlers directly keep receiving the plain string.
    """
    original_add_tool = mcp.add_tool

    def add_tool(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        original_add_tool(wrap_tool_function(fn), *args, **kwargs)

    mcp.add_tool = add_tool  # type: ignore[method-assign]
    return mcp


__all__ = [
    "FAILURE_PREFIX",
    "enable_failure_errors",
    "is_failure_result",
    "raise_for_failure",
    "wrap_tool_function",
]
