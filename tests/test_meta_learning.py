"""
Tests for Hook D self-improvement infrastructure:
  - HookEffectivenessTracker
  - QualityScorecard
  - MetaLearningEngine

Validates CONSTITUTION §23 self-improvement boundaries:
  - Auto-adjust thresholds within ±20%
  - Detect too-strict / too-loose / broken hooks
  - Generate lessons learned
  - Protect forbidden modifications
"""

from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.meta_learning_engine import (
    LessonLearned,
    MetaLearningEngine,
    ThresholdAdjustment,
)
from med_paper_assistant.infrastructure.persistence.quality_scorecard import (
    DIMENSIONS,
    QualityScorecard,
)
from med_paper_assistant.infrastructure.persistence.tool_invocation_store import (
    ToolInvocationStore,
)

# ──────────────────────────────────────────────────────────────────────────────
# HookEffectivenessTracker Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestHookEffectivenessTracker:
    @pytest.fixture()
    def audit_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / ".audit"
        d.mkdir()
        return d

    @pytest.fixture()
    def tracker(self, audit_dir: Path) -> HookEffectivenessTracker:
        return HookEffectivenessTracker(audit_dir)

    # --- basic recording ---

    def test_record_and_stats(self, tracker: HookEffectivenessTracker):
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")
        tracker.record_event("A1", "fix")

        stats = tracker.get_stats("A1")
        assert stats["trigger"] == 2
        assert stats["pass"] == 1
        assert stats["fix"] == 1

    def test_trigger_rate_computation(self, tracker: HookEffectivenessTracker):
        # 8 triggers out of 10 evaluations = 80%
        for _ in range(8):
            tracker.record_event("A3", "trigger")
        for _ in range(2):
            tracker.record_event("A3", "pass")

        stats = tracker.get_stats("A3")
        assert stats["trigger_rate"] == pytest.approx(0.8)

    def test_fix_rate_computation(self, tracker: HookEffectivenessTracker):
        for _ in range(4):
            tracker.record_event("B5", "trigger")
        for _ in range(3):
            tracker.record_event("B5", "fix")

        stats = tracker.get_stats("B5")
        assert stats["fix_rate"] == pytest.approx(0.75)

    def test_false_positive_rate(self, tracker: HookEffectivenessTracker):
        for _ in range(10):
            tracker.record_event("A3", "trigger")
        for _ in range(4):
            tracker.record_event("A3", "false_positive")

        stats = tracker.get_stats("A3")
        assert stats["false_positive_rate"] == pytest.approx(0.4)

    def test_all_hooks_stats(self, tracker: HookEffectivenessTracker):
        tracker.record_event("A1", "trigger")
        tracker.record_event("B1", "pass")
        tracker.record_event("C1", "trigger")

        all_stats = tracker.get_stats()
        assert "A1" in all_stats
        assert "B1" in all_stats
        assert "C1" in all_stats

    def test_empty_stats(self, tracker: HookEffectivenessTracker):
        stats = tracker.get_stats("X99")
        assert stats["trigger"] == 0
        assert stats["trigger_rate"] == 0.0

    # --- recommendations (§23) ---

    def test_recommend_loosen_when_too_strict(self, tracker: HookEffectivenessTracker):
        """§23: trigger_rate > 80% → too strict."""
        for _ in range(9):
            tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")

        recs = tracker.get_recommendations()
        assert any(r["hook_id"] == "A1" and r["type"] == "loosen" for r in recs)

    def test_recommend_tighten_when_too_loose(self, tracker: HookEffectivenessTracker):
        """§23: trigger_rate < 5% over 5+ evaluations."""
        tracker.record_event("C4", "trigger")  # 1 trigger
        for _ in range(24):
            tracker.record_event("C4", "pass")

        recs = tracker.get_recommendations()
        assert any(r["hook_id"] == "C4" and r["type"] == "tighten" for r in recs)

    def test_recommend_fix_logic_high_false_positive(self, tracker: HookEffectivenessTracker):
        """§23: false_positive_rate > 30%."""
        for _ in range(10):
            tracker.record_event("A3", "trigger")
        for _ in range(5):
            tracker.record_event("A3", "false_positive")

        recs = tracker.get_recommendations()
        assert any(r["hook_id"] == "A3" and r["type"] == "fix_logic" for r in recs)

    def test_no_recommendations_normal_hook(self, tracker: HookEffectivenessTracker):
        """Normal performance → no recommendations."""
        for _ in range(3):
            tracker.record_event("B1", "trigger")
        for _ in range(7):
            tracker.record_event("B1", "pass")
        for _ in range(2):
            tracker.record_event("B1", "fix")

        recs = tracker.get_recommendations()
        assert not any(r["hook_id"] == "B1" for r in recs)

    # --- persistence ---

    def test_persistence(self, audit_dir: Path):
        t1 = HookEffectivenessTracker(audit_dir)
        t1.record_event("A1", "trigger")
        t1.record_event("A1", "fix")

        t2 = HookEffectivenessTracker(audit_dir)
        stats = t2.get_stats("A1")
        assert stats["trigger"] == 1
        assert stats["fix"] == 1

    # --- report ---

    def test_generate_report(self, tracker: HookEffectivenessTracker, audit_dir: Path):
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")
        report = tracker.generate_report()

        assert "Hook Effectiveness Report" in report
        assert "A1" in report
        assert (audit_dir / "hook-effectiveness.md").is_file()

    # --- record_run ---

    def test_record_run(self, tracker: HookEffectivenessTracker):
        tracker.record_run(
            "run-001",
            {
                "A1": {"trigger": 3, "pass": 7, "fix": 2, "false_positive": 0},
                "B1": {"trigger": 1, "pass": 4, "fix": 1, "false_positive": 0},
            },
        )

        assert tracker.get_run_count() == 1
        stats = tracker.get_stats("A1")
        assert stats["trigger"] == 3

    # --- reset ---

    def test_reset(self, tracker: HookEffectivenessTracker, audit_dir: Path):
        tracker.record_event("A1", "trigger")
        tracker.generate_report()
        tracker.reset()

        assert not (audit_dir / "hook-effectiveness.json").is_file()
        assert not (audit_dir / "hook-effectiveness.md").is_file()


