"""Guard against locale-dependent text I/O.

Windows hosts with CJK locales (cp950, cp936, cp932) cannot decode the UTF-8
markdown/JSON this project writes unless every text read/write passes an
explicit ``encoding``. CI runners use cp1252, which silently masks the bug.
"""

from __future__ import annotations

import ast
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SCANNED_DIRS = ("src", "scripts")


def _is_text_open(node: ast.Call) -> bool:
    func = node.func
    if not (isinstance(func, ast.Name) and func.id == "open"):
        return False
    mode: ast.expr | None = node.args[1] if len(node.args) >= 2 else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    if mode is None:
        return True
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" not in mode.value


def _missing_encoding_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if any(keyword.arg in ("encoding", None) for keyword in node.keywords):
            continue
        func = node.func
        is_path_read = (
            isinstance(func, ast.Attribute) and func.attr == "read_text" and not node.args
        )
        is_path_write = (
            isinstance(func, ast.Attribute) and func.attr == "write_text" and len(node.args) == 1
        )
        if is_path_read or is_path_write or (_is_text_open(node) and len(node.args) <= 2):
            offenders.append(f"{path.relative_to(WORKSPACE_ROOT).as_posix()}:{node.lineno}")
            continue
        text_flag = next(
            (k for k in node.keywords if k.arg in ("text", "universal_newlines")),
            None,
        )
        if (
            text_flag is not None
            and isinstance(text_flag.value, ast.Constant)
            and text_flag.value.value is True
        ):
            offenders.append(f"{path.relative_to(WORKSPACE_ROOT).as_posix()}:{node.lineno}")
    return offenders


def test_text_io_always_specifies_encoding() -> None:
    offenders: list[str] = []
    for directory in SCANNED_DIRS:
        for path in sorted((WORKSPACE_ROOT / directory).rglob("*.py")):
            offenders.extend(_missing_encoding_calls(path))

    assert offenders == [], "Text I/O without explicit encoding:\n" + "\n".join(offenders)
