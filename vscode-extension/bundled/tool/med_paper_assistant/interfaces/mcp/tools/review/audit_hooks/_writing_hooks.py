"""run_writing_hooks tool."""

from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
    EvolutionItem,
    PendingEvolutionStore,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    WritingHooksEngine,
)

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._tool_doc import nested_tool_doc
from ._common import _coerce_project_info, resolve_manuscript_project
from ._writing_checks import WritingHookRun

_ALL_HOOKS = {
    "A1",
    "A2",
    "A3",
    "A3B",
    "A3C",
    "A4",
    "A5",
    "A6",
    "A7",
    "B8",
    "B9",
    "B10",
    "B11",
    "B12",
    "B13",
    "B14",
    "B15",
    "B16",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7A",
    "C7B",
    "C7D",
    "C9",
    "C10",
    "C11",
    "C12",
    "C13",
    "F",
}

_POST_WRITE_HOOKS = {
    "A1",
    "A2",
    "A3",
    "A3B",
    "A3C",
    "A4",
    "A5",
    "A6",
    "A7",
    "B9",
    "B10",
    "B15",
}

_POST_MANUSCRIPT_HOOKS = {
    "C3",
    "C4",
    "C5",
    "C6",
    "C7A",
    "C7B",
    "C7D",
    "C9",
    "C10",
    "C11",
    "C12",
    "C13",
    "F",
}


def _requested_hooks(hooks: str) -> set[str]:
    """Expand hook ids and aliases (all, post-write, ...) into the set to run."""
    requested: set[str] = set()
    for token in hooks.split(","):
        t = token.strip().upper()
        if t == "ALL":
            requested = set(_ALL_HOOKS)
            break
        elif t == "POST-WRITE":
            requested |= _POST_WRITE_HOOKS
        elif t == "POST-SECTION":
            requested |= {"B8", "B9", "B10", "B11", "B12", "B13", "B14", "B15", "B16"}
        elif t == "POST-MANUSCRIPT":
            requested |= _POST_MANUSCRIPT_HOOKS
        elif t == "PRE-COMMIT":
            requested |= {"P1", "P2", "P4", "P5", "P7", "G9"}
        else:
            requested.add(t)
    return requested


def _report_lines(slug: str, run: WritingHookRun) -> list[str]:
    """TOON report lines for a writing hook run."""
    all_results = run.results
    overall_pass = run.critical == 0
    lines = [
        f"status: {'PASS' if overall_pass else 'FAIL'}",
        f"project: {slug}",
        f"hooks_run: {','.join(sorted(all_results.keys()))}",
        f"critical: {run.critical}",
        f"warnings: {run.warning}",
    ]

    for hook_id in sorted(all_results.keys()):
        hr = all_results[hook_id]
        lines.append(f"\n--- {hook_id} ---")
        lines.append(f"passed: {hr['passed']}")
        if hr.get("stats"):
            for k, v in hr["stats"].items():
                lines.append(f"  {k}: {v}")
        for issue in hr.get("issues", []):
            if isinstance(issue, dict):
                sev = issue.get("severity", "INFO")
                message = issue.get("message", "")
                suggestion = issue.get("suggestion")
            else:
                sev = getattr(issue, "severity", "INFO")
                message = getattr(issue, "message", str(issue))
                suggestion = getattr(issue, "suggestion", None)
            lines.append(f"  [{sev}] {message}")
            if suggestion:
                lines.append(f"    → {suggestion}")
    return lines


def _flush_writing_hook_alerts(
    workspace_root: Path,
    project_slug: str,
    hook_results: dict[str, dict],
) -> None:
    """Persist critical writing hook issues as pending evolution items."""
    try:
        store = PendingEvolutionStore(workspace_root)
        for hook_id, hr in hook_results.items():
            if hr.get("passed", True):
                continue
            critical_issues = [i for i in hr.get("issues", []) if i.get("severity") == "CRITICAL"]
            if critical_issues:
                store.add(
                    EvolutionItem(
                        item_type="writing_hook_alert",
                        source=f"run_writing_hooks_{hook_id}",
                        project=project_slug,
                        auto_apply=False,
                        payload={
                            "hook_id": hook_id,
                            "critical_count": len(critical_issues),
                            "issues": [i.get("message", "") for i in critical_issues[:3]],
                        },
                    )
                )
    except Exception:
        import structlog

        structlog.get_logger().warning(
            "flush_writing_hook_alerts.failed",
            project=project_slug,
            exc_info=True,
        )


async def _run_hook_stages(run: WritingHookRun, prefer_language: str, ctx: Context | None) -> None:
    """Run the hook groups in order, reporting progress between them."""
    # --- Post-write hooks (A1-A6) ---
    await report_tool_progress(ctx, 2, 6, "Running post-write hooks", end=95)
    run.post_write(prefer_language)
    run.data_and_citations()

    # --- Post-manuscript hooks (C3-C7d) ---
    await report_tool_progress(ctx, 3, 6, "Running manuscript-level hooks", end=95)
    run.manuscript_level()
    run.precommit()

    # --- Git status hook (G9) ---
    await report_tool_progress(ctx, 4, 6, "Running pre-commit and git hooks", end=95)
    run.git()

    # --- Section writing quality hooks (B9-B16) ---
    await report_tool_progress(ctx, 5, 6, "Running section quality hooks", end=95)
    run.section_quality()


