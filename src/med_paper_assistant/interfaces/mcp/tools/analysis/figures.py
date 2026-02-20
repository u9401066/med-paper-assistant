"""
Figure & Table Insertion Tools

insert_figure, insert_table — register assets in manifest and insert references into drafts.
"""

import json
import os
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import get_project_manager
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_result,
)

FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tiff", ".drawio"}
TABLE_EXTENSIONS = {".csv", ".xlsx", ".md", ".html"}


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


def _next_number(entries: list, key: str = "number") -> int:
    """Get next sequential number from manifest entries."""
    existing = [e.get(key, 0) for e in entries if isinstance(e.get(key), int)]
    return max(existing, default=0) + 1


def register_figure_tools(mcp: FastMCP, drafter: Drafter):
    """Register figure/table insertion tools."""

    @mcp.tool()
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

        output = (
            f"✅ **Figure {num} Registered**\n\n"
            f"- **File:** results/figures/{filename}\n"
            f"- **Caption:** {caption}\n"
            f"- **Manifest:** {manifest_path}\n"
        )

        # Insert reference into draft if requested
        if draft_filename:
            insert_text = f"\n\n**Figure {num}.** {caption}\n\n"
            insert_result = _insert_into_draft(drafter, draft_filename, insert_text, after_section)
            output += f"\n{insert_result}"

        output += (
            "\n💡 **Next:** Reference as `Figure {num}` in your text. "
            "The consistency checker will verify cross-references."
        ).format(num=num)

        log_tool_result("insert_figure", f"Figure {num} registered", success=True)
        return output

    @mcp.tool()
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

        is_valid, msg, _ = ensure_project_context(project)
        if not is_valid:
            return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        project_path = _get_project_path(project)
        if not project_path:
            return "❌ No active project."

        tables_dir = os.path.join(project_path, "results", "tables")
        file_path = os.path.join(tables_dir, filename)

        # If content provided, write the file
        if table_content:
            os.makedirs(tables_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(table_content)

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

    @mcp.tool()
    def list_assets(project: Optional[str] = None) -> str:
        """
        List all registered figures and tables from the manifest.

        Args:
            project: Project slug (uses current if omitted)
        """
        log_tool_call("list_assets", {"project": project})

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
