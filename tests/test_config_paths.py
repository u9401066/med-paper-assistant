"""Cross-platform path default tests for AppConfig and TemplateReader."""

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
