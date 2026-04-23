"""Tests for ProjectManager — contract tests for get_project_info() return dict.

These tests exist because BUG-001 (dogfooding 2026-02-23) showed that
get_project_info() was missing `project_path`, causing 15 MCP tool call-sites
to silently fall back to relative paths and fail.
"""

import json
from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager


@pytest.fixture
def pm(tmp_path):
    """Create a ProjectManager with a temporary base directory."""
    manager = ProjectManager(base_path=str(tmp_path))
    return manager


@pytest.fixture
def pm_with_project(pm):
    """ProjectManager with one project created and set as current."""
    pm.create_project(
        name="Test Project",
        description="A test project",
        paper_type="original-research",
    )
    return pm


def test_project_manager_rejects_unsafe_slug_inputs(pm):
    pm.create_project(
        name="Safe Project",
        description="A test project",
        paper_type="original-research",
    )

    assert pm.switch_project("../escape")["success"] is False
    assert pm.delete_project("../escape", confirm=True)["success"] is False
    assert pm.get_project_info("../escape")["success"] is False


class TestGetProjectInfoContract:
    """Contract tests: ensure get_project_info() returns all keys MCP tools rely on."""

    REQUIRED_KEYS = {"success", "slug", "project_path", "paths", "stats"}

    def test_returns_all_required_keys(self, pm_with_project):
        info = pm_with_project.get_project_info()
        missing = self.REQUIRED_KEYS - set(info.keys())
        assert not missing, f"get_project_info() missing keys: {missing}"

    def test_project_path_is_absolute_string(self, pm_with_project):
        info = pm_with_project.get_project_info()
        pp = info["project_path"]
        assert isinstance(pp, str)
        assert len(pp) > 0
        # Should be absolute (platform-agnostic check)
        from pathlib import Path

        assert Path(pp).is_absolute(), f"project_path should be absolute, got: {pp}"

    def test_project_path_matches_paths_root(self, pm_with_project):
        info = pm_with_project.get_project_info()
        assert info["project_path"] == info["paths"]["root"]

    def test_project_path_directory_exists(self, pm_with_project):
        import os

        info = pm_with_project.get_project_info()
        assert os.path.isdir(info["project_path"])

    def test_paths_dict_has_all_subdirectories(self, pm_with_project):
        info = pm_with_project.get_project_info()
        expected_path_keys = {
            "root",
            "concept",
            "memory",
            "drafts",
            "references",
            "data",
            "results",
            "config",
        }
        actual = set(info["paths"].keys())
        missing = expected_path_keys - actual
        assert not missing, f"paths dict missing: {missing}"

    def test_drafts_path_joinable(self, pm_with_project):
        """MCP tools do os.path.join(project_path, 'drafts') — must work."""
        import os

        info = pm_with_project.get_project_info()
        drafts_via_join = os.path.join(str(info["project_path"]), "drafts")
        drafts_via_paths = info["paths"]["drafts"]
        assert os.path.normpath(drafts_via_join) == os.path.normpath(drafts_via_paths)

    def test_no_current_project_returns_error(self, pm):
        """When no project is selected, should return error dict."""
        info = pm.get_project_info()
        assert info.get("success") is False
        assert "error" in info

    def test_nonexistent_slug_returns_error(self, pm_with_project):
        info = pm_with_project.get_project_info(slug="nonexistent")
        assert info.get("success") is False

    def test_explicit_slug_returns_project_path(self, pm_with_project):
        slug = pm_with_project.get_current_project()
        info = pm_with_project.get_project_info(slug=slug)
        assert "project_path" in info
        assert info["project_path"].endswith(slug)


class TestGetProjectPaths:
    """Ensure get_project_paths() is consistent with get_project_info()."""

    def test_paths_are_absolute(self, pm_with_project):
        from pathlib import Path

        paths = pm_with_project.get_project_paths()
        for key, path_str in paths.items():
            assert Path(path_str).is_absolute(), f"paths['{key}'] not absolute: {path_str}"

    def test_paths_match_info_paths(self, pm_with_project):
        info = pm_with_project.get_project_info()
        paths = pm_with_project.get_project_paths()
        assert info["paths"] == paths


