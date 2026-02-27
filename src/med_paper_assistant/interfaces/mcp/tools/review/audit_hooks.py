"""
Audit Hook Tools — Hard enforcement MCP tools for quality audit and meta-learning.

These tools wrap the QualityScorecard, HookEffectivenessTracker, MetaLearningEngine,
and DataArtifactTracker as MCP tools that the agent MUST call. The agent cannot bypass
them — the Phase 5, 6, and 10 gate validators check for actual data produced by these tools.
Tool responses use TOON (Token-Oriented Object Notation) format for ~40% token savings.
See: https://github.com/toon-format/toon
Tools:
- record_hook_event: Record a hook evaluation outcome (trigger/pass/fix/false_positive)
- run_quality_audit: Set quality scores for all dimensions and generate audit report
- run_meta_learning: Run D1-D6 meta-learning analysis and write audit trail
- validate_data_artifacts: Cross-validate data artifacts, manifest, and draft references
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, cast

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import (
    DataArtifactTracker,
)
from med_paper_assistant.infrastructure.persistence.domain_constraint_engine import (
    DomainConstraintEngine,
)
from med_paper_assistant.infrastructure.persistence.evolution_verifier import (
    EvolutionVerifier,
)
from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.meta_learning_engine import (
    MetaLearningEngine,
)
from med_paper_assistant.infrastructure.persistence.quality_scorecard import (
    DIMENSIONS,
    QualityScorecard,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    WritingHooksEngine,
)

from .._shared import (
    ensure_project_context,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)

# Minimum dimensions required for Phase 6 gate
MIN_SCORED_DIMENSIONS = 4
# Minimum average score threshold
MIN_AVERAGE_SCORE = 1.0


def register_audit_hook_tools(mcp: FastMCP):
    """Register audit hook enforcement tools with the MCP server."""

    @mcp.tool()
    def record_hook_event(
        hook_id: str,
        event_type: str,
        project: Optional[str] = None,
    ) -> str:
        """
        📊 Record a hook evaluation outcome.

        Call this AFTER evaluating each hook (A1-A4, B1-B7, C1-C8, etc.)
        to record whether the hook triggered, passed, required a fix,
        or produced a false positive.

        This is CODE-ENFORCED — Phase 6 gate validates that hook events
        were actually recorded. You cannot skip this.

        Args:
            hook_id: Hook identifier (e.g., "A1", "B5", "C3", "E2")
            event_type: One of "trigger", "pass", "fix", "false_positive"
            project: Project slug (optional, uses current project)

        Returns:
            Current stats for the recorded hook
        """
        log_tool_call(
            "record_hook_event", {"hook_id": hook_id, "event_type": event_type, "project": project}
        )
        try:
            valid_events = ("trigger", "pass", "fix", "false_positive")
            if event_type not in valid_events:
                return f"❌ Invalid event_type '{event_type}'. Must be one of: {', '.join(valid_events)}"

            # Validate hook_id format: letter prefix + number (e.g., A1, B5, C3, P8)
            if not re.match(r"^[A-Z]\d{1,2}$", hook_id):
                return f"❌ Invalid hook_id '{hook_id}'. Must be a letter + 1-2 digits (e.g., 'A1', 'B5', 'C3')"

            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"
            assert project_info is not None

            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            tracker = HookEffectivenessTracker(audit_dir)
            tracker.record_event(
                hook_id,
                cast(Literal["trigger", "pass", "fix", "false_positive"], event_type),
            )

            # Return current stats for this hook (TOON format)
            stats = tracker.get_stats(hook_id)
            lines = [
                "status: ok",
                f"hook: {hook_id}",
                f"event: {event_type}",
                "stats[1]{triggers,passes,fixes,false_positives,trigger_rate,fix_rate}:",
                f"  {stats.get('trigger', 0)},{stats.get('pass', 0)},{stats.get('fix', 0)},{stats.get('false_positive', 0)},{stats.get('trigger_rate', 0):.0%},{stats.get('fix_rate', 0):.0%}",
            ]

            result = "\n".join(lines)
            log_tool_result("record_hook_event", f"{hook_id}={event_type}")
            return result

        except Exception as e:
            log_tool_error("record_hook_event", e)
            return f"❌ Error recording hook event: {e}"

    @mcp.tool()
    def run_quality_audit(
        scores: str,
        project: Optional[str] = None,
    ) -> str:
        """
        🔍 HARD GATE: Run quality audit — set scores and generate reports.

        Call this AFTER Phase 6 (Hook C post-manuscript audit).
        Sets quality scores for manuscript dimensions and generates:
        - quality-scorecard.json + quality-scorecard.md
        - hook-effectiveness.md (from recorded hook events)

        The agent MUST call this before validate_phase_gate(6) will PASS.
        Phase 6 gate validates actual score data exists (not just files).

        Args:
            scores: JSON string of dimension scores (0-10), e.g.:
                    '{"citation_quality": 8, "methodology_reproducibility": 7,
                      "text_quality": 8.5, "concept_consistency": 9,
                      "format_compliance": 8, "figure_table_quality": 7}'

                    Standard dimensions:
                    - citation_quality
                    - methodology_reproducibility
                    - text_quality
                    - concept_consistency
                    - format_compliance
                    - figure_table_quality
            project: Project slug (optional, uses current project)

        Returns:
            Combined audit report with scorecard and hook effectiveness
        """
        log_tool_call("run_quality_audit", {"project": project})
        try:
            # Parse scores
            try:
                score_dict = json.loads(scores)
            except json.JSONDecodeError:
                return (
                    "❌ Invalid scores JSON. Expected format:\n"
                    "```json\n"
                    '{"citation_quality": 8, "methodology_reproducibility": 7, ...}\n'
                    "```"
                )

            if not isinstance(score_dict, dict) or not score_dict:
                return "❌ Scores must be a non-empty JSON object mapping dimension names to numeric scores."

            # Validate score values
            for dim, score in score_dict.items():
                if not isinstance(score, (int, float)):
                    return f"❌ Score for '{dim}' must be a number, got {type(score).__name__}"
                if not 0 <= score <= 10:
                    return f"❌ Score for '{dim}' must be 0-10, got {score}"

            # Validate minimum dimensions
            standard_scored = [d for d in DIMENSIONS if d in score_dict]
            if len(standard_scored) < MIN_SCORED_DIMENSIONS:
                return (
                    f"❌ At least {MIN_SCORED_DIMENSIONS} of the {len(DIMENSIONS)} standard dimensions must be scored.\n"
                    f"Scored: {len(standard_scored)} ({', '.join(standard_scored)})\n"
                    f"Missing: {', '.join(d for d in DIMENSIONS if d not in score_dict)}\n\n"
                    f"Standard dimensions: {', '.join(DIMENSIONS)}"
                )

            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"
            assert project_info is not None

            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            # Set quality scores
            scorecard = QualityScorecard(audit_dir)
            for dim, score in score_dict.items():
                explanation = ""
                if isinstance(score, dict):
                    explanation = score.get("explanation", "")
                    score = score.get("score", score)
                scorecard.set_score(dim, score, explanation)

            # Generate scorecard report
            scorecard.generate_report()
            sc_data = scorecard.get_scorecard()

            # Generate hook effectiveness report
            tracker = HookEffectivenessTracker(audit_dir)
            tracker.generate_report()

            # Build combined audit report (TOON format)
            lines = [
                "status: ok",
                f"project: {slug}",
                f"timestamp: {datetime.now().isoformat()}",
                f"average_score: {sc_data['average_score']}",
                f"min_score: {sc_data.get('min_score', 'N/A')}",
                f"max_score: {sc_data.get('max_score', 'N/A')}",
                f"scored: {sc_data['scored_count']}/{sc_data['total_dimensions']}",
            ]

            if sc_data.get("missing_dimensions"):
                lines.append(f"missing: {','.join(sc_data['missing_dimensions'])}")

            # Threshold check
            meets_6 = scorecard.meets_threshold(6.0)
            meets_7 = scorecard.meets_threshold(7.0)
            if meets_7:
                lines.append("threshold: PASS (>=7.0, ready for Phase 7)")
            elif meets_6:
                lines.append("threshold: WARN (6-7, consider improvement)")
            else:
                lines.append("threshold: FAIL (<6, significant improvement needed)")

            # Weak dimensions
            weak = scorecard.get_weak_dimensions(min_score=6.0)
            if weak:
                lines.append(f"weak_dimensions[{len(weak)}]{{dimension,score,explanation}}:")
                for w in weak:
                    expl = w.get("explanation", "").replace(",", ";")
                    lines.append(f"  {w['dimension']},{w['score']},{expl}")

            # Hook effectiveness summary
            all_stats = tracker.get_stats()
            if all_stats:
                sorted_hooks = sorted(all_stats.keys())
                lines.append(f"hooks[{len(sorted_hooks)}]{{hook,triggers,passes,fixes,fp_rate}}:")
                for hid in sorted_hooks:
                    s = all_stats[hid]
                    lines.append(
                        f"  {hid},{s['trigger']},{s['pass']},{s['fix']},{s['false_positive_rate']:.0%}"
                    )

                # Recommendations
                recs = tracker.get_recommendations()
                if recs:
                    lines.append(f"recommendations[{len(recs)}]{{hook,type,reason}}:")
                    for r in recs:
                        reason = r["reason"].replace(",", ";")
                        lines.append(f"  {r['hook_id']},{r['type']},{reason}")

            lines.extend(
                [
                    "",
                    "files: .audit/quality-scorecard.md,.audit/hook-effectiveness.md",
                ]
            )

            result = "\n".join(lines)
            log_tool_result(
                "run_quality_audit",
                f"avg={sc_data['average_score']}, dims={sc_data['scored_count']}",
            )
            return result

        except Exception as e:
            log_tool_error("run_quality_audit", e)
            return f"❌ Error running quality audit: {e}"

    @mcp.tool()
    def run_meta_learning(
        project: Optional[str] = None,
    ) -> str:
        """
        🧠 HARD GATE: Run D1-D6 meta-learning analysis.

        Call this during Phase 10 (Retrospective).
        Executes the full MetaLearningEngine analysis:
        - D1: Hook effectiveness statistics
        - D2: Quality scorecard analysis
        - D3: Threshold adjustments (auto-apply within ±20%)
        - D4-D5: SKILL.md improvement suggestions
        - D6: Audit trail generation

        Also writes a meta_learning event to evolution-log.jsonl.

        The agent MUST call this before validate_phase_gate(10) will PASS.
        Phase 10 gate validates actual meta-learning analysis data exists.

        Args:
            project: Project slug (optional, uses current project)

        Returns:
            Meta-learning analysis summary with adjustments, lessons, and suggestions
        """
        log_tool_call("run_meta_learning", {"project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"
            assert project_info is not None

            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"
            audit_dir.mkdir(parents=True, exist_ok=True)

            # Initialize infrastructure
            tracker = HookEffectivenessTracker(audit_dir)
            scorecard = QualityScorecard(audit_dir)
            engine = MetaLearningEngine(audit_dir, tracker, scorecard)

            # Run analysis (D1 through D6)
            result = engine.analyze()

            # Write meta_learning event to evolution-log.jsonl
            elog = audit_dir / "evolution-log.jsonl"
            entry = {
                "event": "meta_learning",
                "timestamp": datetime.now().isoformat(),
                "adjustments_count": len(result.get("adjustments", [])),
                "lessons_count": len(result.get("lessons", [])),
                "suggestions_count": len(result.get("suggestions", [])),
                "auto_adjustments": sum(
                    1 for a in result.get("adjustments", []) if a.get("auto_apply", False)
                ),
            }
            with open(elog, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Build response (TOON format)
            lines = [
                "status: ok",
                f"project: {slug}",
                f"timestamp: {datetime.now().isoformat()}",
            ]

            # Adjustments (D1+D3)
            adjustments = result.get("adjustments", [])
            if adjustments:
                auto = [a for a in adjustments if a.get("auto_apply")]
                manual = [a for a in adjustments if not a.get("auto_apply")]

                if auto:
                    lines.append(
                        f"auto_adjustments[{len(auto)}]{{hook,parameter,current,suggested,change_pct,reason}}:"
                    )
                    for a in auto:
                        reason = a["reason"].replace(",", ";")
                        lines.append(
                            f"  {a['hook_id']},{a['parameter']},{a['current_value']},{a['suggested_value']},{a.get('change_pct', 'N/A')},{reason}"
                        )

                if manual:
                    lines.append(f"manual_adjustments[{len(manual)}]{{hook,parameter,reason}}:")
                    for a in manual:
                        reason = a["reason"].replace(",", ";")
                        lines.append(f"  {a['hook_id']},{a['parameter']},{reason}")

            # Lessons (D2)
            lessons = result.get("lessons", [])
            if lessons:
                lines.append(f"lessons[{len(lessons)}]{{severity,category,lesson}}:")
                for lesson in lessons:
                    lesson_text = lesson["lesson"].replace(",", ";")
                    lines.append(
                        f"  {lesson.get('severity', 'info')},{lesson['category']},{lesson_text}"
                    )

            # Suggestions (D4-D5)
            suggestions = result.get("suggestions", [])
            if suggestions:
                lines.append(f"suggestions[{len(suggestions)}]{{target,type,reason}}:")
                for s in suggestions:
                    reason = s["reason"].replace(",", ";")
                    lines.append(f"  {s['target']},{s['type']},{reason}")

            # Audit trail reference
            lines.append("files: .audit/meta-learning-audit.yaml,.audit/evolution-log.jsonl")

            report = "\n".join(lines)
            log_tool_result(
                "run_meta_learning",
                f"adjustments={len(adjustments)}, lessons={len(lessons)}, suggestions={len(suggestions)}",
            )
            return report

        except Exception as e:
            log_tool_error("run_meta_learning", e)
            return f"❌ Error running meta-learning analysis: {e}"

    @mcp.tool()
    def validate_data_artifacts(
        project: Optional[str] = None,
    ) -> str:
        """
        🔍 HARD GATE: Validate data artifacts — provenance, manifest, and draft cross-references.

        Call this AFTER writing Results / completing figures and tables.
        Cross-validates between:
        - data-artifacts.yaml (provenance from analysis tools)
        - results/manifest.json (registered figures/tables)
        - drafts/manuscript.md (Figure N / Table N references)
        - results/figures/ and results/tables/ (actual files on disk)

        The agent MUST call this before validate_phase_gate(5) will PASS
        if the manuscript contains any figures, tables, or statistical claims.

        Args:
            project: Project slug (optional, uses current project)

        Returns:
            Validation report with issues (CRITICAL = gate-blocking, WARNING = advisory)
        """
        log_tool_call("validate_data_artifacts", {"project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"
            assert project_info is not None

            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            # Read draft content if available
            draft_content = None
            manuscript = project_dir / "drafts" / "manuscript.md"
            if manuscript.is_file():
                draft_content = manuscript.read_text(encoding="utf-8")

            # Run cross-reference validation
            tracker = DataArtifactTracker(audit_dir, project_dir)
            validation = tracker.validate_cross_references(draft_content)

            # Generate provenance report as side effect
            tracker.generate_report()

            # Build TOON response
            summary = validation["summary"]
            issues = validation["issues"]

            lines = [
                f"status: {'PASS' if validation['passed'] else 'FAIL'}",
                f"project: {slug}",
                f"timestamp: {datetime.now().isoformat()}",
                f"total_artifacts: {summary['total_artifacts']}",
                f"figures_tracked: {summary['figures_tracked']}",
                f"tables_tracked: {summary['tables_tracked']}",
                f"stats_tracked: {summary['stats_tracked']}",
                f"manifest_figures: {summary['manifest_figures']}",
                f"manifest_tables: {summary['manifest_tables']}",
                f"critical_issues: {summary['critical_issues']}",
                f"warning_issues: {summary['warning_issues']}",
            ]

            if issues:
                lines.append(f"issues[{len(issues)}]{{severity,category,message}}:")
                for issue in issues:
                    message = issue["message"].replace(",", ";")
                    lines.append(f"  {issue['severity']},{issue['category']},{message}")

            if not issues:
                lines.append("result: All data artifacts validated — provenance complete")

            lines.append("files: .audit/data-artifacts.yaml,.audit/data-artifacts.md")

            result = "\n".join(lines)
            log_tool_result(
                "validate_data_artifacts",
                f"passed={validation['passed']}, critical={summary['critical_issues']}, warnings={summary['warning_issues']}",
            )
            return result

        except Exception as e:
            log_tool_error("validate_data_artifacts", e)
            return f"❌ Error validating data artifacts: {e}"

    @mcp.tool()
    def run_writing_hooks(
        hooks: str = "all",
        prefer_language: str = "american",
        project: Optional[str] = None,
    ) -> str:
        """
        ✍️ Run code-enforced writing hooks (A5, A6, B8, C9, F).

        Call this after writing or editing a section. Runs the specified hooks
        and records events for each via HookEffectivenessTracker.

        Available hooks:
        - A5: Language Consistency (British vs American English mixing)
        - A6: Self-Plagiarism / Overlap Detection (repeated n-grams)
        - B8: Data-Claim Alignment (statistical tests in Results ↔ Methods)
        - C9: Supplementary Cross-Reference (main text ↔ supplementary files)
        - F:  Data Artifact Validation (provenance, manifest, draft)

        Args:
            hooks: Comma-separated hook IDs (e.g., "A5,A6") or "all".
                   Use "post-write" for A5+A6, "post-section" for B8,
                   "post-manuscript" for C9+F.
            prefer_language: "american" or "british" (default: american).
                             Only affects A5.
            project: Project slug (optional, uses current project).

        Returns:
            TOON-formatted report with issues from each hook.
        """
        log_tool_call("run_writing_hooks", {"hooks": hooks, "project": project})
        try:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"
            assert project_info is not None

            slug = project_info["slug"]
            project_dir = Path(project_info["project_path"])
            audit_dir = project_dir / ".audit"

            # Read draft content
            manuscript = project_dir / "drafts" / "manuscript.md"
            if not manuscript.is_file():
                return "❌ No manuscript found at drafts/manuscript.md"
            full_content = manuscript.read_text(encoding="utf-8")

            # Parse section contents
            def _extract_section(title: str) -> str:
                pattern = rf"(?:^|\n)##?\s+{title}\b.*?\n(.*?)(?=\n##?\s|\Z)"
                m = re.search(pattern, full_content, re.DOTALL | re.IGNORECASE)
                return m.group(1).strip() if m else ""

            methods = _extract_section("Methods")
            results = _extract_section("Results")

            # Determine which hooks to run
            requested: set[str] = set()
            for token in hooks.split(","):
                t = token.strip().upper()
                if t == "ALL":
                    requested = {"A5", "A6", "B8", "C9", "F"}
                    break
                elif t == "POST-WRITE":
                    requested |= {"A5", "A6"}
                elif t == "POST-SECTION":
                    requested.add("B8")
                elif t == "POST-MANUSCRIPT":
                    requested |= {"C9", "F"}
                else:
                    requested.add(t)

            engine = WritingHooksEngine(project_dir)
            tracker = HookEffectivenessTracker(audit_dir)

            all_results: dict[str, dict] = {}
            total_critical = 0
            total_warning = 0

            if "A5" in requested:
                r = engine.check_language_consistency(full_content, prefer=prefer_language)
                all_results["A5"] = r.to_dict()
                tracker.record_event("A5", "pass" if r.passed else "trigger")
                total_critical += r.critical_count
                total_warning += r.warning_count

            if "A6" in requested:
                r = engine.check_overlap(full_content)
                all_results["A6"] = r.to_dict()
                tracker.record_event("A6", "pass" if r.passed else "trigger")
                total_critical += r.critical_count
                total_warning += r.warning_count

            if "B8" in requested:
                if methods and results:
                    r = engine.check_data_claim_alignment(methods, results)
                    all_results["B8"] = r.to_dict()
                    tracker.record_event("B8", "pass" if r.passed else "trigger")
                    total_critical += r.critical_count
                    total_warning += r.warning_count
                else:
                    all_results["B8"] = {
                        "hook_id": "B8",
                        "passed": True,
                        "issues": [],
                        "stats": {"skipped": "Methods or Results section not found"},
                    }

            if "C9" in requested:
                r = engine.check_supplementary_crossref(full_content)
                all_results["C9"] = r.to_dict()
                tracker.record_event("C9", "pass" if r.passed else "trigger")
                total_critical += r.critical_count
                total_warning += r.warning_count

            if "F" in requested:
                r = engine.validate_data_artifacts(full_content)
                all_results["F"] = r.to_dict()
                tracker.record_event("F1", "pass" if r.passed else "trigger")
                total_critical += r.critical_count
                total_warning += r.warning_count

            # Build TOON response
            overall_pass = total_critical == 0
            lines = [
                f"status: {'PASS' if overall_pass else 'FAIL'}",
                f"project: {slug}",
                f"hooks_run: {','.join(sorted(all_results.keys()))}",
                f"critical: {total_critical}",
                f"warnings: {total_warning}",
            ]

            for hook_id in sorted(all_results.keys()):
                hr = all_results[hook_id]
                lines.append(f"\n--- {hook_id} ---")
                lines.append(f"passed: {hr['passed']}")
                if hr.get("stats"):
                    for k, v in hr["stats"].items():
                        lines.append(f"  {k}: {v}")
                for issue in hr.get("issues", []):
                    sev = issue["severity"]
                    lines.append(f"  [{sev}] {issue['message']}")
                    if issue.get("suggestion"):
                        lines.append(f"    → {issue['suggestion']}")

            result = "\n".join(lines)
            log_tool_result(
                "run_writing_hooks",
                f"hooks={','.join(sorted(all_results.keys()))}, critical={total_critical}",
            )
            return result

        except Exception as e:
            log_tool_error("run_writing_hooks", e)
            return f"❌ Error running writing hooks: {e}"

    @mcp.tool()
    def verify_evolution() -> str:
        """
        📈 Verify self-evolution across all projects.

        Scans all project `.audit/` directories and aggregates:
        - Quality score trends across projects
        - Hook effectiveness improvement patterns
        - Threshold adjustment history
        - Lessons learned accumulation

        Returns an evidence-based report of whether the self-improvement
        system (Hook D / MetaLearningEngine) is producing measurable results.

        No arguments needed — reads from the projects/ directory automatically.
        """
        log_tool_call("verify_evolution", {})
        try:
            from med_paper_assistant.infrastructure.persistence.project_manager import (
                get_project_manager,
            )

            pm = get_project_manager()
            projects_dir = Path(pm.base_dir)

            verifier = EvolutionVerifier(projects_dir)
            report = verifier.verify()

            # TOON format output
            lines = [
                "status: ok",
                f"projects_analyzed: {report['cross_project'].get('project_count', 0)}",
                f"global_avg_score: {report['cross_project'].get('global_average_score', 0)}",
            ]

            evidence = report.get("evidence", [])
            passed_count = sum(1 for e in evidence if e["passed"])
            lines.append(f"evidence: {passed_count}/{len(evidence)} passed")

            for e in evidence:
                icon = "✅" if e["passed"] else "❌"
                lines.append(f"  {icon} {e['id']}: {e['detail']}")

            if report.get("cross_project", {}).get("weakest_dimension"):
                lines.append(
                    f"weakest_dimension: {report['cross_project']['weakest_dimension']} "
                    f"({report['cross_project']['weakest_score']}/10)"
                )

            lines.append("")
            lines.append(report.get("summary", "No summary available."))

            result = "\n".join(lines)
            log_tool_result("verify_evolution", f"evidence={passed_count}/{len(evidence)}")
            return result

        except Exception as e:
            log_tool_error("verify_evolution", e)
            return f"❌ Error verifying evolution: {e}"

    @mcp.tool()
    def check_domain_constraints(
        content: str,
        section: str = "manuscript",
        paper_type: str = "",
    ) -> str:
        """
        🔒 Validate content against domain constraints (Sand Spreader).

        Checks content against structured JSON constraints for the paper type.
        Detects: AI vocabulary, missing sections, word count violations,
        and any learned constraints from meta-learning evolution.

        Args:
            content: Text content to validate.
            section: Section name (e.g., "manuscript", "introduction").
            paper_type: Override paper type. Defaults to project's type.

        Returns:
            Constraint validation report with violations.
        """
        log_tool_call(
            "check_domain_constraints",
            {"section": section, "paper_type": paper_type},
        )
        try:
            is_valid, msg, project_info = ensure_project_context()
            if not is_valid or project_info is None:
                return f"❌ {msg}"
            project_dir = str(project_info["project_path"])

            # Determine paper type
            pt = paper_type
            if not pt:
                settings_path = Path(project_dir) / ".paper-settings.yaml"
                if settings_path.is_file():
                    settings_text = settings_path.read_text(encoding="utf-8")
                    for line in settings_text.splitlines():
                        if line.strip().startswith("paper_type:"):
                            pt = line.split(":", 1)[1].strip().strip("'\"")
                            break
                if not pt:
                    pt = "original-research"

            engine = DomainConstraintEngine(project_dir, paper_type=pt)
            result = engine.validate_against_constraints(content, section=section)
            summary = engine.get_constraint_summary()

            # Format output
            lines = [
                f"🔒 Domain Constraint Check ({pt})",
                f"Section: {section}",
                f"Constraints: {summary['total_constraints']} "
                f"(base: {result['base_constraints']}, learned: {result['learned_constraints']})",
                "",
            ]

            if result["passed"]:
                lines.append(f"✅ PASSED — {result['violation_count']} warnings, 0 critical")
            else:
                lines.append(
                    f"❌ FAILED — {result['violation_count']} violations "
                    f"({result['critical_count']} critical)"
                )

            if result["violations"]:
                lines.append("")
                lines.append("Violations:")
                for v in result["violations"]:
                    icon = "🔴" if v["severity"] == "CRITICAL" else "🟡"
                    lines.append(f"  {icon} [{v['constraint_id']}] {v['message']}")
                    if v.get("suggestion"):
                        lines.append(f"     → {v['suggestion']}")

            if summary.get("evolution_events", 0) > 0:
                lines.append("")
                lines.append(f"📈 Evolution: {summary['evolution_events']} constraints learned")

            output = "\n".join(lines)
            log_tool_result(
                "check_domain_constraints",
                f"passed={result['passed']}, violations={result['violation_count']}",
            )
            return output

        except Exception as e:
            log_tool_error("check_domain_constraints", e)
            return f"❌ Error checking constraints: {e}"

    @mcp.tool()
    def evolve_constraint(
        constraint_id: str,
        rule: str,
        category: str,
        description: str,
        severity: str = "WARNING",
        reason: str = "",
        source_hook: str = "",
    ) -> str:
        """
        📈 Add a learned constraint from recurring hook pattern.

        Called when MetaLearningEngine detects a pattern that should become
        a permanent structured constraint. This converts ephemeral hook
        feedback into permanent JSON knowledge.

        Args:
            constraint_id: Unique ID (e.g., "L001").
            rule: Rule name (e.g., "no_passive_in_results").
            category: Category (statistical, structural, vocabulary,
                      evidential, temporal, reporting, boundary).
            description: What this constraint enforces.
            severity: INFO, WARNING, or CRITICAL.
            reason: Why this constraint was added.
            source_hook: Which hook triggered this (e.g., "A5").

        Returns:
            Confirmation of constraint evolution.
        """
        log_tool_call(
            "evolve_constraint",
            {"constraint_id": constraint_id, "rule": rule},
        )
        try:
            is_valid, msg, project_info = ensure_project_context()
            if not is_valid or project_info is None:
                return f"❌ {msg}"
            project_dir = str(project_info["project_path"])

            # Validate category
            valid_categories = {
                "statistical",
                "structural",
                "vocabulary",
                "evidential",
                "temporal",
                "reporting",
                "boundary",
            }
            if category not in valid_categories:
                return f"❌ Invalid category '{category}'. Valid: {sorted(valid_categories)}"

            if severity not in ("INFO", "WARNING", "CRITICAL"):
                return f"❌ Invalid severity '{severity}'. Valid: INFO, WARNING, CRITICAL"

            engine = DomainConstraintEngine(project_dir)
            result = engine.evolve(
                constraint_id=constraint_id,
                rule=rule,
                category=category,
                description=description,
                severity=severity,
                reason=reason,
                source_hook=source_hook,
            )

            lines = [
                f"📈 Constraint Evolved: {constraint_id}",
                f"Rule: {rule}",
                f"Category: {category}",
                f"Severity: {severity}",
                f"Reason: {reason or 'not specified'}",
                f"Source hook: {source_hook or 'none'}",
                f"Learned at: {result.get('learned_at', 'unknown')}",
            ]

            summary = engine.get_constraint_summary()
            lines.append(
                f"\nTotal constraints: {summary['total_constraints']} "
                f"(learned: {summary['by_provenance'].get('learned', 0)})"
            )

            output = "\n".join(lines)
            log_tool_result("evolve_constraint", f"id={constraint_id}")
            return output

        except Exception as e:
            log_tool_error("evolve_constraint", e)
            return f"❌ Error evolving constraint: {e}"

    return {
        "record_hook_event": record_hook_event,
        "run_quality_audit": run_quality_audit,
        "run_meta_learning": run_meta_learning,
        "validate_data_artifacts": validate_data_artifacts,
        "run_writing_hooks": run_writing_hooks,
        "verify_evolution": verify_evolution,
        "check_domain_constraints": check_domain_constraints,
        "evolve_constraint": evolve_constraint,
    }


__all__ = ["register_audit_hook_tools"]
