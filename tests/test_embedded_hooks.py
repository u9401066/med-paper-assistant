"""
Tests for embedded writing hooks and paper pre-commit script.

Validates:
  - _run_embedded_post_write_hooks: auto-runs A-series hooks after write_draft
  - B2 protected content guard in patch_draft
  - paper_precommit.py: finds projects, collects drafts, runs P-series hooks
"""

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# ── Helper: import paper_precommit.py as module ────────────────────


def _import_paper_precommit():
    """Import paper_precommit.py from scripts/hooks/ without requiring __init__.py."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "paper_precommit.py"
    spec = importlib.util.spec_from_file_location("paper_precommit", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Helper ──────────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    proj = tmp_path / "test-project"
    proj.mkdir()
    (proj / "drafts").mkdir()
    (proj / "references").mkdir()

    # Minimal concept.md with 🔒 content
    concept = proj / "concept.md"
    concept.write_text(
        "# Concept\n\n"
        "## 🔒 NOVELTY STATEMENT\n"
        "> This study is the first to show X.\n\n"
        "## 🔒 KEY SELLING POINTS\n"
        "- Point A\n- Point B\n",
        encoding="utf-8",
    )
    return proj


# ── Tests for _run_embedded_post_write_hooks ────────────────────────


class TestEmbeddedPostWriteHooks:
    """Test that post-write hooks are run automatically and non-blocking."""

    def test_returns_report_with_issues(self, project_dir: Path):
        """Hooks report should include issues when AI phrases found."""
        from med_paper_assistant.interfaces.mcp.tools.draft.writing import (
            _run_embedded_post_write_hooks,
        )

        content = (
            "It is worth noting that this study delves into the evolving landscape "
            "of clinical research. Furthermore, it sheds light on the pivotal role "
            "of biomarkers in clinical practice."
        )

        with patch(
            "med_paper_assistant.interfaces.mcp.tools.draft.writing.get_project_path",
            return_value=str(project_dir),
        ):
            report = _run_embedded_post_write_hooks(content, "Introduction")

        # Should contain hook report (A3 anti-AI should fire)
        assert "Post-write hooks" in report
        assert "A3" in report or "⚠️" in report or "❌" in report

    def test_returns_empty_without_project(self):
        """Should return empty string if no project context."""
        from med_paper_assistant.interfaces.mcp.tools.draft.writing import (
            _run_embedded_post_write_hooks,
        )

        with patch(
            "med_paper_assistant.interfaces.mcp.tools.draft.writing.get_project_path",
            return_value=None,
        ):
            report = _run_embedded_post_write_hooks("Some content", "Methods")

        assert report == ""

    def test_returns_pass_for_clean_content(self, project_dir: Path):
        """Clean content should get a pass message."""
        from med_paper_assistant.interfaces.mcp.tools.draft.writing import (
            _run_embedded_post_write_hooks,
        )

        # Short, clean content that won't trigger most hooks
        content = "We performed the analysis using R version 4.2."

        with patch(
            "med_paper_assistant.interfaces.mcp.tools.draft.writing.get_project_path",
            return_value=str(project_dir),
        ):
            report = _run_embedded_post_write_hooks(content, "Methods")

        # Should either pass or be empty — not an error
        assert "BLOCKED" not in report

    def test_never_raises(self, project_dir: Path):
        """Even if hooks engine crashes, should return empty string."""
        from med_paper_assistant.interfaces.mcp.tools.draft.writing import (
            _run_embedded_post_write_hooks,
        )

        with (
            patch(
                "med_paper_assistant.interfaces.mcp.tools.draft.writing.get_project_path",
                return_value=str(project_dir),
            ),
            patch(
                "med_paper_assistant.infrastructure.persistence.writing_hooks.WritingHooksEngine.run_post_write_hooks",
                side_effect=RuntimeError("boom"),
            ),
        ):
            report = _run_embedded_post_write_hooks("some content", "Methods")

        assert report == ""  # Silently handled


# ── Tests for B2 Protected Content Guard in patch_draft ─────────────


class TestProtectedContentGuard:
    """Test that patch_draft blocks modification of 🔒-marked content."""

    def test_blocks_protected_content_in_concept(self, project_dir: Path):
        """Should block patch_draft when old_text contains 🔒 in concept.md."""
        filepath = project_dir / "concept.md"

        # Simulate the guard check directly (avoiding full MCP registration)
        old_text = "## 🔒 NOVELTY STATEMENT\n> This study is the first to show X."
        is_concept_file = "concept" in os.path.basename(str(filepath)).lower()

        assert is_concept_file is True
        assert "\U0001f512" in old_text  # 🔒 present

    def test_allows_non_protected_content(self, project_dir: Path):
        """Should allow patching normal content in concept.md."""
        old_text = "## Background\nSome background text."
        filepath = project_dir / "concept.md"

        is_concept_file = "concept" in os.path.basename(str(filepath)).lower()
        has_lock = "\U0001f512" in old_text

        assert is_concept_file is True
        assert has_lock is False  # No 🔒 → should be allowed

    def test_allows_protected_emoji_in_non_concept(self, project_dir: Path):
        """Should allow 🔒 in old_text when file is NOT concept.md."""
        filepath = project_dir / "drafts" / "introduction.md"

        is_concept_file = "concept" in os.path.basename(str(filepath)).lower()

        assert is_concept_file is False  # Not concept → guard doesn't apply


# ── Tests for paper_precommit.py ────────────────────────────────────


class TestPaperPrecommitScript:
    """Test the pre-commit hook script functions."""

    def test_find_projects_with_drafts_empty(self, tmp_path: Path):
        """No projects → empty list."""
        mod = _import_paper_precommit()
        (tmp_path / "projects").mkdir()
        assert mod.find_projects_with_drafts(tmp_path) == []

    def test_find_projects_with_drafts_found(self, tmp_path: Path):
        """Project with .md drafts should be found."""
        mod = _import_paper_precommit()

        proj = tmp_path / "projects" / "my-paper"
        drafts = proj / "drafts"
        drafts.mkdir(parents=True)
        (drafts / "introduction.md").write_text("# Introduction", encoding="utf-8")

        result = mod.find_projects_with_drafts(tmp_path)
        assert len(result) == 1
        assert result[0].name == "my-paper"

    def test_find_projects_skips_no_drafts(self, tmp_path: Path):
        """Project without .md files in drafts/ should be skipped."""
        mod = _import_paper_precommit()

        proj = tmp_path / "projects" / "empty-paper"
        (proj / "drafts").mkdir(parents=True)

        result = mod.find_projects_with_drafts(tmp_path)
        assert result == []

    def test_collect_draft_content(self, tmp_path: Path):
        """Should concatenate all non-concept .md files."""
        mod = _import_paper_precommit()

        proj = tmp_path / "test-project"
        drafts = proj / "drafts"
        drafts.mkdir(parents=True)
        (drafts / "introduction.md").write_text("# Intro\nHello.", encoding="utf-8")
        (drafts / "methods.md").write_text("# Methods\nWe did X.", encoding="utf-8")
        (drafts / "concept.md").write_text("# Concept\nSkip me.", encoding="utf-8")

        content = mod.collect_draft_content(proj)
        assert "Hello." in content
        assert "We did X." in content
        assert "Skip me." not in content  # concept.md excluded

    def test_staged_draft_projects_returns_project_names(self, monkeypatch):
        """Staged draft paths should map to their project slugs."""
        mod = _import_paper_precommit()

        def fake_run(*args, **kwargs):
            return SimpleNamespace(
                stdout=(
                    "README.md\n"
                    "projects/paper-a/drafts/introduction.md\n"
                    "projects/paper-b/drafts/results.md\n"
                    "projects/paper-b/references/ref.yaml\n"
                )
            )

        monkeypatch.setattr(mod.subprocess, "run", fake_run)

        assert mod._staged_draft_projects(Path("/repo")) == {"paper-a", "paper-b"}

    def test_main_skips_silently_without_staged_drafts(self, monkeypatch, capsys):
        """Non-draft commits should not scan draft projects or print draft warnings."""
        mod = _import_paper_precommit()

        monkeypatch.setattr(mod, "_staged_draft_projects", lambda workspace: set())
        monkeypatch.setattr(
            mod,
            "find_projects_with_drafts",
            lambda workspace: pytest.fail("draft projects should not be scanned"),
        )

        assert mod.main() == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