class TestCreateProject:
    """Ensure create_project sets up directory structure correctly."""

    def test_creates_all_directories(self, pm):
        pm.create_project(name="New", paper_type="review-article")
        info = pm.get_project_info()
        import os

        for key in ["drafts", "references", "data", "results", "memory"]:
            assert os.path.isdir(info["paths"][key]), f"Missing directory: {key}"

    def test_creates_concept_template(self, pm):
        pm.create_project(name="New", paper_type="review-article")
        info = pm.get_project_info()
        import os

        assert os.path.isfile(info["paths"]["concept"]), "concept.md not created"

    def test_sets_current_project(self, pm):
        pm.create_project(name="New")
        assert pm.get_current_project() == "new"

    def test_creates_project_json(self, pm):
        pm.create_project(name="New", paper_type="review-article")
        info = pm.get_project_info()
        config_path = info["paths"]["config"]
        with open(config_path) as f:
            config = json.load(f)
        assert config["name"] == "New"
        assert config["paper_type"] == "review-article"

    def test_persists_workflow_mode_and_library_templates(self, pm):
        pm.create_project(name="Library", workflow_mode="library-wiki")

        info = pm.get_project_info()
        assert info["workflow_mode"] == "library-wiki"
        assert "inbox" in info["paths"]
        assert "concepts" in info["paths"]
        assert "projects" in info["paths"]
        assert "drafts" not in info["paths"]

        config_path = info["paths"]["config"]
        with open(config_path) as f:
            config = json.load(f)

        assert config["workflow_mode"] == "library-wiki"
        assert config["workflow_mode_info"]["name"] == "Library Wiki Path"

        concept = open(info["paths"]["concept"], encoding="utf-8").read()
        progress = open(info["paths"]["memory"] + "/progress.md", encoding="utf-8").read()

        assert "# Library Workspace" in concept
        assert "Workflow Mode:** Library Wiki Path" in progress

    def test_updates_workflow_mode(self, pm):
        pm.create_project(name="Switchable")

        result = pm.update_project_settings(workflow_mode="library-wiki")

        assert result["success"] is True
        assert "workflow_mode" in result["updated_fields"]
        info = pm.get_project_info()
        assert info["workflow_mode"] == "library-wiki"
        assert Path(info["paths"]["inbox"]).is_dir()
        assert Path(info["paths"]["concepts"]).is_dir()
        assert Path(info["paths"]["projects"]).is_dir()

    def test_convert_exploration_to_library_project_reports_library_stats(self, pm):
        pm.get_or_create_temp_project()

        result = pm.convert_temp_to_project(
            name="Library Converted",
            workflow_mode="library-wiki",
        )

        assert result["success"] is True
        assert result["workflow_mode"] == "library-wiki"
        assert "Inbox notes" in result["message"]
        assert "Concept notes" in result["message"]
        assert "Synthesis projects" in result["message"]
        assert result["stats"]["references"] == 0
        assert result["stats"]["inbox"] == 0
        assert result["stats"]["concepts"] == 0
        assert result["stats"]["projects"] == 0

    def test_convert_exploration_to_manuscript_project_creates_required_dirs(self, pm):
        pm.get_or_create_temp_project()

        result = pm.convert_temp_to_project(
            name="Paper Converted",
            workflow_mode="manuscript",
            paper_type="original-research",
        )

        assert result["success"] is True
        assert result["workflow_mode"] == "manuscript"
        assert "Drafts" in result["message"]
        assert "Data files" in result["message"]
        assert Path(result["paths"]["drafts"]).is_dir()
        assert Path(result["paths"]["data"]).is_dir()
        assert Path(result["paths"]["results"]).is_dir()
        assert result["stats"]["drafts"] == 0
        assert result["stats"]["data_files"] == 0

    def test_create_project_deduplicates_duplicate_names(self, pm):
        first = pm.create_project(name="Repeated Name")
        second = pm.create_project(name="Repeated Name")

        assert first["success"] is True
        assert first["slug"] == "repeated-name"
        assert second["success"] is True
        assert second["slug"] == "repeated-name-1"


