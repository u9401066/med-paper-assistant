"""Draft loading for the formatting check."""

import os

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import PathGuardError, resolve_child_path

from ..._shared import get_drafts_dir, log_tool_error


def read_drafts(filenames: list[str], drafter: Drafter) -> tuple[str, str | None]:
    """Concatenate the requested drafts; the second item is an error message on failure."""
    all_content = ""
    drafts_dir = get_drafts_dir() or drafter.drafts_dir

    for raw_fname in filenames:
        try:
            fname = normalize_draft_filename(raw_fname)
            fpath = resolve_child_path(drafts_dir, fname, field_name="draft filename")
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"Draft file {fname} not found in {drafts_dir}.")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            all_content += content + "\n\n"
        except (PathGuardError, ValueError) as e:
            return "", f"❌ Invalid draft filename: {e}"
        except FileNotFoundError:
            return "", f"❌ Draft not found: {fname}. Use `list_drafts` to see available files."
        except Exception as e:
            log_tool_error("check_formatting", e, {"draft_filename": fname})
            return "", f"❌ Error reading draft: {e}"
    return all_content, None
