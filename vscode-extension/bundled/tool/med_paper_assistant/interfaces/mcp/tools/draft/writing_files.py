"""
Draft File Operations

write_draft, list_drafts, read_draft and delete_draft implementations.
"""

import os
import re
from collections.abc import Callable
from typing import Optional

from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.drafter import (
    draft_filename_from_section,
    normalize_draft_filename,
)
from med_paper_assistant.shared.path_guard import resolve_child_path

from .._shared import (
    auto_checkpoint_writing,
    get_drafts_dir,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)
from .writing_gates import (
    _check_section_prerequisites,
    _guard_writing_tool,
    _write_gate_error,
)


def _validate_wikilinks_in_content(content: str, references_dir: Optional[str] = None) -> tuple:
    """
    驗證內容中的 wikilinks 並自動修復。

    Returns:
        Tuple of (fixed_content: str, report: str or None)
    """
    result, fixed_content = validate_wikilinks_in_content(
        content, references_dir=references_dir, auto_fix=True
    )

    report = None
    if result.auto_fixed > 0:
        report = f"🔧 自動修復 {result.auto_fixed} 個 wikilink 格式錯誤"
    elif result.issues:
        report = result.to_report()

    return fixed_content, report


def _section_title(filename: str) -> str:
    return (
        os.path.splitext(os.path.basename(filename))[0].replace("_", " ").replace("-", " ").title()
    )


def _validated_write_request(
    filename: str, content: str, section: Optional[str]
) -> tuple[str, str]:
    """Validate write_draft inputs; return (normalized filename, error)."""
    raw_filename = filename.strip() or draft_filename_from_section(section)
    if not raw_filename:
        error_msg = "❌ write_draft requires either `filename` or `section`."
        log_tool_result("write_draft", "missing filename", success=False)
        return "", error_msg

    if not content.strip():
        error_msg = "❌ write_draft requires non-empty `content`."
        log_tool_result("write_draft", "empty content", success=False)
        return "", error_msg

    try:
        filename = normalize_draft_filename(raw_filename)
    except ValueError as e:
        error_msg = f"❌ Invalid draft filename: {e}"
        log_tool_result("write_draft", "invalid filename", success=False)
        return "", error_msg
    return filename, ""


def _project_references_dir() -> Optional[str]:
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if current_info and current_info.get("project_path"):
        return os.path.join(str(current_info["project_path"]), "references")
    return None


def _write_result(
    path: str, is_concept_file: bool, wikilink_report: Optional[str], prereq_warning: str
) -> str:
    reminder = ""
    if not is_concept_file:
        reminder = (
            "\n\n📝 **Protected Content Reminder:**\n"
            "- 🔒 NOVELTY STATEMENT must be reflected in Introduction\n"
            "- 🔒 KEY SELLING POINTS must be emphasized in Discussion\n"
            "- Ask user before modifying any protected content"
        )

    # 附加 wikilink 修復報告
    if wikilink_report:
        reminder += f"\n\n{wikilink_report}"

    # 附加寫作順序建議
    if prereq_warning:
        reminder += f"\n\n{prereq_warning}"

    return f"Draft created successfully at: {path}{reminder}"


def _write_draft(
    drafter: Drafter,
    hooks_runner: Callable[[str, str], str],
    filename: str,
    content: str,
    project: Optional[str],
    skip_validation: bool,
    section: Optional[str],
) -> str:
    content = content or ""
    log_tool_call(
        "write_draft",
        {
            "filename": filename,
            "content_len": len(content),
            "project": project,
            "skip_validation": skip_validation,
            "section": section,
        },
    )

    filename, request_error = _validated_write_request(filename, content, section)
    if request_error:
        return request_error

    guard_error = _guard_writing_tool("write_draft", project)
    if guard_error is not None:
        return guard_error

    is_concept_file = "concept" in filename.lower()

    gate_error = _write_gate_error(skip_validation, is_concept_file)
    if gate_error is not None:
        return gate_error

    # Check writing order prerequisites (advisory, non-blocking)
    prereq_warning = ""
    if not is_concept_file:
        prereq_warning = _check_section_prerequisites(_section_title(filename))

    return _save_draft(drafter, hooks_runner, filename, content, is_concept_file, prereq_warning)