# ──────────────────────────────────────────────────────────────────────────────
# QualityScorecard Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQualityScorecard:
    @pytest.fixture()
    def audit_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / ".audit"
        d.mkdir()
        return d

    @pytest.fixture()
    def sc(self, audit_dir: Path) -> QualityScorecard:
        return QualityScorecard(audit_dir)

    # --- basic operations ---

    def test_set_and_get_score(self, sc: QualityScorecard):
        sc.set_score("text_quality", 7, "Clear writing")
        assert sc.get_score("text_quality") == 7

    def test_score_validation(self, sc: QualityScorecard):
        with pytest.raises(ValueError):
            sc.set_score("text_quality", 11)
        with pytest.raises(ValueError):
            sc.set_score("text_quality", -1)

    def test_get_nonexistent_score(self, sc: QualityScorecard):
        assert sc.get_score("nonexistent") is None

    def test_overwrite_score(self, sc: QualityScorecard):
        sc.set_score("text_quality", 5, "Draft version")
        sc.set_score("text_quality", 8, "After revision")
        assert sc.get_score("text_quality") == 8

    # --- scorecard summary ---

    def test_get_scorecard(self, sc: QualityScorecard):
        sc.set_score("text_quality", 8)
        sc.set_score("citation_quality", 6)

        card = sc.get_scorecard()
        assert card["scored_count"] == 2
        assert card["average_score"] == 7.0
        assert card["min_score"] == 6
        assert card["max_score"] == 8

    def test_missing_dimensions(self, sc: QualityScorecard):
        sc.set_score("text_quality", 8)
        card = sc.get_scorecard()
        assert "citation_quality" in card["missing_dimensions"]

    def test_full_scorecard(self, sc: QualityScorecard):
        for dim in DIMENSIONS:
            sc.set_score(dim, 7)
        card = sc.get_scorecard()
        assert card["missing_dimensions"] == []
        assert card["scored_count"] == len(DIMENSIONS)

    # --- threshold ---

    def test_meets_threshold(self, sc: QualityScorecard):
        sc.set_score("text_quality", 8)
        sc.set_score("citation_quality", 7)
        assert sc.meets_threshold(7.0) is True
        assert sc.meets_threshold(8.0) is False

    # --- weak dimensions ---

    def test_get_weak_dimensions(self, sc: QualityScorecard):
        sc.set_score("text_quality", 4, "Many AI patterns")
        sc.set_score("citation_quality", 8)
        sc.set_score("methodology_reproducibility", 5, "Missing details")

        weak = sc.get_weak_dimensions(min_score=6.0)
        assert len(weak) == 2
        assert weak[0]["dimension"] == "text_quality"  # sorted by score
        assert weak[0]["score"] == 4

    def test_no_weak_dimensions(self, sc: QualityScorecard):
        sc.set_score("text_quality", 8)
        assert sc.get_weak_dimensions() == []

    # --- persistence ---

    def test_persistence(self, audit_dir: Path):
        sc1 = QualityScorecard(audit_dir)
        sc1.set_score("text_quality", 9, "Excellent")

        sc2 = QualityScorecard(audit_dir)
        assert sc2.get_score("text_quality") == 9

    # --- report ---

    def test_generate_report(self, sc: QualityScorecard, audit_dir: Path):
        sc.set_score("text_quality", 7, "Good flow")
        sc.set_score("citation_quality", 4, "Too few refs")
        report = sc.generate_report()

        assert "Quality Scorecard" in report
        assert "🟡" in report  # 7 → yellow
        assert "🔴" in report  # 4 → red
        assert (audit_dir / "quality-scorecard.md").is_file()

    # --- history ---

    def test_history_tracking(self, sc: QualityScorecard):
        sc.set_score("text_quality", 5)
        sc.set_score("text_quality", 8)

        data = sc._load()
        assert len(data["history"]) == 2
        assert data["history"][0]["old_score"] is None
        assert data["history"][1]["old_score"] == 5
        assert data["history"][1]["new_score"] == 8

    # --- reset ---

    def test_reset(self, sc: QualityScorecard, audit_dir: Path):
        sc.set_score("text_quality", 7)
        sc.generate_report()
        sc.reset()

        assert not (audit_dir / "quality-scorecard.json").is_file()
        assert not (audit_dir / "quality-scorecard.md").is_file()


