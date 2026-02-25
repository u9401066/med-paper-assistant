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
