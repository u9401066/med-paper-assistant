"""Draft filename derivation and validation helpers."""

import re

from med_paper_assistant.shared.path_guard import PathGuardError, normalize_relative_filename


def draft_filename_from_section(section: str | None) -> str:
    """Derive a stable draft filename from a paper section label."""
    if not section:
        return ""

    slug = re.sub(r"[^a-z0-9]+", "_", str(section).strip().lower()).strip("_")
    if not slug:
        return ""
    return f"{slug}.md"


def normalize_draft_filename(filename: str | None) -> str:
    """Validate and normalize a draft filename for cross-platform safety."""
    try:
        return normalize_relative_filename(
            filename,
            field_name="Draft filename",
            default_suffix=".md",
            allowed_suffixes={".md"},
        )
    except PathGuardError as e:
        raise ValueError(str(e)) from e