# ──────────────────────────────────────────────────────────────────────────────
# MetaLearningEngine Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestMetaLearningEngine:
    @pytest.fixture()
    def audit_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / ".audit"
        d.mkdir()
        return d

    @pytest.fixture()
    def tracker(self, audit_dir: Path) -> HookEffectivenessTracker:
        return HookEffectivenessTracker(audit_dir)

    @pytest.fixture()
    def scorecard(self, audit_dir: Path) -> QualityScorecard:
        return QualityScorecard(audit_dir)

    @pytest.fixture()
    def engine(
        self, audit_dir: Path, tracker: HookEffectivenessTracker, scorecard: QualityScorecard
    ) -> MetaLearningEngine:
        return MetaLearningEngine(audit_dir, tracker, scorecard)

    # --- ThresholdAdjustment ---

    def test_threshold_within_bounds(self):
        adj = ThresholdAdjustment("A1", "threshold", 1.0, 1.15, "test")
        assert adj.within_bounds is True
        assert adj.change_pct == pytest.approx(0.15)

    def test_threshold_out_of_bounds(self):
        adj = ThresholdAdjustment("A1", "threshold", 1.0, 1.25, "test")
        assert adj.within_bounds is False
        assert adj.change_pct == pytest.approx(0.25)

    def test_threshold_to_dict(self):
        adj = ThresholdAdjustment("A1", "threshold", 1.0, 1.10, "testing", auto_apply=True)
        d = adj.to_dict()
        assert d["hook_id"] == "A1"
        assert d["auto_apply"] is True
        assert d["within_bounds"] is True

    # --- LessonLearned ---

    def test_lesson_to_markdown(self):
        ll = LessonLearned("hook_tuning", "A1 too strict", "D3", severity="warning")
        md = ll.to_markdown()
        assert "⚠️" in md
        assert "hook_tuning" in md
        assert "A1 too strict" in md

    # --- Full analysis ---

    def test_analyze_empty(self, engine: MetaLearningEngine):
        result = engine.analyze()
        assert "adjustments" in result
        assert "lessons" in result
        assert "suggestions" in result
        assert "summary" in result

    def test_analyze_detects_strict_hook(
        self,
        engine: MetaLearningEngine,
        tracker: HookEffectivenessTracker,
    ):
        """§23: Hook triggering > 80% should produce loosen recommendation."""
        for _ in range(9):
            tracker.record_event("A3", "trigger")
        tracker.record_event("A3", "pass")

        result = engine.analyze()
        assert any(
            a["hook_id"] == "A3" and a["suggested_value"] > a["current_value"]
            for a in result["adjustments"]
        )

    def test_analyze_detects_quality_gap(
        self,
        engine: MetaLearningEngine,
        scorecard: QualityScorecard,
    ):
        scorecard.set_score("text_quality", 3, "Full of AI patterns")

        result = engine.analyze()
        quality_lessons = [item for item in result["lessons"] if item["category"] == "quality_gap"]
        assert len(quality_lessons) >= 1
        assert any("text_quality" in item["lesson"] for item in quality_lessons)

    def test_analyze_detects_missing_dimensions(
        self,
        engine: MetaLearningEngine,
        scorecard: QualityScorecard,
    ):
        scorecard.set_score("text_quality", 8)
        # Only 1 of 6 standard dimensions scored

        result = engine.analyze()
        process_gaps = [item for item in result["lessons"] if item["category"] == "process_gap"]
        assert len(process_gaps) >= 1

    def test_analyze_suggests_methodology_improvement(
        self,
        engine: MetaLearningEngine,
        scorecard: QualityScorecard,
        tracker: HookEffectivenessTracker,
    ):
        scorecard.set_score("methodology_reproducibility", 4, "Incomplete methods")
        # Need some hook data for D4/D5
        tracker.record_event("B5", "trigger")

        result = engine.analyze()
        assert any("B5" in s.get("target", "") for s in result["suggestions"])

    def test_analyze_excellent_quality(
        self,
        engine: MetaLearningEngine,
        scorecard: QualityScorecard,
    ):
        for dim in DIMENSIONS:
            scorecard.set_score(dim, 9)

        result = engine.analyze()
        assert any(item["category"] == "achievement" for item in result["lessons"])

    # --- audit trail ---

    def test_audit_trail_persisted(self, engine: MetaLearningEngine, audit_dir: Path):
        engine.analyze()
        assert (audit_dir / "meta-learning-audit.yaml").is_file()

        data = yaml.safe_load((audit_dir / "meta-learning-audit.yaml").read_text(encoding="utf-8"))
        assert len(data) == 1
        assert "timestamp" in data[0]

    def test_multiple_analyses_append(self, engine: MetaLearningEngine, audit_dir: Path):
        engine.analyze()
        engine.analyze()

        data = yaml.safe_load((audit_dir / "meta-learning-audit.yaml").read_text(encoding="utf-8"))
        assert len(data) == 2

    # --- summary generation ---

    def test_summary_format(
        self,
        engine: MetaLearningEngine,
        tracker: HookEffectivenessTracker,
        scorecard: QualityScorecard,
    ):
        for _ in range(9):
            tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")
        scorecard.set_score("text_quality", 4, "AI filler")

        result = engine.analyze()
        assert "Meta-Learning Summary" in result["summary"]
        assert "A1" in result["summary"]

    # --- format lessons for SKILL.md ---

    def test_format_lessons_for_skill_empty(self, engine: MetaLearningEngine):
        text = engine.format_lessons_for_skill([])
        assert "尚無記錄" in text

    def test_format_lessons_for_skill(self, engine: MetaLearningEngine):
        lessons = [
            {
                "category": "hook_tuning",
                "lesson": "A1 threshold too strict",
                "source": "D3",
                "severity": "warning",
                "timestamp": "2026-02-23T10:00:00",
            },
            {
                "category": "quality_gap",
                "lesson": "Low citation score",
                "source": "D1",
                "severity": "info",
                "timestamp": "2026-02-23T10:00:00",
            },
        ]
        text = engine.format_lessons_for_skill(lessons)
        assert "### hook_tuning" in text
        assert "### quality_gap" in text
        assert "⚠️" in text

    # --- §23 protection: auto_apply only within bounds ---

    def test_auto_apply_respects_bounds(
        self,
        engine: MetaLearningEngine,
        tracker: HookEffectivenessTracker,
    ):
        """Adjustments beyond ±20% must not be auto-applied."""
        for _ in range(9):
            tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")

        result = engine.analyze()
        for adj in result["adjustments"]:
            if adj["auto_apply"]:
                # If auto_apply is True, it must be within bounds
                assert adj["within_bounds"] is True

    # --- D1 Hook Coverage Gap ---

    def test_hook_coverage_detects_missing_hooks(
        self,
        engine: MetaLearningEngine,
        tracker: HookEffectivenessTracker,
    ):
        """Engine should detect hooks that were never evaluated."""
        # Only record A1 — all others are missing
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "fix")

        result = engine.analyze()
        coverage_lessons = [ls for ls in result["lessons"] if ls["category"] == "hook_coverage_gap"]
        assert len(coverage_lessons) > 0
        # Should flag missing layers
        all_text = " ".join(ls["lesson"] for ls in coverage_lessons)
        assert "never evaluated" in all_text

    def test_hook_coverage_reports_low_percentage(
        self,
        engine: MetaLearningEngine,
        tracker: HookEffectivenessTracker,
    ):
        """Low coverage percentage should produce a process_gap lesson."""
        # Record only 2 hooks out of ~35 expected
        tracker.record_event("A1", "pass")
        tracker.record_event("B1", "pass")

        result = engine.analyze()
        gap_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] == "process_gap" and "coverage" in ls["lesson"].lower()
        ]
        assert len(gap_lessons) > 0

    # --- D2 Relative Weakness ---

    def test_relative_weakness_always_found(
        self,
        engine: MetaLearningEngine,
        scorecard: QualityScorecard,
    ):
        """Even with all scores >= 7, the lowest dimension should be flagged."""
        for dim in DIMENSIONS:
            scorecard.set_score(dim, 8, "Good")
        # Set one to 7 (still passes absolute threshold)
        scorecard.set_score("figure_table_quality", 7, "Adequate")

        result = engine.analyze()
        improvement_lessons = [
            ls for ls in result["lessons"] if ls["category"] == "improvement_opportunity"
        ]
        assert len(improvement_lessons) == 1
        assert "figure_table_quality" in improvement_lessons[0]["lesson"]
        assert "weakest dimension" in improvement_lessons[0]["lesson"]

    def test_no_relative_weakness_when_absolute_gap_exists(
        self,
        engine: MetaLearningEngine,
        scorecard: QualityScorecard,
    ):
        """If there's already an absolute weak dimension, don't double-flag."""
        for dim in DIMENSIONS:
            scorecard.set_score(dim, 8, "Good")
        scorecard.set_score("text_quality", 4, "Poor")  # Below 6.0 threshold

        result = engine.analyze()
        # Should have quality_gap but NOT improvement_opportunity
        has_gap = any(ls["category"] == "quality_gap" for ls in result["lessons"])
        has_improvement = any(
            ls["category"] == "improvement_opportunity" for ls in result["lessons"]
        )
        assert has_gap
        assert not has_improvement

    # --- D5 Project Completeness ---

    def test_missing_journal_profile(
        self,
        engine: MetaLearningEngine,
    ):
        """Missing journal-profile.yaml should be flagged."""
        result = engine.analyze()
        config_lessons = [ls for ls in result["lessons"] if ls["category"] == "configuration_gap"]
        # audit_dir.parent has no journal-profile.yaml in tmp
        assert len(config_lessons) > 0

    def test_blank_journal_name_detected(
        self,
        audit_dir: Path,
        engine: MetaLearningEngine,
    ):
        """Blank journal name in profile should produce a warning."""
        profile = audit_dir.parent / "journal-profile.yaml"
        profile.write_text(
            yaml.dump({"journal": {"name": ""}, "references": {"style": "vancouver"}}),
            encoding="utf-8",
        )
        result = engine.analyze()
        config_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] == "configuration_gap" and "journal name" in ls["lesson"]
        ]
        assert len(config_lessons) == 1

    def test_missing_concept_md(
        self,
        engine: MetaLearningEngine,
    ):
        """Missing concept.md should be flagged."""
        result = engine.analyze()
        doc_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] == "documentation_gap" and "concept.md" in ls["lesson"]
        ]
        assert len(doc_lessons) == 1

    def test_completeness_passes_with_all_files(
        self,
        audit_dir: Path,
        engine: MetaLearningEngine,
    ):
        """With all files present and configured, no completeness gaps."""
        project_dir = audit_dir.parent
        # Create journal-profile.yaml
        (project_dir / "journal-profile.yaml").write_text(
            yaml.dump({"journal": {"name": "JAMIA"}, "references": {"style": "vancouver"}}),
            encoding="utf-8",
        )
        # Create concept.md
        (project_dir / "concept.md").write_text("# Concept\nTest", encoding="utf-8")
        # Create .memory/
        mem_dir = project_dir / ".memory"
        mem_dir.mkdir(exist_ok=True)
        (mem_dir / "activeContext.md").write_text("# Context", encoding="utf-8")
        (mem_dir / "progress.md").write_text("# Progress", encoding="utf-8")

        result = engine.analyze()
        gap_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] in ("configuration_gap", "documentation_gap")
        ]
        assert len(gap_lessons) == 0

    # --- D7 Review Retrospective ---

    def test_d7_no_review_reports(
        self,
        engine: MetaLearningEngine,
    ):
        """Without review-report files, D7 should flag the gap."""
        result = engine.analyze()
        review_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] == "review_gap" and "No review-report" in ls["lesson"]
        ]
        assert len(review_lessons) == 1

    def test_d7_detects_unchanged_hash(
        self,
        audit_dir: Path,
        engine: MetaLearningEngine,
    ):
        """D7 should flag when manuscript hash didn't change during review."""
        import json

        # Create review artifacts
        (audit_dir / "review-report-1.md").write_text("# Review", encoding="utf-8")
        (audit_dir / "author-response-1.md").write_text("# Response", encoding="utf-8")
        # Create audit-loop-review.json with same start/end hash
        loop_data = {
            "rounds": [
                {
                    "round_number": 1,
                    "artifact_hash_start": "abc123",
                    "artifact_hash_end": "abc123",  # SAME = not modified
                    "issues": [],
                    "fixes": [],
                }
            ]
        }
        (audit_dir / "audit-loop-review.json").write_text(json.dumps(loop_data), encoding="utf-8")

        result = engine.analyze()
        integrity_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] == "review_integrity" and "unchanged" in ls["lesson"]
        ]
        assert len(integrity_lessons) == 1
        assert integrity_lessons[0]["severity"] == "critical"

    def test_d7_detects_issues_without_fixes(
        self,
        audit_dir: Path,
        engine: MetaLearningEngine,
    ):
        """D7 should flag when issues were found but none fixed."""
        import json

        (audit_dir / "review-report-1.md").write_text("# Review", encoding="utf-8")
        (audit_dir / "author-response-1.md").write_text("# Response", encoding="utf-8")
        loop_data = {
            "rounds": [
                {
                    "round_number": 1,
                    "artifact_hash_start": "abc",
                    "artifact_hash_end": "def",
                    "issues": [{"desc": "issue1"}, {"desc": "issue2"}],
                    "fixes": [],
                }
            ]
        }
        (audit_dir / "audit-loop-review.json").write_text(json.dumps(loop_data), encoding="utf-8")

        result = engine.analyze()
        fix_lessons = [
            ls
            for ls in result["lessons"]
            if ls["category"] == "review_integrity" and "0 fixes" in ls["lesson"]
        ]
        assert len(fix_lessons) == 1

    # --- D8 EQUATOR Retrospective ---

    def test_d8_no_equator_reports(
        self,
        engine: MetaLearningEngine,
    ):
        """Without EQUATOR reports, D8 should note the gap."""
        result = engine.analyze()
        equator_lessons = [ls for ls in result["lessons"] if ls["category"] == "equator_gap"]
        assert len(equator_lessons) == 1

    def test_d8_detects_non_compliant_items(
        self,
        audit_dir: Path,
        engine: MetaLearningEngine,
    ):
        """D8 should flag non-compliant EQUATOR items."""
        (audit_dir / "equator-compliance-1.md").write_text(
            "# EQUATOR\n- Item 1: Compliant\n- Item 2: Non-Compliant\n"
            "- Item 3: Not Reported\n- Item 4: Partial\n",
            encoding="utf-8",
        )

        result = engine.analyze()
        eq_lessons = [ls for ls in result["lessons"] if ls["category"] == "equator_finding"]
        assert len(eq_lessons) >= 1
        all_text = " ".join(ls["lesson"] for ls in eq_lessons)
        assert "non-compliant" in all_text.lower() or "Non-Compliant" in all_text

    # --- First-run awareness in D4-D5 ---

    def test_first_run_flags_trigger_without_fix(
        self,
        engine: MetaLearningEngine,
        tracker: HookEffectivenessTracker,
    ):
        """First run with trigger but no fix should suggest verification."""
        tracker.record_event("C7", "trigger")
        tracker.record_event("C7", "pass")

        result = engine.analyze()
        verify_suggestions = [
            s
            for s in result["suggestions"]
            if s["type"] == "verify_fix_mechanism" and "C7" in s["target"]
        ]
        assert len(verify_suggestions) == 1

    # --- Integration: analyze() produces non-empty output ---

    def test_analyze_always_produces_lessons(
        self,
        engine: MetaLearningEngine,
    ):
        """Even with no hook data, analyze must still produce lessons (completeness checks)."""
        result = engine.analyze()
        assert len(result["lessons"]) > 0, "analyze() must always find SOMETHING to improve"


