"""Bind registration-time dependencies to module-level MCP tool handlers.

Handlers used to be closures inside ``register_*`` functions and read services from the
enclosing scope. They now live at module level and read the services bound for the
current call from a ``DepsBinding``. ``bind`` wraps each handler with
``functools.wraps`` so the name, annotations and signature that MCP introspects stay
unchanged.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from typing import Any, Generic, TypeVar

T = TypeVar("T")

_NESTED_INDENT = "    "


def nested_doc(doc: str | None, levels: int = 1) -> str | None:
    """Indent a module-level docstring ``levels`` indentation levels deeper.

    MCP publishes the raw ``__doc__`` as the tool description, and these handlers used to
    be nested inside ``register_*`` functions, so their docstrings carried extra
    indentation levels.
    """
    if not doc:
        return doc
    first, *rest = doc.split("\n")
    if not rest:
        return doc
    indent = _NESTED_INDENT * levels
    indented = [indent + line if line.strip() else line for line in rest[:-1]]
    indented.append(indent + rest[-1])
    return "\n".join([first, *indented])


def register_handlers(
    tool: Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]],
    handlers: Sequence[Callable[..., Any]],
) -> dict[str, Callable[..., Any]]:
    """Register each handler with ``tool()`` in order and return the results by name."""
    return {handler.__name__: tool()(handler) for handler in handlers}


class DepsBinding(Generic[T]):
    """Holds the dependencies that bound handlers read while they run."""

    def __init__(self, name: str) -> None:
        self._var: ContextVar[T] = ContextVar(name)

    def get(self) -> T:
        return self._var.get()

    def bind(
        self, deps: T, handlers: Sequence[Callable[..., Any]], *, doc_levels: int = 1
    ) -> list[Callable[..., Any]]:
        return [self._bind_one(deps, handler, doc_levels) for handler in handlers]

    def _bind_one(
        self, deps: T, handler: Callable[..., Any], doc_levels: int
    ) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(handler):
            bound = self._bind_async(deps, handler)
        else:
            bound = self._bind_sync(deps, handler)
        bound.__doc__ = nested_doc(handler.__doc__, doc_levels)
        return bound

    def _bind_sync(self, deps: T, handler: Callable[..., Any]) -> Callable[..., Any]:
        var = self._var

        @functools.wraps(handler)
        def bound(*args: Any, **kwargs: Any) -> Any:
            token = var.set(deps)
            try:
                return handler(*args, **kwargs)
            finally:
                var.reset(token)

        return bound

    def _bind_async(self, deps: T, handler: Callable[..., Any]) -> Callable[..., Any]:
        var = self._var

        @functools.wraps(handler)
        async def bound(*args: Any, **kwargs: Any) -> Any:
            token = var.set(deps)
            try:
                return await handler(*args, **kwargs)
            finally:
                var.reset(token)

        return bound
