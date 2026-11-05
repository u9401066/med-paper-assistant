"""
Draft Patch Implementation

Shared guard/path helpers and the patch_draft implementation used by editing.py.
"""

import os
from typing import Any, Optional

from med_paper_assistant.domain.services.wikilink_validator import (
    ALL_WIKILINK_PATTERN,
    VALID_WIKILINK_PATTERN,
    validate_wikilinks_in_content,
)
from med_paper_assistant.infrastructure.persistence.draft_snapshot_manager import (
    DraftSnapshotManager,
)
from med_paper_assistant.infrastructure.persistence.git_auto_committer import GitAutoCommitter
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import resolve_child_path

from .._shared import (
    auto_checkpoint_writing,
    get_drafts_dir,
    get_project_path,
    guard_manuscript_tool,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)


def _get_references_dir() -> Optional[str]:
    """Get the current project's references directory."""
    project_path = get_project_path()
    if project_path:
        return os.path.join(project_path, "references")
    return None


def _load_patch_target(filename: str, drafts_dir: str) -> tuple[str, str, str]:
    """Resolve and read the draft; return (filepath, content, error)."""
    try:
        safe_filename = normalize_draft_filename(filename)
    except ValueError as e:
        error_msg = f"❌ Invalid draft filename: {e}"
        log_tool_result("patch_draft", "invalid filename", success=False)
        return "", "", error_msg

    filepath = str(
        resolve_child_path(
            drafts_dir,
            safe_filename,
            field_name="Draft filename",
            allowed_suffixes={".md"},
        )
    )

    if not os.path.exists(filepath):
        error_msg = f"❌ Draft file not found: {filepath}"
        log_tool_result("patch_draft", error_msg, success=False)
        return filepath, "", error_msg

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return filepath, f.read(), ""
    except Exception as e:
        log_tool_error("patch_draft", e, {"filepath": filepath})
        return filepath, "", f"❌ Error reading draft: {e}"


def _match_error(content: str, old_text: str, filepath: str) -> str:
    """Verify old_text matches uniquely; return an error message or ""."""
    match_count = content.count(old_text)
    if match_count == 0:
        error_msg = (
            "❌ **old_text not found in draft.**\n\n"
            f"File: `{filepath}`\n"
            "Make sure the text matches exactly (including whitespace and newlines).\n"
            "Use `read_draft` to check the current content."
        )
        log_tool_result("patch_draft", "old_text not found", success=False)
        return error_msg

    if match_count > 1:
        error_msg = (
            f"❌ **old_text matches {match_count} locations** — must be unique.\n\n"
            "Include more surrounding context to make old_text unique."
        )
        log_tool_result("patch_draft", f"ambiguous: {match_count} matches", success=False)
        return error_msg
    return ""


def _protected_content_error(old_text: str, filename: str, is_concept_file: bool) -> str:
    """B2 Protected Content Guard — block modification of 🔒-marked content."""
    if is_concept_file and "\U0001f512" in old_text:
        error_msg = (
            "❌ **BLOCKED: Cannot modify 🔒-protected content via patch_draft.**\n\n"
            "The old_text contains 🔒-marked protected content (NOVELTY STATEMENT "
            "or KEY SELLING POINTS). These sections require explicit user approval.\n\n"
            "Ask the user before modifying protected sections in concept.md."
        )
        log_agent_misuse(
            "patch_draft",
            "attempted to modify 🔒-protected content",
            {"filename": filename},
            error_msg,
        )
        return error_msg
    return ""


def _wikilink_pmid(wikilink: str) -> Optional[str]:
    if wikilink.isdigit():
        return wikilink
    if "_" in wikilink:
        potential = wikilink.split("_")[-1]
        return potential if potential.isdigit() else None
    if wikilink.upper().startswith("PMID:"):
        return wikilink.split(":")[1].strip()
    return None


def _missing_citations(wikilinks: list[str], ref_manager: Any) -> list[str]:
    missing = []
    for wl in wikilinks:
        pmid = _wikilink_pmid(wl)
        if pmid and not ref_manager.check_reference_exists(pmid):
            missing.append(f"[[{wl}]]")
    return missing


def _missing_citation_error(missing: list[str]) -> str:
    unique_missing = list(dict.fromkeys(missing))
    return (
        "❌ **Citation(s) not found in saved references:**\n\n"
        + "\n".join(f"- {m}" for m in unique_missing)
        + "\n\n"
        'Save these references first with `save_reference_mcp(pmid="...")`, '
        "or call `get_available_citations()` to see valid keys."
    )


