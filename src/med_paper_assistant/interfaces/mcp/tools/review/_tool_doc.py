"""Docstring helper for module-level MCP tool handlers."""

from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable[..., object])

_NESTED_INDENT = "    "


def nested_tool_doc(fn: F) -> F:
    """Indent a module-level handler docstring one level deeper, in place.

    MCP publishes the raw ``fn.__doc__`` as the tool description. These handlers used
    to be defined inside ``register_*`` functions, so their docstrings carried one extra
    indentation level; this keeps the published descriptions byte-identical.
    """
    doc = fn.__doc__
    if doc:
        first, *rest = doc.split("\n")
        indented = [_NESTED_INDENT + line if line.strip() else line for line in rest[:-1]]
        if rest:
            indented.append(_NESTED_INDENT + rest[-1])
        fn.__doc__ = "\n".join([first, *indented])
    return fn