class TestAuthorManagement:
    """Tests for structured author info in project config."""

    def test_create_project_with_structured_authors(self, pm):
        authors = [
            {
                "name": "Jane Doe",
                "affiliations": ["Dept A, University X"],
                "orcid": "0000-0001-0000-0001",
                "email": "jane@example.com",
                "is_corresponding": True,
            }
        ]
        pm.create_project(name="Author Test", authors=authors)
        info = pm.get_project_info()
        stored = info["authors"]
        assert len(stored) == 1
        assert stored[0]["name"] == "Jane Doe"
        assert stored[0]["affiliations"] == ["Dept A, University X"]
        assert stored[0]["is_corresponding"] is True
        assert stored[0]["order"] == 1  # auto-assigned

    def test_create_project_with_legacy_string_authors(self, pm):
        pm.create_project(name="Legacy Test", authors=["Alice", "Bob"])
        info = pm.get_project_info()
        stored = info["authors"]
        assert len(stored) == 2
        assert stored[0]["name"] == "Alice"
        assert stored[0]["order"] == 1
        assert stored[1]["name"] == "Bob"
        assert stored[1]["order"] == 2

    def test_create_project_no_authors(self, pm):
        pm.create_project(name="No Authors")
        info = pm.get_project_info()
        assert info["authors"] == []

    def test_update_authors(self, pm):
        pm.create_project(name="Update Test")
        result = pm.update_authors(
            [
                {
                    "name": "Author One",
                    "affiliations": ["Uni A"],
                    "is_corresponding": True,
                    "order": 1,
                },
                {"name": "Author Two", "affiliations": ["Uni B"], "order": 2},
            ]
        )
        assert result["success"] is True
        assert len(result["authors"]) == 2

        # Verify persistence
        info = pm.get_project_info()
        assert info["authors"][0]["name"] == "Author One"
        assert info["authors"][1]["name"] == "Author Two"

    def test_update_authors_no_project(self, pm):
        result = pm.update_authors([{"name": "Test"}])
        assert result["success"] is False

    def test_normalize_mixed_authors(self, pm):
        """Mix of string and dict entries should all normalize."""
        pm.create_project(
            name="Mixed",
            authors=["Plain Name", {"name": "Dict Name", "orcid": "0000-0002-0000-0002"}],
        )
        info = pm.get_project_info()
        stored = info["authors"]
        assert stored[0]["name"] == "Plain Name"
        assert stored[0]["orcid"] == ""
        assert stored[1]["name"] == "Dict Name"
        assert stored[1]["orcid"] == "0000-0002-0000-0002"


# ─────────────────────────────────────────────────────────────────────────────
# Singleton + MEDPAPER_BASE_DIR fix (stale-project-state bug)
# ─────────────────────────────────────────────────────────────────────────────
class TestGetProjectManagerSingleton:
    """Verify singleton respects MEDPAPER_BASE_DIR and avoids dual-instance bug."""

    def test_default_reads_medpaper_base_dir(self, tmp_path, monkeypatch):
        """get_project_manager() with no args should use MEDPAPER_BASE_DIR, not CWD."""
        from med_paper_assistant.infrastructure.persistence.project_manager import (
            _reset_project_manager,
            get_project_manager,
        )

        _reset_project_manager()
        monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
        # CWD is different from tmp_path
        monkeypatch.chdir("/tmp")  # noqa: S108

        pm = get_project_manager()
        assert pm.base_path == tmp_path
        assert pm.state_file == tmp_path / ".current_project"

        _reset_project_manager()

    def test_singleton_returns_same_instance(self, tmp_path, monkeypatch):
        """Repeated calls return the same object."""
        from med_paper_assistant.infrastructure.persistence.project_manager import (
            _reset_project_manager,
            get_project_manager,
        )

        _reset_project_manager()
        monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))

        pm1 = get_project_manager()
        pm2 = get_project_manager()
        assert pm1 is pm2

        _reset_project_manager()

    def test_switch_project_visible_to_helpers(self, tmp_path, monkeypatch):
        """After switch_project via singleton, helpers see the new project.

        This is the exact scenario that was broken: create_server() used a
        local ProjectManager() while get_drafts_dir() used the singleton,
        so switch_project wrote .current_project to a different location.
        """
        from med_paper_assistant.infrastructure.persistence.project_manager import (
            _reset_project_manager,
            get_project_manager,
        )

        _reset_project_manager()
        monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))

        pm = get_project_manager()

        # Create two projects
        pm.create_project(name="Project A", paper_type="original-research")
        pm.create_project(name="Project B", paper_type="case-report")

        assert pm.get_current_project() == "project-b"

        # Switch back to A
        pm.switch_project("project-a")
        assert pm.get_current_project() == "project-a"

        # A second get_project_manager() call returns the SAME instance
        pm2 = get_project_manager()
        assert pm2.get_current_project() == "project-a"
        info = pm2.get_project_info()
        assert info["slug"] == "project-a"

        _reset_project_manager()
