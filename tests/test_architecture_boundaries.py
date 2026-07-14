"""Static contracts for the documented DDD dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path


def _imports_under(root: Path) -> list[tuple[Path, str]]:
    imports: list[tuple[Path, str]] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((path, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append((path, node.module))
    return imports


def test_application_layer_does_not_import_infrastructure_or_interfaces() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "med_paper_assistant" / "application"
    violations = [
        f"{path.relative_to(root)} -> {module}"
        for path, module in _imports_under(root)
        if module.startswith(
            (
                "med_paper_assistant.infrastructure",
                "med_paper_assistant.interfaces",
            )
        )
    ]
    assert violations == []


def test_domain_layer_does_not_import_application_infrastructure_or_interfaces() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "med_paper_assistant" / "domain"
    violations = [
        f"{path.relative_to(root)} -> {module}"
        for path, module in _imports_under(root)
        if module.startswith(
            (
                "med_paper_assistant.application",
                "med_paper_assistant.infrastructure",
                "med_paper_assistant.interfaces",
            )
        )
    ]
    assert violations == []
