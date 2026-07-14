"""YAML value escaping shared across infrastructure and interface layers.

A single source of truth for escaping scalar values that are written into
double-quoted YAML frontmatter. Backslashes must be escaped first, then
double quotes, so that ``\\`` does not get double-counted.
"""

from __future__ import annotations


def escape_yaml_value(value: str) -> str:
    """Escape backslashes and double quotes for double-quoted YAML scalars.

    Order matters: backslashes are escaped before quotes so an existing
    ``\\`` is not mistaken for the escape introduced by the quote pass.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')
