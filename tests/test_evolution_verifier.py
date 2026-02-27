"""Tests for EvolutionVerifier — cross-project self-evolution evidence collector."""

from pathlib import Path

import yaml

from med_paper_assistant.infrastructure.persistence.evolution_verifier import (
    EvolutionVerifier,
    ProjectSnapshot,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _write_qs(audit_dir: Path, scores: dict[str, float]) -> None:
    """Write a minimal quality-scorecard.yaml."""
    data = {
        "version": 1,
        "scores": {
            dim: {"score": score, "explanation": f"Test {dim}"} for dim, score in scores.items()
        },
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-15T00:00:00",
    }
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "quality-scorecard.yaml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _write_ml(audit_dir: Path, adjustments: int = 0, lessons: int = 0) -> None:
    """Write a minimal meta-learning-audit.yaml."""
    data = {
        "timestamp": "2026-01-15T00:00:00",
        "adjustments": [
            {"hook_id": f"A{i + 1}", "parameter": "threshold", "reason": "test"}
            for i in range(adjustments)
        ],
        "lessons": [{"category": "test", "lesson": f"lesson {i + 1}"} for i in range(lessons)],
    }
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "meta-learning-audit.yaml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _write_he(audit_dir: Path, hooks: dict[str, dict[str, int]]) -> None:
    """Write a minimal hook-effectiveness.yaml."""
    data = {"version": 1, "hooks": hooks, "runs": []}
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "hook-effectiveness.yaml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


# ── ProjectSnapshot ──────────────────────────────────────────────────


class TestProjectSnapshot:
    def test_to_dict(self):
        snap = ProjectSnapshot(
            slug="test",
            timestamp="2026-01-01",
            quality_scores={"text_quality": 8.0},
            average_score=8.0,
            hook_stats={"A1": {"trigger": 1}},
            threshold_adjustments=[{"hook_id": "A1"}],
            lessons_count=3,
        )
        d = snap.to_dict()
        assert d["slug"] == "test"
        assert d["average_score"] == 8.0
        assert d["hook_stats_count"] == 1
        assert d["threshold_adjustments"] == 1
        assert d["lessons_count"] == 3


# ── EvolutionVerifier ────────────────────────────────────────────────


class TestCollectSnapshots:
    def test_empty_projects_dir(self, tmp_path):
        verifier = EvolutionVerifier(tmp_path / "nonexistent")
        assert verifier.collect_snapshots() == []

    def test_project_without_audit(self, tmp_path):
        (tmp_path / "proj-a").mkdir()
        verifier = EvolutionVerifier(tmp_path)
        assert verifier.collect_snapshots() == []

    def test_project_with_empty_audit(self, tmp_path):
        (tmp_path / "proj-a" / ".audit").mkdir(parents=True)
        verifier = EvolutionVerifier(tmp_path)
        # No yaml files → no snapshot
        assert verifier.collect_snapshots() == []

    def test_project_with_qs_data(self, tmp_path):
        audit = tmp_path / "proj-a" / ".audit"
        _write_qs(audit, {"text_quality": 8.0, "citation_quality": 7.0})
        verifier = EvolutionVerifier(tmp_path)
        snaps = verifier.collect_snapshots()
        assert len(snaps) == 1
        assert snaps[0].slug == "proj-a"
        assert snaps[0].average_score == 7.5

    def test_multiple_projects(self, tmp_path):
        for name, score in [("alpha", 7.0), ("beta", 9.0)]:
            audit = tmp_path / name / ".audit"
            _write_qs(audit, {"text_quality": score})
        verifier = EvolutionVerifier(tmp_path)
        snaps = verifier.collect_snapshots()
        assert len(snaps) == 2
        assert snaps[0].slug == "alpha"
        assert snaps[1].slug == "beta"

    def test_reads_meta_learning(self, tmp_path):
        audit = tmp_path / "proj-a" / ".audit"
        _write_qs(audit, {"text_quality": 8.0})
        _write_ml(audit, adjustments=2, lessons=5)
        verifier = EvolutionVerifier(tmp_path)
        snap = verifier.collect_snapshots()[0]
        assert len(snap.threshold_adjustments) == 2
        assert snap.lessons_count == 5

    def test_reads_hook_effectiveness(self, tmp_path):
        audit = tmp_path / "proj-a" / ".audit"
        _write_qs(audit, {"text_quality": 8.0})
        _write_he(audit, {"A1": {"trigger": 3}, "B2": {"trigger": 1}})
        verifier = EvolutionVerifier(tmp_path)
        snap = verifier.collect_snapshots()[0]
        assert "A1" in snap.hook_stats
        assert "B2" in snap.hook_stats

    def test_corrupt_yaml_skipped(self, tmp_path):
        audit = tmp_path / "proj-a" / ".audit"
        audit.mkdir(parents=True)
        (audit / "quality-scorecard.yaml").write_text("{{invalid yaml", encoding="utf-8")
        verifier = EvolutionVerifier(tmp_path)
        # Corrupt QS, no other data → no snapshot
        assert verifier.collect_snapshots() == []


class TestVerify:
    def test_no_data(self, tmp_path):
        verifier = EvolutionVerifier(tmp_path / "empty")
        report = verifier.verify()
        assert report["snapshots"] == []
        assert "No audit data" in report["summary"]

    def test_single_project_evidence(self, tmp_path):
        audit = tmp_path / "proj" / ".audit"
        _write_qs(audit, {"text_quality": 8.0, "citation_quality": 7.5})
        _write_ml(audit, adjustments=1, lessons=3)
        _write_he(
            audit,
            {
                "A1": {"trigger": 2},
                "B1": {"trigger": 1},
                "C1": {"trigger": 1},
            },
        )

        verifier = EvolutionVerifier(tmp_path)
        report = verifier.verify()

        assert len(report["snapshots"]) == 1
        assert report["cross_project"]["project_count"] == 1
        assert report["cross_project"]["global_average_score"] == 7.75

        # E1: threshold tuning
        e1 = next(e for e in report["evidence"] if e["id"] == "E1")
        assert e1["passed"] is True

        # E2: lessons
        e2 = next(e for e in report["evidence"] if e["id"] == "E2")
        assert e2["passed"] is True

        # E3: hook coverage
        e3 = next(e for e in report["evidence"] if e["id"] == "E3")
        assert e3["passed"] is True  # 3 hooks tracked

        # E4: quality measurement
        e4 = next(e for e in report["evidence"] if e["id"] == "E4")
        assert e4["passed"] is True

        # E5: cross-project (needs 2)
        e5 = next(e for e in report["evidence"] if e["id"] == "E5")
        assert e5["passed"] is False

    def test_multi_project_cross_comparison(self, tmp_path):
        for name in ["proj-a", "proj-b"]:
            audit = tmp_path / name / ".audit"
            _write_qs(audit, {"text_quality": 8.0})
            _write_he(audit, {"A1": {"trigger": 1}})

        verifier = EvolutionVerifier(tmp_path)
        report = verifier.verify()

        assert report["cross_project"]["project_count"] == 2
        e5 = next(e for e in report["evidence"] if e["id"] == "E5")
        assert e5["passed"] is True

    def test_weakest_dimension_identified(self, tmp_path):
        audit = tmp_path / "proj" / ".audit"
        _write_qs(audit, {"text_quality": 9.0, "citation_quality": 5.0})
        verifier = EvolutionVerifier(tmp_path)
        report = verifier.verify()
        assert report["cross_project"]["weakest_dimension"] == "citation_quality"
        assert report["cross_project"]["weakest_score"] == 5.0

    def test_no_adjustments_e1_fails(self, tmp_path):
        audit = tmp_path / "proj" / ".audit"
        _write_qs(audit, {"text_quality": 8.0})
        _write_ml(audit, adjustments=0, lessons=0)
        verifier = EvolutionVerifier(tmp_path)
        report = verifier.verify()
        e1 = next(e for e in report["evidence"] if e["id"] == "E1")
        assert e1["passed"] is False


class TestSaveReport:
    def test_creates_yaml_file(self, tmp_path):
        projects = tmp_path / "projects"
        audit = projects / "proj" / ".audit"
        _write_qs(audit, {"text_quality": 8.0})

        verifier = EvolutionVerifier(projects)
        report_path = verifier.save_report(tmp_path / "output")

        assert report_path.exists()
        assert report_path.name == "evolution-report.yaml"
        data = yaml.safe_load(report_path.read_text(encoding="utf-8"))
        assert "generated_at" in data
        assert len(data["snapshots"]) == 1
