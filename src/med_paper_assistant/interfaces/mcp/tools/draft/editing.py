"""
Draft Editing Tools — Citation-Aware Partial Editing

Layer 1: get_available_citations — List all valid citation keys before editing
Layer 2: patch_draft — Partial edit with wikilink validation

These tools solve the problem of citation correctness when Agent uses
partial edits (replace_string_in_file) instead of whole-file write_draft().
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.services.wikilink_validator import (
    ALL_WIKILINK_PATTERN,
    VALID_WIKILINK_PATTERN,
    find_citation_key_for_pmid,
    validate_wikilinks_in_content,
)
from med_paper_assistant.infrastructure.persistence.draft_snapshot_manager import (
    DraftSnapshotManager,
)
from med_paper_assistant.infrastructure.persistence.git_auto_committer import GitAutoCommitter
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    auto_checkpoint_writing,
    ensure_project_context,
    get_drafts_dir,
    get_project_list_for_prompt,
    get_project_path,
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


def register_editing_tools(mcp: FastMCP, drafter: Drafter):
    """Register citation-aware editing tools."""

    @mcp.tool()
    def get_available_citations(project: Optional[str] = None) -> str:
        """
        List all valid citation keys from saved references.
        ⚠️ MUST call this before editing drafts with citations!

        Returns a table of [[citation_key]] with author, year, title, PMID.
        Use these exact keys when inserting wikilinks in drafts.

        Args:
            project: Project slug (uses current if omitted)
        """
        log_tool_call("get_available_citations", {"project": project})

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "get_available_citations",
                    "valid project context",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        refs_dir = _get_references_dir()
        if not refs_dir or not os.path.exists(refs_dir):
            result = (
                "📚 **No references found.**\n\n"
                'Save references first using `save_reference_mcp(pmid="...")` '
                "before adding citations to drafts."
            )
            log_tool_result("get_available_citations", "no references dir", success=True)
            return result

        ref_manager = drafter.ref_manager
        pmids = ref_manager.list_references()

        if not pmids:
            result = (
                "📚 **No references saved yet.**\n\n"
                'Save references first using `save_reference_mcp(pmid="...")` '
                "before adding citations to drafts."
            )
            log_tool_result("get_available_citations", "empty", success=True)
            return result

        output = f"📚 **Available Citations ({len(pmids)} references)**\n\n"
        output += "Use these exact `[[citation_key]]` wikilinks in drafts:\n\n"
        output += "| Citation Key | PMID | First Author | Year | Title |\n"
        output += "|-------------|------|--------------|------|-------|\n"

        valid_keys = []
        for pmid in sorted(pmids):
            meta = ref_manager.get_metadata(pmid)
            if not meta:
                continue

            citation_key = meta.get("citation_key", "")
            if not citation_key:
                # Try to find from directory structure
                citation_key = find_citation_key_for_pmid(pmid, refs_dir) or pmid

            title = meta.get("title", "Unknown")
            if len(title) > 50:
                title = title[:47] + "..."

            # Extract first author
            first_author = ""
            authors_full = meta.get("authors_full", [])
            authors = meta.get("authors", [])
            if authors_full and isinstance(authors_full[0], dict):
                first_author = authors_full[0].get("last_name", "")
            elif authors:
                first_author = authors[0].split()[0] if authors[0] else ""

            year = meta.get("year", "")

            output += f"| `[[{citation_key}]]` | {pmid} | {first_author} | {year} | {title} |\n"
            valid_keys.append(citation_key)

        output += "\n---\n"
        output += "💡 **Usage**: Insert `[[citation_key]]` in draft text.\n"
        output += "💡 **Workflow**: Call `get_available_citations` → edit draft with `patch_draft` → `sync_references`\n"

        log_tool_result(
            "get_available_citations", f"listed {len(valid_keys)} citations", success=True
        )
        return output

    @mcp.tool()
    def patch_draft(
        filename: str,
        old_text: str,
        new_text: str,
        project: Optional[str] = None,
    ) -> str:
        """
        Partially edit a draft with citation validation.
        Replaces old_text with new_text, validating all [[wikilinks]] in new_text.

        Use this instead of replace_string_in_file for draft files!

        Args:
            filename: Draft filename (e.g., "introduction.md")
            old_text: Exact text to find and replace (must match uniquely)
            new_text: Replacement text (wikilinks will be validated/auto-fixed)
            project: Project slug (uses current if omitted)
        """
        log_tool_call(
            "patch_draft",
            {
                "filename": filename,
                "old_text_len": len(old_text),
                "new_text_len": len(new_text),
                "project": project,
            },
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "patch_draft",
                    "valid project context",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        # 1. Resolve file path
        drafts_dir = get_drafts_dir()
        if not drafts_dir:
            drafts_dir = "drafts"

        if os.path.isabs(filename):
            filepath = filename
        else:
            filepath = os.path.join(drafts_dir, filename)
            if not filepath.endswith(".md"):
                filepath += ".md"

        if not os.path.exists(filepath):
            error_msg = f"❌ Draft file not found: {filepath}"
            log_tool_result("patch_draft", error_msg, success=False)
            return error_msg

        # 2. Read current content
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            log_tool_error("patch_draft", e, {"filepath": filepath})
            return f"❌ Error reading draft: {e}"

        # 3. Verify old_text matches uniquely
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

        # 4. Validate wikilinks in new_text
        references_dir = _get_references_dir()
        new_wikilinks = ALL_WIKILINK_PATTERN.findall(new_text)

        validation_report = []
        fixed_new_text = new_text

        if new_wikilinks:
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

                missing = []
                for wl in remaining_wikilinks:
                    # Extract PMID from wikilink
                    pmid = None
                    if wl.isdigit():
                        pmid = wl
                    elif "_" in wl:
                        parts = wl.split("_")
                        potential = parts[-1]
                        if potential.isdigit():
                            pmid = potential
                    elif wl.upper().startswith("PMID:"):
                        pmid = wl.split(":")[1].strip()

                    if pmid and not ref_manager.check_reference_exists(pmid):
                        missing.append(f"[[{wl}]]")

                if missing:
                    unique_missing = list(dict.fromkeys(missing))
                    error_msg = (
                        "❌ **Citation(s) not found in saved references:**\n\n"
                        + "\n".join(f"- {m}" for m in unique_missing)
                        + "\n\n"
                        'Save these references first with `save_reference_mcp(pmid="...")`, '
                        "or call `get_available_citations()` to see valid keys."
                    )
                    log_tool_result("patch_draft", "missing references", success=False)
                    return error_msg

        # 5. Apply the patch
        new_content = content.replace(old_text, fixed_new_text, 1)

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
        auto_checkpoint_writing(
            os.path.basename(filepath), new_content, "patch"
        )

        # Auto-commit after successful write
        if drafts_dir:
            project_root = os.path.dirname(drafts_dir)
            git_committer = GitAutoCommitter(project_root)
            git_committer.commit_draft(os.path.basename(filepath), reason="patch_draft")

        # 6. Build result report
        output = "✅ **Draft patched successfully**\n\n"
        output += f"📄 File: `{filepath}`\n"
        output += f"📝 Replaced {len(old_text)} chars → {len(fixed_new_text)} chars\n"

        if new_wikilinks:
            valid_wl = [
                wl
                for wl in ALL_WIKILINK_PATTERN.findall(fixed_new_text)
                if VALID_WIKILINK_PATTERN.match(f"[[{wl}]]")
            ]
            output += f"📚 Citations in patch: {len(valid_wl)} wikilinks validated\n"

        if validation_report:
            output += "\n" + "\n".join(validation_report) + "\n"

        output += "\n💡 Run `sync_references` to update the References section."

        log_tool_result("patch_draft", f"patched {filepath}", success=True)
        return output
