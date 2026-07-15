#!/usr/bin/env python3
"""Validate the MkDocs wiki source before a strict site build."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
CONFIG_PATH = ROOT / "mkdocs.yml"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target>[^)\n]+)\)")
MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\n]+)\)")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "app://")
LEGACY_SITE_FILES = (
    "index.html",
    "site-content.js",
    "site-manifest.yaml",
    "site.css",
    "site.js",
)


class MkDocsLoader(yaml.SafeLoader):
    """Safe YAML loader that preserves MkDocs' Python-name configuration values."""


def _python_name_constructor(loader: MkDocsLoader, suffix: str, node: yaml.nodes.Node) -> str:
    loader.construct_scalar(node)
    return suffix


MkDocsLoader.add_multi_constructor("tag:yaml.org,2002:python/name:", _python_name_constructor)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the checked-in MkDocs configuration without importing MkDocs."""

    loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=MkDocsLoader)
    if not isinstance(loaded, dict):
        raise ValueError("mkdocs.yml must contain a mapping")
    return loaded


def iter_nav_paths(node: object) -> Iterator[str]:
    """Yield source paths from MkDocs' recursively nested nav structure."""

    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for child in node:
            yield from iter_nav_paths(child)
    elif isinstance(node, dict):
        for child in node.values():
            yield from iter_nav_paths(child)


def _path_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def validate_config(config: dict[str, Any], docs_dir: Path = DOCS_DIR) -> list[str]:
    """Validate navigation completeness and the GitHub Pages contract."""

    issues: list[str] = []
    if config.get("site_url") != "https://u9401066.github.io/med-paper-assistant/":
        issues.append("site_url must target the repository GitHub Pages URL")
    if config.get("docs_dir", "docs") != "docs":
        issues.append("docs_dir must remain docs")
    if not isinstance(config.get("theme"), dict) or config["theme"].get("name") != "material":
        issues.append("theme.name must be material")

    nav_paths = list(iter_nav_paths(config.get("nav")))
    if not nav_paths:
        issues.append("nav must contain at least one documentation page")
        return issues
    if len(nav_paths) != len(set(nav_paths)):
        issues.append("nav paths must be unique")
    if "index.md" not in nav_paths:
        issues.append("nav must include index.md")

    for relative_path in nav_paths:
        candidate = docs_dir / relative_path
        if not _path_within(candidate, docs_dir):
            issues.append(f"nav path escapes docs/: {relative_path}")
        elif not candidate.is_file():
            issues.append(f"nav path not found: {relative_path}")

    markdown_pages = {path.relative_to(docs_dir).as_posix() for path in docs_dir.rglob("*.md")}
    orphan_pages = sorted(markdown_pages - set(nav_paths))
    for orphan in orphan_pages:
        issues.append(f"markdown page missing from nav: {orphan}")

    for stylesheet in config.get("extra_css", []):
        candidate = docs_dir / str(stylesheet)
        if not _path_within(candidate, docs_dir) or not candidate.is_file():
            issues.append(f"extra_css path not found: {stylesheet}")

    config_text = CONFIG_PATH.read_text(encoding="utf-8")
    if "name: mermaid" not in config_text:
        issues.append("native Mermaid custom fence is not configured")
    return issues


def _link_path(target: str) -> str | None:
    """Return the local path portion of a Markdown link, if it is local."""

    target = target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    if not target or target.startswith("#") or target.startswith(EXTERNAL_SCHEMES):
        return None
    return unquote(target.split("#", 1)[0].split("?", 1)[0])


def validate_markdown_links(docs_dir: Path = DOCS_DIR) -> list[str]:
    """Reject local links that cannot be published as part of the static site."""

    issues: list[str] = []
    for page in sorted(docs_dir.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            local_path = _link_path(match.group("target"))
            if local_path is None:
                continue
            candidate = page.parent / local_path
            if not _path_within(candidate, docs_dir):
                issues.append(
                    f"{page.relative_to(ROOT)} links outside publishable docs/: {local_path}"
                )
            elif not candidate.exists():
                issues.append(f"{page.relative_to(ROOT)} has a missing local link: {local_path}")
    return issues


def validate_visuals(docs_dir: Path = DOCS_DIR) -> list[str]:
    """Validate Mermaid coverage, image alternatives, and SVG accessibility."""

    issues: list[str] = []
    mermaid_count = 0
    for page in sorted(docs_dir.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        mermaid_count += len(re.findall(r"^```mermaid\s*$", text, flags=re.MULTILINE))
        for match in MARKDOWN_IMAGE.finditer(text):
            if not match.group("alt").strip():
                issues.append(f"{page.relative_to(ROOT)} contains an image without alt text")
    if mermaid_count < 40:
        issues.append(f"wiki must contain at least 40 Mermaid diagrams; found {mermaid_count}")

    svg_paths = sorted((docs_dir / "assets").glob("*.svg"))
    if len(svg_paths) < 8:
        issues.append(f"wiki must contain at least 8 SVG assets; found {len(svg_paths)}")
    for svg_path in svg_paths:
        try:
            root = ET.parse(svg_path).getroot()
        except ET.ParseError as exc:
            issues.append(f"{svg_path.relative_to(ROOT)} is invalid XML: {exc}")
            continue
        title = root.find(f"{{{SVG_NAMESPACE}}}title")
        description = root.find(f"{{{SVG_NAMESPACE}}}desc")
        if title is None or not (title.text or "").strip():
            issues.append(f"{svg_path.relative_to(ROOT)} is missing a non-empty <title>")
        if description is None or not (description.text or "").strip():
            issues.append(f"{svg_path.relative_to(ROOT)} is missing a non-empty <desc>")
        if root.get("role") != "img" or root.get("aria-labelledby") != "title desc":
            issues.append(f"{svg_path.relative_to(ROOT)} is missing SVG accessibility attributes")
    return issues


def validate_site(
    config_path: Path = CONFIG_PATH, docs_dir: Path = DOCS_DIR
) -> tuple[list[str], dict[str, int]]:
    """Run all source-level contracts and return issues plus useful counts."""

    config = load_config(config_path)
    issues = [
        *validate_config(config, docs_dir),
        *validate_markdown_links(docs_dir),
        *validate_visuals(docs_dir),
    ]
    for legacy_name in LEGACY_SITE_FILES:
        if (docs_dir / legacy_name).exists():
            issues.append(f"legacy documentation site file must be removed: docs/{legacy_name}")

    markdown_text = "\n".join(page.read_text(encoding="utf-8") for page in docs_dir.rglob("*.md"))
    counts = {
        "pages": len(list(docs_dir.rglob("*.md"))),
        "mermaid": len(re.findall(r"^```mermaid\s*$", markdown_text, flags=re.MULTILINE)),
        "svg": len(list((docs_dir / "assets").glob("*.svg"))),
    }
    return issues, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Retained for CI compatibility; validation is always read-only",
    )
    parser.parse_args()

    issues, counts = validate_site()
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    print(
        "Documentation wiki verified: "
        f"{counts['pages']} pages · {counts['mermaid']} Mermaid diagrams · "
        f"{counts['svg']} SVG assets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
