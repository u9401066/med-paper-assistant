"""Shared helpers for consolidated MCP facade tools and optional registration."""

from __future__ import annotations

import difflib
import inspect
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from mcp.server import MCPServer


def normalize_facade_action(action: str, aliases: Mapping[str, str] | None = None) -> str:
    """Normalize a facade action name and resolve aliases."""
    normalized = action.strip().lower().replace("-", "_").replace(" ", "_")
    if aliases is None:
        return normalized
    return aliases.get(normalized, normalized)


def format_unsupported_action_error(
    tool: str,
    action: str,
    supported: Iterable[str],
    *,
    aliases: Mapping[str, str] | None = None,
    help_action: str = "list",
) -> str:
    """Build an actionable error for an unknown facade action with fuzzy suggestion."""
    supported_list = sorted(set(supported))
    candidates = sorted(set(supported_list) | set(aliases or ()))
    normalized = action.strip().lower().replace("-", "_").replace(" ", "_")
    matches = difflib.get_close_matches(normalized, candidates, n=2, cutoff=0.55)
    hint = ""
    if matches:
        resolved = [aliases.get(m, m) if aliases else m for m in matches]
        unique = list(dict.fromkeys(resolved))
        hint = f" Did you mean: {', '.join(unique)}?"
    return (
        f"❌ Unsupported action '{action}'.{hint} "
        f"Supported actions: {', '.join(supported_list)}. "
        f'Call `{tool}(action="{help_action}")` for parameter schemas.'
    )


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
    mcp: MCPServer,
    *,
    register_public_verbs: bool,
) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """Return a MCPServer tool decorator or a no-op replacement."""

    def tool(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        if register_public_verbs:
            return mcp.tool(*args, **kwargs)

        def identity(handler: Callable[..., Any]) -> Callable[..., Any]:
            return handler

        return identity

    return tool
