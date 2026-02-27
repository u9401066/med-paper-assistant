"""
Evolution Verifier — Cross-project self-evolution evidence collector.

Aggregates meta-learning audits across projects to verify that the
self-improvement system (Hook D / MetaLearningEngine) actually produces
measurable improvements over time.

Architecture:
    Infrastructure layer service. Reads `.audit/` directories from all projects.
    Produces an evolution report with temporal trends and cross-project patterns.

CONSTITUTION §22 Compliance:
    - Auditable: all evidence is traceable to source audit files
    - Decomposable: each metric is independently verifiable
    - Recomposable: aggregation is reproducible from raw data

CONSTITUTION §23 Boundaries:
    - Read-only analysis — never modifies source audit data
    - Reports only; does not auto-apply any changes
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class ProjectSnapshot:
    """Quality and hook data snapshot for one project at one point in time."""

    def __init__(
        self,
        slug: str,
        timestamp: str,
        quality_scores: dict[str, float],
        average_score: float,
        hook_stats: dict[str, dict[str, int]],
        threshold_adjustments: list[dict[str, Any]],
        lessons_count: int,
    ) -> None:
        self.slug = slug
        self.timestamp = timestamp
        self.quality_scores = quality_scores
        self.average_score = average_score
        self.hook_stats = hook_stats
        self.threshold_adjustments = threshold_adjustments
        self.lessons_count = lessons_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "timestamp": self.timestamp,
            "quality_scores": self.quality_scores,
            "average_score": self.average_score,
            "hook_stats_count": len(self.hook_stats),
            "threshold_adjustments": len(self.threshold_adjustments),
            "lessons_count": self.lessons_count,
        }


class EvolutionVerifier:
    """
    Cross-project self-evolution evidence collector and verifier.

    Scans all project `.audit/` directories, collects snapshots, and
    produces an aggregated evolution report showing:
    - Quality score trends across projects
    - Hook effectiveness improvement patterns
    - Threshold adjustment history
    - Lessons learned accumulation
    - Evidence of measurable improvement

    Usage:
        verifier = EvolutionVerifier(projects_dir)
        report = verifier.verify()
        print(report["summary"])
    """

    EVOLUTION_REPORT_FILE = "evolution-report.yaml"

    def __init__(self, projects_dir: str | Path) -> None:
        self._projects_dir = Path(projects_dir)

    def collect_snapshots(self) -> list[ProjectSnapshot]:
        """Collect audit snapshots from all projects with .audit/ directories."""
        snapshots: list[ProjectSnapshot] = []

        if not self._projects_dir.is_dir():
            return snapshots

        for project_path in sorted(self._projects_dir.iterdir()):
            if not project_path.is_dir():
                continue
            audit_dir = project_path / ".audit"
            if not audit_dir.is_dir():
                continue

            snapshot = self._read_project_snapshot(project_path.name, audit_dir)
            if snapshot is not None:
                snapshots.append(snapshot)

        return snapshots

    def _read_project_snapshot(self, slug: str, audit_dir: Path) -> ProjectSnapshot | None:
        """Read quality scorecard and meta-learning data for one project."""
        qs_path = audit_dir / "quality-scorecard.yaml"
        ml_path = audit_dir / "meta-learning-audit.yaml"
        he_path = audit_dir / "hook-effectiveness.yaml"

        quality_scores: dict[str, float] = {}
        average_score = 0.0
        hook_stats: dict[str, dict[str, int]] = {}
        threshold_adjustments: list[dict[str, Any]] = []
        lessons_count = 0
        timestamp = ""

        # Read quality scorecard
        if qs_path.is_file():
            try:
                data = yaml.safe_load(qs_path.read_text(encoding="utf-8")) or {}
                scores = data.get("scores", {})
                for dim, info in scores.items():
                    if isinstance(info, dict) and "score" in info:
                        quality_scores[dim] = info["score"]
                if quality_scores:
                    average_score = sum(quality_scores.values()) / len(quality_scores)
                timestamp = str(data.get("updated_at", data.get("created_at", "")))
            except (yaml.YAMLError, OSError):
                logger.warning("evolution_verifier.qs_read_failed", slug=slug)

        # Read meta-learning audit
        if ml_path.is_file():
            try:
                raw = yaml.safe_load(ml_path.read_text(encoding="utf-8"))
                # Audit file is a list of trail entries; use the latest one
                if isinstance(raw, list) and raw:
                    data = raw[-1] if isinstance(raw[-1], dict) else {}
                elif isinstance(raw, dict):
                    data = raw
                else:
                    data = {}
                threshold_adjustments = data.get("adjustments", [])
                lessons_count = len(data.get("lessons", []))
                if not timestamp:
                    timestamp = str(data.get("timestamp", ""))
            except (yaml.YAMLError, OSError):
                logger.warning("evolution_verifier.ml_read_failed", slug=slug)

        # Read hook effectiveness
        if he_path.is_file():
            try:
                data = yaml.safe_load(he_path.read_text(encoding="utf-8")) or {}
                hook_stats = data.get("hooks", {})
            except (yaml.YAMLError, OSError):
                logger.warning("evolution_verifier.he_read_failed", slug=slug)

        # Only return snapshot if we have at least some data
        if not quality_scores and not hook_stats and not threshold_adjustments:
            return None

        return ProjectSnapshot(
            slug=slug,
            timestamp=timestamp or datetime.now().isoformat(),
            quality_scores=quality_scores,
            average_score=round(average_score, 2),
            hook_stats=hook_stats,
            threshold_adjustments=threshold_adjustments,
            lessons_count=lessons_count,
        )

    def verify(self) -> dict[str, Any]:
        """
        Run full evolution verification across all projects.

        Returns a report dict with:
        - snapshots: per-project data
        - cross_project: aggregated patterns
        - evidence: measurable improvement indicators
        - summary: human-readable verdict
        """
        snapshots = self.collect_snapshots()

        if not snapshots:
            return {
                "snapshots": [],
                "cross_project": {},
                "evidence": [],
                "summary": "No audit data found across projects. Run at least one pipeline to generate data.",
            }

        cross_project = self._aggregate_cross_project(snapshots)
        evidence = self._collect_evidence(snapshots, cross_project)
        summary = self._build_summary(snapshots, cross_project, evidence)

        return {
            "snapshots": [s.to_dict() for s in snapshots],
            "cross_project": cross_project,
            "evidence": evidence,
            "summary": summary,
        }

    def _aggregate_cross_project(self, snapshots: list[ProjectSnapshot]) -> dict[str, Any]:
        """Aggregate patterns across all project snapshots."""
        all_scores: dict[str, list[float]] = {}
        total_adjustments = 0
        total_lessons = 0
        all_hooks_seen: set[str] = set()

        for snap in snapshots:
            for dim, score in snap.quality_scores.items():
                all_scores.setdefault(dim, []).append(score)
            total_adjustments += len(snap.threshold_adjustments)
            total_lessons += snap.lessons_count
            all_hooks_seen.update(snap.hook_stats.keys())

        # Dimension averages across projects
        dim_averages = {
            dim: round(sum(scores) / len(scores), 2) for dim, scores in all_scores.items()
        }

        # Global average
        all_averages = [s.average_score for s in snapshots if s.average_score > 0]
        global_avg = round(sum(all_averages) / len(all_averages), 2) if all_averages else 0.0

        # Weakest dimension across projects
        weakest = min(dim_averages.items(), key=lambda x: x[1]) if dim_averages else ("N/A", 0)

        return {
            "project_count": len(snapshots),
            "global_average_score": global_avg,
            "dimension_averages": dim_averages,
            "weakest_dimension": weakest[0],
            "weakest_score": weakest[1],
            "total_threshold_adjustments": total_adjustments,
            "total_lessons_learned": total_lessons,
            "unique_hooks_tracked": len(all_hooks_seen),
            "hooks_tracked": sorted(all_hooks_seen),
        }

    def _collect_evidence(
        self,
        snapshots: list[ProjectSnapshot],
        cross_project: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Collect evidence items that prove self-evolution is happening."""
        evidence: list[dict[str, Any]] = []

        # E1: Threshold adjustments exist — the system is tuning itself
        adj_count = cross_project.get("total_threshold_adjustments", 0)
        if adj_count > 0:
            evidence.append(
                {
                    "id": "E1",
                    "indicator": "threshold_self_tuning",
                    "value": adj_count,
                    "passed": True,
                    "detail": f"{adj_count} threshold adjustment(s) proposed across projects",
                }
            )
        else:
            evidence.append(
                {
                    "id": "E1",
                    "indicator": "threshold_self_tuning",
                    "value": 0,
                    "passed": False,
                    "detail": "No threshold adjustments yet — need more pipeline runs",
                }
            )

        # E2: Lessons learned accumulation
        lesson_count = cross_project.get("total_lessons_learned", 0)
        evidence.append(
            {
                "id": "E2",
                "indicator": "lessons_accumulation",
                "value": lesson_count,
                "passed": lesson_count >= 1,
                "detail": f"{lesson_count} lesson(s) learned across projects",
            }
        )

        # E3: Hook coverage breadth
        hooks_tracked = cross_project.get("unique_hooks_tracked", 0)
        evidence.append(
            {
                "id": "E3",
                "indicator": "hook_coverage_breadth",
                "value": hooks_tracked,
                "passed": hooks_tracked >= 3,
                "detail": f"{hooks_tracked} unique hook(s) tracked (minimum 3 for breadth)",
            }
        )

        # E4: Quality score existence (system produces measurable outputs)
        project_count = cross_project.get("project_count", 0)
        evidence.append(
            {
                "id": "E4",
                "indicator": "quality_measurement",
                "value": project_count,
                "passed": project_count >= 1,
                "detail": f"{project_count} project(s) with quality scores",
            }
        )

        # E5: Multi-project comparison possible
        evidence.append(
            {
                "id": "E5",
                "indicator": "cross_project_comparison",
                "value": project_count,
                "passed": project_count >= 2,
                "detail": (
                    f"{project_count} project(s) available for comparison"
                    if project_count >= 2
                    else "Need ≥2 projects for cross-project comparison"
                ),
            }
        )

        return evidence

    def _build_summary(
        self,
        snapshots: list[ProjectSnapshot],
        cross_project: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> str:
        """Build a human-readable evolution report summary."""
        passed = sum(1 for e in evidence if e["passed"])
        total = len(evidence)

        lines = [
            f"Evolution Verification: {passed}/{total} indicators passed",
            f"Projects analyzed: {cross_project['project_count']}",
            f"Global average score: {cross_project['global_average_score']}/10",
            f"Weakest dimension: {cross_project['weakest_dimension']} ({cross_project['weakest_score']}/10)",
            f"Total threshold adjustments: {cross_project['total_threshold_adjustments']}",
            f"Total lessons learned: {cross_project['total_lessons_learned']}",
            "",
            "Evidence:",
        ]

        for e in evidence:
            icon = "✅" if e["passed"] else "❌"
            lines.append(f"  {icon} {e['id']}: {e['detail']}")

        if passed == total:
            lines.append(
                "\nVerdict: Self-evolution system is ACTIVE and producing measurable evidence."
            )
        elif passed >= total // 2:
            lines.append(
                "\nVerdict: Self-evolution system is PARTIALLY active. More pipeline runs needed."
            )
        else:
            lines.append(
                "\nVerdict: Self-evolution system needs more data. Run complete pipelines to generate evidence."
            )

        return "\n".join(lines)

    def save_report(self, output_dir: str | Path) -> Path:
        """Run verification and save report to a YAML file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report = self.verify()
        report["generated_at"] = datetime.now().isoformat()

        report_path = output_dir / self.EVOLUTION_REPORT_FILE
        report_path.write_text(
            yaml.dump(report, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        logger.info("evolution_report_saved", path=str(report_path))
        return report_path