# ──────────────────────────────────────────────────────────────────────────────
# MetaLearningEngine D9 — Tool Description Evolution Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestMetaLearningEngineD9:
    """Tests for the D9 tool description evolution analysis step."""

    @pytest.fixture()
    def audit_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / ".audit"
        d.mkdir()
        return d

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        ws = tmp_path / "workspace"
        ws.mkdir()
        return ws

    @pytest.fixture()
    def engine_no_workspace(self, audit_dir: Path) -> MetaLearningEngine:
        """Engine without workspace_root — D9 must be skipped."""
        return MetaLearningEngine(
            audit_dir, HookEffectivenessTracker(audit_dir), QualityScorecard(audit_dir)
        )

    @pytest.fixture()
    def engine_with_workspace(self, audit_dir: Path, workspace: Path) -> MetaLearningEngine:
        return MetaLearningEngine(
            audit_dir,
            HookEffectivenessTracker(audit_dir),
            QualityScorecard(audit_dir),
            workspace_root=workspace,
        )

    # ── Backward compatibility ─────────────────────────────────────────

    def test_d9_skipped_when_no_workspace_root(self, engine_no_workspace: MetaLearningEngine):
        """D9 returns [] when workspace_root=None — preserves backward compat."""
        assert engine_no_workspace._d9_tool_description_suggestions() == []

    def test_analyze_still_works_without_workspace_root(
        self, engine_no_workspace: MetaLearningEngine
    ):
        """analyze() must succeed with no workspace_root (D9 simply empty)."""
        result = engine_no_workspace.analyze()
        assert "suggestions" in result
        assert "lessons" in result

    # ── D9 with empty store ────────────────────────────────────────────

    def test_d9_empty_store_returns_no_suggestions(self, engine_with_workspace: MetaLearningEngine):
        """Empty ToolInvocationStore → no D9 suggestions."""
        assert engine_with_workspace._d9_tool_description_suggestions() == []

    # ── High misuse rate detection ────────────────────────────────────

    def test_d9_high_misuse_rate_generates_suggestion(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        store = ToolInvocationStore(workspace)
        for _ in range(5):
            store.record_invocation("confusing_tool")
        for _ in range(2):
            store.record_misuse("confusing_tool")

        suggestions = engine_with_workspace._d9_tool_description_suggestions()
        matching = [
            s
            for s in suggestions
            if s["type"] == "improve_tool_description" and s["target"] == "confusing_tool"
        ]
        assert len(matching) == 1

    def test_d9_misuse_below_threshold_no_suggestion(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        """misuse_count=1 (< 2 minimum) → no suggestion."""
        store = ToolInvocationStore(workspace)
        for _ in range(10):
            store.record_invocation("tool_a")
        store.record_misuse("tool_a")  # only 1, threshold requires >= 2

        suggestions = engine_with_workspace._d9_tool_description_suggestions()
        assert not any(s["target"] == "tool_a" for s in suggestions)

    def test_d9_misuse_rate_below_threshold_no_suggestion(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        """High count but low rate (10%) → no suggestion."""
        store = ToolInvocationStore(workspace)
        for _ in range(100):
            store.record_invocation("popular_tool")
        for _ in range(10):
            store.record_misuse("popular_tool")  # 10% rate, below 20% threshold

        suggestions = engine_with_workspace._d9_tool_description_suggestions()
        assert not any(s["target"] == "popular_tool" for s in suggestions)

    # ── High error count detection ────────────────────────────────────

    def test_d9_high_errors_generates_suggestion(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        store = ToolInvocationStore(workspace)
        for _ in range(4):
            store.record_invocation("broken_tool")
        for _ in range(3):
            store.record_error("broken_tool", "TypeError")

        suggestions = engine_with_workspace._d9_tool_description_suggestions()
        assert any(s["target"] == "broken_tool" for s in suggestions)

    def test_d9_error_count_below_threshold_no_suggestion(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        """error_count=2 (< 3 threshold) → no error-based suggestion."""
        store = ToolInvocationStore(workspace)
        for _ in range(5):
            store.record_invocation("tool_b")
        for _ in range(2):
            store.record_error("tool_b", "ValueError")

        suggestions = engine_with_workspace._d9_tool_description_suggestions()
        assert not any(s["target"] == "tool_b" for s in suggestions)

    # ── All D9 suggestions must be L3 ─────────────────────────────────

    def test_d9_suggestions_all_require_confirmation(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        """CONSTITUTION §23: D9 suggestions must be L3 (requires_confirmation=True)."""
        store = ToolInvocationStore(workspace)
        for _ in range(5):
            store.record_invocation("t")
        for _ in range(3):
            store.record_error("t", "ValueError")

        for s in engine_with_workspace._d9_tool_description_suggestions():
            assert s["requires_confirmation"] is True

    def test_d9_suggestion_has_required_keys(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        store = ToolInvocationStore(workspace)
        for _ in range(5):
            store.record_invocation("t2")
        for _ in range(3):
            store.record_error("t2", "KeyError")

        suggestions = engine_with_workspace._d9_tool_description_suggestions()
        d9_s = [s for s in suggestions if s["target"] == "t2"]
        assert len(d9_s) >= 1
        for s in d9_s:
            assert "type" in s
            assert "target" in s
            assert "reason" in s
            assert "requires_confirmation" in s

    # ── Integration with analyze() ────────────────────────────────────

    def test_d9_suggestions_included_in_analyze_output(
        self, engine_with_workspace: MetaLearningEngine, workspace: Path
    ):
        """analyze() result must include D9 suggestions in 'suggestions' key."""
        store = ToolInvocationStore(workspace)
        for _ in range(5):
            store.record_invocation("overused_tool")
        for _ in range(3):
            store.record_error("overused_tool", "KeyError")

        result = engine_with_workspace.analyze()
        all_types = [s.get("type") for s in result.get("suggestions", [])]
        assert "improve_tool_description" in all_types

    def test_d9_failure_does_not_break_analyze(self, audit_dir: Path):
        """If ToolInvocationStore cannot be instantiated, analyze() must not raise."""
        # Pass a workspace_root that points to a read-only or otherwise problematic path
        engine = MetaLearningEngine(
            audit_dir,
            HookEffectivenessTracker(audit_dir),
            QualityScorecard(audit_dir),
            workspace_root="/nonexistent_path_that_wont_fail_read",
        )
        # Should not raise — D9 returns [] and analyze() proceeds
        result = engine.analyze()
        assert "suggestions" in result
