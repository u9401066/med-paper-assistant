"""run_review_hooks tool."""

from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._manuscript import read_review_manuscript_content
from .._tool_doc import nested_tool_doc
from ._common import _coerce_project_info, resolve_manuscript_project


class _ReviewChecks:
    """Runs the requested R1-R6 review hooks and tallies their issues."""

    def __init__(self, engine: Any, requested: set[str], round_num: int) -> None:
        self.engine = engine
        self.requested = requested
        self.round_num = round_num
        self.results: dict[str, dict] = {}
        self.critical = 0
        self.warning = 0

    def record(self, hook_id: str, result: Any) -> None:
        """Store a hook result and add its issues to the totals."""
        self.results[hook_id] = result.to_dict()
        self.critical += result.critical_count
        self.warning += result.warning_count

    def _skip(self, hook_id: str) -> None:
        """Record a manuscript-based hook as skipped when no manuscript exists."""
        self.results[hook_id] = {
            "hook_id": hook_id,
            "passed": True,
            "issues": [],
            "stats": {"skipped": "no manuscript found"},
        }

    def run(self, issues_fixed: int, manuscript_content: str) -> None:
        """Run R1-R6 in order."""
        req, engine, n = self.requested, self.engine, self.round_num
        if "R1" in req:
            self.record("R1", engine.check_review_report_depth(n))

        if "R2" in req:
            self.record("R2", engine.check_author_response_completeness(n))

        if "R3" in req:
            self.record("R3", engine.check_equator_compliance(n))

        if "R4" in req:
            r = engine.check_review_fix_traceability(
                n,
                issues_fixed=issues_fixed,
                manuscript_changed=True,
            )
            self.record("R4", r)

        if "R5" in req:
            if manuscript_content:
                self.record("R5", engine.check_post_review_anti_ai(manuscript_content))
            else:
                self._skip("R5")

        if "R6" in req:
            if manuscript_content:
                self.record("R6", engine.check_citation_budget(manuscript_content))
            else:
                self._skip("R6")


def _requested_review_hooks(hooks: str) -> set[str]:
    """Expand hook ids and the ``all`` alias into the set of review hooks to run."""
    requested: set[str] = set()
    for token in hooks.split(","):
        t = token.strip().upper()
        if t == "ALL":
            requested = {"R1", "R2", "R3", "R4", "R5", "R6"}
            break
        else:
            requested.add(t)
    return requested


def _review_report_lines(slug: str, round_num: int, checks: _ReviewChecks) -> list[str]:
    """TOON report lines for a review hook run."""
    results = checks.results
    overall_pass = checks.critical == 0
    lines = [
        f"status: {'PASS' if overall_pass else 'FAIL'}",
        f"project: {slug}",
        f"round: {round_num}",
        f"hooks_run: {','.join(sorted(results.keys()))}",
        f"critical: {checks.critical}",
        f"warnings: {checks.warning}",
    ]
    for hook_id in sorted(results.keys()):
        hr = results[hook_id]
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
    return lines


async def _review_hooks(
    round_num: int, hooks: str, issues_fixed: int, project: Optional[str], ctx: Context | None
) -> str:
    """Run the requested review hooks for a round and build the TOON report."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)

    await report_tool_progress(ctx, 0, 4, "Resolving project context", end=95)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])

    from med_paper_assistant.infrastructure.persistence.review_hooks import (
        ReviewHooksEngine,
    )

    engine = ReviewHooksEngine(project_dir)

    # Auto-detect round number if not specified
    await report_tool_progress(ctx, 1, 4, "Loading review round artifacts", end=95)
    if round_num <= 0:
        audit_dir = project_dir / ".audit"
        for i in range(20, 0, -1):
            if (audit_dir / f"review-report-{i}.md").is_file():
                round_num = i
                break
        if round_num <= 0:
            return "❌ No review reports found. Start a review round first."

    # Read manuscript for R5/R6, including section-only draft workflows.
    manuscript_content = read_review_manuscript_content(project_dir)

    checks = _ReviewChecks(engine, _requested_review_hooks(hooks), round_num)
    await report_tool_progress(ctx, 2, 4, "Running review quality hooks", end=95)
    checks.run(issues_fixed, manuscript_content)

    # Build TOON response
    await report_tool_progress(ctx, 3, 4, "Building review hook report", end=95)
    result = "\n".join(_review_report_lines(slug, round_num, checks))
    await report_tool_progress(ctx, 4, 4, "Review hooks complete")
    log_tool_result("run_review_hooks", f"critical={checks.critical}")
    return result


@nested_tool_doc
async def run_review_hooks(
    round_num: int = 0,
    hooks: str = "all",
    issues_fixed: int = 0,
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    🔍 Run code-enforced review quality hooks (R1-R6).

    Call this during Phase 7 to verify review CONTENT quality,
    not just process compliance. Can be run standalone or as part
    of submit_review_round() (which calls these automatically).

    Available hooks:
    - R1: Review Report Depth (word count, perspectives, severity breakdown)
    - R2: Author Response Completeness (ACCEPT/DECLINE, ratio, evidence)
    - R3: EQUATOR Compliance Gate (checklist items ≥ 5)
    - R4: Review-Fix Traceability (ACCEPT'd issues → manuscript changes)
    - R5: Post-Review Anti-AI Gate (re-run A3/A3b after edits)
    - R6: Citation Budget Gate (refs ≤ journal limit, prioritisation)

    Args:
        round_num: Review round number (0 = auto-detect latest)
        hooks: Comma-separated hook IDs (e.g., "R1,R5,R6") or "all"
        issues_fixed: Number of issues fixed (for R4 traceability)
        project: Project slug (optional, uses current project)

    Returns:
        TOON-formatted report with issues from each hook.
    """
    log_tool_call("run_review_hooks", {"round_num": round_num, "hooks": hooks})
    try:
        return await _review_hooks(round_num, hooks, issues_fixed, project, ctx)
    except Exception as e:
        log_tool_error("run_review_hooks", e)
        return f"❌ Error running review hooks: {e}"
