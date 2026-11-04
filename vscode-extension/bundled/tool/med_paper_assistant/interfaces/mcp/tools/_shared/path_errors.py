"""Convert path-guard rejections raised inside tool handlers into clean tool errors."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from med_paper_assistant.shared.path_guard import PathGuardError

ToolDecorator = Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]


def catch_path_errors(tool: ToolDecorator) -> ToolDecorator:
    """Wrap a tool decorator so a ``PathGuardError`` becomes a ``❌`` message.

    Handlers keep their return-a-string contract (and are returned unchanged to the
    caller of the decorator, so facades invoking them directly get the same behaviour).
    """

    def guarded_tool(
        *args: Any, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        register = tool(*args, **kwargs)

        def decorate(handler: Callable[..., Any]) -> Callable[..., Any]:
            if inspect.iscoroutinefunction(handler):

                @functools.wraps(handler)
                async def async_wrapper(*a: Any, **kw: Any) -> Any:
                    try:
                        return await handler(*a, **kw)
                    except PathGuardError as exc:
                        return f"❌ {exc}"

                return register(async_wrapper)

            @functools.wraps(handler)
            def wrapper(*a: Any, **kw: Any) -> Any:
                try:
                    return handler(*a, **kw)
                except PathGuardError as exc:
                    return f"❌ {exc}"

            return register(wrapper)

        return decorate

    return guarded_tool


__all__ = ["catch_path_errors"]
