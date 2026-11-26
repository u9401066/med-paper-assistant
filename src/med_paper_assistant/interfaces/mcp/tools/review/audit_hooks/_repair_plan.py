"""Actionable quality repair plan for ``run_quality_checks(action="repair_plan")``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks import WritingHooksEngine
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import resolve_child_path

from ..._shared import log_tool_call, log_tool_error, log_tool_result, report_tool_progress
from ._common import _coerce_project_info, resolve_manuscript_project
from ._writing_checks import WritingHookRun

_SEVERITY_RANK = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}


def resolve_draft_content(project_dir: Path, draft_filename: str = "") -> tuple[str, str, str]:
    """Load draft markdown for hook checks. Returns ``(content, label, error)``."""
    drafts_dir = project_dir / "drafts"
    if draft_filename.strip():
        try:
            safe_name = normalize_draft_filename(draft_filename.strip())
            target = resolve_child_path(
                drafts_dir, safe_name, field_name="Draft filename", allowed_suffixes={".md"}
            )
        except ValueError as exc:
            return "", "", f"❌ Invalid draft filename: {exc}"
        if not target.is_file():
            return "", "", f"❌ Draft file not found: drafts/{safe_name}"
        return target.read_text(encoding="utf-8"), safe_name, ""

    manuscript = drafts_dir / "manuscript.md"
    if manuscript.is_file():
        return manuscript.read_text(encoding="utf-8"), "manuscript.md", ""

    section_files = sorted(
        p for p in drafts_dir.glob("*.md") if p.is_file() and p.name.lower() != "concept.md"
    )
    if not section_files:
        return "", "", "❌ No manuscript or draft markdown files found in drafts/."

    combined = "\n\n".join(p.read_text(encoding="utf-8") for p in section_files)
    label = ", ".join(p.name for p in section_files)
    return combined, label, ""


def _suggested_call(hook_id: str, target_file: str, project_slug: str) -> dict[str, Any]:
    """Map a failing hook ID to the most direct compact MCP repair call."""
    primary_file = target_file.split(",")[0].strip() or "manuscript.md"
    code = hook_id.split(":")[0].upper()
    if code in {"A4", "C5", "P1"}:
        return {
            "tool": "validation_action",
            "arguments": {
                "action": "wikilinks",
                "filename": primary_file,
                "auto_fix": True,
                "project": project_slug,
            },
        }
    if code == "A7":
        return {
            "tool": "save_reference_mcp",
            "arguments": {"pmid": "<PMID>", "project": project_slug},
        }
    if code in {"C10", "C12"}:
        return {
            "tool": "reference_action",
            "arguments": {"action": "evidence_pack", "project": project_slug},
        }
    if code in {"C7A", "C7B", "C7D", "C13", "F"}:
        return {
            "tool": "analysis_action",
            "arguments": {"action": "list_assets", "project": project_slug},
        }
    return {
        "tool": "draft_action",
        "arguments": {
            "action": "patch",
            "filename": primary_file,
            "old_text": "<exact text to replace>",
            "new_text": "<revised text>",
            "project": project_slug,
        },
    }


def _collect_repair_items(
    results: dict[str, dict[str, Any]],
    target_file: str,
    project_slug: str,
) -> list[dict[str, Any]]:
    """Flatten and prioritize hook issues into actionable repair items."""
    items: list[dict[str, Any]] = []
    for hook_key, hr in sorted(results.items()):
        for issue in hr.get("issues", []):
            is_dict = isinstance(issue, dict)
            sev = str(
                issue.get("severity", "INFO") if is_dict else getattr(issue, "severity", "INFO")
            ).upper()
            section = str(
                (issue.get("section") if is_dict else getattr(issue, "section", ""))
                or (hook_key.split(":", 1)[1] if ":" in hook_key else "manuscript")
            )
            message = str(
                issue.get("message", "") if is_dict else getattr(issue, "message", str(issue))
            )
            suggestion = str(
                issue.get("suggestion") or "" if is_dict else getattr(issue, "suggestion", "") or ""
            )
            items.append(
                {
                    "severity": sev,
                    "hook_id": hook_key,
                    "section": section,
                    "message": message,
                    "suggestion": suggestion,
                    "suggested_call": _suggested_call(hook_key, target_file, project_slug),
                }
            )
    items.sort(
        key=lambda item: (_SEVERITY_RANK.get(item["severity"], 9), item["hook_id"], item["section"])
    )
    for idx, item in enumerate(items, 1):
        item["priority"] = idx
    return items


def _build_repair_payload(
    slug: str,
    target_label: str,
    hooks: str,
    draft_filename: str,
    run: WritingHookRun,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    recheck_args: dict[str, Any] = {"action": "repair_plan", "hooks": hooks, "project": slug}
    if draft_filename.strip():
        recheck_args["draft_filename"] = draft_filename
    return {
        "schema": "mdpaper.repair_plan.v1",
        "status": "clean" if not items else "needs_repair",
        "project": slug,
        "target_file": target_label,
        "counts": {
            "critical": run.critical,
            "warning": run.warning,
            "info": sum(1 for i in items if i["severity"] == "INFO"),
            "total_items": len(items),
        },
        "items": items[:40],
        "recheck_call": {"tool": "run_quality_checks", "arguments": recheck_args},
    }


async def run_quality_repair_plan(
    hooks: str = "all",
    draft_filename: str = "",
    prefer_language: str = "american",
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """Run writing hooks and return a prioritized JSON repair plan with compact patch calls."""
    log_tool_call(
        "run_quality_repair_plan",
        {"hooks": hooks, "draft_filename": draft_filename, "project": project},
    )
    try:
        from ._writing_hooks import _requested_hooks, _run_hook_stages

        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _coerce_project_info(project_info)
        slug = project_info["slug"]
        project_dir = Path(project_info["project_path"])

        content, target_label, load_error = resolve_draft_content(project_dir, draft_filename)
        if load_error:
            return load_error

        await report_tool_progress(ctx, 1, 3, "Running quality hooks for repair plan", end=90)
        run = WritingHookRun(
            WritingHooksEngine(project_dir),
            HookEffectivenessTracker(project_dir / ".audit"),
            _requested_hooks(hooks),
            content,
        )
        await _run_hook_stages(run, prefer_language, ctx)

        items = _collect_repair_items(run.results, target_label, slug)
        payload = _build_repair_payload(slug, target_label, hooks, draft_filename, run, items)
        await report_tool_progress(ctx, 3, 3, "Repair plan ready")
        log_tool_result("run_quality_repair_plan", f"items={len(items)}, critical={run.critical}")
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as e:
        log_tool_error("run_quality_repair_plan", e)
        return f"❌ Error generating quality repair plan: {e}"