async def _writing_hooks(
    hooks: str, prefer_language: str, project: Optional[str], ctx: Context | None
) -> str:
    """Run the requested writing hooks and build the TOON report."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)

    await report_tool_progress(ctx, 0, 6, "Resolving project context", end=95)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"

    # Read draft content
    await report_tool_progress(ctx, 1, 6, "Loading manuscript content", end=95)
    manuscript = project_dir / "drafts" / "manuscript.md"
    if not manuscript.is_file():
        return "❌ No manuscript found at drafts/manuscript.md"
    full_content = manuscript.read_text(encoding="utf-8")

    requested = _requested_hooks(hooks)
    engine = WritingHooksEngine(project_dir)
    tracker = HookEffectivenessTracker(audit_dir)
    run = WritingHookRun(engine, tracker, requested, full_content)
    await _run_hook_stages(run, prefer_language, ctx)

    result = "\n".join(_report_lines(slug, run))
    log_tool_result(
        "run_writing_hooks",
        f"hooks={','.join(sorted(run.results.keys()))}, critical={run.critical}",
    )

    # Flush critical issues to PendingEvolutionStore for cross-conversation tracking
    if run.critical > 0:
        workspace_root = project_dir.parent.parent
        _flush_writing_hook_alerts(workspace_root, slug, run.results)

    await report_tool_progress(ctx, 6, 6, "Writing hook audit complete")
    return result


@nested_tool_doc
async def run_writing_hooks(
    hooks: str = "all",
    prefer_language: str = "american",
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    DEPRECATED public verb. Prefer `run_quality_checks(action="writing_hooks", ...)`.

    ✍️ Run code-enforced writing hooks (40 checks).

    Call this after writing or editing a section. Runs the specified hooks
    and records events for each via HookEffectivenessTracker.

    Available hooks:
    - A1: Word Count Compliance (section word count vs target ±20%)
    - A2: Citation Density (wikilinks per N words)
    - A3: Anti-AI Pattern Detection (forbidden AI-characteristic phrases)
    - A3b: AI Writing Structural Signals (list-heavy, uniform paragraphs)
    - A3c: Voice Consistency (register/tone uniformity)
    - A4: Wikilink Format Validation (correct [[author2024_12345678]] format)
    - A5: Language Consistency (British vs American English mixing)
    - A6: Self-Plagiarism / Overlap Detection (repeated n-grams)
    - A7: Reference Sufficiency (saved refs meet paper-type minimum)
    - B8: Data-Claim Alignment (statistical tests in Results ↔ Methods)
    - B9: Section Tense Consistency (Methods/Results → past tense)
    - B10: Paragraph Quality (length, structure, single-sentence detection)
    - B11: Results Interpretive Language Guard (no speculation in Results)
    - B12: Introduction Funnel Structure (context → gap → objective)
    - B13: Discussion Structure (findings, limitations, implications)
    - B14: Ethical & Registration Statements (IRB, consent, trial reg.)
    - B15: Hedging Language Density (excessive may/might/could)
    - B16: Effect Size & Statistical Reporting (p-values, CIs, effect sizes)
    - C3: N-value Consistency (sample sizes across sections)
    - C4: Abbreviation First-Use (defined at first occurrence)
    - C5: Wikilink Resolvable (wikilinks map to saved references)
    - C6: Total Word Count (manuscript total vs journal limit)
    - C7a: Figure/Table Count Limits
    - C7b: Asset Plan Coverage (figures/tables match asset plan)
    - C7d: Cross-Reference Orphan/Phantom Detection
    - C9: Supplementary Cross-Reference (main text ↔ supplementary files)
    - C10: Reference Fulltext Status (cited refs have fulltext ingested)
    - C11: Citation Distribution (citations spread across sections)
    - C12: Citation Relevance Audit (usage justification recorded)
    - C13: Figure/Table Quality (captions, labels, resolution)
    - F:  Data Artifact Validation (provenance, manifest, draft)
    - P1: Citation Integrity (pre-commit, delegates to C5)
    - P2: Anti-AI Scan (pre-commit, delegates to A3+A3b+A3c)
    - P4: Word Count (pre-commit, delegates to A1 with stricter threshold)
    - P5: Protected Content (🔒 blocks in concept.md)
    - P7: Reference Integrity (verified metadata)
    - G9: Git Status (uncommitted/unpushed changes)

    Args:
        hooks: Comma-separated hook IDs (e.g., "A5,A6,B11") or aliases:
               "all", "post-write" (A1-A7,A3b,A3c,B9,B10,B15),
               "post-section" (B8-B16),
               "post-manuscript" (C3-C13,F),
               "pre-commit" (P1,P2,P4,P5,P7,G9).
        prefer_language: "american" or "british" (default: american).
                         Only affects A5.
        project: Project slug (optional, uses current project).

    Returns:
        TOON-formatted report with issues from each hook.
    """
    log_tool_call("run_writing_hooks", {"hooks": hooks, "project": project})
    try:
        return await _writing_hooks(hooks, prefer_language, project, ctx)
    except Exception as e:
        log_tool_error("run_writing_hooks", e)
        return f"❌ Error running writing hooks: {e}"
