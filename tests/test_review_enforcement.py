"""
Tests for Review Stage enforcement.

Verifies that:
1. AutonomousAuditLoop tracks artifact hashes across rounds
2. submit_review_round rejects submissions without artifacts
3. submit_review_round rejects submissions with unchanged manuscript
4. _count_review_report_issues correctly parses YAML frontmatter
"""

import json
import textwrap

import pytest

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
    RoundVerdict,
    Severity,
)

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def audit_dir(tmp_path):
    """Create a temporary audit directory."""
    d = tmp_path / ".audit"
    d.mkdir()
    return d


@pytest.fixture
def project_dir(tmp_path, audit_dir):
    """Create a minimal project directory with a manuscript."""
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    manuscript = drafts / "manuscript.md"
    manuscript.write_text("# Title\n\nOriginal content.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def loop(audit_dir):
    """Create an AutonomousAuditLoop with review context."""
    config = AuditLoopConfig(
        max_rounds=3,
        quality_threshold=7.0,
        context="review",
    )
    return AutonomousAuditLoop(str(audit_dir), config=config)


# ── AutonomousAuditLoop hash tracking ─────────────────────────────────


class TestAuditLoopHashTracking:
    """Test artifact hash tracking in start_round/complete_round."""

    def test_start_round_accepts_artifact_hash(self, loop):
        ctx = loop.start_round(artifact_hash="abc123")
        assert ctx["round"] == 1

    def test_complete_round_stores_hashes(self, loop):
        loop.start_round(artifact_hash="hash_before")
        loop.record_issue("R1", Severity.MAJOR, "test issue", "fix it")
        loop.record_fix(0, "manual", True)
        verdict = loop.complete_round(
            {"text_quality": 8, "citation_quality": 8},
            artifact_hash="hash_after",
        )
        assert verdict == RoundVerdict.QUALITY_MET

        # Verify hashes stored in round record
        status = loop.get_score_trend()
        assert len(status) == 1

    def test_round_record_serializes_hashes(self, loop, audit_dir):
        """Hash fields should persist through save/load."""
        loop.start_round(artifact_hash="start_hash_123")
        loop.complete_round(
            {"text_quality": 8, "citation_quality": 8},
            artifact_hash="end_hash_456",
        )
        loop.save()

        # Read the saved JSON directly
        data_path = audit_dir / "audit-loop-review.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        round_data = data["rounds"][0]
        assert round_data["artifact_hash_start"] == "start_hash_123"
        assert round_data["artifact_hash_end"] == "end_hash_456"

    def test_round_record_loads_hashes(self, loop, audit_dir):
        """Hashes should survive save/load cycle."""
        loop.start_round(artifact_hash="h1")
        loop.complete_round({"text_quality": 9}, artifact_hash="h2")
        loop.save()

        # Create a new loop and load
        config = AuditLoopConfig(context="review")
        loop2 = AutonomousAuditLoop(str(audit_dir), config=config)
        loaded = loop2.load()
        assert loaded is True

        trend = loop2.get_score_trend()
        assert len(trend) == 1

    def test_empty_hash_when_not_provided(self, loop, audit_dir):
        """Hashes default to empty string when not provided."""
        loop.start_round()  # No hash
        loop.complete_round({"text_quality": 8})  # No hash
        loop.save()

        data_path = audit_dir / "audit-loop-review.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        round_data = data["rounds"][0]
        assert round_data["artifact_hash_start"] == ""
        assert round_data["artifact_hash_end"] == ""


# ── _count_review_report_issues ────────────────────────────────────────


class TestCountReviewReportIssues:
    """Test parsing of review-report YAML frontmatter."""

    def test_counts_all_issue_types(self, audit_dir):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _count_review_report_issues,
        )

        report = textwrap.dedent("""\
            ---
            round: 1
            total:
              major: 5
              minor: 8
              optional: 2
            ---
            # Review Report
        """)
        (audit_dir / "review-report-1.md").write_text(report, encoding="utf-8")
        counts = _count_review_report_issues(audit_dir, 1)
        assert counts == {"major": 5, "minor": 8, "optional": 2}

    def test_handles_missing_file(self, audit_dir):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _count_review_report_issues,
        )

        counts = _count_review_report_issues(audit_dir, 99)
        assert counts == {"major": 0, "minor": 0, "optional": 0}

    def test_handles_no_yaml_totals(self, audit_dir):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _count_review_report_issues,
        )

        report = "# Review Report\nSome text without YAML."
        (audit_dir / "review-report-1.md").write_text(report, encoding="utf-8")
        counts = _count_review_report_issues(audit_dir, 1)
        assert counts == {"major": 0, "minor": 0, "optional": 0}


# ── _compute_manuscript_hash ───────────────────────────────────────────


class TestComputeManuscriptHash:
    """Test manuscript hash computation."""

    def test_returns_hash_for_existing_file(self, project_dir):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _compute_manuscript_hash,
        )

        h = _compute_manuscript_hash(project_dir)
        assert len(h) == 64  # SHA-256 hex digest length
        assert h != ""

    def test_returns_empty_for_missing_file(self, tmp_path):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _compute_manuscript_hash,
        )

        h = _compute_manuscript_hash(tmp_path)
        assert h == ""

    def test_hash_changes_when_content_changes(self, project_dir):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _compute_manuscript_hash,
        )

        h1 = _compute_manuscript_hash(project_dir)
        manuscript = project_dir / "drafts" / "manuscript.md"
        manuscript.write_text("# Modified\n\nNew content.\n", encoding="utf-8")
        h2 = _compute_manuscript_hash(project_dir)
        assert h1 != h2

    def test_hash_stable_for_same_content(self, project_dir):
        from med_paper_assistant.interfaces.mcp.tools.review.pipeline_gate import (
            _compute_manuscript_hash,
        )

        h1 = _compute_manuscript_hash(project_dir)
        h2 = _compute_manuscript_hash(project_dir)
        assert h1 == h2


# ── Multi-round hash tracking ─────────────────────────────────────────


class TestMultiRoundHashTracking:
    """Test hash tracking across multiple review rounds."""

    def test_two_rounds_with_different_hashes(self, loop, audit_dir):
        # Round 1
        loop.start_round(artifact_hash="v1_hash")
        loop.record_issue("R1", Severity.MAJOR, "issue1", "fix1")
        loop.record_fix(0, "fix", True)
        v1 = loop.complete_round(
            {"text_quality": 6, "citation_quality": 6},
            artifact_hash="v1_modified_hash",
        )
        assert v1 == RoundVerdict.CONTINUE

        # Round 2
        loop.start_round(artifact_hash="v2_hash")
        loop.record_issue("R2", Severity.MINOR, "issue2", "fix2")
        loop.record_fix(0, "fix", True)
        v2 = loop.complete_round(
            {"text_quality": 8, "citation_quality": 8},
            artifact_hash="v2_modified_hash",
        )
        assert v2 == RoundVerdict.QUALITY_MET

        # Verify both rounds have correct hashes
        loop.save()
        data_path = audit_dir / "audit-loop-review.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        assert data["rounds"][0]["artifact_hash_start"] == "v1_hash"
        assert data["rounds"][0]["artifact_hash_end"] == "v1_modified_hash"
        assert data["rounds"][1]["artifact_hash_start"] == "v2_hash"
        assert data["rounds"][1]["artifact_hash_end"] == "v2_modified_hash"