def _save_draft(
    drafter: Drafter,
    hooks_runner: Callable[[str, str], str],
    filename: str,
    content: str,
    is_concept_file: bool,
    prereq_warning: str,
) -> str:
    # 🔧 Pre-check: 驗證並修復 wikilink 格式
    references_dir = _project_references_dir()
    fixed_content, wikilink_report = _validate_wikilinks_in_content(content, references_dir)

    try:
        path = drafter.create_draft(filename, fixed_content)

        # Auto-checkpoint writing session for compaction recovery
        auto_checkpoint_writing(filename, fixed_content, "write")

        result = _write_result(path, is_concept_file, wikilink_report, prereq_warning)

        # 🔒 Embedded post-write hooks (auto-run, agent cannot skip)
        if not is_concept_file:
            result += hooks_runner(fixed_content, _section_title(filename))

        log_tool_result("write_draft", result, success=True)
        return result
    except Exception as e:
        log_tool_error("write_draft", e, {"filename": filename, "content_len": len(content)})
        return f"Error creating draft: {str(e)}"


def _draft_table_row(index: int, drafts_dir: str, draft_file: str) -> str:
    draft_path = os.path.join(drafts_dir, draft_file)
    try:
        with open(draft_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = len(re.findall(r"^#+\s+", content, re.MULTILINE))
        words = len([w for w in content.split() if w.strip()])

        return f"| {index} | {draft_file} | {sections} | {words} |\n"
    except Exception:
        return f"| {index} | {draft_file} | Error | - |\n"


def _list_drafts(project: Optional[str]) -> str:
    log_tool_call("list_drafts", {"project": project})

    guard_error = _guard_writing_tool("list_drafts", project, always_validate=False)
    if guard_error is not None:
        return guard_error

    drafts_dir = get_drafts_dir()
    if not drafts_dir:
        drafts_dir = "drafts"
    if not os.path.exists(drafts_dir):
        result = "📁 No drafts/ directory found. Create drafts using write_draft tool first."
        log_tool_result("list_drafts", result, success=True)
        return result

    drafts = [f for f in os.listdir(drafts_dir) if f.endswith(".md")]

    if not drafts:
        result = "📁 No draft files found in drafts/ directory."
        log_tool_result("list_drafts", result, success=True)
        return result

    output = "📄 **Available Drafts**\n\n"
    output += "| # | Filename | Sections | Total Words |\n"
    output += "|---|----------|----------|-------------|\n"

    for i, draft_file in enumerate(sorted(drafts), 1):
        output += _draft_table_row(i, drafts_dir, draft_file)

    log_tool_result("list_drafts", f"found {len(drafts)} drafts", success=True)
    return output


def _draft_path(safe_filename: str) -> str:
    drafts_dir = get_drafts_dir() or "drafts"
    return str(
        resolve_child_path(
            drafts_dir,
            safe_filename,
            field_name="Draft filename",
            allowed_suffixes={".md"},
        )
    )


def _split_sections(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_section: Optional[str] = None
    current_content: list[str] = []

    for line in content.split("\n"):
        if line.startswith("#"):
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content)
            section_name = re.sub(r"^#+\s*\d*\.?\s*", "", line).strip()
            current_section = section_name if section_name else "Untitled"
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section and current_content:
        sections[current_section] = "\n".join(current_content)
    return sections


def _sections_report(filename: str, sections: dict[str, str]) -> str:
    output = f"📝 **Draft: {os.path.basename(filename)}**\n\n"
    output += "| Section | Word Count | Preview |\n"
    output += "|---------|------------|----------|\n"

    for sec_name, sec_content in sections.items():
        words = len([w for w in sec_content.split() if w.strip()])
        preview = sec_content[:50].replace("\n", " ").strip() + "..."
        output += f"| {sec_name} | {words} | {preview} |\n"

    output += "\n---\n\n"
    output += "**Full Content by Section:**\n\n"

    for sec_name, sec_content in sections.items():
        output += f"### {sec_name}\n\n"
        output += sec_content.strip()[:500]
        if len(sec_content) > 500:
            output += f"\n\n*... ({len(sec_content)} characters total)*"
        output += "\n\n"
    return output


def _read_draft(filename: str, project: Optional[str]) -> str:
    log_tool_call("read_draft", {"filename": filename, "project": project})

    guard_error = _guard_writing_tool("read_draft", project, always_validate=False)
    if guard_error is not None:
        return guard_error

    try:
        safe_filename = normalize_draft_filename(filename)
    except ValueError as e:
        result = f"❌ Invalid draft filename: {e}"
        log_tool_result("read_draft", result, success=False)
        return result

    filename = _draft_path(safe_filename)

    if not os.path.exists(filename):
        result = f"Error: Draft file not found: {filename}"
        log_tool_result("read_draft", result, success=False)
        return result

    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        sections = _split_sections(content)
        output = _sections_report(filename, sections)

        log_tool_result(
            "read_draft", f"read {len(sections)} sections from {filename}", success=True
        )
        return output
    except Exception as e:
        log_tool_error("read_draft", e, {"filename": filename})
        return f"Error reading draft: {str(e)}"


def _delete_preview(
    basename: str, filename: str, word_count: int, sections: int, file_size: int
) -> str:
    output = "⚠️ **即將刪除草稿 (Preview)**\n\n"
    output += f"**檔案名稱**: {basename}\n"
    output += f"**路徑**: {filename}\n"
    output += f"**字數**: {word_count} words\n"
    output += f"**章節數**: {sections} sections\n"
    output += f"**檔案大小**: {file_size:,} bytes\n"
    output += "\n⚠️ 此操作無法復原！\n"
    output += f'請使用 `delete_draft(filename="{basename}", confirm=True)` 確認刪除。'
    log_tool_result("delete_draft", "preview shown", success=True)
    return output


def _remove_draft(filename: str, basename: str, word_count: int, sections: int) -> str:
    try:
        os.remove(filename)
        result = "✅ **已刪除草稿**\n\n"
        result += f"**檔案名稱**: {basename}\n"
        result += f"**已刪除字數**: {word_count} words\n"
        result += f"**已刪除章節數**: {sections} sections\n"
        log_tool_result("delete_draft", f"deleted {basename}", success=True)
        return result
    except Exception as e:
        error_msg = f"❌ 刪除失敗: {str(e)}"
        log_tool_error("delete_draft", e, {"filename": filename})
        return error_msg


def _delete_draft(filename: str, confirm: bool, project: Optional[str]) -> str:
    log_tool_call("delete_draft", {"filename": filename, "confirm": confirm, "project": project})

    guard_error = _guard_writing_tool("delete_draft", project, always_validate=False)
    if guard_error is not None:
        return guard_error

    # Resolve the full path
    try:
        safe_filename = normalize_draft_filename(filename)
    except ValueError as e:
        error_msg = f"❌ Invalid draft filename: {e}"
        log_tool_result("delete_draft", error_msg, success=False)
        return error_msg

    filename = _draft_path(safe_filename)

    if not os.path.exists(filename):
        error_msg = f"❌ Draft file not found: {filename}"
        log_tool_result("delete_draft", error_msg, success=False)
        return error_msg

    # Get file info
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        word_count = len([w for w in content.split() if w.strip()])
        sections = len(re.findall(r"^#+\s+", content, re.MULTILINE))
        file_size = os.path.getsize(filename)
    except Exception as e:
        error_msg = f"❌ Error reading draft: {str(e)}"
        log_tool_error("delete_draft", e, {"filename": filename})
        return error_msg

    basename = os.path.basename(filename)

    if not confirm:
        return _delete_preview(basename, filename, word_count, sections, file_size)

    return _remove_draft(filename, basename, word_count, sections)
