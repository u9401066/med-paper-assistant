"""
Figure & Table Insertion Flows

Message-rendering and step helpers behind the insert/list/review asset tools.
"""

import os
from pathlib import Path
from typing import Any, Literal, Optional

from med_paper_assistant.infrastructure.persistence import DataArtifactTracker
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import normalize_relative_filename, resolve_child_path

from .._shared import log_tool_result
from .figure_assets import (
    FIGURE_EXTENSIONS,
    TABLE_EXTENSIONS,
    _build_figure_insertion_markdown,
    _get_tracker,
    _insert_into_draft,
    _load_manifest,
    _next_number,
    _relative_asset_path,
    _save_manifest,
)

_MISSING_ASSET_HINTS = {
    "figure": "💡 Use `create_plot` or `save_diagram` first to generate the figure.",
    "table": "💡 Use `generate_table_one` first, or pass `table_content` to create the file.",
}


def _asset_file_path(kind: str, project_path: str, filename: str) -> Path:
    """Resolve an asset file inside the project's results/{figures,tables} folder."""
    folder = "figures" if kind == "figure" else "tables"
    return resolve_child_path(
        Path(project_path) / "results" / folder,
        filename,
        field_name=f"{kind.title()} filename",
        allowed_suffixes=FIGURE_EXTENSIONS if kind == "figure" else TABLE_EXTENSIONS,
    )


def _normalize_insert_inputs(
    kind: str,
    filename: str,
    draft_filename: Optional[str],
    table_content: Optional[str] = None,
) -> tuple[str, Optional[str], str]:
    """Normalize asset/draft filenames; return (filename, draft_filename, error)."""
    try:
        if kind == "figure":
            filename = normalize_relative_filename(
                filename,
                field_name="Figure filename",
                allowed_suffixes=FIGURE_EXTENSIONS,
            )
        else:
            filename = normalize_relative_filename(
                filename,
                field_name="Table filename",
                default_suffix=".md" if table_content else None,
                allowed_suffixes=TABLE_EXTENSIONS,
            )
        if draft_filename:
            draft_filename = normalize_draft_filename(draft_filename)
    except ValueError as e:
        return filename, draft_filename, f"❌ Invalid filename: {e}"
    return filename, draft_filename, ""


def _missing_file_error(kind: str, project_path: str, filename: str, file_path: Any) -> str:
    """Return the not-found message for a missing asset file, or "" when it exists."""
    if os.path.isfile(file_path):
        return ""
    folder = "figures" if kind == "figure" else "tables"
    extensions = FIGURE_EXTENSIONS if kind == "figure" else TABLE_EXTENSIONS
    assets_dir = Path(project_path) / "results" / folder
    available = [
        f
        for f in (os.listdir(assets_dir) if os.path.isdir(assets_dir) else [])
        if os.path.splitext(f)[1].lower() in extensions
    ]
    avail_str = ", ".join(available[:10]) if available else "none"
    return (
        f"❌ File '{filename}' not found in results/{folder}/.\n"
        f"Available: {avail_str}\n\n"
        f"{_MISSING_ASSET_HINTS[kind]}"
    )


def _caption_review_error(
    tracker: DataArtifactTracker,
    project_path: str,
    kind: Literal["figure", "table"],
    filename: str,
    caption: str,
) -> str:
    """Return the blocked message when no matching review receipt exists, else ""."""
    review_ok, review_detail = tracker.review_satisfies_caption(
        _relative_asset_path(project_path, kind, filename),
        caption,
        asset_type=kind,
    )
    if review_ok:
        return ""
    return (
        f"❌ {kind.title()} caption blocked — {review_detail}.\n\n"
        f'Call `review_asset_for_insertion(asset_type="{kind}", ...)` first using the same caption.'
    )


def _duplicate_entry_message(manifest: dict, key: str, label: str, filename: str) -> str:
    """Return the already-registered warning for a manifest entry, or "" when new."""
    for entry in manifest.get(key, []):
        if entry.get("filename") == filename:
            return (
                f"⚠️ {label} '{filename}' already registered as {label} {entry.get('number')}.\n"
                f"Caption: {entry.get('caption')}"
            )
    return ""


def _append_manifest_entry(
    project_path: str, manifest: dict, key: str, filename: str, caption: str, num: int
) -> str:
    entry = {
        "number": num,
        "filename": filename,
        "caption": caption,
    }
    manifest.setdefault(key, []).append(entry)
    return _save_manifest(project_path, manifest)


def _record_asset_artifact(
    tracker: DataArtifactTracker,
    kind: Literal["figure", "table"],
    filename: str,
    caption: str,
    num: int,
    output_rel: str,
) -> None:
    if tracker.get_artifact_by_output(output_rel):
        return
    tracker.record_artifact(
        tool_name=f"insert_{kind}",
        artifact_type=kind,
        parameters={"filename": filename, "caption": caption, f"{kind}_number": num},
        output_path=output_rel,
        data_source=filename,
        provenance_code=(
            f"# Manual {kind} registration via insert_{kind}\n"
            f"{kind}_path = '{output_rel}'\n"
            "# Preserve the registered source asset for reproducibility."
        ),
        result_summary=f"Registered {kind.title()} {num}: {caption}",
    )


def _registered_header(
    label: str, folder: str, num: int, filename: str, caption: str, manifest_path: str
) -> str:
    return (
        f"✅ **{label} {num} Registered**\n\n"
        f"- **File:** results/{folder}/{filename}\n"
        f"- **Caption:** {caption}\n"
        f"- **Manifest:** {manifest_path}\n"
    )


