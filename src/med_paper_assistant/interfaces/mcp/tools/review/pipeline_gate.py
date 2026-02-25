"""
Pipeline Gate Tools — Hard enforcement MCP tools.

These tools expose PipelineGateValidator as MCP tools that the agent
MUST call. Unlike SKILL.md (soft constraint), these return FAIL with
specific missing artifacts — the agent cannot bypass them.

Tools:
- validate_phase_gate: Check all required artifacts for a phase
- pipeline_heartbeat: Get full pipeline status across all phases
- start_review_round: Begin a review round (exposes AutonomousAuditLoop)
- submit_review_round: Complete a review round with scores + verdict
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager
from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
    Severity,
)
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)
from med_paper_assistant.infrastructure.persistence.workspace_state_manager import (
    get_workspace_state_manager,
)

from .._shared import (
    ensure_project_context,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)

# Phase name mapping (shared across tools)
_PHASE_NAMES = {
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
}
_ALL_PHASES = [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10]

# Module-level cache: slug → AutonomousAuditLoop instance
_active_loops: dict[str, AutonomousAuditLoop] = {}


def _get_or_create_loop(project_dir: str, config: dict | None = None) -> AutonomousAuditLoop:
    """Get existing loop or create/restore from checkpoint."""
    from pathlib import Path

    project_path = Path(project_dir)
    slug = project_path.name

    if slug in _active_loops:
        return _active_loops[slug]

    # Try to load from checkpoint
    audit_dir = project_path / ".audit"
    loop_file = audit_dir / "audit-loop-review.json"

    # Create loop config
    loop_config = AuditLoopConfig(
        max_rounds=config.get("max_rounds", 3) if config else 3,
        quality_threshold=config.get("quality_threshold", 7.0) if config else 7.0,
        stagnation_rounds=config.get("stagnation_rounds", 2) if config else 2,
        stagnation_delta=config.get("stagnation_delta", 0.3) if config else 0.3,
        context="review",
    )
    loop = AutonomousAuditLoop(str(audit_dir), config=loop_config)

    # Try to load from checkpoint
    if loop_file.is_file():
        loop.load()

    _active_loops[slug] = loop
    return loop


def _sync_to_workspace_state(
    slug: str,
    phase: int,
    gate_passed: bool,
    gate_failures: list[str] | None = None,
    next_action: str | None = None,
    current_round: int | None = None,
    review_verdict: str | None = None,
) -> None:
    """
    Auto-sync pipeline state to per-project .mdpaper-state.json.

    This is the anti-compaction defense: even if the agent's context is
    summarized, the pipeline state is persisted on disk and will be
    recovered by get_workspace_state().
    """
    try:
        wsm = get_workspace_state_manager()
        # Calculate phases passed/remaining from heartbeat
        phases_passed = []
        phases_remaining = []
        if gate_passed:
            phases_passed.append(phase)
        else:
            phases_remaining.append(phase)

        wsm.sync_pipeline_state(
            project=slug,
            current_phase=phase,
            phase_name=_PHASE_NAMES.get(phase, "Unknown"),
            gate_passed=gate_passed,
            gate_failures=gate_failures,
            next_action=next_action,
            phases_passed=phases_passed,
            phases_remaining=phases_remaining,
            current_round=current_round,
            review_verdict=review_verdict,
        )
    except Exception:
        # Non-fatal: don't let state sync failure break the gate tool
        pass  # nosec B110 - intentional: state sync is best-effort


def register_pipeline_tools(
    mcp: FastMCP,
    project_manager: ProjectManager,
):
    """Register pipeline enforcement tools with the MCP server."""

    @mcp.tool()
    def validate_phase_gate(
        phase: int,
        project: Optional[str] = None,
    ) -> str:
        """
        🚧 HARD GATE: Validate all required artifacts for a pipeline phase.

        Call this AFTER completing a phase, BEFORE proceeding to the next.
        Returns PASS only if ALL critical artifacts exist.
        Returns FAIL with specific missing items if incomplete.

        The agent MUST receive PASS before moving to the next phase.
        This is CODE-ENFORCED — cannot be bypassed.

        Phase numbers:
        - 0: Configuration (journal-profile.yaml)
        - 1: Setup (directory structure)
        - 2: Literature (≥10 refs)
        - 3: Concept (concept.md with 🔒 sections)
        - 4: Planning (manuscript plan)
        - 5: Writing (manuscript with all sections)
        - 6: Audit (scorecard + hook effectiveness)
        - 65: Evolution Gate (baseline + evolution log)
        - 7: Autonomous Review (review reports + responses per round)
        - 8: Reference Sync (references section)
        - 9: Export (docx/pdf)
        - 10: Retrospective (D1-D8 analysis)

        Args:
            phase: Phase number to validate (0-10, use 65 for Phase 6.5)
            project: Project slug (optional, uses current project)

        Returns:
            Markdown report with PASS/FAIL and specific check results
        """
        log_tool_call("validate_phase_gate", {"phase": phase, "project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = project_manager.get_project_dir(slug)

            validator = PipelineGateValidator(project_dir)
            result = validator.validate_phase(phase)

            # Auto-sync pipeline state (anti-compaction defense)
            failure_names = [c.name for c in result.critical_failures]
            next_phase = (
                _ALL_PHASES[min(_ALL_PHASES.index(phase) + 1, len(_ALL_PHASES) - 1)]
                if result.passed
                else phase
            )
            next_act = (
                f"Proceed to Phase {next_phase} ({_PHASE_NAMES.get(next_phase, '')})"
                if result.passed
                else f"Fix {len(failure_names)} failures in Phase {phase}, then re-validate"
            )
            _sync_to_workspace_state(
                slug=slug,
                phase=phase,
                gate_passed=result.passed,
                gate_failures=failure_names,
                next_action=next_act,
            )

            report = result.to_markdown()
            log_tool_result(
                "validate_phase_gate", f"Phase {phase}: {'PASSED' if result.passed else 'FAILED'}"
            )
            return report

        except Exception as e:
            log_tool_error("validate_phase_gate", e)
            return f"❌ Error validating phase gate: {e}"

    @mcp.tool()
    def pipeline_heartbeat(
        project: Optional[str] = None,
    ) -> str:
        """
        💓 Pipeline heartbeat — get full status across ALL phases.

        Returns:
        - Overall completion percentage
        - Per-phase pass/fail status
        - Specific missing artifacts for each failing phase
        - Total critical failures remaining

        Call this periodically during pipeline execution to stay on track.
        The result shows EXACTLY what remains to be done — no guessing.

        Args:
            project: Project slug (optional, uses current project)

        Returns:
            Detailed pipeline status report in markdown
        """
        log_tool_call("pipeline_heartbeat", {"project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = project_manager.get_project_dir(slug)

            validator = PipelineGateValidator(project_dir)
            status = validator.get_pipeline_status()

            # Build markdown report
            lines = [
                "# 💓 Pipeline Heartbeat",
                f"**Completion**: {status['completion_pct']}% ({status['phases_passed']}/{status['phases_total']} phases)",
                f"**Critical Failures Remaining**: {status['total_critical_failures']}",
                f"**Timestamp**: {status['timestamp']}",
                "",
                "| Phase | Name | Status | Critical | Warnings |",
                "|-------|------|--------|----------|----------|",
            ]

            for p in status["phases"]:
                status_icon = "✅" if p["passed"] else "❌"
                lines.append(
                    f"| {p['phase']} | {p['name']} | {status_icon} | {p['critical_failures']} | {p['warnings']} |"
                )

            # Add details for failing phases
            failing = [p for p in status["phases"] if not p["passed"]]
            if failing:
                lines.extend(["", "## ❌ Failing Phases — Remaining Work", ""])
                for p in failing:
                    if p["details"]:
                        lines.append(f"### Phase {p['phase']}: {p['name']}")
                        for d in p["details"]:
                            lines.append(f"- **{d['check']}**: {d['details']}")
                        lines.append("")

            report = "\n".join(lines)

            # Auto-sync pipeline state from heartbeat (anti-compaction)
            failing = [p for p in status["phases"] if not p["passed"]]
            current_phase = failing[0]["phase"] if failing else 10
            _sync_to_workspace_state(
                slug=slug,
                phase=current_phase,
                gate_passed=not failing,
                gate_failures=[f"Phase {p['phase']}" for p in failing[:5]],
                next_action=(
                    f"Complete Phase {current_phase} ({_PHASE_NAMES.get(current_phase, '')})"
                    if failing
                    else "Pipeline complete! Run validate_phase_gate(10) for final check."
                ),
            )

            log_tool_result("pipeline_heartbeat", f"{status['completion_pct']}% complete")
            return report

        except Exception as e:
            log_tool_error("pipeline_heartbeat", e)
            return f"❌ Error getting pipeline heartbeat: {e}"

    @mcp.tool()
    def start_review_round(
        project: Optional[str] = None,
        max_rounds: int = 3,
        quality_threshold: float = 7.0,
    ) -> str:
        """
        🔄 Start a new review round (Phase 7 state machine).

        This exposes the AutonomousAuditLoop as an MCP tool.
        The agent MUST call this to begin each review round.
        Cannot skip rounds or fake completion.

        Workflow for Phase 7:
        1. Call start_review_round() → get round context
        2. Perform the actual review (read manuscript, check issues)
        3. Write review-report-{N}.md and author-response-{N}.md
        4. Call submit_review_round() with scores → get verdict
        5. If verdict is CONTINUE → go to step 1
        6. If verdict is QUALITY_MET/MAX_ROUNDS/STAGNATED → Phase 7 done

        Args:
            project: Project slug (optional, uses current project)
            max_rounds: Maximum review rounds (default: 3)
            quality_threshold: Minimum quality score to pass (default: 7.0)

        Returns:
            Round context with round number, previous issues, and score trends
        """
        log_tool_call("start_review_round", {"project": project, "max_rounds": max_rounds})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = project_manager.get_project_dir(slug)

            loop = _get_or_create_loop(
                project_dir,
                config={"max_rounds": max_rounds, "quality_threshold": quality_threshold},
            )

            context = loop.start_round()
            round_num = context.get("round", 1)

            # Save state immediately
            loop.save()

            # Auto-sync pipeline state (anti-compaction)
            _sync_to_workspace_state(
                slug=slug,
                phase=7,
                gate_passed=False,  # Round started = not yet passed
                next_action=f"Complete review round {round_num}: write review-report-{round_num}.md, author-response-{round_num}.md, then call submit_review_round()",
                current_round=round_num,
            )

            lines = [
                f"# 🔄 Review Round {round_num} Started",
                "",
                f"**Max Rounds**: {max_rounds}",
                f"**Quality Threshold**: {quality_threshold}",
                "",
                "## Your Tasks This Round",
                "",
                "1. Read the manuscript carefully",
                "2. Review from 4 perspectives: methodology, domain, statistics, editor",
                f"3. Write `.audit/review-report-{round_num}.md` with YAML front matter",
                f"4. Write `.audit/author-response-{round_num}.md` (ACCEPT/DECLINE each issue)",
                f"5. Write `.audit/equator-compliance-{round_num}.md` (or equator-na-{round_num}.md)",
                "6. Apply fixes to the manuscript",
                "7. Call `submit_review_round()` with updated quality scores",
                "",
            ]

            if context.get("previous_issues"):
                lines.extend(
                    [
                        "## Unresolved Issues from Previous Rounds",
                        "",
                    ]
                )
                for issue in context.get("previous_issues", []):
                    lines.append(
                        f"- [{issue.get('severity', 'MEDIUM')}] {issue.get('description', 'N/A')}"
                    )
                lines.append("")

            if context.get("score_trend"):
                lines.extend(
                    [
                        "## Score Trend",
                        "",
                        "| Dimension | Previous |",
                        "|-----------|----------|",
                    ]
                )
                for dim, scores in context.get("score_trend", {}).items():
                    prev = scores[-1] if scores else "N/A"
                    lines.append(f"| {dim} | {prev} |")

            report = "\n".join(lines)
            log_tool_result("start_review_round", f"Round {round_num} started")
            return report

        except Exception as e:
            log_tool_error("start_review_round", e)
            return f"❌ Error starting review round: {e}"

    @mcp.tool()
    def submit_review_round(
        scores: str,
        issues_found: int = 0,
        issues_fixed: int = 0,
        project: Optional[str] = None,
    ) -> str:
        """
        ✅ Submit a completed review round with quality scores.

        Call this AFTER writing review-report and author-response files.
        Returns the verdict: CONTINUE, QUALITY_MET, MAX_ROUNDS, or STAGNATED.

        Args:
            scores: JSON string of dimension scores, e.g.:
                    '{"citation_quality": 8, "methodology_reproducibility": 7,
                      "text_quality": 8, "concept_consistency": 9,
                      "format_compliance": 8, "figure_table_quality": 7}'
            issues_found: Number of issues found this round
            issues_fixed: Number of issues fixed this round
            project: Project slug (optional, uses current project)

        Returns:
            Verdict and next steps
        """
        log_tool_call("submit_review_round", {"scores": scores, "issues_found": issues_found})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = project_manager.get_project_dir(slug)

            loop = _get_or_create_loop(project_dir)

            # Parse scores
            try:
                score_dict = json.loads(scores)
            except json.JSONDecodeError:
                return '❌ Invalid scores JSON. Expected format: {"citation_quality": 8, ...}'

            # Record issues and fixes (simplified — agent already wrote the files)
            for i in range(issues_found):
                loop.record_issue(
                    hook_id="review_round",
                    severity=Severity.MEDIUM,
                    description=f"Issue {i + 1} from review round",
                    suggested_fix="See author response for details",
                )
            for i in range(min(issues_fixed, issues_found)):
                loop.record_fix(
                    issue_index=i,
                    strategy="author_revision",
                    success=True,
                )

            # Complete the round
            verdict = loop.complete_round(score_dict)

            # Save state
            loop.save()

            # Log to evolution log
            _log_review_round_to_evolution(project_dir, loop, score_dict, verdict.value)

            # Get status for both sync and response
            status = loop.get_status()

            # Auto-sync pipeline state (anti-compaction)
            is_done = verdict.value in ("quality_met", "max_rounds", "stagnated", "user_needed")
            next_act = (
                "Phase 7 complete. Run validate_phase_gate(7), then proceed to Phase 8."
                if is_done
                else f"Start review round {status['current_round'] + 1} with start_review_round()"
            )
            _sync_to_workspace_state(
                slug=slug,
                phase=7,
                gate_passed=is_done,
                next_action=next_act,
                current_round=status["current_round"],
                review_verdict=verdict.value,
            )

            # Build response
            verdict_actions = {
                "continue": "🔄 **CONTINUE** — Start next round with `start_review_round()`",
                "quality_met": "🎉 **QUALITY_MET** — Quality threshold reached! Proceed to Phase 8.",
                "max_rounds": "⚠️ **MAX_ROUNDS** — Maximum rounds reached. Proceed to Phase 8 with current quality.",
                "stagnated": "⚠️ **STAGNATED** — No improvement detected. Consider user intervention or proceed.",
                "user_needed": "🛑 **USER_NEEDED** — Critical unresolved issues. Escalate to user.",
            }
            lines = [
                f"# Review Round {status['current_round']} Complete",
                "",
                verdict_actions.get(verdict.value, f"Unknown verdict: {verdict.value}"),
                "",
                f"**Rounds Completed**: {status['current_round']}/{status['max_rounds']}",
                f"**Weighted Score**: {status.get('latest_weighted_score', 'N/A')}",
                "",
                "## Scores This Round",
                "",
                "| Dimension | Score |",
                "|-----------|-------|",
            ]
            for dim, score in score_dict.items():
                lines.append(f"| {dim} | {score} |")

            report = "\n".join(lines)
            log_tool_result("submit_review_round", f"verdict={verdict.value}")
            return report

        except Exception as e:
            log_tool_error("submit_review_round", e)
            return f"❌ Error submitting review round: {e}"

    @mcp.tool()
    def validate_project_structure(
        project: Optional[str] = None,
    ) -> str:
        """
        🏗️ Validate project file structure integrity.

        Checks required directories, config files, and memory files.
        Works for both new and existing projects.
        Call this after create_project or when resuming work on an existing project.

        Args:
            project: Project slug (optional, uses current project)

        Returns:
            Markdown report of structural checks
        """
        log_tool_call("validate_project_structure", {"project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = project_manager.get_project_dir(slug)

            validator = PipelineGateValidator(project_dir)
            result = validator.validate_project_structure()

            report = result.to_markdown()
            log_tool_result(
                "validate_project_structure", f"{'PASSED' if result.passed else 'FAILED'}"
            )
            return report

        except Exception as e:
            log_tool_error("validate_project_structure", e)
            return f"❌ Error validating project structure: {e}"

    return {
        "validate_phase_gate": validate_phase_gate,
        "pipeline_heartbeat": pipeline_heartbeat,
        "start_review_round": start_review_round,
        "submit_review_round": submit_review_round,
        "validate_project_structure": validate_project_structure,
    }


def _log_review_round_to_evolution(
    project_dir, loop: AutonomousAuditLoop, scores: dict, verdict: str
) -> None:
    """Append review_round event to evolution-log.jsonl."""
    from datetime import datetime
    from pathlib import Path

    elog = Path(project_dir) / ".audit" / "evolution-log.jsonl"
    status = loop.get_status()

    entry = {
        "event": "review_round",
        "round": status["current_round"],
        "verdict": verdict,
        "scores": scores,
        "weighted_score": status.get("latest_weighted_score"),
        "timestamp": datetime.now().isoformat(),
    }

    try:
        elog.parent.mkdir(parents=True, exist_ok=True)
        with open(elog, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


__all__ = ["register_pipeline_tools"]
