"""
Pipeline Gate Validator — Hard enforcement of phase completion criteria.

Unlike SKILL.md instructions (soft constraints the LLM can ignore),
this module enforces artifact existence via code-level checks.
Each phase transition MUST pass validation before proceeding.

Architecture:
  Infrastructure layer service. Exposed as MCP tool `validate_phase_gate`.
  Agent cannot bypass — the tool returns FAIL with specific missing artifacts.

Design rationale:
  - SKILL.md = "what to do" (soft, agent may skip)
  - This module = "did you actually do it?" (hard, code-enforced)
  - Prevents premature phase transitions
  - Prevents declaring "done" without required artifacts

Usage:
    validator = PipelineGateValidator(project_dir)
    result = validator.validate_phase(7)
    # result.passed == False → cannot proceed
    # result.missing == ["review-report-1.md", "author-response-1.md", ...]
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


@dataclass
class GateCheck:
    """A single gate check item."""

    name: str
    description: str
    passed: bool
    details: str = ""
    severity: str = "CRITICAL"  # CRITICAL = blocks, WARNING = advisory


@dataclass
class GateResult:
    """Result of a phase gate validation."""

    phase: int
    phase_name: str
    passed: bool
    checks: list[GateCheck] = field(default_factory=list)
    timestamp: str = ""

    @property
    def critical_failures(self) -> list[GateCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "CRITICAL"]

    @property
    def warnings(self) -> list[GateCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "WARNING"]

    def to_markdown(self) -> str:
        """Generate a markdown report of the gate result."""
        lines = [
            f"# Phase {self.phase} Gate Validation: {'✅ PASSED' if self.passed else '❌ FAILED'}",
            f"**Phase**: {self.phase_name}",
            f"**Timestamp**: {self.timestamp}",
            "",
            "| # | Check | Status | Severity | Details |",
            "|---|-------|--------|----------|---------|",
        ]
        for i, c in enumerate(self.checks, 1):
            status = "✅" if c.passed else "❌"
            lines.append(f"| {i} | {c.name} | {status} | {c.severity} | {c.details} |")

        if self.critical_failures:
            lines.extend(
                [
                    "",
                    "## ❌ BLOCKING: Cannot proceed to next phase",
                    "",
                ]
            )
            for f in self.critical_failures:
                lines.append(f"- **{f.name}**: {f.description}")

        return "\n".join(lines)


class PipelineGateValidator:
    """
    Validate required artifacts exist before phase transitions.

    This is a HARD GATE — the agent MUST call this and receive PASS
    before proceeding. Unlike SKILL.md instructions, this is code-enforced.

    Args:
        project_dir: Path to the project directory (e.g., projects/{slug}/)
    """

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"
        self._drafts_dir = self._project_dir / "drafts"
        self._exports_dir = self._project_dir / "exports"
        self._memory_dir = self._project_dir / ".memory"

    def validate_phase(self, phase: int) -> GateResult:
        """
        Validate all required artifacts for a given phase.

        This checks that the phase's OUTPUTS exist — call this
        AFTER completing a phase, BEFORE proceeding to the next.
        For phases > 1, also validates prerequisite structure.

        Args:
            phase: Phase number (0-10, 65 for Phase 6.5)

        Returns:
            GateResult with pass/fail and specific missing items
        """
        validators = {
            0: self._validate_phase_0,
            1: self._validate_phase_1,
            2: self._validate_phase_2,
            3: self._validate_phase_3,
            4: self._validate_phase_4,
            5: self._validate_phase_5,
            6: self._validate_phase_6,
            65: self._validate_phase_6_5,
            7: self._validate_phase_7,
            8: self._validate_phase_8,
            9: self._validate_phase_9,
            10: self._validate_phase_10,
        }

        validator = validators.get(phase)
        if validator is None:
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
        checks = []

        # project.json
        pj = self._project_dir / "project.json"
        checks.append(
            GateCheck(
                name="project.json",
                description="Project configuration file",
                passed=pj.is_file(),
                details="exists"
                if pj.is_file()
                else "MISSING — run create_project or fix manually",
            )
        )

        # Required directories
        for subdir in ["drafts", "references", "data", "results", ".audit", ".memory"]:
            p = self._project_dir / subdir
            checks.append(
                GateCheck(
                    name=f"dir:{subdir}",
                    description=f"Project subdirectory {subdir}",
                    passed=p.is_dir(),
                    details="exists" if p.is_dir() else "MISSING",
                )
            )

        # concept.md (can be in root or drafts/)
        concept = self._project_dir / "concept.md"
        concept_in_drafts = self._drafts_dir / "concept.md"
        has_concept = concept.is_file() or concept_in_drafts.is_file()
        checks.append(
            GateCheck(
                name="concept.md",
                description="Research concept document",
                passed=has_concept,
                details="exists" if has_concept else "MISSING — required for writing phases",
                severity="WARNING",
            )
        )

        # Memory files
        for mem_file in ["activeContext.md", "progress.md"]:
            p = self._memory_dir / mem_file
            checks.append(
                GateCheck(
                    name=f"memory:{mem_file}",
                    description="Project memory file",
                    passed=p.is_file(),
                    details="exists" if p.is_file() else "MISSING",
                    severity="WARNING",
                )
            )

        return GateResult(
            phase=-1,
            phase_name="Project Structure",
            checks=checks,
            passed=len([c for c in checks if not c.passed and c.severity == "CRITICAL"]) == 0,
            timestamp=datetime.now().isoformat(),
        )

    def _check_prerequisites(self, phase: int) -> list[GateCheck]:
        """
        Check prerequisite artifacts for a given phase.

        Each phase depends on artifacts from earlier phases.
        Returns CRITICAL-level checks for missing prerequisites to enforce
        sequential execution — the agent cannot skip phases.

        Note: Phase 65 (Evolution Gate) is numerically 65 but logically sits
        between Phase 6 and Phase 7.  The numeric comparisons (>=) happen to be
        correct for Phase 65 in all cases except exports — ``65 >= 7`` (manuscript)
        and ``65 >= 9`` (scorecard) are both True, which is desired because
        Phase 65 comes after Phase 5 (Writing) and Phase 6 (Audit).
        Only exports uses ``== 11`` to avoid Phase 65 triggering it.
        """
        checks = []

        # Phase 2+ needs project.json
        if phase >= 2:
            pj = self._project_dir / "project.json"
            checks.append(
                GateCheck(
                    name="prereq:project.json",
                    description="Project config required",
                    passed=pj.is_file(),
                    details="exists" if pj.is_file() else "MISSING — complete Phase 0 first",
                    severity="CRITICAL",
                )
            )

        # Phase 3+ needs references
        if phase >= 3:
            refs_dir = self._project_dir / "references"
            ref_count = self._count_references(refs_dir)
            checks.append(
                GateCheck(
                    name="prereq:references",
                    description="References from Phase 2",
                    passed=ref_count >= 5,
                    details=f"{ref_count} references"
                    if ref_count > 0
                    else "No references — complete Phase 2 first",
                    severity="CRITICAL",
                )
            )

        # Phase 5+ needs concept.md
        if phase >= 5:
            concept = self._project_dir / "concept.md"
            concept_in_drafts = self._drafts_dir / "concept.md"
            has_concept = concept.is_file() or concept_in_drafts.is_file()
            checks.append(
                GateCheck(
                    name="prereq:concept.md",
                    description="Concept from Phase 3",
                    passed=has_concept,
                    details="exists" if has_concept else "MISSING — complete Phase 3 first",
                    severity="CRITICAL",
                )
            )

        # Phase 7+ needs manuscript
        if phase >= 7:
            ms = self._drafts_dir / "manuscript.md"
            checks.append(
                GateCheck(
                    name="prereq:manuscript.md",
                    description="Manuscript from Phase 5",
                    passed=ms.is_file(),
                    details="exists" if ms.is_file() else "MISSING — complete Phase 5 first",
                    severity="CRITICAL",
                )
            )

        # Phase 9+ needs .audit directory with audit artifacts
        if phase >= 9:
            scorecard = self._audit_dir / "quality-scorecard.md"
            checks.append(
                GateCheck(
                    name="prereq:quality-scorecard",
                    description="Quality scorecard from Phase 6",
                    passed=scorecard.is_file(),
                    details="exists" if scorecard.is_file() else "MISSING — complete Phase 6 first",
                    severity="CRITICAL",
                )
            )

        # Phase 11 needs exports (docx + pdf) — use == because Phase 65 (6.5)
        # is numerically > 11 but logically before Phase 9
        if phase == 11:
            export_dir = self._project_dir / "exports"
            has_docx = bool(list(export_dir.glob("*.docx"))) if export_dir.is_dir() else False
            has_pdf = bool(list(export_dir.glob("*.pdf"))) if export_dir.is_dir() else False
            checks.append(
                GateCheck(
                    name="prereq:exports",
                    description="Export files from Phase 9 (docx + pdf)",
                    passed=has_docx and has_pdf,
                    details="docx+pdf exist" if (has_docx and has_pdf) else
                            f"MISSING — {'no docx' if not has_docx else ''}"
                            f"{'no pdf' if not has_pdf else ''} — complete Phase 9 first",
                    severity="CRITICAL",
                )
            )

        return checks

    def get_pipeline_status(self) -> dict[str, Any]:
        """
        Get full pipeline status — heartbeat check.

        Returns current state across ALL phases:
        - Which phases have passed gates
        - What artifacts exist
        - What's missing
        - Completion percentage

        This is the "heartbeat" — the agent calls this to see
        remaining work. Cannot lie about completion.
        """
        phases = [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11]
        phase_names = {
            0: "Configuration",
            1: "Setup",
            2: "Literature",
            3: "Concept",
            4: "Planning",
            5: "Writing",
            6: "Audit",
            65: "Evolution Gate",
            7: "Autonomous Review",
            8: "Reference Sync",
            9: "Export",
            10: "Retrospective",
            11: "Commit & Push",
        }

        results = []
        total_critical = 0
        total_passed = 0

        for phase in phases:
            result = self.validate_phase(phase)
            critical_count = len(result.critical_failures)
            total_critical += critical_count
            if result.passed:
                total_passed += 1
            results.append(
                {
                    "phase": phase,
                    "name": phase_names.get(phase, "Unknown"),
                    "passed": result.passed,
                    "critical_failures": critical_count,
                    "warnings": len(result.warnings),
                    "details": [
                        {"check": c.name, "passed": c.passed, "details": c.details}
                        for c in result.checks
                        if not c.passed
                    ],
                }
            )

        completion_pct = (total_passed / len(phases)) * 100

        return {
            "completion_pct": round(completion_pct, 1),
            "phases_passed": total_passed,
            "phases_total": len(phases),
            "total_critical_failures": total_critical,
            "phases": results,
            "timestamp": datetime.now().isoformat(),
        }

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _count_references(refs_dir: Path) -> int:
        """Count references: PMID subdirs with metadata.json, or flat .md files."""
        if not refs_dir.is_dir():
            return 0
        # Primary: count subdirs containing metadata.json (PMID-based storage)
        count = len(list(refs_dir.glob("*/metadata.json")))
        if count > 0:
            return count
        # Fallback: count flat .md files (legacy format)
        return len(list(refs_dir.glob("*.md")))

    # ── Phase Validators ───────────────────────────────────────────

    def _validate_phase_0(self) -> GateResult:
        """Phase 0: journal-profile.yaml must exist."""
        checks = []
        jp = self._project_dir / "journal-profile.yaml"
        checks.append(
            GateCheck(
                name="journal-profile.yaml",
                description="Journal profile configuration file",
                passed=jp.is_file(),
                details=str(jp) if not jp.is_file() else "exists",
            )
        )
        return GateResult(phase=0, phase_name="Configuration", checks=checks, passed=False)

    def _validate_phase_1(self) -> GateResult:
        """Phase 1: Project directory structure must exist."""
        checks = []
        for subdir in ["drafts", "references", "data", "results", ".audit", ".memory"]:
            p = self._project_dir / subdir
            checks.append(
                GateCheck(
                    name=f"dir:{subdir}",
                    description=f"Project subdirectory {subdir}",
                    passed=p.is_dir(),
                    details="exists" if p.is_dir() else "MISSING",
                )
            )
        return GateResult(phase=1, phase_name="Setup", checks=checks, passed=False)

    def _validate_phase_2(self) -> GateResult:
        """Phase 2: ≥10 references saved."""
        checks = []
        refs_dir = self._project_dir / "references"
        ref_count = self._count_references(refs_dir)

        checks.append(
            GateCheck(
                name="references_count",
                description="At least 10 references saved",
                passed=ref_count >= 10,
                details=f"{ref_count} references found",
            )
        )

        # Audit artifacts
        for artifact in ["search-strategy.md", "reference-selection.md"]:
            p = self._audit_dir / artifact
            checks.append(
                GateCheck(
                    name=f"audit:{artifact}",
                    description="Search audit artifact",
                    passed=p.is_file(),
                    details="exists" if p.is_file() else "MISSING",
                    severity="WARNING",
                )
            )

        return GateResult(phase=2, phase_name="Literature", checks=checks, passed=False)

    def _validate_phase_3(self) -> GateResult:
        """Phase 3: concept.md exists with required sections."""
        checks = []

        concept = self._drafts_dir / "concept.md"
        if not concept.is_file():
            concept = self._project_dir / "concept.md"

        checks.append(
            GateCheck(
                name="concept.md",
                description="Concept document exists",
                passed=concept.is_file(),
                details="exists" if concept.is_file() else "MISSING",
            )
        )

        if concept.is_file():
            content = concept.read_text(encoding="utf-8")
            for marker in ["NOVELTY", "KEY SELLING POINTS"]:
                found = marker in content
                checks.append(
                    GateCheck(
                        name=f"concept:{marker}",
                        description=f"🔒 {marker} section present",
                        passed=found,
                        details="found" if found else "MISSING — protected content required",
                    )
                )

        # Audit artifact
        p = self._audit_dir / "concept-validation.md"
        checks.append(
            GateCheck(
                name="audit:concept-validation.md",
                description="Concept validation record",
                passed=p.is_file(),
                details="exists" if p.is_file() else "MISSING",
                severity="WARNING",
            )
        )

        return GateResult(phase=3, phase_name="Concept", checks=checks, passed=False)

    def _validate_phase_4(self) -> GateResult:
        """Phase 4: manuscript-plan exists."""
        checks = []

        # Check both .yaml and .md variants
        plan_yaml = self._project_dir / "manuscript-plan.yaml"
        plan_md = self._drafts_dir / "manuscript-plan.md"
        plan_exists = plan_yaml.is_file() or plan_md.is_file()

        checks.append(
            GateCheck(
                name="manuscript-plan",
                description="Manuscript plan (yaml or md)",
                passed=plan_exists,
                details="exists" if plan_exists else "MISSING",
            )
        )

        return GateResult(phase=4, phase_name="Planning", checks=checks, passed=False)

    def _validate_phase_5(self) -> GateResult:
        """Phase 5: manuscript.md exists with all required sections + data artifact provenance."""
        checks = []

        ms = self._drafts_dir / "manuscript.md"
        checks.append(
            GateCheck(
                name="manuscript.md",
                description="Manuscript draft exists",
                passed=ms.is_file(),
                details="exists" if ms.is_file() else "MISSING",
            )
        )

        if ms.is_file():
            content = ms.read_text(encoding="utf-8")
            required_sections = ["Abstract", "Introduction", "Methods", "Results", "Discussion"]
            for section in required_sections:
                found = f"## {section}" in content or f"# {section}" in content
                checks.append(
                    GateCheck(
                        name=f"section:{section}",
                        description=f"{section} section present",
                        passed=found,
                        details="found" if found else "MISSING",
                    )
                )

            # Data artifact provenance check:
            # If manuscript references Figure N or Table N, data-artifacts.yaml must exist
            import re

            has_fig_refs = bool(re.search(r"Figure\s+\d+", content, re.IGNORECASE))
            has_tbl_refs = bool(re.search(r"Table\s+\d+", content, re.IGNORECASE))
            has_stat_claims = bool(
                re.search(r"p\s*[<>=]\s*0\.\d+|statistically\s+significant", content, re.IGNORECASE)
            )

            if has_fig_refs or has_tbl_refs or has_stat_claims:
                da_yaml = self._audit_dir / "data-artifacts.yaml"
                da_has_data = False
                artifact_count = 0

                if da_yaml.is_file():
                    try:
                        data = yaml.safe_load(da_yaml.read_text(encoding="utf-8")) or {}
                        artifacts = data.get("artifacts", [])
                        artifact_count = len(artifacts)
                        da_has_data = artifact_count > 0
                    except (yaml.YAMLError, OSError):
                        pass

                checks.append(
                    GateCheck(
                        name="data-artifacts:provenance",
                        description="Data artifacts tracked with provenance (validate_data_artifacts required)",
                        passed=da_has_data,
                        details=(
                            f"{artifact_count} artifacts tracked"
                            if da_yaml.is_file()
                            else "MISSING data-artifacts.yaml — analysis tools must be used with provenance tracking"
                        ),
                    )
                )

        # Section approval check: all sections must be user-approved
        checkpoint_path = self._audit_dir / "checkpoint.json"
        if checkpoint_path.is_file():
            try:
                ckpt = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                section_progress = ckpt.get("section_progress", {})
                if section_progress:
                    unapproved = [
                        name
                        for name, data in section_progress.items()
                        if data.get("approval_status", "pending") != "approved"
                    ]
                    checks.append(
                        GateCheck(
                            name="section_approval",
                            description="All sections must be user-approved",
                            passed=len(unapproved) == 0,
                            details=(
                                "all sections approved"
                                if len(unapproved) == 0
                                else f"unapproved: {', '.join(unapproved)}"
                            ),
                        )
                    )
            except (json.JSONDecodeError, OSError):
                pass

        return GateResult(phase=5, phase_name="Writing", checks=checks, passed=False)

    def _validate_phase_6(self) -> GateResult:
        """
        Phase 6: Quality audit — scorecard + hook effectiveness + data artifacts with DATA validation.

        Beyond file existence, validates:
        - quality-scorecard.json has ≥4 dimensions scored with avg > 0
        - hook-effectiveness.json has ≥1 hook with recorded events
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

        # 2. Quality scorecard DATA validation
        qs_yaml = self._audit_dir / "quality-scorecard.yaml"
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

        checks.append(
            GateCheck(
                name="quality-scorecard:data",
                description="Quality scorecard has ≥4 dimensions scored (run_quality_audit required)",
                passed=qs_has_data,
                details=(
                    f"{qs_scored_count} dimensions scored, avg={qs_avg_score:.1f}"
                    if qs_yaml.is_file()
                    else "MISSING quality-scorecard.yaml — call run_quality_audit()"
                ),
            )
        )

        # 3. Hook effectiveness DATA validation
        he_yaml = self._audit_dir / "hook-effectiveness.yaml"
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

        checks.append(
            GateCheck(
                name="hook-effectiveness:data",
                description="Hook effectiveness has ≥1 hook with recorded events (record_hook_event required)",
                passed=he_has_data,
                details=(
                    f"{he_hook_count} hooks with events"
                    if he_yaml.is_file()
                    else "MISSING hook-effectiveness.yaml — call record_hook_event()"
                ),
            )
        )

        # 4. Data artifact validation report (if artifacts exist)
        da_yaml = self._audit_dir / "data-artifacts.yaml"
        if da_yaml.is_file():
            try:
                data = yaml.safe_load(da_yaml.read_text(encoding="utf-8")) or {}
                artifacts = data.get("artifacts", [])
                if artifacts:
                    da_report = self._audit_dir / "data-artifacts.md"
                    checks.append(
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
                    )
            except (yaml.YAMLError, OSError):
                pass

        return GateResult(phase=6, phase_name="Audit", checks=checks, passed=False)

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

    def _validate_phase_7(self) -> GateResult:
        """
        Phase 7: Autonomous Review — THE MOST CRITICAL GATE.

        Required artifacts per round:
        - review-report-{N}.md
        - author-response-{N}.md
        - equator-compliance-{N}.md (or equator-na-{N}.md for N/A cases)

        Additionally:
        - At least 1 round must be completed
        - evolution-log.jsonl must contain review_round events
        - audit-loop-review.json must exist (state machine state)
        """
        checks = []

        # 1. Check audit-loop-review.json (state machine)
        loop_state = self._audit_dir / "audit-loop-review.json"
        checks.append(
            GateCheck(
                name="audit-loop:state",
                description="Review loop state machine file exists",
                passed=loop_state.is_file(),
                details="exists"
                if loop_state.is_file()
                else "MISSING — AutonomousAuditLoop not used",
            )
        )

        # Parse loop state to find how many rounds were completed
        rounds_completed = 0
        loop_verdict = "unknown"
        max_rounds = 3
        if loop_state.is_file():
            try:
                state = json.loads(loop_state.read_text(encoding="utf-8"))
                rounds_completed = len(state.get("rounds", []))
                max_rounds = state.get("config", {}).get("max_rounds", 3)
                if state.get("rounds"):
                    loop_verdict = state["rounds"][-1].get("verdict", "unknown")
            except (json.JSONDecodeError, OSError):
                pass

        checks.append(
            GateCheck(
                name="review:rounds_completed",
                description="At least 1 review round completed",
                passed=rounds_completed >= 1,
                details=f"{rounds_completed}/{max_rounds} rounds completed, verdict={loop_verdict}",
            )
        )

        # 2. Check review artifacts for each completed round
        for i in range(1, rounds_completed + 1):
            for artifact_pattern, desc in [
                (f"review-report-{i}.md", f"Round {i} review report"),
                (f"author-response-{i}.md", f"Round {i} author response"),
            ]:
                p = self._audit_dir / artifact_pattern
                checks.append(
                    GateCheck(
                        name=f"review:{artifact_pattern}",
                        description=desc,
                        passed=p.is_file(),
                        details="exists" if p.is_file() else "MISSING",
                    )
                )

            # EQUATOR compliance (may be N/A)
            equator_p = self._audit_dir / f"equator-compliance-{i}.md"
            equator_na = self._audit_dir / f"equator-na-{i}.md"
            equator_exists = equator_p.is_file() or equator_na.is_file()
            checks.append(
                GateCheck(
                    name=f"review:equator-{i}",
                    description=f"Round {i} EQUATOR compliance report (or N/A declaration)",
                    passed=equator_exists,
                    details="exists"
                    if equator_exists
                    else "MISSING — even N/A needs a formal report file",
                )
            )

        # 3. If 0 rounds completed, flag that we need artifacts for round 1
        if rounds_completed == 0:
            for artifact in [
                "review-report-1.md",
                "author-response-1.md",
                "equator-compliance-1.md",
            ]:
                checks.append(
                    GateCheck(
                        name=f"review:{artifact}",
                        description="Round 1 artifact (not yet created)",
                        passed=False,
                        details="MISSING — review has not started",
                    )
                )

        # 4. evolution-log.jsonl must contain review_round events
        elog = self._audit_dir / "evolution-log.jsonl"
        has_review_event = False
        review_events_count = 0
        if elog.is_file():
            try:
                for line in elog.read_text(encoding="utf-8").strip().split("\n"):
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("event") == "review_round":
                            has_review_event = True
                            review_events_count += 1
            except (json.JSONDecodeError, OSError):
                pass

        checks.append(
            GateCheck(
                name="evolution-log:review_events",
                description="evolution-log.jsonl contains review_round events",
                passed=has_review_event,
                details=f"{review_events_count} review_round events"
                if has_review_event
                else "MISSING",
            )
        )

        # 5. Verify loop terminated properly (not just abandoned)
        proper_termination = loop_verdict in (
            "quality_met",
            "max_rounds",
            "stagnated",
            "user_needed",
        )
        checks.append(
            GateCheck(
                name="review:proper_termination",
                description="Review loop terminated with valid verdict",
                passed=proper_termination,
                details=f"verdict={loop_verdict}"
                if proper_termination
                else f"verdict={loop_verdict} — loop may not have run to completion",
            )
        )

        return GateResult(phase=7, phase_name="Autonomous Review", checks=checks, passed=False)

    def _validate_phase_8(self) -> GateResult:
        """Phase 8: References synced in manuscript."""
        checks = []

        ms = self._drafts_dir / "manuscript.md"
        if ms.is_file():
            content = ms.read_text(encoding="utf-8")
            has_references = "## References" in content or "# References" in content
            checks.append(
                GateCheck(
                    name="manuscript:references_section",
                    description="References section in manuscript",
                    passed=has_references,
                    details="found" if has_references else "MISSING",
                )
            )
        else:
            checks.append(
                GateCheck(
                    name="manuscript.md",
                    description="Manuscript exists for ref sync",
                    passed=False,
                    details="MISSING",
                )
            )

        return GateResult(phase=8, phase_name="Reference Sync", checks=checks, passed=False)

    def _validate_phase_9(self) -> GateResult:
        """Phase 9: Export files exist."""
        checks = []

        for ext in ["docx", "pdf"]:
            candidates = (
                list(self._exports_dir.glob(f"*.{ext}")) if self._exports_dir.is_dir() else []
            )
            checks.append(
                GateCheck(
                    name=f"export:{ext}",
                    description=f"Exported {ext.upper()} file",
                    passed=len(candidates) > 0,
                    details=f"{len(candidates)} {ext} file(s)" if candidates else "MISSING",
                    severity="WARNING",  # Export can fail due to tooling
                )
            )

        return GateResult(phase=9, phase_name="Export", checks=checks, passed=False)

    def _validate_phase_10(self) -> GateResult:
        """
        Phase 10: Retrospective — D1-D8 artifacts with DATA validation.

        Beyond file existence, validates:
        - meta-learning-audit.json has ≥1 analysis entry (run_meta_learning required)
        - evolution-log.jsonl meta_learning event has analysis counts
        - pipeline-run with D7+D8 content
        - hook-effectiveness report + data
        - .memory/ updated

        Required:
        - pipeline-run-{ts}.md (with D7+D8 sections)
        - hook-effectiveness.md (D1)
        - meta-learning-audit.json with actual analysis data
        - evolution-log.jsonl with meta_learning event
        - .memory/ updated
        """
        checks = []

        # 1. pipeline-run file
        pipeline_runs = list(self._audit_dir.glob("pipeline-run-*.md"))
        checks.append(
            GateCheck(
                name="pipeline-run.md",
                description="Pipeline run retrospective document",
                passed=len(pipeline_runs) > 0,
                details=f"{len(pipeline_runs)} run(s)" if pipeline_runs else "MISSING",
            )
        )

        # Check latest pipeline-run has D7 and D8 sections
        if pipeline_runs:
            latest = sorted(pipeline_runs)[-1]
            content = latest.read_text(encoding="utf-8")
            for section in ["D7", "D8"]:
                found = section in content
                checks.append(
                    GateCheck(
                        name=f"pipeline-run:{section}",
                        description=f"{section} retrospective section in pipeline run",
                        passed=found,
                        details="found" if found else "MISSING",
                    )
                )

        # 2. hook-effectiveness.md
        he = self._audit_dir / "hook-effectiveness.md"
        checks.append(
            GateCheck(
                name="hook-effectiveness.md",
                description="Hook effectiveness report (D1)",
                passed=he.is_file(),
                details="exists" if he.is_file() else "MISSING",
            )
        )

        # 3. evolution-log.jsonl with meta_learning event
        elog = self._audit_dir / "evolution-log.jsonl"
        has_meta = False
        if elog.is_file():
            try:
                for line in elog.read_text(encoding="utf-8").strip().split("\n"):
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("event") == "meta_learning":
                            has_meta = True
                            break
            except (json.JSONDecodeError, OSError):
                pass

        checks.append(
            GateCheck(
                name="evolution-log:meta_learning",
                description="evolution-log.jsonl contains meta_learning event (D6)",
                passed=has_meta,
                details="found" if has_meta else "MISSING",
            )
        )

        # 4. meta-learning-audit.yaml DATA validation
        mla_yaml = self._audit_dir / "meta-learning-audit.yaml"
        mla_has_data = False
        mla_details = "MISSING meta-learning-audit.yaml — call run_meta_learning()"

        if mla_yaml.is_file():
            try:
                data = yaml.safe_load(mla_yaml.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    latest_entry = data[-1]
                    has_counts = all(
                        k in latest_entry
                        for k in ("adjustments_count", "lessons_count", "suggestions_count")
                    )
                    if has_counts:
                        mla_has_data = True
                        mla_details = (
                            f"{len(data)} analysis entries, latest: "
                            f"adj={latest_entry.get('adjustments_count', 0)}, "
                            f"lessons={latest_entry.get('lessons_count', 0)}, "
                            f"suggestions={latest_entry.get('suggestions_count', 0)}"
                        )
                    else:
                        mla_details = (
                            "meta-learning-audit.yaml exists but entry missing analysis counts"
                        )
                else:
                    mla_details = "meta-learning-audit.yaml exists but empty or invalid format"
            except (yaml.YAMLError, OSError, TypeError):
                mla_details = "meta-learning-audit.yaml exists but cannot be parsed"

        checks.append(
            GateCheck(
                name="meta-learning-audit:data",
                description="Meta-learning audit has ≥1 analysis entry (run_meta_learning required)",
                passed=mla_has_data,
                details=mla_details,
            )
        )

        # 5. .memory/ files
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

        return GateResult(phase=10, phase_name="Retrospective", checks=checks, passed=False)

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
