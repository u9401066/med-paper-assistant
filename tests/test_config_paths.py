"""Cross-platform path default tests for AppConfig and TemplateReader."""

import tomllib
from pathlib import Path

from med_paper_assistant.infrastructure.config import AppConfig, get_project_root
from med_paper_assistant.infrastructure.services.template_reader import TemplateReader


def test_app_config_defaults_to_repo_root(monkeypatch):
    monkeypatch.delenv("MEDPAPER_BASE_DIR", raising=False)
    monkeypatch.delenv("MEDPAPER_PROJECTS_DIR", raising=False)
    monkeypatch.delenv("MEDPAPER_TEMPLATES_DIR", raising=False)

    config = AppConfig.from_env()
    project_root = get_project_root().resolve()

    assert config.base_dir == project_root
    assert config.projects_dir == project_root / "projects"
    assert config.templates_dir == project_root / "templates"


def test_template_reader_defaults_to_repo_templates_dir():
    reader = TemplateReader()
    expected = get_project_root().resolve() / "templates"
    assert reader.templates_dir == expected


def test_template_reader_accepts_explicit_directory(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    reader = TemplateReader(str(templates_dir))

    assert reader.templates_dir == templates_dir


def test_root_ruff_excludes_external_integration_submodules():
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()
    )

    excluded = pyproject["tool"]["ruff"]["extend-exclude"]

    assert "integrations" in excluded


def test_agent_harness_uses_existing_vscode_test_script():
    repo_root = Path(__file__).resolve().parent.parent
    harness_paths = [
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
    ]

    stale_paths = [
        path for path in harness_paths if "npm run test:ci" in (repo_root / path).read_text()
    ]

    assert stale_paths == []


def test_agent_harness_uses_latest_pubmed_and_bundle_docs():
    repo_root = Path(__file__).resolve().parent.parent
    scanned_roots = [
        repo_root / "src" / "med_paper_assistant",
        repo_root / ".claude" / "skills",
        repo_root / ".github" / "prompts",
        repo_root / ".github" / "agents",
        repo_root / "vscode-extension" / "bundled" / "tool" / "med_paper_assistant",
        repo_root / "vscode-extension" / "skills",
        repo_root / "vscode-extension" / "prompts",
        repo_root / "vscode-extension" / "agents",
    ]
    scanned_files = [
        repo_root / "README.md",
        repo_root / "README.zh-TW.md",
        repo_root / "vscode-extension" / "README.md",
    ]
    text_suffixes = {".py", ".md", ".txt", ".json", ".yaml", ".yml"}
    for root in scanned_roots:
        scanned_files.extend(
            path for path in root.rglob("*") if path.is_file() and path.suffix in text_suffixes
        )

    stale_markers = [
        "search_literature",
        "list_search_history",
        "merge_search_results",
        "generate_queries()",
        "37 search tools",
        "37 個搜尋工具",
        "medpaper-assistant-0.6.3.vsix",
    ]

    stale_locations = {
        str(path.relative_to(repo_root)): marker
        for path in scanned_files
        for marker in stale_markers
        if marker in path.read_text(encoding="utf-8")
    }

    assert stale_locations == {}


def test_pipeline_phase_docs_match_gate_heartbeat():
    repo_root = Path(__file__).resolve().parent.parent
    docs_to_scan = [
        "README.md",
        "README.zh-TW.md",
        "docs/auto-paper-guide.md",
        "docs/design/multi-stage-review-architecture.md",
        "docs/assets/medpaper-intro.svg",
        "vscode-extension/resources/marketplace-banner.svg",
        ".claude/skills/auto-paper/SKILL.md",
        ".github/prompts/mdpaper.write-paper.prompt.md",
        "scripts/hooks/copilot/prompt-analyzer.sh",
        "scripts/sync_repo_counts.py",
        "src/med_paper_assistant/infrastructure/persistence/checkpoint_manager.py",
        "src/med_paper_assistant/infrastructure/persistence/pipeline_gate_validator.py",
        "src/med_paper_assistant/interfaces/mcp/tools/review/pipeline_gate.py",
        "tests/test_integration_pipeline.py",
        "vscode-extension/README.md",
        "vscode-extension/package.json",
    ]
    stale_markers = [
        "11-Phase",
        "11 階段",
        "Phase 0-10",
        "0-10（全流程）",
        "9 phases, fully",
        "Pipeline phases (11",
    ]

    stale_locations = {
        relative_path: marker
        for relative_path in docs_to_scan
        for marker in stale_markers
        if marker in (repo_root / relative_path).read_text(encoding="utf-8")
    }

    assert stale_locations == {}

    auto_paper_guide = (repo_root / "docs/auto-paper-guide.md").read_text(encoding="utf-8")
    assert "13 Main Gate Checkpoints" in auto_paper_guide
    assert "Phase 2.1: Fulltext & Source-Material Ingestion" in auto_paper_guide
    assert "Phase 6.5: Evolution Gate" in auto_paper_guide
    assert "Phase 11: Final Delivery" in auto_paper_guide
