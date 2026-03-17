"""
Tests: Weak Model Guardrails — Code-Enforced Hooks Catch Common Mistakes.

Simulates mistakes a weak/less-capable model (e.g., Haiku) might make
and verifies that Code-Enforced hooks catch them automatically, without
relying on the Agent reading SKILL.md instructions.

Scenarios:
  1. Weak model overwrites 🔒 protected content → B2 catches it
  2. Weak model skips required submission documents → C2 catches it
  3. Weak model forgets to sync memory files → P6 warns about staleness
  4. Weak model uses deprecated save_reference() → deprecation warning emitted
  5. Batch runners include the newly Code-Enforced hooks (B2, C2, P6)
"""

import time
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    HookResult,
    WritingHooksEngine,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Minimal project directory with concept.md containing 🔒 blocks."""
    d = tmp_path / "weak-model-project"
    d.mkdir()
    (d / ".audit").mkdir()
    (d / "drafts").mkdir()
    return d


@pytest.fixture()
def engine(project_dir: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_dir)


@pytest.fixture()
def project_with_journal_profile(tmp_path: Path) -> Path:
    """Project with journal-profile.yaml that requires submission documents."""
    d = tmp_path / "journal-project"
    d.mkdir()
    (d / ".audit").mkdir()
    (d / "drafts").mkdir()
    profile = {
        "word_limits": {"total_manuscript": 5000},
        "paper": {
            "sections": [
                {"name": "Introduction", "word_limit": 800},
                {"name": "Methods", "word_limit": 1500},
            ],
        },
        "required_documents": {
            "cover_letter": True,
            "ethics_statement": True,
            "conflict_of_interest": True,
            "data_availability": True,
            "highlights": False,  # not required
        },
        "pipeline": {
            "tolerance": {"word_percent": 20},
        },
    }
    with open(d / "journal-profile.yaml", "w") as f:
        yaml.dump(profile, f)
    return d


@pytest.fixture()
def engine_with_profile(project_with_journal_profile: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_with_journal_profile)


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 1: Weak model overwrites 🔒 protected content
# ──────────────────────────────────────────────────────────────────────────────


class TestScenario1ProtectedContentOverwrite:
    """B2 should catch when a weak model empties 🔒-marked sections."""

    def test_b2_catches_empty_protected_block(self, project_dir: Path, engine: WritingHooksEngine):
        """Simulate: model replaces novelty statement with placeholder brackets."""
        concept = project_dir / "concept.md"
        concept.write_text(
            "# Research Concept\n\n"
            "## 🔒 NOVELTY STATEMENT\n\n"
            "[TODO: fill in novelty]\n\n"
            "## 🔒 KEY SELLING POINTS\n\n"
            "- [placeholder]\n"
            "- [another placeholder]\n\n"
            "## Background\n\nSome real background content here.\n",
            encoding="utf-8",
        )

        result = engine._run_b2_protected_content()

        assert not result.passed, "B2 should FAIL when 🔒 blocks have only placeholders"
        assert result.hook_id == "B2"
        assert len(result.issues) == 2, "Both 🔒 blocks are empty (placeholders stripped)"
        for issue in result.issues:
            assert issue.hook_id == "B2"
            assert issue.severity == "CRITICAL"

    def test_b2_passes_with_real_content(self, project_dir: Path, engine: WritingHooksEngine):
        """When 🔒 blocks have real content, B2 should pass."""
        concept = project_dir / "concept.md"
        concept.write_text(
            "# Research Concept\n\n"
            "## 🔒 NOVELTY STATEMENT\n\n"
            "This is the first study to demonstrate that remimazolam reduces "
            "ICU delirium incidence compared to propofol in elderly patients.\n\n"
            "## 🔒 KEY SELLING POINTS\n\n"
            "- Novel comparison in geriatric ICU population\n"
            "- Prospective randomized design\n\n"
            "## Background\n\nSome background.\n",
            encoding="utf-8",
        )

        result = engine._run_b2_protected_content()

        assert result.passed, "B2 should PASS when 🔒 blocks have real content"
        assert result.hook_id == "B2"
        # empty_blocks is a list of heading names
        assert len(result.stats["empty_blocks"]) == 0

    def test_b2_catches_partial_overwrite(self, project_dir: Path, engine: WritingHooksEngine):
        """Weak model empties one 🔒 block but leaves the other — B2 still fails."""
        concept = project_dir / "concept.md"
        concept.write_text(
            "# Research Concept\n\n"
            "## 🔒 NOVELTY STATEMENT\n\n"
            "This study is novel because of its unique geriatric focus.\n\n"
            "## 🔒 KEY SELLING POINTS\n\n"
            "[TODO]\n\n"
            "## Methods\n\nSome methods.\n",
            encoding="utf-8",
        )

        result = engine._run_b2_protected_content()

        assert not result.passed, "B2 should FAIL if any 🔒 block is empty"
        assert len(result.issues) == 1
        assert "KEY SELLING POINTS" in result.issues[0].message

    def test_b2_included_in_post_write_batch(self, project_dir: Path, engine: WritingHooksEngine):
        """B2 must be included in run_post_write_hooks() batch runner."""
        concept = project_dir / "concept.md"
        concept.write_text(
            "## 🔒 NOVELTY STATEMENT\n\n[empty]\n",
            encoding="utf-8",
        )

        results = engine.run_post_write_hooks(
            content="Some draft content for the introduction section.",
            section="Introduction",
        )

        assert "B2" in results, "B2 must be in post-write batch runner output"
        assert not results["B2"].passed, "B2 should detect empty protected block"

    def test_b2_no_concept_file_passes(self, project_dir: Path, engine: WritingHooksEngine):
        """If concept.md doesn't exist, B2 should pass (no file to check)."""
        result = engine._run_b2_protected_content()
        assert result.passed


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 2: Weak model skips required submission documents
# ──────────────────────────────────────────────────────────────────────────────


