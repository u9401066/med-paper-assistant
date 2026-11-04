"""validate_data_artifacts tool."""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import (
    DataArtifactTracker,
)

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._tool_doc import nested_tool_doc
from ._common import _coerce_project_info, resolve_manuscript_project


def _read_draft_content(project_dir: Path) -> str | None:
    """Read manuscript.md, or concatenate the section drafts when it is absent."""
    draft_content = None
    manuscript = project_dir / "drafts" / "manuscript.md"
    if manuscript.is_file():
        draft_content = manuscript.read_text(encoding="utf-8")
    else:
        draft_files = sorted((project_dir / "drafts").glob("*.md"))
        parts = [
            p.read_text(encoding="utf-8")
            for p in draft_files
            if p.name != "concept.md" and p.is_file()
        ]
        draft_content = "\n\n".join(parts) if parts else None
    return draft_content


def _validation_lines(slug: str, validation: dict[str, Any]) -> list[str]:
    """TOON lines for a data-artifact cross-reference validation."""
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
    return lines


async def _validate_artifacts(project: Optional[str], ctx: Context | None) -> str:
    """Cross-validate data artifacts, manifest and draft references."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)

    await report_tool_progress(ctx, 0, 4, "Resolving project context", end=95)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"

    # Read draft content if available
    await report_tool_progress(ctx, 1, 4, "Reading manuscript and artifact inputs", end=95)
    draft_content = _read_draft_content(project_dir)

    # Run cross-reference validation
    await report_tool_progress(ctx, 2, 4, "Cross-validating data artifacts", end=95)
    tracker = DataArtifactTracker(audit_dir, project_dir)
    validation = tracker.validate_cross_references(draft_content)

    # Generate provenance report as side effect
    tracker.generate_report()

    summary = validation["summary"]
    result = "\n".join(_validation_lines(slug, validation))
    await report_tool_progress(ctx, 4, 4, "Data artifact validation complete")
    log_tool_result(
        "validate_data_artifacts",
        f"passed={validation['passed']}, critical={summary['critical_issues']}, warnings={summary['warning_issues']}",
    )
    return result


@nested_tool_doc
async def validate_data_artifacts(
    project: Optional[str] = None,
    ctx: Context | None = None,
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
        return await _validate_artifacts(project, ctx)
    except Exception as e:
        log_tool_error("validate_data_artifacts", e)
        return f"❌ Error validating data artifacts: {e}"
