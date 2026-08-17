import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_tool_surface_authority.py"


def test_tool_surface_authority_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise AssertionError(result.stdout + "\n" + result.stderr)


def test_forbidden_legacy_doc_snippets_are_absent() -> None:
    authority = json.loads((REPO_ROOT / "tool-surface-authority.json").read_text(encoding="utf-8"))

    assert set(authority["externalMcp"]) == {
        "asset-aware",
        "pubmed-search",
        "cgu",
        "drawio",
        "zotero-keeper",
    }
    for relative_path, snippets in authority["forbiddenDocs"].items():
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert not [snippet for snippet in snippets if snippet in content], relative_path