class TestScenario2SubmissionChecklist:
    """C2 should catch when required submission documents are missing."""

    def test_c2_catches_missing_required_docs(
        self,
        project_with_journal_profile: Path,
        engine_with_profile: WritingHooksEngine,
    ):
        """Manuscript has no ethics, COI, or data availability statements."""
        manuscript = (
            "# Introduction\n\nThis is a study about something.\n\n"
            "# Methods\n\nWe did the thing.\n\n"
            "# Results\n\nThe results showed stuff.\n\n"
            "# Discussion\n\nWe discussed the findings.\n"
        )

        result = engine_with_profile.check_submission_checklist(manuscript)

        assert not result.passed, "C2 should FAIL when required docs are missing"
        assert result.hook_id == "C2"
        # cover_letter, ethics_statement, conflict_of_interest, data_availability
        # = 4 required. None present in manuscript or as files.
        assert result.stats["missing_count"] >= 3, (
            f"At least 3 docs should be missing, got {result.stats['missing_count']}: "
            f"{result.stats['missing_docs']}"
        )

    def test_c2_passes_when_content_has_statements(
        self,
        project_with_journal_profile: Path,
        engine_with_profile: WritingHooksEngine,
    ):
        """Manuscript includes the required statements inline."""
        manuscript = (
            "# Introduction\n\nThis is a study.\n\n"
            "# Methods\n\nEthics approval was obtained from the Institutional Review Board. "
            "Informed consent was obtained from all participants.\n\n"
            "# Results\n\nResults here.\n\n"
            "# Discussion\n\nDiscussion here.\n\n"
            "## Conflict of Interest\n\nThe authors declare no competing interests.\n\n"
            "## Data Availability\n\nData are available upon reasonable request.\n\n"
        )
        # Also create cover letter file
        (project_with_journal_profile / "cover-letter.md").write_text(
            "Dear Editor,\n\nPlease consider...\n"
        )

        result = engine_with_profile.check_submission_checklist(manuscript)

        assert result.passed, (
            f"C2 should PASS when all docs are present. Missing: {result.stats.get('missing_docs')}"
        )

    def test_c2_included_in_post_manuscript_batch(
        self,
        engine_with_profile: WritingHooksEngine,
    ):
        """C2 must be in run_post_manuscript_hooks() batch runner."""
        manuscript = "# Introduction\n\nSome content.\n"

        results = engine_with_profile.run_post_manuscript_hooks(content=manuscript)

        assert "C2" in results, "C2 must be in post-manuscript batch runner output"

    def test_c2_skips_when_no_profile(self, engine: WritingHooksEngine):
        """Without journal-profile.yaml, C2 should pass (nothing to check)."""
        result = engine.check_submission_checklist("Some content")
        assert result.passed
        assert "skipping" in result.stats.get("note", "").lower()


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 3: Weak model forgets to sync memory
# ──────────────────────────────────────────────────────────────────────────────


class TestScenario3MemorySync:
    """P6 should warn when memory files are stale (>2 hours old)."""

    def test_p6_warns_stale_memory(self, project_dir: Path, engine: WritingHooksEngine):
        """Create memory files with old timestamps (>3 hours ago)."""
        memory_dir = project_dir / ".memory"
        memory_dir.mkdir()
        active_ctx = memory_dir / "activeContext.md"
        active_ctx.write_text("# Active Context\n\nSome old context.\n")

        # Set modification time to 4 hours ago
        four_hours_ago = time.time() - (4 * 3600)
        import os

        os.utime(active_ctx, (four_hours_ago, four_hours_ago))

        result = engine.check_memory_sync()

        assert not result.passed, "P6 should FAIL when memory files are stale"
        assert result.hook_id == "P6"
        assert len(result.issues) > 0
        assert result.issues[0].severity == "WARNING"
        assert "stale" in result.issues[0].message.lower()

    def test_p6_passes_fresh_memory(self, project_dir: Path, engine: WritingHooksEngine):
        """Memory files modified recently should pass."""
        memory_dir = project_dir / ".memory"
        memory_dir.mkdir()
        active_ctx = memory_dir / "activeContext.md"
        active_ctx.write_text("# Active Context\n\nJust updated.\n")
        # Default mtime is now (just created) → should be fresh

        result = engine.check_memory_sync()

        assert result.passed, "P6 should PASS when memory files are fresh"

    def test_p6_passes_no_memory_dir(self, project_dir: Path, engine: WritingHooksEngine):
        """If no memory directory exists, P6 should pass (nothing to check)."""
        result = engine.check_memory_sync()
        assert result.passed

    def test_p6_included_in_precommit_batch(self, project_dir: Path, engine: WritingHooksEngine):
        """P6 must be in run_precommit_hooks() batch runner."""
        results = engine.run_precommit_hooks(
            content="Some manuscript content for pre-commit.",
        )

        assert "P6" in results, "P6 must be in precommit batch runner output"


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 4: Weak model uses deprecated save_reference
# ──────────────────────────────────────────────────────────────────────────────


