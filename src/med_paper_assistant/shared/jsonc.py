"""Small, dependency-free JSONC parsing helpers.

The parser accepts JavaScript-style line and block comments plus trailing
commas, while preserving comment-like text inside JSON strings (for example,
``https://`` URLs). Strict JSON is attempted first so normal configuration
files keep the standard library's exact behaviour and diagnostics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def strip_jsonc_comments(text: str) -> str:
    """Remove JSONC comments without changing quoted string content."""
    output: list[str] = []
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if in_line_comment:
            if char in "\r\n":
                in_line_comment = False
                output.append(char)
            index += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 2
                continue
            if char in "\r\n":
                output.append(char)
            index += 1
            continue

        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            index += 2
            continue

        output.append(char)
        index += 1

    return "".join(output)


def strip_jsonc_trailing_commas(text: str) -> str:
    """Remove commas immediately before a closing object or array token."""
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue

        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue

        output.append(char)
        index += 1

    return "".join(output)


def loads_jsonc(text: str) -> Any:
    """Parse strict JSON or JSONC text and return the decoded value."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        normalized = strip_jsonc_trailing_commas(strip_jsonc_comments(text))
        return json.loads(normalized)


def load_jsonc(path: Path) -> Any:
    """Read and parse a UTF-8 JSON or JSONC file."""
    return loads_jsonc(path.read_text(encoding="utf-8"))
