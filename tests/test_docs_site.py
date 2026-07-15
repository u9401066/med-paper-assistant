"""Contracts for the MkDocs-powered GitHub Pages wiki."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_docs_site.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_docs_site", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load build_docs_site.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _load_workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


def test_all_markdown_pages_are_unique_publishable_nav_entries() -> None:
    config = MODULE.load_config()
    assert MODULE.validate_config(config) == []
    paths = list(MODULE.iter_nav_paths(config["nav"]))
    assert len(paths) == len(set(paths))
    assert "wiki/research-pipeline.md" in paths
    assert "wiki/visual-atlas.md" in paths
    assert "wiki/development-and-release.md" in paths


def test_wiki_has_no_broken_local_source_links() -> None:
    assert MODULE.validate_markdown_links() == []


def test_visual_documentation_contracts_are_accessible_and_substantial() -> None:
    assert MODULE.validate_visuals() == []
    _, counts = MODULE.validate_site()
    assert counts["pages"] >= 30
    assert counts["mermaid"] >= 40
    assert counts["svg"] >= 8


def test_legacy_dependency_free_index_was_fully_replaced() -> None:
    for filename in MODULE.LEGACY_SITE_FILES:
        assert not (MODULE.DOCS_DIR / filename).exists()
    assert (MODULE.DOCS_DIR / "index.md").is_file()
    assert (REPO_ROOT / "mkdocs.yml").is_file()


def test_pages_workflow_builds_strictly_and_deploys_only_after_build() -> None:
    workflow = _load_workflow()
    build = workflow["jobs"]["build"]
    deploy = workflow["jobs"]["deploy"]
    build_steps = build["steps"]
    commands = "\n".join(str(step.get("run", "")) for step in build_steps)
    actions = {step.get("uses") for step in build_steps if step.get("uses")}

    assert "scripts/build_docs_site.py --check" in commands
    assert "mkdocs build --strict" in commands
    assert "actions/configure-pages@v5" in actions
    assert "actions/upload-pages-artifact@v4" in actions
    assert deploy["needs"] == "build"
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert deploy["steps"][0]["uses"] == "actions/deploy-pages@v4"
