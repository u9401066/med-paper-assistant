"""YAML value escaping shared across infrastructure and interface layers.

A single source of truth for escaping scalar values that are written into
double-quoted YAML frontmatter. Backslashes must be escaped first, then
double quotes, so that ``\\`` does not get double-counted.
"""

from __future__ import annotations

_CONTROL_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def escape_yaml_value(value: str) -> str:
    """Escape a value for a double-quoted YAML scalar on a single line.

    Order matters: backslashes are escaped before quotes so an existing
    ``\\`` is not mistaken for the escape introduced by the quote pass.
    Newlines, tabs and other control characters are escaped too so a value
    can never terminate the line and inject extra frontmatter keys.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    out: list[str] = []
    for ch in escaped:
        if ch in _CONTROL_ESCAPES:
            out.append(_CONTROL_ESCAPES[ch])
        elif ord(ch) < 32 or ord(ch) == 127 or ch in "\u0085\u2028\u2029":
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return "".join(out)
