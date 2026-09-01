"""Contract tests for GitHub Actions workflow runtime hygiene."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
pytestmark = pytest.mark.contract

ACTION_PINS = {
    "actions/checkout": ("3d3c42e5aac5ba805825da76410c181273ba90b1", "v7.0.1"),
    "actions/configure-pages": ("45bfe0192ca1faeb007ade9deae92b16b8254a0d", "v6.0.0"),
    "actions/deploy-pages": ("cd2ce8fcbc39b97be8ca5fce6e763baed58fa128", "v5.0.0"),
    "actions/download-artifact": ("3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c", "v8.0.1"),
    "actions/github-script": ("3a2844b7e9c422d3c10d287c895573f7108da1b3", "v9.0.0"),
    "actions/setup-node": ("820762786026740c76f36085b0efc47a31fe5020", "v7.0.0"),
    "actions/setup-python": ("5fda3b95a4ea91299a34e894583c3862153e4b97", "v7.0.0"),
    "actions/upload-artifact": ("043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "v7.0.1"),
    "actions/upload-pages-artifact": ("fc324d3547104276b827a68afc52ff2a11cc49c9", "v5.0.0"),
    "astral-sh/setup-uv": ("20cfd1bf945f4377ade1205e4dbc17946fc9a30d", "v10.0.1"),
    "pypa/gh-action-pypi-publish": ("dc37677b2e1c63e2034f94d8a5b11f265b73ba33", "v1.14.2"),
    "softprops/action-gh-release": ("3d0d9888cb7fd7b750713d6e236d1fcb99157228", "v3.0.2"),
}


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that fails instead of silently overwriting duplicate keys."""


def _construct_unique_mapping(
    loader: yaml.SafeLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_workflow(path: Path) -> dict[str, Any]:
    loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    assert isinstance(loaded, dict), f"{path} must contain a YAML mapping"
    return loaded


def _workflow_data() -> dict[str, dict[str, Any]]:
    return {path.name: _load_workflow(path) for path in sorted(WORKFLOW_DIR.glob("*.yml"))}


def _iter_steps(data: dict[str, Any]):
    jobs = data.get("jobs", {})
    for job in jobs.values():
        for step in job.get("steps", []):
            yield step


def test_workflow_yaml_has_unique_keys() -> None:
    """Every workflow must parse without YAML mappings silently losing a duplicate key."""
    assert _workflow_data()


def test_remote_actions_are_verified_immutable_commits_with_version_comments() -> None:
    """Every remote action is a reviewed commit pin with a human-readable stable tag."""
    seen: set[str] = set()
    line_pattern = re.compile(
        r"^\s*(?:-\s+)?uses:\s+([^@\s]+)@([0-9a-f]{40})\s+#\s+(v\d+\.\d+\.\d+)\s*$"
    )
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "uses:" not in line or "uses: ./" in line or "uses: docker://" in line:
                continue
            match = line_pattern.fullmatch(line)
            assert match, f"{path.name}:{line_number} has an unpinned or uncommented action"
            action, sha, version = match.groups()
            assert action in ACTION_PINS, (
                f"{path.name}:{line_number} uses unreviewed action {action}"
            )
            assert (sha, version) == ACTION_PINS[action]
            seen.add(action)

    assert seen == set(ACTION_PINS)

    parsed_uses = {
        step["uses"]
        for workflow in _workflow_data().values()
        for step in _iter_steps(workflow)
        if "uses" in step and not str(step["uses"]).startswith(("./", "docker://"))
    }
    assert parsed_uses == {f"{action}@{sha}" for action, (sha, _) in ACTION_PINS.items()}


def test_setup_node_uses_node24():
    """Workflow Node runtime should match the GitHub Actions Node 24 transition."""
    setup_node_ref = f"actions/setup-node@{ACTION_PINS['actions/setup-node'][0]}"
    setup_node_steps = [
        step
        for workflow in _workflow_data().values()
        for step in _iter_steps(workflow)
        if step.get("uses") == setup_node_ref
    ]

    assert setup_node_steps
    assert all(str(step.get("with", {}).get("node-version")) == "24" for step in setup_node_steps)


def test_setup_uv_version_policy_is_reproducible_across_workflows() -> None:
    setup_uv_ref = f"astral-sh/setup-uv@{ACTION_PINS['astral-sh/setup-uv'][0]}"
    for workflow_name, workflow in _workflow_data().items():
        versions = [
            str(step.get("with", {}).get("version"))
            for step in _iter_steps(workflow)
            if step.get("uses") == setup_uv_ref
        ]
        if versions:
            assert set(versions) == {"0.12.5"}, workflow_name


def test_vscode_types_match_the_first_stable_mcp_provider_engine() -> None:
    package = json.loads((REPO_ROOT / "vscode-extension" / "package.json").read_text())
    lock = json.loads((REPO_ROOT / "vscode-extension" / "package-lock.json").read_text())

    assert package["engines"]["vscode"] == "^1.101.0"
    assert package["devDependencies"]["@types/vscode"] == "1.101.0"
    assert lock["packages"][""]["devDependencies"]["@types/vscode"] == "1.101.0"
    assert lock["packages"]["node_modules/@types/vscode"]["version"] == "1.101.0"


def test_documentation_and_test_dependencies_are_locked_to_supported_releases() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_versions = {package["name"]: package["version"] for package in lock["package"]}

    assert pyproject["dependency-groups"]["docs"] == ["mkdocs-material==9.7.7"]
    assert locked_versions["mkdocs-material"] == "9.7.7"
    assert locked_versions["pytest-timeout"] == "2.4.0"


def test_release_install_smokes_use_the_verified_minimum_api_patch() -> None:
    for workflow_name in ("release.yml", "marketplace-recovery.yml"):
        content = (WORKFLOW_DIR / workflow_name).read_text(encoding="utf-8")
        assert "VSCODE_VERSION=1.101.2" in content
        assert (
            "VSCODE_SHA256="
            "ef62ab0835017bec498e7498fe79eb347f7610fe2da7bd71d5f69d8743ded033" in content
        )
        assert "update.code.visualstudio.com/${VSCODE_VERSION}/linux-x64/stable" in content
        assert "sha256sum --check --strict" in content
