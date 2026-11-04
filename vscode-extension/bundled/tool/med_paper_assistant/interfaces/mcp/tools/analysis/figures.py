"""
Figure & Table Insertion Tools

insert_figure, insert_table — register assets in manifest and insert references into drafts.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Optional, cast

from mcp.server import MCPServer

from med_paper_assistant.application.content_integrity import ContentIntegrityInspector
from med_paper_assistant.infrastructure.external import (
    C2paProvenanceAdapter,
    ConservativeVisibleWatermarkHeuristic,
    RemoveAiWatermarksInspectionAdapter,
)
from med_paper_assistant.infrastructure.persistence import get_project_manager
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    ensure_project_context,
    get_optional_tool_decorator,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_result,
    resolve_project_context,
)
from .figure_assets import (
    _build_figure_insertion_markdown,
    _get_tracker,
    _load_manifest,
    _relative_asset_path,
    _to_markdown_asset_path,
    _validate_review_inputs,
)
from .figure_flows import (
    _asset_file_path,
    _missing_file_error,
    _normalize_insert_inputs,
    _register_figure,
    _register_table,
    _render_asset_list,
)
from .figure_review import _locate_review_asset, _normalize_review_filename, _record_review
from .figure_tools import register_asset_tools

__all__ = [
    "_build_figure_insertion_markdown",
    "_to_markdown_asset_path",
    "register_figure_tools",
]


def _get_project_path(project: Optional[str] = None) -> Optional[str]:
    """Get the current project path."""
    pm = get_project_manager()
    if project:
        info = pm.get_project_info(project)
    else:
        info = pm.get_project_info()
    if info and info.get("project_path"):
        return str(info["project_path"])
    return None


def _build_content_integrity_inspector() -> ContentIntegrityInspector:
    """Build the read-only C2PA and removal-package inspection pipeline."""
    return ContentIntegrityInspector(
        provenance_inspector=C2paProvenanceAdapter(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
        removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
    )


def _guard_project(project: Optional[str]) -> str:
    """Apply the manuscript workflow guard and project check; return an error or ""."""
    _, workflow_error = resolve_project_context(
        project,
        required_mode="manuscript",
    )
    if workflow_error:
        return workflow_error

    is_valid, msg, _ = ensure_project_context(project)
    if not is_valid:
        return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    return ""


def _guarded_project_path(project: Optional[str]) -> tuple[str, str]:
    """Return (project_path, error); project_path is empty when error is set."""
    guard_error = _guard_project(project)
    if guard_error:
        return "", guard_error

    project_path = _get_project_path(project)
    if not project_path:
        return "", "❌ No active project."
    return project_path, ""


def _inspect_asset(
    tracker: Any, asset_type: str, asset_path: str, asset_rel: str
) -> tuple[Any, dict]:
    """Run the integrity inspection and record its receipt."""
    integrity = _build_content_integrity_inspector().inspect(
        asset_path,
        asset_path=asset_rel,
    )
    integrity_receipt = tracker.record_content_integrity_receipt(
        asset_type=cast(Literal["figure", "table"], asset_type),
        asset_path=asset_rel,
        receipt=integrity.to_dict(),
    )
    return integrity, integrity_receipt


def _review_asset(
    asset_type: str,
    filename: str,
    observations: str,
    rationale: str,
    proposed_caption: str,
    evidence_excerpt: str,
    project: Optional[str],
    visible_watermark_review: str,
) -> str:
    log_tool_call(
        "review_asset_for_insertion",
        {"asset_type": asset_type, "filename": filename, "project": project},
    )

    guard_error = _guard_project(project)
    if guard_error:
        return guard_error

    filename, error = _normalize_review_filename(asset_type, filename)
    if error:
        return error

    valid_inputs, error_msg = _validate_review_inputs(observations, rationale, proposed_caption)
    if not valid_inputs:
        return error_msg

    project_path = _get_project_path(project)
    if not project_path:
        return "❌ No active project."

    asset_path, error = _locate_review_asset(project_path, asset_type, filename)
    if error:
        return error

    asset_rel = _relative_asset_path(project_path, asset_type, filename)
    tracker = _get_tracker(project_path)
    integrity, integrity_receipt = _inspect_asset(tracker, asset_type, asset_path, asset_rel)

    review = {
        "observations": observations,
        "rationale": rationale,
        "proposed_caption": proposed_caption,
        "evidence_excerpt": evidence_excerpt,
        "visible_watermark_review": visible_watermark_review,
    }
    return _record_review(
        tracker, asset_type, filename, asset_rel, review, integrity, integrity_receipt
    )


def _insert_figure(
    drafter: Drafter,
    filename: str,
    caption: str,
    figure_number: Optional[int],
    draft_filename: Optional[str],
    after_section: Optional[str],
    project: Optional[str],
) -> str:
    log_tool_call("insert_figure", {"filename": filename, "caption": caption})

    project_path, error = _guarded_project_path(project)
    if error:
        return error

    filename, draft_filename, error = _normalize_insert_inputs("figure", filename, draft_filename)
    if error:
        return error

    # Validate file exists
    file_path = _asset_file_path("figure", project_path, filename)
    error = _missing_file_error("figure", project_path, filename, file_path)
    if error:
        return error

    return _register_figure(
        drafter, project_path, filename, caption, figure_number, draft_filename, after_section
    )


def _write_inline_table(
    project_path: str, file_path: Any, filename: str, caption: str, table_content: str
) -> str:
    """Write inline table content and auto-record its review receipt; return an error or ""."""
    tables_dir = Path(project_path) / "results" / "tables"
    os.makedirs(tables_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(table_content)

    tracker = _get_tracker(project_path)
    asset_rel = _relative_asset_path(project_path, "table", filename)
    lines = table_content.strip().split("\n")
    n_rows = max(0, len(lines) - 2)  # header + delimiter
    n_cols = len([c for c in (lines[0].split("|") if lines else []) if c.strip()])
    integrity, integrity_receipt = _inspect_asset(tracker, "table", file_path, asset_rel)
    if integrity.gate_status.value == "BLOCK":
        return (
            "❌ Table integrity gate blocked — "
            + "; ".join(integrity.gate_reasons)
            + f" (receipt {integrity_receipt['id']})."
        )
    tracker.record_asset_review(
        asset_type="table",
        asset_path=asset_rel,
        observations=[
            f"Table has {n_rows} data rows and {n_cols} columns",
            f"Content provided inline ({len(table_content)} chars)",
        ],
        rationale="Content provided directly via table_content parameter; agent has full access.",
        proposed_caption=caption,
        evidence_excerpt=table_content[:500],
        content_integrity_receipt_id=integrity_receipt["id"],
    )
    return ""


def _insert_table(
    drafter: Drafter,
    filename: str,
    caption: str,
    table_number: Optional[int],
    table_content: Optional[str],
    draft_filename: Optional[str],
    after_section: Optional[str],
    project: Optional[str],
) -> str:
    log_tool_call("insert_table", {"filename": filename, "caption": caption})

    project_path, error = _guarded_project_path(project)
    if error:
        return error

    filename, draft_filename, error = _normalize_insert_inputs(
        "table", filename, draft_filename, table_content
    )
    if error:
        return error

    file_path = _asset_file_path("table", project_path, filename)

    # If content provided, write the file and auto-record review receipt.
    # The agent has literal access to the content (passed as argument),
    # so "reviewing" is implicit — no separate review_asset_for_insertion needed.
    if table_content:
        error = _write_inline_table(project_path, file_path, filename, caption, table_content)
        if error:
            return error

    # Validate file exists
    error = _missing_file_error("table", project_path, filename, file_path)
    if error:
        return error

    # Every table path, including inline content, must pass receipt/hash validation.
    return _register_table(
        drafter,
        project_path,
        file_path,
        filename,
        caption,
        table_number,
        table_content,
        draft_filename,
        after_section,
    )


def _list_assets(project: Optional[str]) -> str:
    log_tool_call("list_assets", {"project": project})

    project_path, error = _guarded_project_path(project)
    if error:
        return error

    manifest = _load_manifest(project_path)
    figures = manifest.get("figures", [])
    tables = manifest.get("tables", [])

    if not figures and not tables:
        return (
            "📭 No figures or tables registered.\n\n"
            "Use `insert_figure` or `insert_table` to register assets."
        )

    output = _render_asset_list(figures, tables)
    log_tool_result("list_assets", f"{len(figures)} figs, {len(tables)} tbls", success=True)
    return output


def register_figure_tools(
    mcp: MCPServer,
    drafter: Drafter,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register figure/table insertion tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return register_asset_tools(
        tool,
        drafter,
        review_impl=_review_asset,
        insert_figure_impl=_insert_figure,
        insert_table_impl=_insert_table,
        list_assets_impl=_list_assets,
    )
