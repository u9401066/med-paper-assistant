"""Shared helpers for consolidated MCP facade tools and optional registration."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any

from mcp.server.fastmcp import FastMCP


def normalize_facade_action(action: str, aliases: Mapping[str, str] | None = None) -> str:
    """Normalize a facade action name and resolve aliases."""
    normalized = action.strip().lower().replace("-", "_").replace(" ", "_")
    if aliases is None:
        return normalized
    return aliases.get(normalized, normalized)


def compact_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop only None values so defaulted falsey inputs still flow through."""
    return {key: value for key, value in kwargs.items() if value is not None}


async def invoke_tool_handler(handler: Callable[..., Any], **kwargs: Any) -> Any:
    """Call a registered MCP tool helper whether it is sync or async."""
    result = handler(**compact_kwargs(kwargs))
    if inspect.isawaitable(result):
        return await result
    return result


def get_optional_tool_decorator(
    mcp: FastMCP,
    *,
    register_public_verbs: bool,
) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """Return a FastMCP tool decorator or a no-op replacement."""

    def tool(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        if register_public_verbs:
            return mcp.tool(*args, **kwargs)

        def identity(handler: Callable[..., Any]) -> Callable[..., Any]:
            return handler

        return identity

    return tool