def _next_tip(label: str, num: int) -> str:
    return (
        "\n💡 **Next:** Reference as `{label} {num}` in your text. "
        "The consistency checker will verify cross-references."
    ).format(label=label, num=num)


def _figure_draft_output(
    drafter: Drafter,
    project_path: str,
    filename: str,
    caption: str,
    num: int,
    draft_filename: str,
    after_section: Optional[str],
) -> str:
    """Insert a figure reference into the draft and describe the outcome."""
    insert_text, exportable_asset = _build_figure_insertion_markdown(
        project_path,
        filename,
        caption,
        num,
    )
    insert_result = _insert_into_draft(drafter, draft_filename, insert_text, after_section)
    output = f"\n{insert_result}"
    if exportable_asset:
        output += f"\n- **Embedded Asset:** {exportable_asset}\n"
    else:
        output += (
            "\n⚠️ No exportable image asset found. "
            "Save a companion PNG/SVG (for example via `save_diagram(rendered_content=...)`) "
            "to embed this figure in DOCX/PDF exports.\n"
        )
    return output


def _table_draft_output(
    drafter: Drafter,
    file_path: Any,
    num: int,
    caption: str,
    table_content: Optional[str],
    draft_filename: str,
    after_section: Optional[str],
) -> str:
    """Insert the table into the draft and describe the outcome."""
    # Read table content for inline insertion
    if not table_content:
        with open(file_path, "r", encoding="utf-8") as f:
            table_content = f.read()

    insert_text = f"\n\n**Table {num}.** {caption}\n\n{table_content}\n"
    insert_result = _insert_into_draft(drafter, draft_filename, insert_text, after_section)
    return f"\n{insert_result}"


def _render_asset_list(figures: list, tables: list) -> str:
    output = "# 📊 Project Assets\n\n"

    if figures:
        output += "## Figures\n\n"
        output += "| # | Filename | Caption |\n"
        output += "|---|----------|--------|\n"
        for f in sorted(figures, key=lambda x: x.get("number", 0)):
            output += (
                f"| Figure {f.get('number')} | {f.get('filename')} | {f.get('caption', '')} |\n"
            )
        output += "\n"

    if tables:
        output += "## Tables\n\n"
        output += "| # | Filename | Caption |\n"
        output += "|---|----------|--------|\n"
        for t in sorted(tables, key=lambda x: x.get("number", 0)):
            output += (
                f"| Table {t.get('number')} | {t.get('filename')} | {t.get('caption', '')} |\n"
            )
        output += "\n"

    output += f"**Total:** {len(figures)} figures, {len(tables)} tables"
    return output


def _register_figure(
    drafter: Drafter,
    project_path: str,
    filename: str,
    caption: str,
    figure_number: Optional[int],
    draft_filename: Optional[str],
    after_section: Optional[str],
) -> str:
    """Review-gate, register and (optionally) insert a figure that already exists."""
    tracker = _get_tracker(project_path)
    error = _caption_review_error(tracker, project_path, "figure", filename, caption)
    if error:
        return error

    manifest = _load_manifest(project_path)
    error = _duplicate_entry_message(manifest, "figures", "Figure", filename)
    if error:
        return error

    # Assign number
    num = figure_number if figure_number else _next_number(manifest.get("figures", []))

    manifest_path = _append_manifest_entry(
        project_path, manifest, "figures", filename, caption, num
    )
    output_rel = _relative_asset_path(project_path, "figure", filename)
    _record_asset_artifact(tracker, "figure", filename, caption, num, output_rel)
    drafter.ref_manager.refresh_foam_graph()

    output = _registered_header("Figure", "figures", num, filename, caption, manifest_path)

    # Insert reference into draft if requested
    if draft_filename:
        output += _figure_draft_output(
            drafter, project_path, filename, caption, num, draft_filename, after_section
        )

    output += _next_tip("Figure", num)

    log_tool_result("insert_figure", f"Figure {num} registered", success=True)
    return output


def _register_table(
    drafter: Drafter,
    project_path: str,
    file_path: Any,
    filename: str,
    caption: str,
    table_number: Optional[int],
    table_content: Optional[str],
    draft_filename: Optional[str],
    after_section: Optional[str],
) -> str:
    """Review-gate, register and (optionally) insert a table that already exists."""
    # Every table path, including inline content, must pass receipt/hash validation.
    tracker = _get_tracker(project_path)
    error = _caption_review_error(tracker, project_path, "table", filename, caption)
    if error:
        return error

    manifest = _load_manifest(project_path)
    error = _duplicate_entry_message(manifest, "tables", "Table", filename)
    if error:
        return error

    # Assign number
    num = table_number if table_number else _next_number(manifest.get("tables", []))

    manifest_path = _append_manifest_entry(project_path, manifest, "tables", filename, caption, num)
    tracker = _get_tracker(project_path)
    output_rel = _relative_asset_path(project_path, "table", filename)
    _record_asset_artifact(tracker, "table", filename, caption, num, output_rel)
    drafter.ref_manager.refresh_foam_graph()

    output = _registered_header("Table", "tables", num, filename, caption, manifest_path)

    # Insert into draft if requested
    if draft_filename:
        output += _table_draft_output(
            drafter, file_path, num, caption, table_content, draft_filename, after_section
        )

    output += _next_tip("Table", num)

    log_tool_result("insert_table", f"Table {num} registered", success=True)
    return output
