"""
Figure & Table Insertion Tools

insert_figure, insert_table — register assets in manifest and insert references into drafts.
"""

from collections.abc import Callable
import json
import os
import re
from pathlib import Path
from typing import Any, Literal, Optional, cast

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import (
    DataArtifactTracker,
    get_project_manager,
)
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    ensure_project_context,
    get_optional_tool_decorator,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_result,
    resolve_project_context,
)

FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tiff", ".drawio"}
TABLE_EXTENSIONS = {".csv", ".xlsx", ".md", ".html"}
EXPORTABLE_FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tiff"}
COMPANION_FIGURE_EXTENSIONS = [".png", ".svg", ".jpg", ".jpeg", ".tiff"]


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


def _load_manifest(project_path: str) -> dict:
    """Load manifest.json from results/, creating default if not found."""
    manifest_path = os.path.join(project_path, "results", "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"figures": [], "tables": []}


def _save_manifest(project_path: str, manifest: dict) -> str:
    """Save manifest.json to results/."""
    results_dir = os.path.join(project_path, "results")
    os.makedirs(results_dir, exist_ok=True)
    manifest_path = os.path.join(results_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest_path


def _get_tracker(project_path: str) -> DataArtifactTracker:
    """Build a DataArtifactTracker for the current project."""
    project_dir = Path(project_path)
    return DataArtifactTracker(project_dir / ".audit", project_dir)


def _relative_asset_path(project_path: str, kind: str, filename: str) -> str:
    """Return a stable project-relative asset path for review receipts."""
    folder = "figures" if kind == "figure" else "tables"
    return f"results/{folder}/{filename}"


def _validate_review_inputs(
    observations: str, rationale: str, proposed_caption: str
) -> tuple[bool, str]:
    observation_items = [o.strip() for o in observations.split("|") if o.strip()]
    if len(observation_items) < 2:
        return False, "❌ Provide at least 2 observations separated by `|` to prove asset review."
    if not rationale.strip():
        return False, "❌ Rationale is required. Explain why the caption fits the asset."
    if not proposed_caption.strip():
        return False, "❌ proposed_caption is required."
    return True, ""


def _resolve_exportable_figure_path(project_path: str, filename: str) -> Optional[str]:
    """Resolve the file that should be embedded into the manuscript export.

    Args:
        project_path: Absolute project root path.
        filename: Registered figure filename stored in ``results/figures``.

    Returns:
        Absolute path to an exportable figure asset, or ``None`` when only the
        source ``.drawio`` file exists and no rendered companion asset is found.
    """
    figures_dir = Path(project_path) / "results" / "figures"
    figure_path = figures_dir / filename

    if figure_path.suffix.lower() in EXPORTABLE_FIGURE_EXTENSIONS and figure_path.is_file():
        return str(figure_path)

    stem = figure_path.stem
    for extension in COMPANION_FIGURE_EXTENSIONS:
        candidate = figures_dir / f"{stem}{extension}"
        if candidate.is_file():
            return str(candidate)

    return None


def _to_markdown_asset_path(asset_path: str, drafts_dir: Path) -> str:
    """Convert a filesystem path to a Markdown-safe relative asset path.

    Markdown image links should always use forward slashes, even on Windows.
    This helper preserves relative semantics while normalizing path separators.

    Args:
        asset_path: Absolute or relative filesystem path to the asset.
        drafts_dir: Directory containing the draft markdown file.

    Returns:
        Relative path string using POSIX separators.
    """
    relative_path = os.path.relpath(asset_path, drafts_dir)
    return relative_path.replace("\\", "/")


def _build_figure_insertion_markdown(
    project_path: str,
    filename: str,
    caption: str,
    figure_number: int,
) -> tuple[str, Optional[str]]:
    """Build the draft snippet for a registered figure.

    Args:
        project_path: Absolute project root path.
        filename: Figure filename registered in the manifest.
        caption: Figure caption.
        figure_number: Sequential figure number.

    Returns:
        Tuple of ``(markdown_block, exportable_asset_path)``.  The markdown block
        contains an embedded image when a renderable asset is available; otherwise
        it falls back to caption-only text.
    """
    caption_line = f"**Figure {figure_number}.** {caption}"
    exportable_asset = _resolve_exportable_figure_path(project_path, filename)

    if not exportable_asset:
        return f"\n\n{caption_line}\n\n", None

    drafts_dir = Path(project_path) / "drafts"
    relative_path = _to_markdown_asset_path(exportable_asset, drafts_dir)
    image_alt = f"Figure {figure_number}. {caption}"
    markdown = f"\n\n![{image_alt}]({relative_path})\n\n{caption_line}\n\n"
    return markdown, exportable_asset


def _next_number(entries: list, key: str = "number") -> int:
    """Get next sequential number from manifest entries."""
    existing = [e.get(key, 0) for e in entries if isinstance(e.get(key), int)]
    return max(existing, default=0) + 1


def register_figure_tools(
    mcp: FastMCP,
    drafter: Drafter,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register figure/table insertion tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
    def review_asset_for_insertion(
        asset_type: str,
        filename: str,
        observations: str,
        rationale: str,
        proposed_caption: str,
        evidence_excerpt: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        Record an auditable asset review receipt before inserting a figure/table.

        This is the hard-gated proof that the agent reviewed the asset before
        writing a caption or legend. `insert_figure`/`insert_table` will refuse
        to proceed unless a matching receipt exists.

        Args:
            asset_type: "figure" or "table"
            filename: Asset filename inside results/figures or results/tables
            observations: Pipe-separated observations, e.g. "2 groups|error bars shown"
            rationale: Why the proposed caption accurately represents the asset
            proposed_caption: The caption to be used later in insert_figure/table
            evidence_excerpt: Optional verbatim excerpt from a table or source note
            project: Project slug (uses current if omitted)
        """
        log_tool_call(
            "review_asset_for_insertion",
            {"asset_type": asset_type, "filename": filename, "project": project},
        )

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            return workflow_error

        is_valid, msg, _ = ensure_project_context(project)
        if not is_valid:
            return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        if asset_type not in {"figure", "table"}:
            return "❌ asset_type must be `figure` or `table`."

        valid_inputs, error_msg = _validate_review_inputs(observations, rationale, proposed_caption)
        if not valid_inputs:
            return error_msg

        project_path = _get_project_path(project)
        if not project_path:
            return "❌ No active project."

        folder = "figures" if asset_type == "figure" else "tables"
        asset_path = os.path.join(project_path, "results", folder, filename)
        if not os.path.isfile(asset_path):
            return f"❌ File '{filename}' not found in results/{folder}/."

        observation_items = [o.strip() for o in observations.split("|") if o.strip()]
        tracker = _get_tracker(project_path)
        receipt = tracker.record_asset_review(
            asset_type=cast(Literal["figure", "table"], asset_type),
            asset_path=_relative_asset_path(project_path, asset_type, filename),
            observations=observation_items,
            rationale=rationale,
            proposed_caption=proposed_caption,
            evidence_excerpt=evidence_excerpt,
        )

        result = (
            f"✅ **Asset Review Recorded**\n\n"
            f"- **Receipt:** {receipt['id']}\n"
            f"- **Type:** {asset_type}\n"
            f"- **File:** results/{folder}/{filename}\n"
            f"- **Caption:** {proposed_caption}\n"
            f"- **Observations:** {len(receipt['observations'])}\n\n"
            "You can now call `insert_figure` or `insert_table` with the same caption."
        )
        log_tool_result("review_asset_for_insertion", receipt["id"], success=True)
        return result

    @tool()
    def insert_figure(
        filename: str,
        caption: str,
        figure_number: Optional[int] = None,
        draft_filename: Optional[str] = None,
        after_section: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Register a figure in the manifest and optionally insert a reference into a draft.

        The figure file must already exist in results/figures/.
        Use create_plot or save_diagram first to generate the file.

        Args:
            filename: Figure filename in results/figures/ (e.g., "boxplot_age.png")
            caption: Figure caption text
            figure_number: Figure number (auto-assigned if omitted)
            draft_filename: Draft file to insert reference into (optional)
            after_section: Insert after this heading (e.g., "Results"). Used with draft_filename.
            project: Project slug (uses current if omitted)
        """
        log_tool_call("insert_figure", {"filename": filename, "caption": caption})

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            return workflow_error

        is_valid, msg, _ = ensure_project_context(project)
        if not is_valid:
            return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        project_path = _get_project_path(project)
        if not project_path:
            return "❌ No active project."

        # Validate file exists
        figures_dir = os.path.join(project_path, "results", "figures")
        file_path = os.path.join(figures_dir, filename)
        if not os.path.isfile(file_path):
            available = [
                f
                for f in (os.listdir(figures_dir) if os.path.isdir(figures_dir) else [])
                if os.path.splitext(f)[1].lower() in FIGURE_EXTENSIONS
            ]
            avail_str = ", ".join(available[:10]) if available else "none"
            return (
                f"❌ File '{filename}' not found in results/figures/.\n"
                f"Available: {avail_str}\n\n"
                "💡 Use `create_plot` or `save_diagram` first to generate the figure."
            )

        tracker = _get_tracker(project_path)
        review_ok, review_detail = tracker.review_satisfies_caption(
            _relative_asset_path(project_path, "figure", filename),
            caption,
            asset_type="figure",
        )
        if not review_ok:
            return (
                f"❌ Figure caption blocked — {review_detail}.\n\n"
                'Call `review_asset_for_insertion(asset_type="figure", ...)` first using the same caption.'
            )

        # Load manifest
        manifest = _load_manifest(project_path)

        # Check duplicate
        for entry in manifest.get("figures", []):
            if entry.get("filename") == filename:
                return (
                    f"⚠️ Figure '{filename}' already registered as Figure {entry.get('number')}.\n"
                    f"Caption: {entry.get('caption')}"
                )

        # Assign number
        num = figure_number if figure_number else _next_number(manifest.get("figures", []))

        # Add to manifest
        entry = {
            "number": num,
            "filename": filename,
            "caption": caption,
        }
        manifest.setdefault("figures", []).append(entry)
        manifest_path = _save_manifest(project_path, manifest)
        drafter.ref_manager.refresh_foam_graph()

        output = (
            f"✅ **Figure {num} Registered**\n\n"
            f"- **File:** results/figures/{filename}\n"
            f"- **Caption:** {caption}\n"
            f"- **Manifest:** {manifest_path}\n"
        )

        # Insert reference into draft if requested
        if draft_filename:
            insert_text, exportable_asset = _build_figure_insertion_markdown(
                project_path,
                filename,
                caption,
                num,
            )
            insert_result = _insert_into_draft(drafter, draft_filename, insert_text, after_section)
            output += f"\n{insert_result}"
            if exportable_asset:
                output += f"\n- **Embedded Asset:** {exportable_asset}\n"
            else:
                output += (
                    "\n⚠️ No exportable image asset found. "
                    "Save a companion PNG/SVG (for example via `save_diagram(rendered_content=...)`) "
                    "to embed this figure in DOCX/PDF exports.\n"
                )

        output += (
            "\n💡 **Next:** Reference as `Figure {num}` in your text. "
            "The consistency checker will verify cross-references."
        ).format(num=num)

        log_tool_result("insert_figure", f"Figure {num} registered", success=True)
        return output

    @tool()
    def insert_table(
        filename: str,
        caption: str,
        table_number: Optional[int] = None,
        table_content: Optional[str] = None,
        draft_filename: Optional[str] = None,
        after_section: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Register a table in the manifest and optionally insert into a draft.

        For generated tables (generate_table_one), pass the markdown content directly.
        For file-based tables, the file must exist in results/tables/.

        Args:
            filename: Table filename in results/tables/ (e.g., "table1.md")
            caption: Table caption text
            table_number: Table number (auto-assigned if omitted)
            table_content: Markdown table content to save (optional, creates the file)
            draft_filename: Draft file to insert into (optional)
            after_section: Insert after this heading (e.g., "Results")
            project: Project slug (uses current if omitted)
        """
        log_tool_call("insert_table", {"filename": filename, "caption": caption})

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            return workflow_error

        is_valid, msg, _ = ensure_project_context(project)
        if not is_valid:
            return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        project_path = _get_project_path(project)
        if not project_path:
            return "❌ No active project."

        tables_dir = os.path.join(project_path, "results", "tables")
        file_path = os.path.join(tables_dir, filename)

        # If content provided, write the file and auto-record review receipt.
        # The agent has literal access to the content (passed as argument),
        # so "reviewing" is implicit — no separate review_asset_for_insertion needed.
        if table_content:
            os.makedirs(tables_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(table_content)

            tracker = _get_tracker(project_path)
            asset_rel = _relative_asset_path(project_path, "table", filename)
            existing_review = tracker.get_asset_review(asset_rel, asset_type="table")
            if not existing_review or DataArtifactTracker._normalize_caption(
                str(existing_review.get("proposed_caption", ""))
            ) != DataArtifactTracker._normalize_caption(caption):
                lines = table_content.strip().split("\n")
                n_rows = max(0, len(lines) - 2)  # header + delimiter
                n_cols = len([c for c in (lines[0].split("|") if lines else []) if c.strip()])
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
                )

        # Validate file exists
        if not os.path.isfile(file_path):
            available = [
                f
                for f in (os.listdir(tables_dir) if os.path.isdir(tables_dir) else [])
                if os.path.splitext(f)[1].lower() in TABLE_EXTENSIONS
            ]
            avail_str = ", ".join(available[:10]) if available else "none"
            return (
                f"❌ File '{filename}' not found in results/tables/.\n"
                f"Available: {avail_str}\n\n"
                "💡 Use `generate_table_one` first, or pass `table_content` to create the file."
            )

        # For file-based tables (no inline content), require explicit review receipt.
        if not table_content:
            tracker = _get_tracker(project_path)
            review_ok, review_detail = tracker.review_satisfies_caption(
                _relative_asset_path(project_path, "table", filename),
                caption,
                asset_type="table",
            )
            if not review_ok:
                return (
                    f"❌ Table caption blocked — {review_detail}.\n\n"
                    'Call `review_asset_for_insertion(asset_type="table", ...)` first using the same caption.'
                )

        # Load manifest
        manifest = _load_manifest(project_path)

        # Check duplicate
        for entry in manifest.get("tables", []):
            if entry.get("filename") == filename:
                return (
                    f"⚠️ Table '{filename}' already registered as Table {entry.get('number')}.\n"
                    f"Caption: {entry.get('caption')}"
                )

        # Assign number
        num = table_number if table_number else _next_number(manifest.get("tables", []))

        # Add to manifest
        entry = {
            "number": num,
            "filename": filename,
            "caption": caption,
        }
        manifest.setdefault("tables", []).append(entry)
        manifest_path = _save_manifest(project_path, manifest)
        drafter.ref_manager.refresh_foam_graph()

        output = (
            f"✅ **Table {num} Registered**\n\n"
            f"- **File:** results/tables/{filename}\n"
            f"- **Caption:** {caption}\n"
            f"- **Manifest:** {manifest_path}\n"
        )

        # Insert into draft if requested
        if draft_filename:
            # Read table content for inline insertion
            if not table_content:
                with open(file_path, "r", encoding="utf-8") as f:
                    table_content = f.read()

            insert_text = f"\n\n**Table {num}.** {caption}\n\n{table_content}\n"
            insert_result = _insert_into_draft(drafter, draft_filename, insert_text, after_section)
            output += f"\n{insert_result}"

        output += (
            "\n💡 **Next:** Reference as `Table {num}` in your text. "
            "The consistency checker will verify cross-references."
        ).format(num=num)

        log_tool_result("insert_table", f"Table {num} registered", success=True)
        return output

    @tool()
    def list_assets(project: Optional[str] = None) -> str:
        """
        List all registered figures and tables from the manifest.

        Args:
            project: Project slug (uses current if omitted)
        """
        log_tool_call("list_assets", {"project": project})

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            return workflow_error

        is_valid, msg, _ = ensure_project_context(project)
        if not is_valid:
            return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        project_path = _get_project_path(project)
        if not project_path:
            return "❌ No active project."

        manifest = _load_manifest(project_path)
        figures = manifest.get("figures", [])
        tables = manifest.get("tables", [])

        if not figures and not tables:
            return (
                "📭 No figures or tables registered.\n\n"
                "Use `insert_figure` or `insert_table` to register assets."
            )

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
        log_tool_result("list_assets", f"{len(figures)} figs, {len(tables)} tbls", success=True)
        return output

    return {
        "review_asset_for_insertion": review_asset_for_insertion,
        "insert_figure": insert_figure,
        "insert_table": insert_table,
        "list_assets": list_assets,
    }


def _insert_into_draft(
    drafter: Drafter,
    draft_filename: str,
    insert_text: str,
    after_section: Optional[str] = None,
) -> str:
    """Insert text into a draft after a specified section heading."""
    filepath = os.path.join(drafter.drafts_dir, draft_filename)
    if not os.path.isfile(filepath):
        return f"⚠️ Draft '{draft_filename}' not found — skipping insertion."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"⚠️ Error reading draft: {e}"

    if after_section:
        # Find the section heading and insert after its content
        # fmt: off
        pattern = re.compile(
            rf"^(#{{1,3}}\s+{re.escape(after_section)}.*?)(\n#{{1,3}}\s|\Z)",
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        # fmt: on
        match = pattern.search(content)
        if match:
            insert_pos = match.end(1)
            new_content = content[:insert_pos] + insert_text + content[insert_pos:]
        else:
            new_content = content + insert_text
            drafter.create_draft(draft_filename, new_content)
            return (
                f"⚠️ Section '{after_section}' not found in {draft_filename}. "
                "Appended to end of file."
            )
    else:
        new_content = content + insert_text

    try:
        drafter.create_draft(draft_filename, new_content)
        return f"✅ Inserted into {draft_filename}" + (
            f" after '{after_section}'" if after_section else " (appended)"
        )
    except Exception as e:
        return f"⚠️ Error writing draft: {e}"
