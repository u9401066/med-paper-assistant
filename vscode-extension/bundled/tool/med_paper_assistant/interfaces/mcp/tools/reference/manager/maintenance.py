"""Handlers that rebuild Foam files and delete references."""

import os
from typing import Optional

from med_paper_assistant.infrastructure.persistence import ReferenceManager

from ..._shared import log_agent_misuse, log_tool_call, log_tool_result
from ._deps import REFERENCE, project_context_error


def _migrate_reference_dirs(
    ref_manager: ReferenceManager, refs_dir: str
) -> tuple[list[str], list[str], list[str]]:
    migrated: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for pmid_dir in os.listdir(refs_dir):
        pmid_path = os.path.join(refs_dir, pmid_dir)
        if not os.path.isdir(pmid_path):
            continue

        metadata = ref_manager.get_metadata(pmid_dir)
        if not metadata:
            continue

        citation_key = metadata.get("citation_key") or ref_manager._generate_citation_key(metadata)
        new_md_path = os.path.join(pmid_path, f"{citation_key}.md")
        old_content_path = os.path.join(pmid_path, "content.md")

        # Check if new format already exists
        if os.path.exists(new_md_path):
            skipped.append(citation_key)
            continue

        try:
            # Regenerate content with new format (includes aliases)
            metadata["citation"] = ref_manager._format_citation(metadata)
            metadata["citation_key"] = citation_key
            content = ref_manager._generate_content_md(metadata)

            # Write new file
            with open(new_md_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Remove old content.md if exists
            if os.path.exists(old_content_path):
                os.remove(old_content_path)

            migrated.append(citation_key)

        except Exception as e:
            errors.append(f"{pmid_dir}: {str(e)}")

    return migrated, skipped, errors


def _remove_root_aliases(refs_dir: str) -> int:
    root_aliases_removed = 0
    for filename in os.listdir(refs_dir):
        if filename.endswith(".md") and not os.path.isdir(os.path.join(refs_dir, filename)):
            try:
                os.remove(os.path.join(refs_dir, filename))
                root_aliases_removed += 1
            except Exception:  # nosec B110 - ignore cleanup errors
                pass
    return root_aliases_removed


def _render_foam_report(
    migrated: list[str], skipped: list[str], errors: list[str], root_aliases_removed: int
) -> str:
    output = "📚 **Foam Migration Complete**\n\n"
    output += f"✅ Migrated: {len(migrated)} references\n"
    output += f"⏭️ Skipped: {len(skipped)} (already new format)\n"
    if root_aliases_removed:
        output += f"🧹 Cleaned: {root_aliases_removed} old root aliases\n"

    if errors:
        output += f"\n⚠️ Errors: {len(errors)}\n"
        for err in errors[:5]:
            output += f"  - {err}\n"

    if migrated:
        output += "\n**Migrated references:**\n"
        for key in migrated[:10]:
            output += f"- `[[{key}]]`\n"
        if len(migrated) > 10:
            output += f"- ... and {len(migrated) - 10} more\n"

    output += (
        "\n💡 New structure: `references/{pmid}/{citation_key}.md` with aliases in frontmatter"
    )
    return output


def rebuild_foam_aliases(project: Optional[str] = None) -> str:
    """
    Rebuild Foam-compatible markdown files for all references (2025-12 format).

    Args:
        project: Project slug (uses current project if omitted)
    """
    ref_manager = REFERENCE.get().ref_manager
    project_error = project_context_error(project)
    if project_error:
        return project_error

    refs_dir = ref_manager.base_dir
    if not os.path.exists(refs_dir):
        return f"❌ References directory not found: {refs_dir}"

    migrated, skipped, errors = _migrate_reference_dirs(ref_manager, refs_dir)

    # Clean up old root-level alias files
    root_aliases_removed = _remove_root_aliases(refs_dir)

    return _render_foam_report(migrated, skipped, errors, root_aliases_removed)


def _render_delete_preview(result: dict, pmid: str) -> str:
    output = "⚠️ **即將刪除文獻 (Preview)**\n\n"
    output += f"**PMID**: {result['pmid']}\n"
    output += f"**標題**: {result['title']}\n"
    output += f"**Citation Key**: `[[{result['citation_key']}]]`\n\n"
    output += "**將刪除的檔案**:\n"
    for f in result.get("files_to_delete", []):
        output += f"  - {f}\n"
    output += "\n⚠️ 此操作無法復原！\n"
    output += '請使用 `delete_reference(pmid="{}", confirm=True)` 確認刪除。'.format(pmid)
    return output


def _render_delete_success(result: dict) -> str:
    output = "✅ **已刪除文獻**\n\n"
    output += f"**PMID**: {result['pmid']}\n"
    output += f"**標題**: {result['title']}\n"
    output += f"**Citation Key**: `[[{result['citation_key']}]]`\n\n"
    output += "**已刪除的檔案**:\n"
    for f in result.get("deleted_files", []):
        output += f"  - {f}\n"
    output += "\n💡 提示：如果其他草稿中有引用此文獻 (`[[{}]]`)，請記得更新。".format(
        result["citation_key"]
    )
    return output


def delete_reference(pmid: str, confirm: bool = False, project: Optional[str] = None) -> str:
    """
    ⚠️ DESTRUCTIVE: Delete a reference and all associated files.

    Args:
        pmid: PubMed ID to delete
        confirm: False=preview, True=actually delete
        project: Project slug (uses current if omitted)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call("delete_reference", {"pmid": pmid, "confirm": confirm, "project": project})

    project_error = project_context_error(project)
    if project_error:
        log_agent_misuse(
            "delete_reference",
            "valid project slug",
            {"pmid": pmid, "project": project},
            project_error,
        )
        return project_error

    result = ref_manager.delete_reference(pmid, confirm=confirm)
    log_tool_result("delete_reference", result)

    if result.get("requires_confirmation"):
        # Preview mode
        return _render_delete_preview(result, pmid)

    elif result.get("success"):
        # Deletion successful
        return _render_delete_success(result)

    else:
        # Error
        return f"❌ {result.get('error', '未知錯誤')}"
