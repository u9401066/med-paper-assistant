from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_project_management_guidance_prefers_facade_verbs() -> None:
    expected = 'project_action(action="list")'
    forbidden = "list_projects()"

    for relative_path in [
        ".claude/skills/project-management/SKILL.md",
        "vscode-extension/skills/project-management/SKILL.md",
        ".github/prompts/mdpaper.project.prompt.md",
        "vscode-extension/prompts/mdpaper.project.prompt.md",
    ]:
        content = _read(relative_path)
        assert expected in content
        assert forbidden not in content


def test_export_guidance_prefers_facade_verbs() -> None:
    skill_paths = [
        ".claude/skills/word-export/SKILL.md",
        "vscode-extension/skills/word-export/SKILL.md",
    ]
    prompt_paths = [
        ".github/prompts/mdpaper.format.prompt.md",
        "vscode-extension/prompts/mdpaper.format.prompt.md",
    ]

    for relative_path in skill_paths:
        content = _read(relative_path)
        assert 'inspect_export(action="list_templates")' in content
        assert 'export_document(action="session_start"' in content

    for relative_path in prompt_paths:
        content = _read(relative_path)
        assert 'inspect_export(action="list_templates")' in content
        assert 'export_document(action="session_start"' in content
        assert "start_document_session" not in content


def test_auto_paper_guidance_prefers_review_and_workspace_facades() -> None:
    required_fragments = [
        'pipeline_action(action="validate_phase"',
        'run_quality_checks(action="writing_hooks"',
        'workspace_state_action(action="checkpoint"',
        'export_document(action="docx")',
    ]
    forbidden_fragments = [
        "validate_phase_gate(",
        "run_writing_hooks(",
        "checkpoint_writing_context(",
        "submit_review_round(",
    ]

    for relative_path in [
        ".claude/skills/auto-paper/SKILL.md",
        "vscode-extension/skills/auto-paper/SKILL.md",
    ]:
        content = _read(relative_path)
        for fragment in required_fragments:
            assert fragment in content
        for fragment in forbidden_fragments:
            assert fragment not in content


def test_agent_guidance_prefers_project_facade_for_context() -> None:
    for relative_path in [
        ".github/agents/domain-reviewer.agent.md",
        ".github/agents/literature-searcher.agent.md",
        ".github/agents/methodology-reviewer.agent.md",
        ".github/agents/review-orchestrator.agent.md",
        ".github/agents/statistics-reviewer.agent.md",
        "vscode-extension/agents/domain-reviewer.agent.md",
        "vscode-extension/agents/literature-searcher.agent.md",
        "vscode-extension/agents/methodology-reviewer.agent.md",
        "vscode-extension/agents/review-orchestrator.agent.md",
        "vscode-extension/agents/statistics-reviewer.agent.md",
    ]:
        content = _read(relative_path)
        assert 'project_action(action="current")' in content
        assert "get_current_project()" not in content


def test_bundled_instructions_prefer_project_and_export_facades() -> None:
    instruction_paths = [
        "src/med_paper_assistant/interfaces/mcp/instructions.py",
        "vscode-extension/bundled/tool/med_paper_assistant/interfaces/mcp/instructions.py",
    ]

    for relative_path in instruction_paths:
        content = _read(relative_path)
        assert 'project_action(action="current")' in content
        assert 'inspect_export(action="list_templates")' in content
        assert 'export_document(action="session_start")' in content
        assert "get_current_project()" not in content
