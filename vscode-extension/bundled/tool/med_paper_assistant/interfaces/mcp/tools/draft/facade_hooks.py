"""Best-effort post-write hook runner for draft facade actions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks import WritingHooksEngine
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename

from .._shared import resolve_project_context


def _infer_section_name(filename: str, section: str = "") -> str:
    if section.strip():
        return section.strip()
    stem = Path(filename).stem
    return stem.replace("-", " ").replace("_", " ").title() or "manuscript"


def _hook_content(project_dir: Path, filename: str, content_hint: str) -> str:
    draft_path = project_dir / "drafts" / normalize_draft_filename(filename)
    content = content_hint
    if draft_path.is_file():
        content = draft_path.read_text(encoding="utf-8")
    return content


def _record_hook_results(project_dir: Path, results: Any) -> tuple[list[dict[str, Any]], int, int]:
    """Record hook coverage; return (issue summary, critical count, warning count)."""
    tracker = HookEffectivenessTracker(project_dir / ".audit")
    summary = []
    critical = 0
    warnings = 0
    for hook_id, result in results.items():
        tracker.record_event(hook_id, "pass" if result.passed else "trigger")
        issue_count = len(result.issues)
        if issue_count:
            critical += sum(1 for issue in result.issues if issue.severity == "CRITICAL")
            warnings += sum(1 for issue in result.issues if issue.severity == "WARNING")
            summary.append(
                {
                    "hook": hook_id,
                    "passed": result.passed,
                    "issues": issue_count,
                }
            )
    tracker.generate_report()
    return summary, critical, warnings


def _write_auto_hook_report(
    project_dir: Path,
    filename: str,
    section: str,
    hooks_run: int,
    critical: int,
    warnings: int,
    summary: list[dict[str, Any]],
) -> None:
    auto_hook_path = project_dir / ".audit" / "auto-hooks-latest.json"
    auto_hook_path.parent.mkdir(parents=True, exist_ok=True)
    auto_hook_path.write_text(
        json.dumps(
            {
                "schema": "mdpaper.auto_hooks.v1",
                "source": "draft_action",
                "filename": filename,
                "section": section,
                "hooks_run": hooks_run,
                "critical": critical,
                "warnings": warnings,
                "issues": summary[:20],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _hook_status_message(hooks_run: int, critical: int, warnings: int) -> str:
    if critical or warnings:
        return (
            "\n\n---\n"
            "auto_hooks: warning\n"
            f"hooks_run: {hooks_run}\n"
            f"critical: {critical}\n"
            f"warnings: {warnings}\n"
            "details: .audit/auto-hooks-latest.json"
        )
    return (
        f"\n\n---\nauto_hooks: ok\nhooks_run: {hooks_run}\ndetails: .audit/auto-hooks-latest.json"
    )


def _auto_run_post_write_hooks(
    *,
    project: str | None,
    filename: str,
    section: str,
    content_hint: str,
) -> str:
    """Run lightweight post-write hooks after mutating draft facade actions.

    This is intentionally best-effort and non-blocking: hooks should surface
    scientific-writing risks and record coverage, but they should not make the
    write tool unusable.
    """
    try:
        project_info, workflow_error = resolve_project_context(project, required_mode="manuscript")
        if workflow_error or project_info is None:
            return ""

        project_dir = Path(project_info["project_path"])
        content = _hook_content(project_dir, filename, content_hint)
        if not content.strip():
            return ""

        engine = WritingHooksEngine(project_dir)
        results = engine.run_post_write_hooks(content, section=section)
        summary, critical, warnings = _record_hook_results(project_dir, results)
        _write_auto_hook_report(
            project_dir, filename, section, len(results), critical, warnings, summary
        )
        return _hook_status_message(len(results), critical, warnings)
    except Exception:
        return (
            "\n\n---\n"
            "auto_hooks: skipped\n"
            'reason: best-effort hook runner failed; run run_quality_checks(action="writing_hooks") if needed'
        )
