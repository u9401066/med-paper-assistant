#!/usr/bin/env python3
"""Build or verify the dependency-free documentation index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
MANIFEST_PATH = DOCS_DIR / "site-manifest.yaml"
OUTPUT_PATH = DOCS_DIR / "site-content.js"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("docs site manifest must be a mapping")
    return loaded


def validate_manifest(manifest: dict[str, Any], docs_dir: Path = DOCS_DIR) -> list[str]:
    issues: list[str] = []
    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups:
        return ["groups must be a non-empty list"]

    group_ids: set[str] = set()
    paths: set[str] = set()
    for group_index, group in enumerate(groups):
        if not isinstance(group, dict):
            issues.append(f"groups[{group_index}] must be a mapping")
            continue
        group_id = str(group.get("id", "")).strip()
        if not group_id or group_id in group_ids:
            issues.append(f"groups[{group_index}].id must be non-empty and unique")
        group_ids.add(group_id)
        items = group.get("items")
        if not isinstance(items, list) or not items:
            issues.append(f"groups[{group_index}].items must be a non-empty list")
            continue
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                issues.append(f"groups[{group_index}].items[{item_index}] must be a mapping")
                continue
            relative_path = str(item.get("path", "")).strip()
            if not relative_path or relative_path in paths:
                issues.append(f"duplicate or missing documentation path: {relative_path!r}")
                continue
            paths.add(relative_path)
            candidate = (docs_dir / relative_path).resolve()
            try:
                candidate.relative_to(docs_dir.resolve())
            except ValueError:
                issues.append(f"documentation path escapes docs/: {relative_path}")
                continue
            if not candidate.is_file():
                issues.append(f"documentation path not found: {relative_path}")
    return issues


def render_site_content(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    return f"window.MEDPAPER_DOCS = {payload};\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without writing")
    args = parser.parse_args()

    manifest = load_manifest()
    issues = validate_manifest(manifest)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1

    rendered = render_site_content(manifest)
    if args.check:
        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
            print("ERROR: docs/site-content.js is out of sync; run scripts/build_docs_site.py")
            return 1
        print(
            f"Documentation site verified: {sum(len(g['items']) for g in manifest['groups'])} pages"
        )
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Documentation site index written: {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
