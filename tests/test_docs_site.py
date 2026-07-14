"""Contracts for the dependency-free documentation index."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_docs_site.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_docs_site", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load build_docs_site.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def test_docs_manifest_references_existing_unique_pages() -> None:
    manifest = MODULE.load_manifest()
    assert MODULE.validate_manifest(manifest) == []
    paths = [item["path"] for group in manifest["groups"] for item in group["items"]]
    assert len(paths) == len(set(paths))
    assert "harness/output-profiles.md" in paths
    assert "design/production-academic-writing-harness.md" in paths


def test_generated_site_content_is_in_sync() -> None:
    expected = MODULE.render_site_content(MODULE.load_manifest())
    assert MODULE.OUTPUT_PATH.read_text(encoding="utf-8") == expected


def test_docs_index_uses_local_dependency_free_assets() -> None:
    html = (MODULE.DOCS_DIR / "index.html").read_text(encoding="utf-8")
    assert 'href="site.css"' in html
    assert 'src="site-content.js"' in html
    assert 'src="site.js"' in html
    assert "https://" not in html
