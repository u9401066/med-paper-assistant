"""
End-to-end pipeline lifecycle test — proves the WHOLE workflow runs smoothly.

Unlike test_pipeline_gate.py (which tests each phase gate in isolation) and
test_integration_pipeline.py (which tests components + a mini smoke flow),
this module walks the FULL 11-phase pipeline (0 → 11) sequentially the way the
agent actually drives it:

  For each phase:
    1. Assert the gate FAILS before the phase's artifacts exist.
    2. Build exactly that phase's artifacts (incrementally).
    3. Assert the gate PASSES once artifacts are present.

It also covers EDGE CASES that a real run can hit:
  - Skipping a phase (prerequisite enforcement blocks the next phase).
  - Corrupted JSON/YAML artifacts (validators must fail gracefully, not crash).
  - Out-of-order execution.
  - Regression mid-flow (Phase 7 → Phase 5) and recovery.
  - Invalid phase numbers.
  - Heartbeat completion percentage rising monotonically.

Phases: [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11]

These tests are pure filesystem + validator logic — no network, no MCP server
spawn — so they are fast and OOM-safe (no parallel workers required).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)

# Linear order the agent walks (matches _ALL_PHASES in pipeline_gate.py).
LIFECYCLE_PHASES = [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10]

# A case-report profile keeps the Phase 2 reference minimum at 8 (vs 20 for
# original-research), so the happy-path builder stays light.
PAPER_TYPE = "case-report"
MIN_REFS = 8


class PipelineProjectBuilder:
    """Incrementally builds a project's artifacts phase by phase.

    Each ``complete_phase_N`` method writes exactly the artifacts that phase N's
    gate validates, so a test can assert FAIL before calling it and PASS after.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.audit = root / ".audit"
        self.drafts = root / "drafts"
        self.refs = root / "references"
        self.memory = root / ".memory"
        self.exports = root / "exports"

    # ── Phase 0: Configuration ────────────────────────────────────
    def complete_phase_0(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        # v0.7.11 Phase 0 writes the source-material scan into .audit/, so the
        # audit dir must exist this early (before the Phase 1 dir scaffold).
        self.audit.mkdir(parents=True, exist_ok=True)
        (self.root / "journal-profile.yaml").write_text(
            yaml.dump({"paper": {"type": PAPER_TYPE}, "journal": {"name": "Test J"}}),
            encoding="utf-8",
        )
        # v0.7.11 Phase 0 gate also requires the source-material scan manifest.
        # An empty materials list = "no user DOCX/XLSX/PDF inputs to ingest".
        (self.audit / "source-materials.yaml").write_text(
            yaml.dump({"scanned_at": "2026-01-01T00:00:00", "materials": []}),
            encoding="utf-8",
        )

    # ── Phase 1: Project Setup ────────────────────────────────────
    def complete_phase_1(self) -> None:
        for d in ["drafts", "references", "data", "results", ".audit", ".memory", "exports"]:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        (self.root / "project.json").write_text(
            json.dumps({"slug": "e2e-project", "name": "E2E", "paper_type": PAPER_TYPE}),
            encoding="utf-8",
        )

    # ── Phase 2: Literature Search ────────────────────────────────
    def complete_phase_2(self) -> None:
        for i in range(MIN_REFS):
            ref_dir = self.refs / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "pmid": f"300000{i:02d}",
                        "title": f"Reference {i}",
                        "analysis_completed": True,
                        "fulltext_ingested": True,
                    }
                ),
                encoding="utf-8",
            )
        # Optional WARNING-level audit artifacts (do not block the gate).
        (self.audit / "search-strategy.md").write_text("# Search Strategy", encoding="utf-8")
        (self.audit / "reference-selection.md").write_text("# Selection", encoding="utf-8")
        # Phase 2.1 (in the heartbeat sweep) needs this status file; refs above
        # are already flagged analysis_completed + fulltext_ingested.
        (self.refs / "fulltext-ingestion-status.md").write_text(
            "# Fulltext Ingestion Status\nAll references ingested + analysed.",
            encoding="utf-8",
        )

    # ── Phase 3: Concept Development ──────────────────────────────
    def complete_phase_3(self) -> None:
        (self.root / "concept.md").write_text(
            "# Concept\n\n"
            "## 🔒 NOVELTY STATEMENT\nFirst study to evaluate X in setting Y.\n\n"
            "## 🔒 KEY SELLING POINTS\n- Point A\n- Point B\n",
            encoding="utf-8",
        )
        (self.audit / "concept-validation.md").write_text(
            "# Concept Validation\nValidated.", encoding="utf-8"
        )
        (self.audit / "concept-review.yaml").write_text(
            yaml.dump(
                {
                    "metadata": {"generated_at": "2026-01-01T00:00:00"},
                    "review": {"readiness": "ready"},
                    "research_question": {
                        "canonical_question": "Does X improve outcome Y in setting Z?"
                    },
                    "claims_required": [{"id": "claim-1", "text": "X improves Y."}],
                    "protected_content": {
                        "novelty_statement_locked": {"present": True},
                        "selling_points_locked": {"present": True},
                    },
                }
            ),
            encoding="utf-8",
        )

    # ── Phase 4: Manuscript Planning ──────────────────────────────
    def complete_phase_4(self) -> None:
        # A plan with NO required assets keeps Phase 5 focused on sections+approval.
        (self.root / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {"sections": ["Abstract", "Introduction", "Methods", "Results", "Discussion"]}
            ),
            encoding="utf-8",
        )

    # ── Phase 5: Section Writing ──────────────────────────────────
    def complete_phase_5(self) -> None:
        # Deliberately avoids "Figure N" / "Table N" / "p < 0.05" so the
        # data-artifact provenance sub-check does not trigger.
        (self.drafts / "manuscript.md").write_text(
            "# Manuscript\n\n"
            "## Abstract\nA concise structured summary of the work.\n\n"
            "## Introduction\nBackground and the research gap addressed here.\n\n"
            "## Methods\nWe enrolled one hundred participants and analysed them.\n\n"
            "## Results\nThe cohort showed the anticipated pattern of recovery.\n\n"
            "## Discussion\nThis is the first study to examine the question.\n",
            encoding="utf-8",
        )
        self._approve_all_sections()

    def _approve_all_sections(self) -> None:
        checkpoint = self.audit / "checkpoint.json"
        checkpoint.write_text(
            json.dumps(
                {
                    "section_progress": {
                        name: {"approval_status": "approved"}
                        for name in [
                            "Abstract",
                            "Introduction",
                            "Methods",
                            "Results",
                            "Discussion",
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

    # ── Phase 6: Cross-Section Audit ──────────────────────────────
    def complete_phase_6(self) -> None:
        (self.audit / "quality-scorecard.md").write_text("# Scorecard\nRound 0", encoding="utf-8")
        (self.audit / "hook-effectiveness.md").write_text("# Hook Effectiveness", encoding="utf-8")
        (self.audit / "quality-scorecard.yaml").write_text(
            yaml.dump(
                {
                    "scores": {
                        "novelty": {"score": 8},
                        "rigor": {"score": 7},
                        "clarity": {"score": 9},
                        "completeness": {"score": 8},
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.audit / "hook-effectiveness.yaml").write_text(
            yaml.dump({"hooks": {"A1": {"trigger": 3, "pass": 2, "fix": 1}}}),
            encoding="utf-8",
        )

    # ── Phase 6.5: Evolution Gate ─────────────────────────────────
    def complete_phase_65(self) -> None:
        elog = self.audit / "evolution-log.jsonl"
        self._append_jsonl(elog, {"event": "baseline", "round": 0})

    # ── Phase 7: Autonomous Review ────────────────────────────────
    def complete_phase_7(self, rounds: int = 2) -> None:
        loop_state = {
            "config": {"min_rounds": 2, "max_rounds": 3},
            "rounds": [],
        }
        elog = self.audit / "evolution-log.jsonl"
        for i in range(1, rounds + 1):
            verdict = "quality_met" if i == rounds else "needs_revision"
            loop_state["rounds"].append({"round": i, "verdict": verdict})
            (self.audit / f"review-report-{i}.md").write_text(
                f"# Review Report {i}\nDetailed findings.", encoding="utf-8"
            )
            (self.audit / f"author-response-{i}.md").write_text(
                f"# Author Response {i}\nPoint-by-point response.", encoding="utf-8"
            )
            (self.audit / f"equator-compliance-{i}.md").write_text(
                f"# EQUATOR {i}\nCONSORT checklist addressed.", encoding="utf-8"
            )
            self._append_jsonl(elog, {"event": "review_round", "round": i, "verdict": verdict})
        (self.audit / "audit-loop-review.json").write_text(json.dumps(loop_state), encoding="utf-8")

    # ── Phase 8: Reference Sync ───────────────────────────────────
    def complete_phase_8(self) -> None:
        ms = self.drafts / "manuscript.md"
        content = ms.read_text(encoding="utf-8")
        if "## References" not in content:
            content += "\n\n## References\n\n1. Author A. Title. Journal. 2024.\n"
            ms.write_text(content, encoding="utf-8")

    # ── Phase 9: Export ───────────────────────────────────────────
    def complete_phase_9(self) -> None:
        # v0.7.11 Phase 9 runs structural integrity smoke tests, not mere
        # existence — so write a valid DOCX zip and a parseable one-page PDF.
        self.exports.mkdir(parents=True, exist_ok=True)
        self._write_minimal_docx(self.exports / "paper.docx")
        self._write_minimal_pdf(self.exports / "paper.pdf")

    @staticmethod
    def _write_minimal_docx(path: Path) -> None:
        """Write a structurally valid DOCX (valid zip + parseable body + text)."""
        import zipfile

        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types></Types>")
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                'wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>Manuscript export.</w:t></w:r></w:p></w:body>"
                "</w:document>",
            )

    @staticmethod
    def _write_minimal_pdf(path: Path) -> None:
        """Write a minimal parseable one-page PDF (header, xref, trailer, EOF)."""
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << >> >>",
        ]
        payload = b"%PDF-1.4\n"
        offsets = [0]
        for index, obj in enumerate(objects, 1):
            offsets.append(len(payload))
            payload += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
        xref_offset = len(payload)
        payload += f"xref\n0 {len(objects) + 1}\n".encode()
        payload += b"0000000000 65535 f \n"
        for offset in offsets[1:]:
            payload += f"{offset:010d} 00000 n \n".encode()
        payload += (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
        path.write_bytes(payload)

    # ── Phase 10: Retrospective ───────────────────────────────────
    def complete_phase_10(self) -> None:
        ts = "2026-01-01T00:00:00"
        # v0.7.11 requires specific "## D7 retrospective:" / "## D8 retrospective:"
        # headings (not just the substring "D7"/"D8").
        (self.audit / "pipeline-run-20260101-0000.md").write_text(
            "# Pipeline Run\n\n"
            "## D7 retrospective: Lessons Learned\nWhat worked and what did not.\n\n"
            "## D8 retrospective: Evolution Plan\nNext-cycle improvements.\n",
            encoding="utf-8",
        )
        # hook-effectiveness.md already exists from Phase 6.
        # v0.7.11 meta-learning audit: v2 schema + D1-D9 steps + count/list
        # consistency + matching evolution-log provenance (shared timestamp).
        audit_entry = {
            "schema": "mdpaper.meta_learning_audit.v2",
            "source_tool": "run_meta_learning",
            "timestamp": ts,
            "adjustments_count": 1,
            "lessons_count": 1,
            "suggestions_count": 1,
            "adjustments": [{"id": "adj-1", "detail": "tightened a hook threshold"}],
            "lessons": [{"id": "lesson-1", "detail": "captured a recurring pattern"}],
            "suggestions": [{"id": "sug-1", "detail": "proposed a follow-up"}],
            "analysis_steps": {f"D{i}": {"status": "completed"} for i in range(1, 10)},
        }
        (self.audit / "meta-learning-audit.yaml").write_text(
            yaml.dump([audit_entry]), encoding="utf-8"
        )
        # evolution-log meta_learning event must carry source_tool + matching counts.
        self._append_jsonl(
            self.audit / "evolution-log.jsonl",
            {
                "event": "meta_learning",
                "source_tool": "run_meta_learning",
                "audit_timestamp": ts,
                "adjustments_count": 1,
                "lessons_count": 1,
                "suggestions_count": 1,
            },
        )
        (self.memory / "activeContext.md").write_text("# Active Context", encoding="utf-8")
        (self.memory / "progress.md").write_text("# Progress", encoding="utf-8")

    # ── Helpers ───────────────────────────────────────────────────
    @staticmethod
    def _append_jsonl(path: Path, entry: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def complete_up_to(self, target_phase: int) -> None:
        """Run every completion step up to and including ``target_phase``.

        Uses the LOGICAL pipeline order (Phase 6.5 sits between 6 and 7), not a
        numeric comparison — ``65`` is numerically large but logically early.
        """
        # Ordered list mirrors LIFECYCLE_PHASES (65 between 6 and 7).
        steps: list[tuple[int, Callable[..., None]]] = [
            (0, self.complete_phase_0),
            (1, self.complete_phase_1),
            (2, self.complete_phase_2),
            (3, self.complete_phase_3),
            (4, self.complete_phase_4),
            (5, self.complete_phase_5),
            (6, self.complete_phase_6),
            (65, self.complete_phase_65),
            (7, self.complete_phase_7),
            (8, self.complete_phase_8),
            (9, self.complete_phase_9),
            (10, self.complete_phase_10),
        ]
        # Find the cut-off index by the logical order, not numeric value.
        if target_phase not in LIFECYCLE_PHASES:
            raise ValueError(f"Unknown target phase: {target_phase}")
        cutoff = LIFECYCLE_PHASES.index(target_phase)
        for phase, fn in steps:
            if LIFECYCLE_PHASES.index(phase) <= cutoff:
                fn()


@pytest.fixture
def builder(tmp_path: Path) -> PipelineProjectBuilder:
    return PipelineProjectBuilder(tmp_path / "e2e-project")


# ──────────────────────────────────────────────────────────────────────
# A. Full lifecycle happy path — the core "whole workflow runs" e2e test
# ──────────────────────────────────────────────────────────────────────


class TestFullLifecycleHappyPath:
    """Walk Phase 0 → 10, asserting each gate flips FAIL → PASS in order."""

    def test_phase_0_fails_then_passes(self, builder: PipelineProjectBuilder) -> None:
        builder.root.mkdir(parents=True, exist_ok=True)
        v = PipelineGateValidator(builder.root)
        assert not v.validate_phase(0).passed
        builder.complete_phase_0()
        assert v.validate_phase(0).passed

    def test_full_sequential_walk(self, builder: PipelineProjectBuilder) -> None:
        """The heart of the e2e test: every phase fails before its artifacts,
        then passes after, with all prior phases still satisfied."""
        completion: dict[int, Callable[..., None]] = {
            0: builder.complete_phase_0,
            1: builder.complete_phase_1,
            2: builder.complete_phase_2,
            3: builder.complete_phase_3,
            4: builder.complete_phase_4,
            5: builder.complete_phase_5,
            6: builder.complete_phase_6,
            65: builder.complete_phase_65,
            7: builder.complete_phase_7,
            8: builder.complete_phase_8,
            9: builder.complete_phase_9,
            10: builder.complete_phase_10,
        }
        builder.root.mkdir(parents=True, exist_ok=True)

        for phase in LIFECYCLE_PHASES:
            v = PipelineGateValidator(builder.root)
            before = v.validate_phase(phase)
            assert not before.passed, (
                f"Phase {phase} unexpectedly PASSED before its artifacts were built. "
                f"Failures: {[c.name for c in before.critical_failures]}"
            )

            completion[phase]()

            after = PipelineGateValidator(builder.root).validate_phase(phase)
            assert after.passed, (
                f"Phase {phase} FAILED after building its artifacts. "
                f"Failures: {[(c.name, c.details) for c in after.critical_failures]}"
            )

    def test_all_phases_pass_after_full_build(self, builder: PipelineProjectBuilder) -> None:
        """After a complete build, every lifecycle phase gate passes at once."""
        builder.complete_up_to(10)
        v = PipelineGateValidator(builder.root)
        for phase in LIFECYCLE_PHASES:
            result = v.validate_phase(phase)
            assert result.passed, (
                f"Phase {phase} failed in final sweep: "
                f"{[(c.name, c.details) for c in result.critical_failures]}"
            )


# ──────────────────────────────────────────────────────────────────────
# B. Heartbeat progression
# ──────────────────────────────────────────────────────────────────────


class TestHeartbeatProgression:
    """The pipeline heartbeat completion % should rise as phases complete."""

    def test_completion_rises_monotonically(self, builder: PipelineProjectBuilder) -> None:
        builder.root.mkdir(parents=True, exist_ok=True)
        last_pct = -1.0
        checkpoints = [0, 2, 5, 7, 10]
        for target in checkpoints:
            builder.complete_up_to(target)
            status = PipelineGateValidator(builder.root).get_pipeline_status()
            pct = status["completion_pct"]
            assert pct >= last_pct, (
                f"Completion % dropped after completing up to phase {target}: {last_pct} → {pct}"
            )
            last_pct = pct

    def test_final_completion_is_high(self, builder: PipelineProjectBuilder) -> None:
        """After a full build, all but Phase 11 (git) should pass → ≥ 90%."""
        builder.complete_up_to(10)
        status = PipelineGateValidator(builder.root).get_pipeline_status()
        # v0.7.11 sweeps 14 phases (incl. Phase 2.1). 13 pass; only Phase 11
        # (git) fails because the tmp project has no repository.
        assert status["completion_pct"] >= 90.0
        assert status["phases_passed"] >= 12


# ──────────────────────────────────────────────────────────────────────
# C. Edge cases — prerequisite enforcement & out-of-order execution
# ──────────────────────────────────────────────────────────────────────


class TestPrerequisiteEdgeCases:
    """Skipping or reordering phases must be blocked by prerequisite checks."""

    def test_phase_5_blocked_without_concept(self, builder: PipelineProjectBuilder) -> None:
        """Jumping to Phase 5 with no concept (Phase 3) must fail on prerequisites."""
        builder.complete_phase_0()
        builder.complete_phase_1()
        builder.complete_phase_2()
        # Skip 3 + 4, write a manuscript directly.
        builder.complete_phase_5()
        result = PipelineGateValidator(builder.root).validate_phase(5)
        assert not result.passed
        prereq_failures = [c.name for c in result.critical_failures if "prereq" in c.name]
        assert any("concept" in name for name in prereq_failures)

    def test_phase_2_blocked_without_project_json(self, builder: PipelineProjectBuilder) -> None:
        """Phase 2 requires project.json from Phase 1."""
        builder.complete_phase_0()
        for d in ["drafts", "references", "data", "results", ".audit", ".memory"]:
            (builder.root / d).mkdir(parents=True, exist_ok=True)
        builder.complete_phase_2()  # refs exist but no project.json
        result = PipelineGateValidator(builder.root).validate_phase(2)
        prereq = [c for c in result.critical_failures if c.name == "prereq:project.json"]
        assert prereq, "Phase 2 should fail without project.json"

    def test_phase_7_blocked_without_manuscript(self, builder: PipelineProjectBuilder) -> None:
        """Phase 7 requires a manuscript from Phase 5."""
        builder.complete_up_to(4)
        builder.complete_phase_7()  # review artifacts but no manuscript
        result = PipelineGateValidator(builder.root).validate_phase(7)
        assert not result.passed
        assert any(c.name == "prereq:manuscript.md" for c in result.critical_failures)

    def test_phase_8_blocked_without_completed_review(
        self, builder: PipelineProjectBuilder
    ) -> None:
        """Phase 8 requires a completed Phase 7 review loop."""
        builder.complete_up_to(6)
        builder.complete_phase_65()
        builder.complete_phase_8()  # references synced but no review loop
        result = PipelineGateValidator(builder.root).validate_phase(8)
        assert not result.passed
        assert any(c.name == "prereq:review_completed" for c in result.critical_failures)


# ──────────────────────────────────────────────────────────────────────
# D. Edge cases — corrupted artifacts must fail gracefully (no crash)
# ──────────────────────────────────────────────────────────────────────


class TestCorruptedArtifactEdgeCases:
    """Validators must degrade gracefully on malformed inputs, never raise."""

    def test_corrupt_checkpoint_json_phase_5(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_up_to(4)
        builder.complete_phase_5()
        # Corrupt the approval checkpoint.
        (builder.audit / "checkpoint.json").write_text("{not valid json", encoding="utf-8")
        result = PipelineGateValidator(builder.root).validate_phase(5)
        assert not result.passed  # must fail, but not crash
        assert any(c.name == "section_approval" for c in result.checks)

    def test_corrupt_quality_scorecard_yaml_phase_6(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_up_to(5)
        builder.complete_phase_6()
        (builder.audit / "quality-scorecard.yaml").write_text("scores: [unclosed", encoding="utf-8")
        result = PipelineGateValidator(builder.root).validate_phase(6)
        # Corrupt YAML → scorecard data check fails, but no exception.
        assert not result.passed
        assert any(c.name == "quality-scorecard:data" for c in result.checks)

    def test_corrupt_audit_loop_json_phase_7(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_up_to(65)
        builder.complete_phase_7()
        (builder.audit / "audit-loop-review.json").write_text("}{ corrupt", encoding="utf-8")
        result = PipelineGateValidator(builder.root).validate_phase(7)
        assert not result.passed
        # rounds parsed as 0 → rounds_completed check fails gracefully
        assert any(c.name == "review:rounds_completed" for c in result.checks)

    def test_corrupt_evolution_log_phase_65(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_up_to(6)
        # Write a malformed evolution log (not valid JSON lines).
        (builder.audit / "evolution-log.jsonl").write_text(
            "not json\n{also bad\n", encoding="utf-8"
        )
        result = PipelineGateValidator(builder.root).validate_phase(65)
        assert not result.passed  # baseline not found, but no crash
        assert any(c.name == "evolution-log:baseline" for c in result.checks)

    def test_empty_project_dir_does_not_crash(self, tmp_path: Path) -> None:
        """A completely empty directory should fail cleanly across all phases."""
        v = PipelineGateValidator(tmp_path / "empty")
        for phase in LIFECYCLE_PHASES:
            result = v.validate_phase(phase)
            assert isinstance(result.passed, bool)
            assert result.to_markdown()  # rendering must not crash

    def test_invalid_phase_number(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_phase_1()
        result = PipelineGateValidator(builder.root).validate_phase(999)
        assert not result.passed
        assert result.phase_name == "UNKNOWN"


# ──────────────────────────────────────────────────────────────────────
# E. Edge case — regression mid-flow then recovery
# ──────────────────────────────────────────────────────────────────────


class TestRegressionAndRecovery:
    """Simulate a Phase 7 → Phase 5 regression and confirm recovery is possible."""

    def test_regression_reopens_then_recovers(self, builder: PipelineProjectBuilder) -> None:
        # Full build through Phase 7.
        builder.complete_up_to(7)
        v = PipelineGateValidator(builder.root)
        assert v.validate_phase(7).passed

        # Regression: a section needs a rewrite → mark it unapproved (back to Phase 5).
        checkpoint = builder.audit / "checkpoint.json"
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        data["section_progress"]["Methods"]["approval_status"] = "pending"
        checkpoint.write_text(json.dumps(data), encoding="utf-8")

        # Phase 5 now fails again (the regression target).
        assert not PipelineGateValidator(builder.root).validate_phase(5).passed

        # Re-approve after the rewrite → Phase 5 recovers.
        builder._approve_all_sections()
        assert PipelineGateValidator(builder.root).validate_phase(5).passed

        # And Phase 7 is still satisfied (review artifacts untouched).
        assert PipelineGateValidator(builder.root).validate_phase(7).passed


# ──────────────────────────────────────────────────────────────────────
# F. Edge case — partial review loop (only 1 of 2 required rounds)
# ──────────────────────────────────────────────────────────────────────


class TestPartialReviewLoop:
    """Phase 7 must not pass with fewer than min_rounds completed."""

    def test_single_round_insufficient(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_up_to(65)
        builder.complete_phase_7(rounds=1)  # only 1 round, min is 2
        result = PipelineGateValidator(builder.root).validate_phase(7)
        assert not result.passed
        rounds_check = next(c for c in result.checks if c.name == "review:rounds_completed")
        assert not rounds_check.passed

    def test_two_rounds_sufficient(self, builder: PipelineProjectBuilder) -> None:
        builder.complete_up_to(65)
        builder.complete_phase_7(rounds=2)
        result = PipelineGateValidator(builder.root).validate_phase(7)
        assert result.passed
