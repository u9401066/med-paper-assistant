"""
Figure & table asset helpers

Manifest, path, markdown and registration helpers shared by the figure/table insertion tools.
Tool registration and project-context handling live in ``figures.py``.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

from med_paper_assistant.infrastructure.persistence import DataArtifactTracker
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import normalize_relative_filename, resolve_child_path

FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tiff", ".drawio"}
TABLE_EXTENSIONS = {".csv", ".xlsx", ".md", ".html"}
EXPORTABLE_FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tiff"}
COMPANION_FIGURE_EXTENSIONS = [".png", ".svg", ".jpg", ".jpeg", ".tiff"]


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
    filename = normalize_relative_filename(
        filename,
        field_name="Figure filename",
        allowed_suffixes=FIGURE_EXTENSIONS,
    )
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


def _insert_after_section(content: str, insert_text: str, after_section: str) -> Optional[str]:
    """Return content with insert_text after the section, or None when the heading is missing."""
    # Find the section heading and insert after its content
    # fmt: off
    pattern = re.compile(
        rf"^(#{{1,3}}\s+{re.escape(after_section)}.*?)(\n#{{1,3}}\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    # fmt: on
    match = pattern.search(content)
    if not match:
        return None
    insert_pos = match.end(1)
    return content[:insert_pos] + insert_text + content[insert_pos:]


def _insert_into_draft(
    drafter: Drafter,
    draft_filename: str,
    insert_text: str,
    after_section: Optional[str] = None,
) -> str:
    """Insert text into a draft after a specified section heading."""
    try:
        draft_filename = normalize_draft_filename(draft_filename)
        filepath = str(
            resolve_child_path(drafter.drafts_dir, draft_filename, field_name="Draft filename")
        )
    except ValueError as e:
        return f"⚠️ Invalid draft filename — skipping insertion: {e}"
    if not os.path.isfile(filepath):
        return f"⚠️ Draft '{draft_filename}' not found — skipping insertion."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"⚠️ Error reading draft: {e}"

    if after_section:
        spliced = _insert_after_section(content, insert_text, after_section)
        if spliced is None:
            drafter.create_draft(draft_filename, content + insert_text)
            return (
                f"⚠️ Section '{after_section}' not found in {draft_filename}. "
                "Appended to end of file."
            )
        new_content = spliced
    else:
        new_content = content + insert_text

    try:
        drafter.create_draft(draft_filename, new_content)
        return f"✅ Inserted into {draft_filename}" + (
            f" after '{after_section}'" if after_section else " (appended)"
        )
    except Exception as e:
        return f"⚠️ Error writing draft: {e}"
