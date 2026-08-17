"""Release hardening contracts for versions, authority docs, and workflows."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_ACTION = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_UV_ACTION = "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d"


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
    package_lock = json.loads(
        (REPO_ROOT / "vscode-extension" / "package-lock.json").read_text(encoding="utf-8")
    )

    expected = pyproject["project"]["version"]
    assert package_json["version"] == expected
    assert package_lock["version"] == expected
    assert package_lock["packages"][""]["version"] == expected
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

    citation = (REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    citation_version = re.search(r"^version:\s*(\S+)$", citation, re.M)
    citation_date = re.search(r"^date-released:\s*(\d{4}-\d{2}-\d{2})$", citation, re.M)
    assert citation_version and citation_version.group(1) == expected
    assert citation_date

    for readme_name in ("README.md", "README.zh-TW.md"):
        readme = (REPO_ROOT / readme_name).read_text(encoding="utf-8")
        assert re.findall(r"version = \{([^}]+)\}", readme) == [expected]

    docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    assert f"`v{expected}` 提供 MCP SDK2-only runtime" in docs_index

    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{expected}] - {citation_date.group(1)}" in changelog
    vsx_changelog = (REPO_ROOT / "vscode-extension" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {expected} - {citation_date.group(1)}" in vsx_changelog

    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    root_packages = [
        package for package in lock["package"] if package["name"] == "med-paper-assistant"
    ]
    assert len(root_packages) == 1
    assert root_packages[0]["version"] == expected


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
    assert "git add -A" not in script
    for surface in (
        "CITATION.cff",
        "README.md",
        "README.zh-TW.md",
        "docs/index.md",
        "CHANGELOG.md",
        "vscode-extension/CHANGELOG.md",
        "uv lock --offline",
    ):
        assert surface in script


def test_release_entrypoint_is_preflight_first_and_never_stages_source() -> None:
    script = (REPO_ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")

    assert "--untracked-files=all" in script
    assert "uv lock --check" in script
    assert "test_release_hardening.py" in script
    assert "test:install-smoke" in script
    assert "git add" not in script
    assert "bump-version.sh" not in script


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
    assert "VALIDATED_VERSION: ${{ steps.version.outputs.version }}" in content
    assert 'TAG_VERSION="$VALIDATED_VERSION"' in content
    assert "RELEASE_REF:" in content
    assert "ref: ${{ env.RELEASE_REF }}" in content


def test_release_workflow_accepts_stable_versions_only() -> None:
    content = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 're.fullmatch(r"[0-9]+\\.[0-9]+\\.[0-9]+", version)' in content
    assert "((a|b|rc)" not in content
    assert "\\.post[0-9]+" not in content
    assert "\\.dev[0-9]+" not in content


def test_release_runs_all_managed_exact_archive_smokes() -> None:
    content = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "Initialize and inspect all five immutable SDK2 archives" in content
    assert "tests/integration/test_zotero_sdk2_install_smoke.py" in content


def test_release_workflow_uses_frozen_dependency_installs() -> None:
    release = _workflow("release.yml")
    for job_name, step in _iter_steps(release):
        uses = step.get("uses", "")
        if uses == SETUP_UV_ACTION:
            assert step.get("with", {}).get("version") == "0.12.5", job_name
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


def test_release_artifacts_are_installed_and_published_together() -> None:
    content = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    release = _workflow("release.yml")
    build_steps = {step.get("name"): step for step in release["jobs"]["build-artifacts"]["steps"]}

    assert "Install and smoke-test the built wheel" in build_steps
    assert (
        "${WHEEL_PATH}[provenance,watermark]"
        in build_steps["Install and smoke-test the built wheel"]["run"]
    )
    assert "Install VSIX into an isolated VS Code profile" in build_steps
    assert (
        "test:install-smoke" in build_steps["Install VSIX into an isolated VS Code profile"]["run"]
    )
    assert "medpaper-python-dist-${{ needs.validate.outputs.version }}" in content
    assert 'files: "release-assets/*"' in content
    publish_steps = {
        step.get("name"): step
        for step in release["jobs"]["publish-vsx"]["steps"]
        if step.get("name")
    }
    assert "Smoke the published runtime and watermark extras" in publish_steps
    assert (
        "med-paper-assistant[provenance,watermark]=="
        in publish_steps["Smoke the published runtime and watermark extras"]["run"]
    )
    assert "update.code.visualstudio.com/latest" not in content
    assert "sha256sum --check --strict" in content
    assert "needs.publish-pypi.result == 'success'" in content
    assert 'echo "VSCODE_CLI=$RUNNER_TEMP/vscode-linux/bin/code"' in content
    assert "VSCODE_CLI_JS" not in content
    install_smoke = (REPO_ROOT / "vscode-extension" / "scripts" / "install-smoke.cjs").read_text(
        encoding="utf-8"
    )
    assert "process.env.VSCODE_CLI" in install_smoke
    assert "--install-extension" in install_smoke
    assert "--list-extensions" in install_smoke
    assert "needs.publish-vsx.result" in content


def test_release_bundle_checks_have_recursive_submodules() -> None:
    release = _workflow("release.yml")
    for job_name in ("validate", "vsx-bundle-drift", "build-artifacts"):
        checkout = next(
            step
            for step in release["jobs"][job_name]["steps"]
            if step.get("uses") == CHECKOUT_ACTION
        )
        assert checkout.get("with", {}).get("submodules") == "recursive", job_name


def test_marketplace_recovery_is_manual_least_privilege_and_fail_closed() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "marketplace-recovery.yml"
    content = workflow_path.read_text(encoding="utf-8")
    recovery = _workflow("marketplace-recovery.yml")

    assert "workflow_dispatch:" in content
    assert "push:" not in content
    assert "pull_request:" not in content
    assert recovery.get("permissions") == {"contents": "read"}
    assert recovery["concurrency"]["group"] == "marketplace-recovery-u9401066-medpaper-assistant"
    assert recovery["concurrency"]["cancel-in-progress"] is False
    assert "confirm_publish" in content
    assert "expected_sha256" in content
    assert "continue-on-error" not in content
    assert "--oidc" not in content

    publish = recovery["jobs"]["publish-and-verify"]
    assert publish["needs"] == ["validate-inputs", "validate-artifact"]
    assert publish["environment"]["name"] == "vs-marketplace"
    assert "id-token" not in json.dumps(publish)
    recovery_checkouts = [
        step for _, step in _iter_steps(recovery) if step.get("uses") == CHECKOUT_ACTION
    ]
    assert recovery_checkouts
    assert all(
        step.get("with", {}).get("persist-credentials") is False for step in recovery_checkouts
    )


def test_marketplace_recovery_binds_and_installs_the_existing_release_asset() -> None:
    content = (REPO_ROOT / ".github" / "workflows" / "marketplace-recovery.yml").read_text(
        encoding="utf-8"
    )

    for contract in (
        "refs/tags/v${{ needs.validate-inputs.outputs.version }}",
        "git cat-file -t",
        'gh api "repos/$GITHUB_REPOSITORY/releases/tags/$RELEASE_TAG"',
        "gh release download",
        "RELEASE_DIGEST",
        "sha256sum --check --strict",
        "extension/package.json",
        "extension.vsixmanifest",
        "VSIX contains duplicate archive members",
        "VSIX contains an unsafe archive member",
        'if "\\\\" in name',
        "npm ci --ignore-scripts",
        "test:install-smoke",
        "VSCODE_VERSION=1.101.2",
        "VSCODE_SHA256=ef62ab0835017bec498e7498fe79eb347f7610fe2da7bd71d5f69d8743ded033",
    ):
        assert contract in content


def test_marketplace_recovery_limits_pat_exposure_and_verifies_public_hash() -> None:
    recovery = _workflow("marketplace-recovery.yml")
    content = (REPO_ROOT / ".github" / "workflows" / "marketplace-recovery.yml").read_text(
        encoding="utf-8"
    )
    publish_steps = recovery["jobs"]["publish-and-verify"]["steps"]
    secret_steps = [
        step.get("name") for step in publish_steps if "secrets.VSCE_PAT" in json.dumps(step)
    ]
    workflow_secret_references = sum(
        path.read_text(encoding="utf-8").count("secrets.VSCE_PAT")
        for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml")
    )

    assert secret_steps == [
        "Verify Marketplace PAT authorization",
        "Publish the verified VSIX",
    ]
    assert workflow_secret_references == 2
    assert "verify-pat u9401066" in content
    assert "--skip-duplicate" in content
    assert '-p "$VSCE_PAT"' not in content
    assert "Microsoft.VisualStudio.Services.VsixSha256" in content
    assert "ACTUAL_SHA256" in content
    assert "Marketplace did not expose" in content
