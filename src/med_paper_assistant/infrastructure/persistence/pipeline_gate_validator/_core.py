"""PipelineGateValidator: the hard phase gate composed from per-phase mixins."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ._assets import AssetPlanMixin
from ._concept_review import ConceptReviewMixin
from ._heartbeat import HeartbeatMixin
from ._phase_audit import AuditPhasesMixin
from ._phase_concept import ConceptPhasesMixin
from ._phase_early import EarlyPhasesMixin
from ._phase_export import ExportPhasesMixin
from ._phase_final import FinalDeliveryPhaseMixin
from ._phase_fulltext import FulltextPhaseMixin
from ._phase_retrospective import RetrospectivePhaseMixin
from ._phase_review import ReviewPhaseMixin
from ._phase_writing import WritingPhaseMixin
from ._prerequisites import PrerequisitesMixin
from ._references import ReferenceChecksMixin
from ._review_completion import ReviewCompletionMixin
from ._types import GateCheck, GateResult


def _invalid_phase_result(phase: int) -> GateResult:
    return GateResult(
        phase=phase,
        phase_name="UNKNOWN",
        passed=False,
        checks=[
            GateCheck(
                name="Invalid Phase",
                description=f"Phase {phase} does not exist",
                passed=False,
            )
        ],
        timestamp=datetime.now().isoformat(),
    )


def _library_wiki_result(phase: int) -> GateResult:
    return GateResult(
        phase=phase,
        phase_name=f"Phase {phase} (Library Wiki Path)",
        passed=True,
        checks=[
            GateCheck(
                name="workflow_mode:library-wiki",
                description="Manuscript-only phase gates are not required in library-wiki mode.",
                passed=True,
                details=(
                    "Switch workflow_mode to manuscript when you want concept, drafting, "
                    "review, and export gates to apply."
                ),
            )
        ],
        timestamp=datetime.now().isoformat(),
    )


def _structure_checks(project_dir: Path, drafts_dir: Path, memory_dir: Path) -> list[GateCheck]:
    checks = []

    # project.json
    pj = project_dir / "project.json"
    checks.append(
        GateCheck(
            name="project.json",
            description="Project configuration file",
            passed=pj.is_file(),
            details="exists" if pj.is_file() else "MISSING — run create_project or fix manually",
        )
    )

    # Required directories
    for subdir in ["drafts", "references", "data", "results", ".audit", ".memory"]:
        p = project_dir / subdir
        checks.append(
            GateCheck(
                name=f"dir:{subdir}",
                description=f"Project subdirectory {subdir}",
                passed=p.is_dir(),
                details="exists" if p.is_dir() else "MISSING",
            )
        )

    checks.append(_concept_presence_check(project_dir, drafts_dir))
    checks.extend(_memory_file_checks(memory_dir))
    return checks


def _concept_presence_check(project_dir: Path, drafts_dir: Path) -> GateCheck:
    # concept.md (can be in root or drafts/)
    concept = project_dir / "concept.md"
    concept_in_drafts = drafts_dir / "concept.md"
    has_concept = concept.is_file() or concept_in_drafts.is_file()
    return GateCheck(
        name="concept.md",
        description="Research concept document",
        passed=has_concept,
        details="exists" if has_concept else "MISSING — required for writing phases",
        severity="WARNING",
    )


def _memory_file_checks(memory_dir: Path) -> list[GateCheck]:
    checks = []
    for mem_file in ["activeContext.md", "progress.md"]:
        p = memory_dir / mem_file
        checks.append(
            GateCheck(
                name=f"memory:{mem_file}",
                description="Project memory file",
                passed=p.is_file(),
                details="exists" if p.is_file() else "MISSING",
                severity="WARNING",
            )
        )
    return checks


class PipelineGateValidator(
    EarlyPhasesMixin,
    FulltextPhaseMixin,
    ConceptPhasesMixin,
    WritingPhaseMixin,
    AuditPhasesMixin,
    ReviewPhaseMixin,
    ExportPhasesMixin,
    RetrospectivePhaseMixin,
    FinalDeliveryPhaseMixin,
    PrerequisitesMixin,
    HeartbeatMixin,
    ReferenceChecksMixin,
    ConceptReviewMixin,
    ReviewCompletionMixin,
    AssetPlanMixin,
):
    """
    Validate required artifacts exist before phase transitions.

    This is a HARD GATE — the agent MUST call this and receive PASS
    before proceeding. Unlike SKILL.md instructions, this is code-enforced.

    Args:
        project_dir: Path to the project directory (e.g., projects/{slug}/)
    """

    def validate_phase(self, phase: int) -> GateResult:
        """
        Validate all required artifacts for a given phase.

        This checks that the phase's OUTPUTS exist — call this
        AFTER completing a phase, BEFORE proceeding to the next.
        For phases > 1, also validates prerequisite structure.

        Args:
            phase: Phase number (0-11, 65 for Phase 6.5)

        Returns:
            GateResult with pass/fail and specific missing items
        """
        validator = self._phase_validators().get(phase)
        if validator is None:
            return _invalid_phase_result(phase)

        workflow_mode = self._get_workflow_mode()
        if workflow_mode == "library-wiki" and self._phase_rank(phase) >= self._phase_rank(3):
            result = _library_wiki_result(phase)
            self._log_gate_result(result)
            return result

        if phase == 11:
            result = self._validate_final_delivery_with_prerequisites(validator)
        else:
            result = validator()

            # For phases > 1, prepend prerequisite structure checks
            if phase > 1:
                prereq = self._check_prerequisites(phase)
                result.checks = prereq + result.checks

        result.timestamp = datetime.now().isoformat()

        # Overall pass = all CRITICAL checks pass
        result.passed = len(result.critical_failures) == 0

        # Log result
        self._log_gate_result(result)
        return result

    def _phase_validators(self) -> dict[int, Callable[[], GateResult]]:
        return {
            0: self._validate_phase_0,
            1: self._validate_phase_1,
            2: self._validate_phase_2,
            21: self._validate_phase_2_1,
            3: self._validate_phase_3,
            4: self._validate_phase_4,
            5: self._validate_phase_5,
            6: self._validate_phase_6,
            65: self._validate_phase_6_5,
            7: self._validate_phase_7,
            8: self._validate_phase_8,
            9: self._validate_phase_9,
            10: self._validate_phase_10,
            11: self._validate_phase_11,
        }

    def _validate_final_delivery_with_prerequisites(
        self, validator: Callable[[], GateResult]
    ) -> GateResult:
        # Phase 11 may run optional Git provenance checks. Avoid doing that work
        # when earlier hard prerequisites already block the final delivery gate.
        prereq = self._check_prerequisites(11)
        if any(not c.passed and c.severity == "CRITICAL" for c in prereq):
            return GateResult(
                phase=11,
                phase_name="Final Delivery",
                passed=False,
                checks=[
                    *prereq,
                    GateCheck(
                        name="git:skipped",
                        description="Optional Git provenance checks skipped until Phase 11 prerequisites pass",
                        passed=True,
                        details="Skipped because earlier critical checks failed",
                        severity="INFO",
                    ),
                ],
            )
        result = validator()
        result.checks = prereq + result.checks
        return result

    def validate_project_structure(self) -> GateResult:
        """
        Validate project file structure — callable independently of pipeline.

        Checks:
        - Required directories (drafts, references, data, results, .audit, .memory)
        - project.json exists
        - concept.md exists (in root or drafts/)
        - .memory/activeContext.md and .memory/progress.md exist
        - .audit/ is writable

        Use this for new or existing projects to verify integrity.

        Returns:
            GateResult with structural checks
        """
        checks = _structure_checks(self._project_dir, self._drafts_dir, self._memory_dir)
        return GateResult(
            phase=-1,
            phase_name="Project Structure",
            checks=checks,
            passed=len([c for c in checks if not c.passed and c.severity == "CRITICAL"]) == 0,
            timestamp=datetime.now().isoformat(),
        )

    # ── Logging ────────────────────────────────────────────────────

    def _log_gate_result(self, result: GateResult) -> None:
        """Append gate validation result to audit log."""
        log_file = self._audit_dir / "gate-validations.jsonl"
        self._audit_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "phase": result.phase,
            "phase_name": result.phase_name,
            "passed": result.passed,
            "critical_failures": len(result.critical_failures),
            "warnings": len(result.warnings),
            "timestamp": result.timestamp,
            "checks": [
                {"name": c.name, "passed": c.passed, "severity": c.severity} for c in result.checks
            ],
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
