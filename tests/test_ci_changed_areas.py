"""Contract and edge tests for the fail-open CI area classifier.

The classifier gates required checks, so the tests focus on the failure mode
that matters: under-selection. Inputs are derived from the real bundle
manifest, tool-surface authority, and ci.yml so a new input that the VSIX or
smoke jobs read cannot silently escape its gate.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci_changed_areas.py"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED_CHECKS = {
    "python-lint": ("Python Lint & Security", "python"),
    "python-test": ("Python Tests", "python"),
    "vsx": ("VS Code Extension", "vsx"),
    "dashboard": ("Dashboard Build", "dashboard"),
    "markdown": ("Markdown Format", "markdown"),
}


def _load_module():
    spec = importlib.util.spec_from_file_location("ci_changed_areas", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load ci_changed_areas.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


areas = _load_module()
FULL = list(areas.FULL_SMOKE_OS)
WIN = list(areas.WINDOWS_SMOKE_OS)


def _ci_jobs() -> dict[str, Any]:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (
            ["memory-bank/progress.md"],
            {"python": False, "vsx": False, "markdown": True, "sdk2": False, "smoke_os": []},
        ),
        (
            ["dashboard/src/App.tsx"],
            {"python": False, "vsx": False, "dashboard": True, "markdown": False, "smoke_os": []},
        ),
        (
            ["docs/wiki/development-and-release.md"],
            {"python": True, "vsx": False, "markdown": True, "smoke_os": []},
        ),
        (
            ["src/med_paper_assistant/domain/entities/project.py"],
            {"python": True, "vsx": True, "markdown": False, "sdk2": False, "smoke_os": WIN},
        ),
        (["src/med_paper_assistant/infrastructure/x.py"], {"vsx": True, "smoke_os": FULL}),
        (["tests/test_anything.py"], {"python": True, "vsx": False, "smoke_os": WIN}),
        (["uv.lock"], {"python": True, "sdk2": True, "vsx": False, "smoke_os": FULL}),
        (["vscode-extension/src/extension.ts"], {"vsx": True, "smoke_os": FULL}),
        (["integrations/cgu/src/cgu/server.py"], {"vsx": True, "sdk2": True, "smoke_os": FULL}),
        (["scripts/setup-integrations.ps1"], {"python": True, "vsx": False, "smoke_os": FULL}),
        (["tool-surface-authority.json"], {"python": True, "vsx": True, "smoke_os": []}),
        (["README.md"], {"vsx": True, "markdown": True}),
        (["./src\\med_paper_assistant\\domain\\x.py", "  "], {"python": True, "smoke_os": WIN}),
    ],
)
def test_classify_paths_selects_only_affected_areas(
    paths: list[str], expected: dict[str, object]
) -> None:
    selection = areas.classify_paths(paths)
    assert {key: selection[key] for key in expected} == expected


@pytest.mark.parametrize(
    "path",
    [".github/workflows/ci.yml", "scripts/ci_changed_areas.py", ".pre-commit-config.yaml"],
)
def test_changing_the_ci_wiring_selects_everything(path: str) -> None:
    selection = areas.classify_paths(["memory-bank/progress.md", path])
    assert all(selection[area] for area in areas.AREAS)
    assert selection["smoke_os"] == FULL


def _boom(*_args: str) -> list[str]:
    raise RuntimeError("compare API failed")


@pytest.mark.parametrize(
    ("kwargs", "reason_fragment"),
    [
        ({"event": "schedule"}, "event 'schedule'"),
        ({"event": "workflow_dispatch"}, "event 'workflow_dispatch'"),
        ({"base": "0" * 40}, "no usable base/head SHA"),
        ({"base": ""}, "no usable base/head SHA"),
        ({"token": ""}, "no token"),
        ({"fetcher": _boom}, "diff unavailable"),
        ({"fetcher": lambda *_args: []}, "empty diff"),
    ],
)
def test_decide_fails_open_to_the_full_matrix(kwargs: dict[str, Any], reason_fragment: str) -> None:
    params: dict[str, Any] = {
        "event": "push",
        "repo": "u9401066/med-paper-assistant",
        "base": "a" * 40,
        "head": "b" * 40,
        "token": "token",
        "fetcher": lambda *_args: ["memory-bank/progress.md"],
    }
    params.update(kwargs)
    selection = areas.decide(**params)
    assert all(selection[area] for area in areas.AREAS)
    assert selection["smoke_os"] == FULL
    assert reason_fragment in str(selection["reason"])


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _serve(monkeypatch: pytest.MonkeyPatch, files: list[dict[str, str]]) -> None:
    payload = json.dumps({"files": files}).encode("utf-8")
    monkeypatch.setattr(areas.urllib.request, "urlopen", lambda *_a, **_k: _FakeResponse(payload))


def test_compare_api_includes_rename_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """A file moved out of src/ must still gate the jobs that tested its old path."""
    _serve(
        monkeypatch,
        [{"filename": "memory-bank/x.md", "previous_filename": "src/med_paper_assistant/x.py"}],
    )
    paths = areas.fetch_changed_paths("o/r", "a", "b", "t")
    assert paths == ["memory-bank/x.md", "src/med_paper_assistant/x.py"]
    assert areas.classify_paths(paths)["python"] is True


def test_compare_api_truncation_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, [{"filename": f"memory-bank/{i}.md"} for i in range(300)])
    selection = areas.decide(event="push", repo="o/r", base="a" * 40, head="b" * 40, token="t")
    assert selection["python"] is True
    assert "truncated" in str(selection["reason"])


def test_cli_writes_github_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    changed = tmp_path / "changed.txt"
    changed.write_text("dashboard/package.json\n", encoding="utf-8")
    output = tmp_path / "github_output"
    assert areas.main(["--files-from", str(changed), "--github-output", str(output)]) == 0

    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[:6] == [
        "python=false",
        "vsx=false",
        "dashboard=true",
        "markdown=false",
        "sdk2=false",
        "smoke_os=[]",
    ]
    assert lines[6].startswith("reason=")
    assert capsys.readouterr().out.splitlines() == lines


def _vsx_input_paths() -> list[str]:
    manifest = json.loads(
        (REPO_ROOT / "vscode-extension" / "bundle-manifest.json").read_text(encoding="utf-8")
    )
    authority = json.loads((REPO_ROOT / "tool-surface-authority.json").read_text(encoding="utf-8"))
    paths = [f".claude/skills/{skill}/SKILL.md" for skill in manifest["skills"]]
    paths += [f".claude/skills/{skill}/references/x.md" for skill in manifest["skills"]]
    paths += [f".github/prompts/{prompt}.prompt.md" for prompt in manifest["prompts"]]
    paths += [f".github/agents/{agent}.agent.md" for agent in manifest["agents"]]
    paths += [f"templates/{template}" for template in manifest["templates"]]
    paths += [entry["source"] for entry in manifest["supportFiles"]]
    paths += [f"{entry['source']}/__init__.py" for entry in manifest["pythonSources"]]
    paths += list(authority["docs"])
    paths += [
        "tool-surface-authority.json",
        "mcp-integration-lock.json",
        ".github/workflows/release.yml",
    ]
    return paths


def test_every_vsix_build_input_triggers_the_vsx_job() -> None:
    missed = [path for path in _vsx_input_paths() if not areas.classify_paths([path])["vsx"]]
    assert missed == []


def test_every_cross_platform_smoke_test_file_triggers_the_full_matrix() -> None:
    smoke_job = _ci_jobs()["cross-platform-smoke"]
    commands = " ".join(str(step.get("run", "")) for step in smoke_job["steps"])
    test_files = set(re.findall(r"tests/[\w/]+\.py", commands))
    assert test_files
    partial = [
        path for path in sorted(test_files) if areas.classify_paths([path])["smoke_os"] != FULL
    ]
    assert partial == []


def test_ci_jobs_are_gated_fail_open_on_classifier_outputs() -> None:
    jobs = _ci_jobs()
    changes = jobs["changes"]
    assert set(changes["outputs"]) == {*areas.AREAS, "smoke_os"}
    # The classifier must run on the runner's stock Python: no dependency install.
    assert all("uses" not in step or "checkout" in step["uses"] for step in changes["steps"])

    for job_id, (name, area) in REQUIRED_CHECKS.items():
        job = jobs[job_id]
        assert job["name"] == name, "branch protection matches required checks by name"
        assert "strategy" not in job, f"{job_id}: a matrix would rename the required check"
        assert job["needs"] == "changes"
        assert job["if"] == f"${{{{ !cancelled() && needs.changes.outputs.{area} != 'false' }}}}"

    smoke = jobs["cross-platform-smoke"]
    assert smoke["if"] == "${{ !cancelled() && needs.changes.outputs.smoke_os != '[]' }}"
    fallback = re.search(r"\|\| '(\[.*\])'", smoke["strategy"]["matrix"]["os"])
    assert fallback and json.loads(fallback.group(1)) == FULL

    sdk2 = jobs["external-mcp-sdk2-smoke"]
    assert sdk2["if"] == "${{ !cancelled() && needs.changes.outputs.sdk2 != 'false' }}"


def test_ci_keeps_a_scheduled_full_run() -> None:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow[True]  # PyYAML 1.1 parses the bare `on:` key as boolean True
    assert triggers["schedule"] and "workflow_dispatch" in triggers
    assert "schedule" not in areas.DIFF_EVENTS