class TestScenario4DeprecatedSaveReference:
    """Verify the deprecation warning text is hard-coded in the tool."""

    def test_deprecation_warning_text_present_in_source(self):
        """The save_reference tool source must contain the deprecation warning."""
        import inspect

        from med_paper_assistant.interfaces.mcp.tools.reference import manager as ref_mgr_module

        source = inspect.getsource(ref_mgr_module)

        assert "DEPRECATION WARNING" in source, (
            "save_reference() must contain 'DEPRECATION WARNING' text"
        )
        assert "save_reference_mcp" in source, (
            "Deprecation message must recommend save_reference_mcp"
        )

    def test_save_reference_docstring_warns(self):
        """The save_reference function definition must say DEPRECATED."""
        import inspect

        from med_paper_assistant.interfaces.mcp.tools.reference import manager as ref_mgr_module

        source = inspect.getsource(ref_mgr_module)

        # The docstring of save_reference should start with DEPRECATED
        assert "DEPRECATED" in source
        assert "Use save_reference_mcp" in source

    def test_deprecation_warning_variable_is_complete(self):
        """The deprecation_warning string must mention both the old and new tools."""
        from med_paper_assistant.interfaces.mcp.tools.reference import manager as ref_mgr_module

        source_code = Path(ref_mgr_module.__file__).read_text(encoding="utf-8")

        # Must contain the full deprecation guidance
        assert "unverified metadata" in source_code
        assert "verified data from PubMed API" in source_code


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 5: Batch runner completeness
# ──────────────────────────────────────────────────────────────────────────────


class TestScenario5BatchRunnerCompleteness:
    """All 4 batch runners must include the newly Code-Enforced hooks."""

    def test_post_write_includes_b2(self, project_dir: Path, engine: WritingHooksEngine):
        """run_post_write_hooks() must return B2 key."""
        results = engine.run_post_write_hooks(
            content="A simple draft paragraph.",
            section="Introduction",
        )
        expected_hooks = {
            "A1",
            "A2",
            "A3",
            "A3b",
            "A3c",
            "A4",
            "A5",
            "A6",
            "A7",
            "B2",
            "B9",
            "B10",
            "B15",
        }
        actual_hooks = set(results.keys())
        assert expected_hooks.issubset(actual_hooks), (
            f"Missing hooks in post-write: {expected_hooks - actual_hooks}"
        )

    def test_post_manuscript_includes_c2(self, engine_with_profile: WritingHooksEngine):
        """run_post_manuscript_hooks() must return C2 key."""
        results = engine_with_profile.run_post_manuscript_hooks(
            content="# Introduction\n\nContent.\n",
        )
        expected_hooks = {
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7a",
            "C7b",
            "C7d",
            "C9",
            "C10",
            "C11",
            "C12",
            "C13",
            "F",
        }
        actual_hooks = set(results.keys())
        assert expected_hooks.issubset(actual_hooks), (
            f"Missing hooks in post-manuscript: {expected_hooks - actual_hooks}"
        )

    def test_precommit_includes_p6(self, project_dir: Path, engine: WritingHooksEngine):
        """run_precommit_hooks() must return P6 key."""
        results = engine.run_precommit_hooks(
            content="Manuscript pre-commit content.",
        )
        expected_hooks = {"P1", "P2", "P4", "P5", "P6", "P7"}
        actual_hooks = set(results.keys())
        assert expected_hooks.issubset(actual_hooks), (
            f"Missing hooks in precommit: {expected_hooks - actual_hooks}"
        )

    def test_post_section_returns_expected_hooks(self, engine: WritingHooksEngine):
        """run_post_section_hooks() returns B-series hooks."""
        results = engine.run_post_section_hooks(
            methods_content="We measured X using Y.",
            results_content="X was 5.0 (p=0.03).",
            full_content="# Methods\nWe measured X.\n# Results\nX was 5.0.\n",
        )
        assert "B8" in results, "B8 must be in post-section batch runner output"

    def test_all_batch_results_are_hook_results(
        self, project_dir: Path, engine: WritingHooksEngine
    ):
        """Every value returned by batch runners must be a HookResult instance."""
        post_write = engine.run_post_write_hooks(content="test", section="Introduction")
        precommit = engine.run_precommit_hooks(content="test")

        for hook_id, result in {**post_write, **precommit}.items():
            assert isinstance(result, HookResult), (
                f"Hook {hook_id} returned {type(result).__name__}, expected HookResult"
            )
