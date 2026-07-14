"""Contract tests for GitHub Actions workflow runtime hygiene."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def _workflow_data() -> dict[str, dict[str, Any]]:
    return {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for path in sorted(WORKFLOW_DIR.glob("*.yml"))
    }


def _iter_steps(data: dict[str, Any]):
    jobs = data.get("jobs", {})
    for job in jobs.values():
        for step in job.get("steps", []):
            yield step


def test_javascript_actions_are_on_node24_ready_majors():
    """Pinned workflow actions should use Node 24-ready major versions."""
    uses = {
        step["uses"]
        for workflow in _workflow_data().values()
        for step in _iter_steps(workflow)
        if "uses" in step
    }

    required = {
        "actions/checkout@v6",
        "actions/setup-node@v6",
        "actions/setup-python@v6",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "actions/github-script@v9",
        "astral-sh/setup-uv@v7",
        "softprops/action-gh-release@v3",
    }
    deprecated = {
        "actions/checkout@v4",
        "actions/setup-node@v4",
        "actions/setup-python@v5",
        "actions/upload-artifact@v4",
        "actions/download-artifact@v4",
        "actions/github-script@v7",
        "astral-sh/setup-uv@v5",
        "softprops/action-gh-release@v2",
    }

    assert required.issubset(uses)
    assert uses.isdisjoint(deprecated)


def test_setup_node_uses_node24():
    """Workflow Node runtime should match the GitHub Actions Node 24 transition."""
    setup_node_steps = [
        step
        for workflow in _workflow_data().values()
        for step in _iter_steps(workflow)
        if step.get("uses") == "actions/setup-node@v6"
    ]

    assert setup_node_steps
    assert all(str(step.get("with", {}).get("node-version")) == "24" for step in setup_node_steps)
