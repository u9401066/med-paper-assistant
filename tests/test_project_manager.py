"""Tests for ProjectManager — contract tests for get_project_info() return dict.

These tests exist because BUG-001 (dogfooding 2026-02-23) showed that
get_project_info() was missing `project_path`, causing 15 MCP tool call-sites
to silently fall back to relative paths and fail.
"""

import json

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
        expected_path_keys = {"root", "concept", "memory", "drafts", "references", "data", "results", "config"}
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
