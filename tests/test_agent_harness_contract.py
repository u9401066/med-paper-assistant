from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHARED_WORKFLOW = ROOT / "docs" / "harness" / "academic-writing-workflow.md"
SKILL_PATHS = [
    ROOT / ".agents" / "skills" / "academic-writing-harness" / "SKILL.md",
    ROOT / ".claude" / "skills" / "academic-writing-harness" / "SKILL.md",
]


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    assert match, f"missing YAML frontmatter: {path}"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


def test_cross_agent_skill_entrypoints_are_valid_and_aligned() -> None:
    metadata = [_frontmatter(path) for path in SKILL_PATHS]

    assert {item["name"] for item in metadata} == {"academic-writing-harness"}
    assert len({item["description"] for item in metadata}) == 1
    assert len(str(metadata[0]["description"])) <= 160
    for path in SKILL_PATHS:
        assert "docs/harness/academic-writing-workflow.md" in path.read_text(encoding="utf-8")


def test_all_repository_skills_have_valid_unique_frontmatter() -> None:
    skill_paths = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    names: dict[str, Path] = {}

    assert skill_paths
    for path in skill_paths:
        metadata = _frontmatter(path)
        name = metadata.get("name")
        description = metadata.get("description")
        assert isinstance(name, str) and name
        assert isinstance(description, str) and description
        assert name not in names, f"duplicate skill name {name}: {names.get(name)} and {path}"
        names[name] = path


def test_shared_workflow_covers_extended_outputs_and_exemplar_boundaries() -> None:
    content = SHARED_WORKFLOW.read_text(encoding="utf-8")

    for required in [
        "Research proposal / grant",
        "Project closeout report",
        "Student paper / short thesis",
        "arXiv preprint",
        "exemplar_structure",
        "exemplar_style",
        "Never copy or lightly paraphrase",
    ]:
        assert required in content


def test_always_loaded_claude_instructions_stay_compact() -> None:
    claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(claude_md.splitlines()) < 200
    assert ".copilot-mode.json" in claude_md
    assert "AGENTS.md" in claude_md


def test_workspace_mcp_configuration_has_no_user_home_paths() -> None:
    content = (ROOT / ".vscode" / "mcp.json").read_text(encoding="utf-8")
    assert "/home/" not in content
    assert "C:\\Users\\" not in content