def _validate_patch_wikilinks(new_text: str, drafter: Drafter) -> tuple[str, list[str], str]:
    """Validate/auto-fix wikilinks; return (fixed text, report lines, error)."""
    references_dir = _get_references_dir()
    validation_report: list[str] = []
    if not ALL_WIKILINK_PATTERN.findall(new_text):
        return new_text, validation_report, ""

    # Validate and auto-fix wikilinks
    result, fixed_new_text = validate_wikilinks_in_content(
        new_text, references_dir=references_dir, auto_fix=True
    )

    if result.auto_fixed > 0:
        validation_report.append(f"🔧 Auto-fixed {result.auto_fixed} wikilink format(s)")

    # Check if all wikilinks reference existing citations
    if references_dir and os.path.exists(references_dir):
        ref_manager = drafter.ref_manager
        remaining_wikilinks = ALL_WIKILINK_PATTERN.findall(fixed_new_text)
        missing = _missing_citations(remaining_wikilinks, ref_manager)
        if missing:
            log_tool_result("patch_draft", "missing references", success=False)
            return fixed_new_text, validation_report, _missing_citation_error(missing)
    return fixed_new_text, validation_report, ""


def _apply_patch(filepath: str, drafts_dir: str, new_content: str) -> str:
    """Snapshot, write, checkpoint and commit; return an error message or ""."""
    # Auto-snapshot before overwrite
    if drafts_dir:
        snap_mgr = DraftSnapshotManager(drafts_dir)
        snap_mgr.snapshot_before_write(os.path.basename(filepath), reason="patch_draft")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        log_tool_error("patch_draft", e, {"filepath": filepath})
        return f"❌ Error writing draft: {e}"

    # Auto-checkpoint writing session for compaction recovery
    auto_checkpoint_writing(os.path.basename(filepath), new_content, "patch")

    # Auto-commit after successful write
    if drafts_dir:
        project_root = os.path.dirname(drafts_dir)
        git_committer = GitAutoCommitter(project_root)
        git_committer.commit_draft(os.path.basename(filepath), reason="patch_draft")
    return ""


def _patch_report(
    filepath: str,
    old_text: str,
    new_text: str,
    fixed_new_text: str,
    validation_report: list[str],
) -> str:
    output = "✅ **Draft patched successfully**\n\n"
    output += f"📄 File: `{filepath}`\n"
    output += f"📝 Replaced {len(old_text)} chars → {len(fixed_new_text)} chars\n"

    if ALL_WIKILINK_PATTERN.findall(new_text):
        valid_wl = [
            wl
            for wl in ALL_WIKILINK_PATTERN.findall(fixed_new_text)
            if VALID_WIKILINK_PATTERN.match(f"[[{wl}]]")
        ]
        output += f"📚 Citations in patch: {len(valid_wl)} wikilinks validated\n"

    if validation_report:
        output += "\n" + "\n".join(validation_report) + "\n"

    output += "\n💡 Run `sync_references` to update the References section."
    return output


def _patch_hook_report(filepath: str, new_content: str) -> str:
    """🔒 Embedded post-write hooks (auto-run, agent cannot skip)."""
    from .writing import _run_embedded_post_write_hooks

    section_for_hooks = (
        os.path.splitext(os.path.basename(filepath))[0].replace("_", " ").replace("-", " ").title()
    )
    return _run_embedded_post_write_hooks(new_content, section_for_hooks)


def _patch_draft(
    drafter: Drafter, filename: str, old_text: str, new_text: str, project: Optional[str]
) -> str:
    log_tool_call(
        "patch_draft",
        {
            "filename": filename,
            "old_text_len": len(old_text),
            "new_text_len": len(new_text),
            "project": project,
        },
    )

    guard_error = guard_manuscript_tool("patch_draft", project)
    if guard_error:
        return guard_error

    # 1. Resolve file path + 2. Read current content
    drafts_dir = get_drafts_dir() or "drafts"
    filepath, content, error_msg = _load_patch_target(filename, drafts_dir)
    if error_msg:
        return error_msg

    # 3. Verify old_text matches uniquely + 3.5 B2 Protected Content Guard
    is_concept_file = "concept" in os.path.basename(filepath).lower()
    error_msg = _match_error(content, old_text, filepath) or _protected_content_error(
        old_text, filename, is_concept_file
    )
    if error_msg:
        return error_msg

    # 4. Validate wikilinks in new_text
    fixed_new_text, validation_report, error_msg = _validate_patch_wikilinks(new_text, drafter)
    if error_msg:
        return error_msg

    # 5. Apply the patch
    new_content = content.replace(old_text, fixed_new_text, 1)
    error_msg = _apply_patch(filepath, drafts_dir, new_content)
    if error_msg:
        return error_msg

    # 6. Build result report
    output = _patch_report(filepath, old_text, new_text, fixed_new_text, validation_report)
    if not is_concept_file:
        output += _patch_hook_report(filepath, new_content)

    log_tool_result("patch_draft", f"patched {filepath}", success=True)
    return output
