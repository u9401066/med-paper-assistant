"""Heartbeat snapshots for phases 6-11: cheap artifact checks without side effects."""

from __future__ import annotations

from ._base import GateBase
from ._io import UNREADABLE, read_json_value, read_text_or_empty
from ._types import GateCheck


class HeartbeatLateMixin(GateBase):
    """Heartbeat checks for audit, review, reference sync, export and delivery."""

    def _heartbeat_phase_6(self) -> list[GateCheck]:
        return [
            GateCheck(
                name=f"audit:{artifact}",
                description=f"Audit artifact: {artifact}",
                passed=(self._audit_dir / artifact).is_file(),
                details="exists" if (self._audit_dir / artifact).is_file() else "MISSING",
            )
            for artifact in ["quality-scorecard.md", "hook-effectiveness.md"]
        ]

    def _heartbeat_phase_65(self) -> list[GateCheck]:
        return [
            GateCheck(
                name="evolution-log.jsonl",
                description="Evolution log file exists",
                passed=(self._audit_dir / "evolution-log.jsonl").is_file(),
                details="exists"
                if (self._audit_dir / "evolution-log.jsonl").is_file()
                else "MISSING",
            ),
            GateCheck(
                name="quality-scorecard:exists",
                description="Quality scorecard baseline established",
                passed=(self._audit_dir / "quality-scorecard.md").is_file(),
                details="exists"
                if (self._audit_dir / "quality-scorecard.md").is_file()
                else "MISSING",
            ),
        ]

    def _heartbeat_phase_7(self) -> list[GateCheck]:
        loop_state = self._audit_dir / "audit-loop-review.json"
        checks = [
            GateCheck(
                name="audit-loop:state",
                description="Review loop state machine file exists",
                passed=loop_state.is_file(),
                details="exists" if loop_state.is_file() else "MISSING",
            )
        ]
        rounds_completed = 0
        min_rounds = 2
        loop_verdict = "unknown"
        if loop_state.is_file():
            state = read_json_value(loop_state)
            if state is not UNREADABLE:
                rounds = state.get("rounds", [])
                rounds_completed = len(rounds)
                min_rounds = state.get("config", {}).get("min_rounds", 2)
                if rounds:
                    loop_verdict = rounds[-1].get("verdict", "unknown")
        checks.append(
            GateCheck(
                name="review:rounds_completed",
                description=f"At least {min_rounds} review rounds completed",
                passed=rounds_completed >= min_rounds,
                details=f"{rounds_completed} round(s), verdict={loop_verdict}",
            )
        )
        return checks

    def _heartbeat_phase_8(self) -> list[GateCheck]:
        ms = self._drafts_dir / "manuscript.md"
        if not ms.is_file():
            return [
                GateCheck(
                    name="manuscript.md",
                    description="Manuscript exists for ref sync",
                    passed=False,
                    details="MISSING",
                )
            ]
        content = read_text_or_empty(ms)
        has_references = "## References" in content or "# References" in content
        return [
            GateCheck(
                name="manuscript:references_section",
                description="References section in manuscript",
                passed=has_references,
                details="found" if has_references else "MISSING",
            )
        ]

    def _heartbeat_phase_9(self) -> list[GateCheck]:
        checks = []
        for ext in ["docx", "pdf"]:
            candidates = (
                list(self._exports_dir.glob(f"*.{ext}")) if self._exports_dir.is_dir() else []
            )
            checks.append(
                GateCheck(
                    name=f"export:{ext}",
                    description=f"Exported {ext.upper()} file",
                    passed=bool(candidates),
                    details=f"{len(candidates)} {ext} file(s)" if candidates else "MISSING",
                )
            )
        return checks

    def _heartbeat_phase_10(self) -> list[GateCheck]:
        pipeline_runs = list(self._audit_dir.glob("pipeline-run-*.md"))
        found_candidates = self._find_pipeline_run_candidates()
        checks = [
            GateCheck(
                name="pipeline-run.md",
                description="Pipeline run retrospective document",
                passed=bool(pipeline_runs),
                details=f"{len(pipeline_runs)} run(s)"
                if pipeline_runs
                else (
                    "MISSING — need `.audit/pipeline-run-*.md`"
                    if not found_candidates
                    else "MISSING — found pipeline-run-like file(s) with wrong name/location"
                ),
                expected_pattern="pipeline-run-*.md",
                search_path=".audit/pipeline-run-*.md",
                actual_found=found_candidates,
                fix_hint="Create or rename to `.audit/pipeline-run-YYYYMMDD-HHmm.md`.",
            ),
            GateCheck(
                name="hook-effectiveness.md",
                description="Hook effectiveness report",
                passed=(self._audit_dir / "hook-effectiveness.md").is_file(),
                details="exists"
                if (self._audit_dir / "hook-effectiveness.md").is_file()
                else "MISSING",
            ),
            GateCheck(
                name="meta-learning-audit.yaml",
                description="Meta-learning audit data",
                passed=(self._audit_dir / "meta-learning-audit.yaml").is_file(),
                details="exists"
                if (self._audit_dir / "meta-learning-audit.yaml").is_file()
                else "MISSING",
            ),
        ]
        for mem_file in ["activeContext.md", "progress.md"]:
            p = self._memory_dir / mem_file
            checks.append(
                GateCheck(
                    name=f"memory:{mem_file}",
                    description=f"Project memory file {mem_file}",
                    passed=p.is_file(),
                    details="exists" if p.is_file() else "MISSING",
                    severity="WARNING",
                )
            )
        return checks

    def _heartbeat_phase_11(self) -> list[GateCheck]:
        return [
            GateCheck(
                name="git:omitted",
                description="Git provenance is omitted from heartbeat",
                passed=True,
                details="Run validate_phase(11) for optional Git provenance details",
                severity="INFO",
            )
        ]
