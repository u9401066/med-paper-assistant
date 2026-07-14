"""Release hardening contracts for versions, authority docs, and workflows."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _version_from_init(path: Path) -> str:
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.M)
    assert match, f"missing __version__ in {path}"
    return match.group(1)


def test_release_version_surfaces_match() -> None:
    """All runtime and packaging version surfaces must match before tagging."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_json = json.loads(
        (REPO_ROOT / "vscode-extension" / "package.json").read_text(encoding="utf-8")
    )

    expected = pyproject["project"]["version"]
    assert package_json["version"] == expected
    assert _version_from_init(REPO_ROOT / "src" / "med_paper_assistant" / "__init__.py") == expected
    assert (
        _version_from_init(
            REPO_ROOT
            / "vscode-extension"
            / "bundled"
            / "tool"
            / "med_paper_assistant"
            / "__init__.py"
        )
        == expected
    )


def test_sdist_is_explicitly_scoped() -> None:
    """Source distributions must not accidentally absorb VSIX/node/workspace artifacts."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    sdist = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]
    include = set(sdist.get("include", []))
    wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert "/src/med_paper_assistant" in include
    assert "/templates" in include
    assert wheel["force-include"]["templates"] == "med_paper_assistant/templates"
    assert "/README.md" in include
    assert all("vscode-extension" not in item for item in include)
    assert all("node_modules" not in item for item in include)


def test_release_helper_uses_portable_pep440_version_updates() -> None:
    script = (REPO_ROOT / "scripts" / "bump-version.sh").read_text(encoding="utf-8")

    assert "sed -i" not in script
    assert "PEP 440" in script
    assert "X.Y.Z-beta.1" not in script


def test_readme_authority_counts_have_no_stale_contradictions() -> None:
    """Authority-bearing docs must not contain old public count snippets."""
    forbidden = {
        "README.md": [
            r"\b115 tools\b",
            r"\b37 tools\b",
            r"CGU \(13\)",
            r"176\+ tools",
        ],
        "README.zh-TW.md": [
            r"\b115 tools\b",
            r"\b37 tools\b",
            r"CGU \(13\)",
            r"176\+ 個工具",
        ],
    }
    for relative, patterns in forbidden.items():
        content = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for pattern in patterns:
            assert not re.search(pattern, content), f"{relative} contains stale count {pattern}"


def _workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / ".github" / "workflows" / name).read_text()) or {}


def _iter_steps(workflow: dict[str, Any]):
    for job_name, job in workflow.get("jobs", {}).items():
        for step in job.get("steps", []):
            yield job_name, step


def test_release_workflow_uses_least_privilege_permissions() -> None:
    release = _workflow("release.yml")
    assert release.get("permissions") == {"contents": "read"}
    assert release["jobs"]["github-release"].get("permissions") == {"contents": "write"}
    assert release["jobs"]["publish-pypi"].get("permissions") == {"id-token": "write"}


def test_release_workflow_manual_dispatch_uses_explicit_version() -> None:
    content = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in content
    assert "DISPATCH_VERSION" in content
    assert "github.event.inputs.version" in content
    assert "Validate manual release tag exists" in content
    assert 'TAG_VERSION="${GITHUB_REF_NAME#v}"' in content
    assert 'TAG_VERSION="${{ steps.version.outputs.version }}"' in content


def test_release_workflow_uses_frozen_dependency_installs() -> None:
    release = _workflow("release.yml")
    for job_name, step in _iter_steps(release):
        uses = step.get("uses", "")
        if uses == "astral-sh/setup-uv@v7":
            assert step.get("with", {}).get("version") != "latest", job_name
        run = step.get("run", "")
        if "uv sync" in run:
            assert "--frozen" in run, f"{job_name} uses non-frozen uv sync"


def test_release_publish_jobs_depend_on_security_gate() -> None:
    release = _workflow("release.yml")
    assert "lint-security" in release["jobs"]
    for job_name in ("publish-pypi", "publish-vsx", "github-release"):
        needs = release["jobs"][job_name].get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "lint-security" in needs, f"{job_name} does not depend on lint-security"
