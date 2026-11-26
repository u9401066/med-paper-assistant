"""Prose coherence & whole-manuscript concept-threading MCP handler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.writing_hooks._manuscript._coherence import (
    analyze_manuscript_coherence,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result, report_tool_progress
from ._common import _coerce_project_info, resolve_manuscript_project
from ._repair_plan import resolve_draft_content


async def run_coherence_audit(
    draft_filename: str = "",
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """Audit paragraph flow, Results->Discussion echo, terminology drift, and Golden Thread coverage."""
    log_tool_call("run_coherence_audit", {"draft_filename": draft_filename, "project": project})
    try:
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _coerce_project_info(project_info)
        slug = project_info["slug"]
        project_dir = Path(project_info["project_path"])

        content, target_label, load_error = resolve_draft_content(project_dir, draft_filename)
        if load_error:
            return load_error

        await report_tool_progress(
            ctx, 1, 2, "Auditing prose coherence and concept threading", end=90
        )
        payload = analyze_manuscript_coherence(project_dir, slug, content, target_label)
        await report_tool_progress(ctx, 2, 2, "Coherence audit complete")
        log_tool_result(
            "run_coherence_audit",
            f"score={payload['coherence_score']}, total={payload['counts']['total']}",
        )
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as e:
        log_tool_error("run_coherence_audit", e)
        return f"❌ Error running coherence audit: {e}"
