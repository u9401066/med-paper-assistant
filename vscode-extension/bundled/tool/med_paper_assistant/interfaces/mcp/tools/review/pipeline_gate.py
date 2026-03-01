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
- request_section_rewrite: Regress from Phase 7 to Phase 5 for section rewrite
- pause_pipeline: Pause pipeline for user manual editing
- resume_pipeline: Resume pipeline after pause, detecting user edits
- approve_section: Approve or request revision for a written section
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

import structlog
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager
from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
    RoundVerdict,
    Severity,
)
from med_paper_assistant.infrastructure.persistence.checkpoint_manager import (
    CheckpointManager,
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

from datetime import datetime

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
    11: "Commit & Push",
}
_ALL_PHASES = [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11]

# Module-level cache: slug → AutonomousAuditLoop instance
_active_loops: dict[str, AutonomousAuditLoop] = {}


def _get_or_create_loop(project_dir: str | Path, config: dict | None = None) -> AutonomousAuditLoop:
    """Get existing loop or create/restore from checkpoint."""

    project_path = Path(project_dir)
    slug = project_path.name

    audit_dir = project_path / ".audit"
    loop_file = audit_dir / "audit-loop-review.json"

    # If cached loop is completed and checkpoint file is gone, evict stale cache
    if slug in _active_loops:
        cached = _active_loops[slug]
        if cached.is_completed and not loop_file.is_file():
            del _active_loops[slug]
        else:
            return cached

    # Create loop config
    loop_config = AuditLoopConfig(
        max_rounds=config.get("max_rounds", 3) if config else 3,
        min_rounds=config.get("min_rounds", 2) if config else 2,
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
        # Read existing state to merge phases cumulatively
        existing_state = wsm.get_state()
        existing_pipeline = existing_state.get("pipeline_state", {})
        existing_passed = set(existing_pipeline.get("phases_passed", []))
        existing_remaining = set(existing_pipeline.get("phases_remaining", []))

        # Update cumulatively
        if gate_passed:
            existing_passed.add(phase)
            existing_remaining.discard(phase)
        else:
            existing_remaining.add(phase)

        wsm.sync_pipeline_state(
            project=slug,
            current_phase=phase,
            phase_name=_PHASE_NAMES.get(phase, "Unknown"),
            gate_passed=gate_passed,
            gate_failures=gate_failures,
            next_action=next_action,
            phases_passed=sorted(existing_passed),
            phases_remaining=sorted(existing_remaining),
            current_round=current_round,
            review_verdict=review_verdict,
        )
    except Exception:
        # Non-fatal: don't let state sync failure break the gate tool
        structlog.get_logger().debug("State sync failed (best-effort)", exc_info=True)  # nosec B110


def _compute_manuscript_hash(project_dir: str | Path) -> str:
    """Compute SHA-256 hash of the manuscript file for change detection."""
    manuscript = Path(project_dir) / "drafts" / "manuscript.md"
    if not manuscript.is_file():
        return ""
    content = manuscript.read_bytes()
    return hashlib.sha256(content).hexdigest()


def _write_pipeline_completed(project_dir: Path, slug: str) -> None:
    """Write pipeline-completed.json marker when Phase 11 gate passes."""
    audit_dir = project_dir / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    marker = {
        "project": slug,
        "status": "COMPLETED",
        "completed_at": datetime.now().isoformat(),
        "phases_completed": [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11],
    }
    marker_path = audit_dir / "pipeline-completed.json"
    marker_path.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")
    structlog.get_logger().info("Pipeline completed", project=slug, marker=str(marker_path))


def _count_review_report_issues(audit_dir: Path, round_num: int) -> dict[str, int]:
    """Parse review-report YAML frontmatter to count reported issues."""
    report_path = audit_dir / f"review-report-{round_num}.md"
    if not report_path.is_file():
        return {"major": 0, "minor": 0, "optional": 0}
    content = report_path.read_text(encoding="utf-8")
    # Parse YAML frontmatter totals
    counts: dict[str, int] = {"major": 0, "minor": 0, "optional": 0}
    for key in counts:
        match = re.search(rf"^\s*{key}:\s*(\d+)", content, re.MULTILINE)
        if match:
            counts[key] = int(match.group(1))
    return counts


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
            project_dir = Path(project_info["project_path"])

            validator = PipelineGateValidator(project_dir)
            result = validator.validate_phase(phase)

            # Write pipeline-completed marker when Phase 11 passes
            if phase == 11 and result.passed:
                _write_pipeline_completed(project_dir, slug)

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
            project_dir = Path(project_info["project_path"])

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
        min_rounds: int = 2,
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
            min_rounds: Minimum review rounds before QUALITY_MET allowed (default: 2)
            quality_threshold: Minimum quality score to pass (default: 7.0)

        Returns:
            Round context with round number, previous issues, and score trends
        """
        log_tool_call(
            "start_review_round",
            {"project": project, "max_rounds": max_rounds, "min_rounds": min_rounds},
        )
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])

            loop = _get_or_create_loop(
                project_dir,
                config={
                    "max_rounds": max_rounds,
                    "min_rounds": min_rounds,
                    "quality_threshold": quality_threshold,
                },
            )

            # Compute manuscript hash BEFORE the round starts
            ms_hash = _compute_manuscript_hash(project_dir)

            context = loop.start_round(artifact_hash=ms_hash)
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
                f"**Min Rounds**: {min_rounds} (mandatory before QUALITY_MET)",
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
                "6. **MANDATORY**: Apply fixes to the manuscript using `patch_draft()`",
                "   - Even if no structural issues, MUST strengthen narrative (tighten prose, improve transitions)",
                "   - Manuscript MUST be modified — hash is checked at submit time",
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

        Call this AFTER writing review-report and author-response files,
        AND after applying fixes to the manuscript.

        ENFORCEMENT:
        - review-report-{N}.md MUST exist
        - author-response-{N}.md MUST exist
        - Manuscript MUST have been modified (hash comparison)
        - issues_found MUST be > 0 (a real review always finds something)

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
            project_dir = Path(project_info["project_path"])

            loop = _get_or_create_loop(project_dir)
            audit_dir = project_dir / ".audit"

            # ── Enforcement: Artifact verification ──
            round_num = loop.current_round_number
            enforcement_failures: list[str] = []

            # Check review-report exists
            review_report = audit_dir / f"review-report-{round_num}.md"
            if not review_report.is_file():
                enforcement_failures.append(
                    f"❌ Missing `.audit/review-report-{round_num}.md` — "
                    "write the review report before submitting"
                )

            # Check author-response exists
            author_response = audit_dir / f"author-response-{round_num}.md"
            if not author_response.is_file():
                enforcement_failures.append(
                    f"❌ Missing `.audit/author-response-{round_num}.md` — "
                    "write the author response before submitting"
                )

            # Check manuscript was actually modified (hash comparison)
            current_hash = _compute_manuscript_hash(project_dir)
            start_hash = getattr(loop, "_artifact_hash_start", "")
            # Also check round records for start hash
            if not start_hash and loop._rounds:
                # Fallback: recover from last completed round's end hash
                last_round = loop._rounds[-1]
                if last_round.artifact_hash_end:
                    start_hash = last_round.artifact_hash_end

            if start_hash and current_hash and start_hash == current_hash:
                enforcement_failures.append(
                    "❌ Manuscript NOT modified — hash unchanged since round start. "
                    "A review MUST produce actual changes (use `patch_draft()` to apply fixes). "
                    "Even if no structural issues exist, strengthen narrative, tighten prose, "
                    "or improve transitions."
                )

            # Check issues_found is realistic
            if issues_found == 0:
                # Cross-check with review-report if it exists
                if review_report.is_file():
                    report_counts = _count_review_report_issues(audit_dir, round_num)
                    total_in_report = sum(report_counts.values())
                    if total_in_report > 0:
                        enforcement_failures.append(
                            f"❌ issues_found=0 but review-report-{round_num}.md contains "
                            f"{total_in_report} issues ({report_counts}). "
                            f"Set issues_found={total_in_report} and fix the accepted ones."
                        )
                else:
                    enforcement_failures.append(
                        "⚠️ issues_found=0 is suspicious — a thorough review almost always "
                        "finds at least narrative improvements. Ensure you reviewed carefully."
                    )

            # ── R-series: Content-quality enforcement (Code-Enforced) ──
            from med_paper_assistant.infrastructure.persistence.review_hooks import (
                ReviewHooksEngine,
            )

            review_engine = ReviewHooksEngine(project_dir)
            manuscript_content = ""
            draft_dir = project_dir / "drafts"
            if draft_dir.is_dir():
                manuscript_path = draft_dir / "manuscript.md"
                if manuscript_path.is_file():
                    try:
                        manuscript_content = manuscript_path.read_text(encoding="utf-8")
                    except OSError:
                        pass
                else:
                    # Fallback: pick the largest .md file
                    for md_file in sorted(
                        draft_dir.glob("*.md"),
                        key=lambda p: p.stat().st_size,
                        reverse=True,
                    ):
                        try:
                            manuscript_content = md_file.read_text(encoding="utf-8")
                            break
                        except OSError:
                            pass

            # Determine actual manuscript modification status
            if start_hash and current_hash:
                manuscript_modified = start_hash != current_hash
                mod_label = "✅ (hash changed)" if manuscript_modified else "❌ (hash unchanged)"
            else:
                manuscript_modified = True  # assume modified if hashes unavailable
                mod_label = "⚠️ (hash unavailable — assumed modified)"

            r_results = review_engine.run_all(
                round_num=round_num,
                issues_fixed=issues_fixed,
                manuscript_changed=manuscript_modified,
                manuscript_content=manuscript_content,
            )

            r_warnings: list[str] = []
            for hook_id, result in r_results.items():
                if not result.passed:
                    for issue in result.issues:
                        if issue.severity == "CRITICAL":
                            enforcement_failures.append(
                                f"❌ [{hook_id}] {issue.message}"
                                + (f" — {issue.suggestion}" if issue.suggestion else "")
                            )
                        elif issue.severity == "WARNING":
                            r_warnings.append(
                                f"⚠️ [{hook_id}] {issue.message}"
                                + (f" — {issue.suggestion}" if issue.suggestion else "")
                            )
                else:
                    # Even passing hooks may have warnings
                    for issue in result.issues:
                        if issue.severity == "WARNING":
                            r_warnings.append(
                                f"⚠️ [{hook_id}] {issue.message}"
                                + (f" — {issue.suggestion}" if issue.suggestion else "")
                            )

            # If enforcement failures, REJECT the submission
            if enforcement_failures:
                failure_lines = [
                    f"# 🚫 Review Round {round_num} Submission REJECTED\n",
                    "The following enforcement checks failed:\n",
                    *[f"- {f}" for f in enforcement_failures],
                ]
                if r_warnings:
                    failure_lines.extend([
                        "\n## Warnings (address if possible)\n",
                        *[f"- {w}" for w in r_warnings],
                    ])
                failure_lines.append("\nFix these issues and call `submit_review_round()` again.")
                failure_report = "\n".join(failure_lines)
                log_tool_result("submit_review_round", "REJECTED: enforcement failures")
                return failure_report

            # ── Enforcement passed — proceed with normal submission ──

            # Parse scores
            try:
                score_dict = json.loads(scores)
            except json.JSONDecodeError:
                return '❌ Invalid scores JSON. Expected format: {"citation_quality": 8, ...}'

            # Record issues and fixes
            for i in range(issues_found):
                loop.record_issue(
                    hook_id="review_round",
                    severity=Severity.MAJOR,
                    description=f"Issue {i + 1} from review round",
                    suggested_fix="See author response for details",
                )
            for i in range(min(issues_fixed, issues_found)):
                loop.record_fix(
                    issue_index=i,
                    strategy="author_revision",
                    success=True,
                )

            # Complete the round with manuscript hash
            verdict = loop.complete_round(score_dict, artifact_hash=current_hash)

            # Save state
            loop.save()

            # Log to evolution log
            _log_review_round_to_evolution(project_dir, loop, score_dict, verdict.value)

            # Get status for both sync and response
            status = loop.get_status()

            # Auto-sync pipeline state (anti-compaction)
            is_done = verdict.value in (
                "quality_met",
                "max_rounds",
                "stagnated",
                "user_needed",
                "rewrite_needed",
            )
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
                "rewrite_needed": "🔁 **REWRITE_NEEDED** — Section(s) need major rewrite. Call `request_section_rewrite()` to regress to Phase 5.",
            }
            lines = [
                f"# Review Round {status['current_round']} Complete",
                "",
                verdict_actions.get(verdict.value, f"Unknown verdict: {verdict.value}"),
                "",
                f"**Rounds Completed**: {status['current_round']}/{status['max_rounds']}",
                f"**Weighted Score**: {status.get('latest_weighted_score', 'N/A')}",
                "**Manuscript Modified**: " + mod_label,
                "",
                "## Scores This Round",
                "",
                "| Dimension | Score |",
                "|-----------|-------|",
            ]
            for dim, score in score_dict.items():
                lines.append(f"| {dim} | {score} |")

            # Append R-hook summary
            lines.extend(["", "## Review Hook Results (R-series)", ""])
            for hook_id, result in r_results.items():
                status_icon = "✅" if result.passed else "❌"
                lines.append(f"- {status_icon} **{hook_id}**: {'PASS' if result.passed else 'FAIL'}")

            if r_warnings:
                lines.extend(["", "## Warnings", ""])
                for w in r_warnings:
                    lines.append(f"- {w}")

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
            project_dir = Path(project_info["project_path"])

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

    # ── New Flexibility Tools ─────────────────────────────────────

    @mcp.tool()
    def request_section_rewrite(
        sections: str,
        reason: str,
        project: Optional[str] = None,
    ) -> str:
        """
        🔁 Request a pipeline regression from Phase 7 to Phase 5 for section rewrite.

        When review discovers that a section needs a fundamental rewrite (not just
        patching), call this to regress the pipeline back to Phase 5. Only the
        specified sections will be rewritten; other approved sections are preserved.

        ENFORCEMENT:
        - Only callable during Phase 7 (review phase)
        - Maximum 2 regressions per pipeline run (prevent infinite loops)
        - Creates a pre-regression snapshot of all drafts

        After calling this:
        1. Rewrite the specified sections using write_draft/draft_section
        2. Run Hook A/B on rewritten sections
        3. Call approve_section() for each rewritten section
        4. Proceed through Phase 6 → Phase 7 again

        Args:
            sections: Comma-separated section names to rewrite (e.g., "Methods,Results")
            reason: Why these sections need rewriting
            project: Project slug (optional, uses current project)

        Returns:
            Regression confirmation with instructions
        """
        log_tool_call("request_section_rewrite", {"sections": sections, "reason": reason})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            section_list = [s.strip() for s in sections.split(",") if s.strip()]
            if not section_list:
                return "❌ Must specify at least one section to rewrite."

            # Verify sections exist in manuscript
            manuscript = project_dir / "drafts" / "manuscript.md"
            if manuscript.is_file():
                content = manuscript.read_text(encoding="utf-8")
                missing = [
                    s for s in section_list if f"## {s}" not in content and f"# {s}" not in content
                ]
                if missing:
                    return f"❌ Sections not found in manuscript: {', '.join(missing)}"

            # Check regression count limit
            ckpt = CheckpointManager(audit_dir, project_dir=project_dir)
            state = ckpt.load() or {}
            regression_ctx = state.get("regression_context", {})
            regression_count = regression_ctx.get("regression_count", 0)
            if regression_count >= 2:
                return (
                    "❌ Maximum regression count (2) reached. "
                    "Further regressions require user approval. "
                    "Ask the user whether to continue or accept current quality."
                )

            # Check we're in Phase 7
            current_phase = state.get("current_phase", state.get("last_completed_phase", -1))
            if current_phase != 7 and current_phase < 6:
                return (
                    f"❌ Regression only allowed from Phase 7. "
                    f"Current phase: {current_phase}. "
                    f"Use patch_draft() for in-phase fixes."
                )

            # Mark the review loop as needing rewrite
            loop = _get_or_create_loop(project_dir)
            if not loop.is_completed:
                loop.request_rewrite(section_list, reason)
            # Evict cached loop so next review starts fresh
            if slug in _active_loops:
                del _active_loops[slug]

            # Save regression to checkpoint
            ckpt.save_phase_regression(
                from_phase=7,
                to_phase=5,
                reason=reason,
                sections_to_rewrite=section_list,
            )

            # Auto-sync workspace state
            _sync_to_workspace_state(
                slug=slug,
                phase=5,
                gate_passed=False,
                next_action=f"Rewrite sections: {', '.join(section_list)}. Then re-audit (Phase 6) and re-review (Phase 7).",
                review_verdict=RoundVerdict.REWRITE_NEEDED.value,
            )

            lines = [
                "# 🔁 Pipeline Regression: Phase 7 → Phase 5",
                "",
                f"**Reason**: {reason}",
                f"**Sections to rewrite**: {', '.join(section_list)}",
                f"**Regression count**: {regression_count + 1}/2",
                "",
                "## Next Steps",
                "",
                "1. Rewrite the specified sections using `draft_section()` + `write_draft()`",
                "2. Run Hook A/B cascading audit on each rewritten section",
                "3. Call `approve_section(section, action='approve')` for each section",
                "4. Validate Phase 5 gate: `validate_phase_gate(5)`",
                "5. Proceed through Phase 6 (cross-section audit)",
                "6. Phase 7 review will restart with a fresh review loop",
                "",
                "**Other sections are preserved** — only rewrite the specified sections.",
            ]

            report = "\n".join(lines)
            log_tool_result("request_section_rewrite", f"regression to Phase 5: {section_list}")
            return report

        except Exception as e:
            log_tool_error("request_section_rewrite", e)
            return f"❌ Error requesting section rewrite: {e}"

    @mcp.tool()
    def pause_pipeline(
        reason: str = "user_requested",
        project: Optional[str] = None,
    ) -> str:
        """
        ⏸️ Pause the pipeline for manual editing.

        Call this when the user wants to pause the auto-paper pipeline to
        manually edit drafts, review content, or take a break. The system
        records current draft hashes so it can detect changes when resumed.

        After pausing:
        - User can freely edit any draft files
        - User can edit concept.md, manuscript-plan.yaml, etc.
        - When ready, call resume_pipeline() to continue

        Args:
            reason: Why the pipeline is being paused (e.g., "user wants to edit Methods")
            project: Project slug (optional, uses current project)

        Returns:
            Pause confirmation with resume instructions
        """
        log_tool_call("pause_pipeline", {"reason": reason})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            ckpt = CheckpointManager(audit_dir, project_dir=project_dir)
            ckpt.save_pause(reason=reason)

            state = ckpt.load() or {}
            current_phase = state.get("pause_state", {}).get("phase_at_pause", "N/A")

            _sync_to_workspace_state(
                slug=slug,
                phase=current_phase if isinstance(current_phase, int) else 0,
                gate_passed=False,
                next_action="Pipeline paused. User editing. Call resume_pipeline() when ready.",
            )

            lines = [
                "# ⏸️ Pipeline Paused",
                "",
                f"**Phase at pause**: {current_phase}",
                f"**Reason**: {reason}",
                "",
                "## What You Can Do",
                "",
                "- Edit any draft files in `drafts/`",
                "- Modify `concept.md` or `manuscript-plan.yaml`",
                "- Add or update references",
                "- Take notes in `.memory/`",
                "",
                "## When Ready to Resume",
                "",
                "Call `resume_pipeline()` — the system will:",
                "1. Detect which files changed during the pause",
                "2. Recommend which audits to re-run",
                "3. Continue from the current phase",
            ]

            report = "\n".join(lines)
            log_tool_result("pause_pipeline", f"paused at phase {current_phase}")
            return report

        except Exception as e:
            log_tool_error("pause_pipeline", e)
            return f"❌ Error pausing pipeline: {e}"

    @mcp.tool()
    def resume_pipeline(
        project: Optional[str] = None,
    ) -> str:
        """
        ▶️ Resume the pipeline after a pause.

        Detects which draft files were modified during the pause and
        recommends appropriate re-validation steps.

        Args:
            project: Project slug (optional, uses current project)

        Returns:
            Resume report with detected changes and recommended actions
        """
        log_tool_call("resume_pipeline", {"project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            ckpt = CheckpointManager(audit_dir, project_dir=project_dir)
            resume_result = ckpt.resume_from_pause()

            changed = resume_result["changed"]
            changed_files = resume_result["changed_files"]
            phase_at_pause = resume_result["phase_at_pause"]

            _sync_to_workspace_state(
                slug=slug,
                phase=phase_at_pause if phase_at_pause >= 0 else 0,
                gate_passed=False,
                next_action=(
                    f"Re-run audits for changed files: {', '.join(changed_files)}"
                    if changed
                    else f"Continue from Phase {phase_at_pause}"
                ),
            )

            lines = [
                "# ▶️ Pipeline Resumed",
                "",
                f"**Phase**: {phase_at_pause}",
                f"**Drafts modified during pause**: {'Yes' if changed else 'No'}",
            ]

            if changed:
                lines.extend(
                    [
                        "",
                        "## Modified Files",
                        "",
                    ]
                )
                for f in changed_files:
                    lines.append(f"- `{f}`")
                lines.extend(
                    [
                        "",
                        "## Recommended Actions",
                        "",
                    ]
                )
                if phase_at_pause >= 5:
                    lines.append("1. Re-run `run_writing_hooks()` on modified sections (Hook A/B)")
                if phase_at_pause >= 6:
                    lines.append("2. Re-run Phase 6 cross-section audit (Hook C)")
                if phase_at_pause >= 7:
                    lines.append("3. Consider restarting Phase 7 review loop")
                lines.append("")
                lines.append("These are recommendations — proceed based on the scope of changes.")
            else:
                lines.extend(
                    [
                        "",
                        "No changes detected. Continuing from where we left off.",
                    ]
                )

            report = "\n".join(lines)
            log_tool_result("resume_pipeline", f"resumed, changed={changed}")
            return report

        except Exception as e:
            log_tool_error("resume_pipeline", e)
            return f"❌ Error resuming pipeline: {e}"

    @mcp.tool()
    def approve_section(
        section: str,
        action: str = "approve",
        feedback: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        ✅ Approve or request revision for a written section.

        During Phase 5, call this after each section is written and audited.
        The Phase 5 gate REQUIRES all sections to be approved before proceeding.

        **Autopilot mode (default)**: Agent self-reviews the section using Hook A/B
        results, then calls this with action="approve" to auto-approve and continue.
        No user confirmation needed unless the user explicitly requests review.

        **Manual mode**: User reviews each section and provides approve/revise.

        Actions:
        - "approve": Mark section as approved. Pipeline can continue to next section.
        - "revise": Mark section as needing revision. Agent must apply the feedback
                    using patch_draft/write_draft, re-run hooks, then call this again.

        Args:
            section: Section name (e.g., "Methods", "Results", "Introduction")
            action: "approve" or "revise"
            feedback: User feedback for revision (required when action="revise")
            project: Project slug (optional, uses current project)

        Returns:
            Confirmation with next steps
        """
        log_tool_call("approve_section", {"section": section, "action": action})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return msg
            assert project_info is not None
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            if action not in ("approve", "revise"):
                return "❌ Action must be 'approve' or 'revise'."

            if action == "revise" and not feedback.strip():
                return "❌ Feedback is required when requesting revision. What should be changed?"

            # Verify section exists in manuscript
            manuscript = project_dir / "drafts" / "manuscript.md"
            if manuscript.is_file():
                content = manuscript.read_text(encoding="utf-8")
                if f"## {section}" not in content and f"# {section}" not in content:
                    return f"❌ Section '{section}' not found in manuscript."

            ckpt = CheckpointManager(audit_dir, project_dir=project_dir)

            if action == "approve":
                ckpt.save_section_progress(
                    section=section,
                    approval_status="approved",
                )
                lines = [
                    f"# ✅ Section Approved: {section}",
                    "",
                    "The section has been marked as approved.",
                    "You can proceed to the next section in the writing order.",
                    "",
                    "## Current Approval Status",
                    "",
                ]
            else:
                ckpt.save_section_progress(
                    section=section,
                    approval_status="revision_requested",
                    user_feedback=feedback,
                )
                lines = [
                    f"# ✏️ Revision Requested: {section}",
                    "",
                    f"**Feedback**: {feedback}",
                    "",
                    "## Next Steps",
                    "",
                    f"1. Apply the feedback to the {section} section using `patch_draft()` or `write_draft()`",
                    "2. Re-run `run_writing_hooks()` on the modified section",
                    f"3. Call `approve_section(section='{section}', action='approve')` when satisfied",
                    "",
                    "## Current Approval Status",
                    "",
                ]

            # Show all section statuses
            statuses = ckpt.get_section_approval_status()
            for sec_name, sec_status in statuses.items():
                icon = {"approved": "✅", "revision_requested": "✏️", "pending": "⏳"}.get(
                    sec_status, "❓"
                )
                lines.append(f"- {icon} {sec_name}: {sec_status}")

            report = "\n".join(lines)
            log_tool_result("approve_section", f"{section}: {action}")
            return report

        except Exception as e:
            log_tool_error("approve_section", e)
            return f"❌ Error processing section approval: {e}"

    return {
        "validate_phase_gate": validate_phase_gate,
        "pipeline_heartbeat": pipeline_heartbeat,
        "start_review_round": start_review_round,
        "submit_review_round": submit_review_round,
        "validate_project_structure": validate_project_structure,
        "request_section_rewrite": request_section_rewrite,
        "pause_pipeline": pause_pipeline,
        "resume_pipeline": resume_pipeline,
        "approve_section": approve_section,
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
        structlog.get_logger().warning("Failed to write evolution log entry", path=str(elog))


__all__ = ["register_pipeline_tools"]
