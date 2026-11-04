"""Phase 6 and 6.5 gates: quality audit and evolution baseline."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker

from ._base import GateBase
from ._types import GateCheck, GateResult


def _scorecard_stats(qs_yaml: Path) -> tuple[bool, int, float]:
    qs_has_data = False
    qs_scored_count = 0
    qs_avg_score = 0.0

    if qs_yaml.is_file():
        try:
            data = yaml.safe_load(qs_yaml.read_text(encoding="utf-8")) or {}
            scores = data.get("scores", {})
            scored = {k: v["score"] for k, v in scores.items() if "score" in v}
            qs_scored_count = len(scored)
            qs_avg_score = sum(scored.values()) / len(scored) if scored else 0.0
            qs_has_data = qs_scored_count >= 4 and qs_avg_score > 0
        except (yaml.YAMLError, OSError, KeyError, TypeError):
            pass
    return qs_has_data, qs_scored_count, qs_avg_score


def _hook_effectiveness_stats(he_yaml: Path) -> tuple[bool, int]:
    he_has_data = False
    he_hook_count = 0

    if he_yaml.is_file():
        try:
            data = yaml.safe_load(he_yaml.read_text(encoding="utf-8")) or {}
            hooks = data.get("hooks", {})
            # Count hooks with at least one event
            he_hook_count = sum(
                1
                for h in hooks.values()
                if any(h.get(et, 0) > 0 for et in ("trigger", "pass", "fix", "false_positive"))
            )
            he_has_data = he_hook_count >= 1
        except (yaml.YAMLError, OSError, KeyError, TypeError):
            pass
    return he_has_data, he_hook_count


def _has_baseline_event(elog: Path) -> bool:
    has_baseline = False
    try:
        for line in elog.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                entry = json.loads(line)
                if entry.get("event") == "baseline":
                    has_baseline = True
                    break
    except (json.JSONDecodeError, OSError):
        pass
    return has_baseline


class AuditPhasesMixin(GateBase):
    """Validation of Phase 6 (quality audit) and Phase 6.5 (evolution gate)."""

    def _validate_phase_6(self) -> GateResult:
        """
        Phase 6: Quality audit — scorecard + hook effectiveness + data artifacts with DATA validation.

        Beyond file existence, validates:
        - quality-scorecard.yaml has ≥4 dimensions scored with avg > 0
        - hook-effectiveness.yaml has ≥1 hook with recorded events
        - data-artifacts.yaml validation report generated (if artifacts exist)
        - Report files (.md) are generated
        """
        checks = []

        # 1. Report files exist
        for artifact in ["quality-scorecard.md", "hook-effectiveness.md"]:
            p = self._audit_dir / artifact
            checks.append(
                GateCheck(
                    name=f"audit:{artifact}",
                    description=f"Audit artifact: {artifact}",
                    passed=p.is_file(),
                    details="exists" if p.is_file() else "MISSING",
                )
            )

        checks.append(self._scorecard_data_check())
        checks.append(self._hook_effectiveness_data_check())
        checks.extend(self._data_artifact_report_checks())

        return GateResult(phase=6, phase_name="Audit", checks=checks, passed=False)

    def _scorecard_data_check(self) -> GateCheck:
        qs_yaml = self._audit_dir / "quality-scorecard.yaml"
        qs_has_data, qs_scored_count, qs_avg_score = _scorecard_stats(qs_yaml)
        return GateCheck(
            name="quality-scorecard:data",
            description="Quality scorecard has ≥4 dimensions scored (run_quality_audit required)",
            passed=qs_has_data,
            details=(
                f"{qs_scored_count} dimensions scored, avg={qs_avg_score:.1f}"
                if qs_yaml.is_file()
                else "MISSING quality-scorecard.yaml — call run_quality_audit()"
            ),
        )

    def _hook_effectiveness_data_check(self) -> GateCheck:
        he_yaml = self._audit_dir / "hook-effectiveness.yaml"
        he_has_data, he_hook_count = _hook_effectiveness_stats(he_yaml)
        return GateCheck(
            name="hook-effectiveness:data",
            description="Hook effectiveness has ≥1 hook with recorded events (record_hook_event required)",
            passed=he_has_data,
            details=(
                f"{he_hook_count} hooks with events"
                if he_yaml.is_file()
                else "MISSING hook-effectiveness.yaml — call record_hook_event()"
            ),
        )

    def _data_artifact_report_checks(self) -> list[GateCheck]:
        tracker = DataArtifactTracker(self._audit_dir, self._project_dir)
        artifacts = tracker.get_artifacts()
        if not artifacts:
            return []

        da_report = self._audit_dir / "data-artifacts.md"
        return [
            GateCheck(
                name="data-artifacts:report",
                description="Data artifact validation report (validate_data_artifacts required)",
                passed=da_report.is_file(),
                details=(
                    "exists"
                    if da_report.is_file()
                    else f"MISSING — {len(artifacts)} artifacts tracked but validate_data_artifacts() not called"
                ),
            )
        ]

    def _validate_phase_6_5(self) -> GateResult:
        """Phase 6.5: Evolution Gate — baseline + evolution-log."""
        checks = []

        # evolution-log.jsonl must exist and contain baseline event
        elog = self._audit_dir / "evolution-log.jsonl"
        checks.append(
            GateCheck(
                name="evolution-log.jsonl",
                description="Evolution log file exists",
                passed=elog.is_file(),
                details="exists" if elog.is_file() else "MISSING",
            )
        )

        if elog.is_file():
            has_baseline = _has_baseline_event(elog)
            checks.append(
                GateCheck(
                    name="evolution-log:baseline",
                    description='evolution-log.jsonl contains {"event": "baseline"} entry',
                    passed=has_baseline,
                    details="baseline found"
                    if has_baseline
                    else 'MISSING {"event": "baseline"} entry',
                )
            )

        # quality-scorecard.md must have Round 0 scores
        qs = self._audit_dir / "quality-scorecard.md"
        checks.append(
            GateCheck(
                name="quality-scorecard:exists",
                description="Quality scorecard baseline established",
                passed=qs.is_file(),
                details="exists" if qs.is_file() else "MISSING",
            )
        )

        return GateResult(phase=65, phase_name="Evolution Gate", checks=checks, passed=False)
