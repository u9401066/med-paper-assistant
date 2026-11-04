"""Handlers that archive or permanently delete projects."""

from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE

from ..._shared import log_agent_misuse, log_tool_call, log_tool_error, log_tool_result
from .._deps import PROJECT_MANAGER


def archive_project(slug: str, confirm: bool = False) -> str:
    """
    Archive project (soft delete). Data preserved, can restore manually.

    Args:
        slug: Project slug to archive
        confirm: False=preview, True=execute
    """
    project_manager = PROJECT_MANAGER.get()
    import shutil
    from datetime import datetime

    log_tool_call("archive_project", {"slug": slug, "confirm": confirm})

    # Get project info
    result = project_manager.get_project_info(slug)
    if not result.get("success"):
        error_msg = f"❌ Project '{slug}' not found.\n\n"
        error_msg += "Use `list_projects()` to see available projects."
        log_agent_misuse("archive_project", "valid project slug", {"slug": slug}, error_msg)
        return error_msg

    name = result.get("name", slug)
    stats = result.get("stats", {})
    paths = result.get("paths", {})
    project_path = paths.get("root", "")

    if not confirm:
        # Preview mode
        output = "⚠️ **即將封存專案 (Preview)**\n\n"
        output += f"**專案名稱**: {name}\n"
        output += f"**Slug**: {slug}\n"
        output += f"**狀態**: {result.get('status', 'unknown')}\n\n"
        output += "**統計**:\n"
        if result.get("workflow_mode", DEFAULT_WORKFLOW_MODE) == "library-wiki":
            output += f"  - 📥 Inbox notes: {stats.get('inbox', 0)} files\n"
            output += f"  - 🧠 Concept notes: {stats.get('concepts', 0)} files\n"
            output += f"  - 🗂️ Synthesis projects: {stats.get('projects', 0)} files\n"
            output += f"  - 📚 文獻: {stats.get('references', 0)} saved\n\n"
        else:
            output += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            output += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            output += f"  - 📊 資料: {stats.get('data_files', 0)} files\n\n"
        output += "**封存後**:\n"
        output += f"  - 專案將被重命名為 `_archived_{{timestamp}}_{slug}`\n"
        output += "  - 所有資料都會保留\n"
        output += "  - 可以手動還原\n\n"
        output += f'請使用 `archive_project(slug="{slug}", confirm=True)` 確認封存。'
        log_tool_result("archive_project", "preview shown", success=True)
        return output

    # Actually archive
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived_slug = f"_archived_{timestamp}_{slug}"
        archived_path = project_manager.projects_dir / archived_slug

        # Move the project directory
        shutil.move(project_path, archived_path)

        # Clear current if this was the current project
        if project_manager.get_current_project() == slug:
            if project_manager.state_file.exists():
                project_manager.state_file.unlink()

        result_msg = "✅ **已封存專案**\n\n"
        result_msg += f"**原專案**: {name} (`{slug}`)\n"
        result_msg += f"**封存名稱**: `{archived_slug}`\n"
        result_msg += f"**封存位置**: `{archived_path}`\n\n"
        result_msg += "**已封存內容**:\n"
        if result.get("workflow_mode", DEFAULT_WORKFLOW_MODE) == "library-wiki":
            result_msg += f"  - 📥 Inbox notes: {stats.get('inbox', 0)} files\n"
            result_msg += f"  - 🧠 Concept notes: {stats.get('concepts', 0)} files\n"
            result_msg += f"  - 🗂️ Synthesis projects: {stats.get('projects', 0)} files\n"
            result_msg += f"  - 📚 文獻: {stats.get('references', 0)} saved\n\n"
        else:
            result_msg += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            result_msg += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            result_msg += f"  - 📊 資料: {stats.get('data_files', 0)} files\n\n"
        result_msg += "💡 如需還原，請手動將資料夾重新命名為原始 slug。"

        log_tool_result("archive_project", f"archived {slug}", success=True)
        return result_msg

    except Exception as e:
        error_msg = f"❌ 封存失敗: {str(e)}"
        log_tool_error("archive_project", e, {"slug": slug})
        return error_msg


def delete_project(slug: str, confirm: bool = False) -> str:
    """
    ⚠️ PERMANENTLY delete project. Cannot undo! Use archive_project for soft delete.

    Args:
        slug: Project slug to delete
        confirm: False=preview, True=execute
    """
    project_manager = PROJECT_MANAGER.get()
    log_tool_call("delete_project", {"slug": slug, "confirm": confirm})

    # Get project info
    result = project_manager.get_project_info(slug)
    if not result.get("success"):
        error_msg = f"❌ Project '{slug}' not found.\n\n"
        error_msg += "Use `list_projects()` to see available projects."
        log_agent_misuse("delete_project", "valid project slug", {"slug": slug}, error_msg)
        return error_msg

    name = result.get("name", slug)
    stats = result.get("stats", {})
    paths = result.get("paths", {})

    if not confirm:
        # Preview mode
        output = "⚠️ **即將永久刪除專案 (Preview)**\n\n"
        output += f"**專案名稱**: {name}\n"
        output += f"**Slug**: {slug}\n"
        output += f"**狀態**: {result.get('status', 'unknown')}\n\n"
        output += "**將被刪除的內容**:\n"
        if result.get("workflow_mode", DEFAULT_WORKFLOW_MODE) == "library-wiki":
            output += f"  - 📥 Inbox notes: {stats.get('inbox', 0)} files\n"
            output += f"  - 🧠 Concept notes: {stats.get('concepts', 0)} files\n"
            output += f"  - 🗂️ Synthesis projects: {stats.get('projects', 0)} files\n"
            output += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
        else:
            output += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            output += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            output += f"  - 📊 資料: {stats.get('data_files', 0)} files\n"
        output += f"  - 📁 整個專案目錄: `{paths.get('root', '')}`\n\n"
        output += "⛔ **此操作無法復原！所有資料將永久消失！**\n\n"
        output += "💡 建議改用 `archive_project` 進行軟刪除。\n\n"
        output += f'如確定要刪除，請使用 `delete_project(slug="{slug}", confirm=True)`'
        log_tool_result("delete_project", "preview shown", success=True)
        return output

    # Actually delete
    delete_result = project_manager.delete_project(slug, confirm=True)

    if delete_result.get("success"):
        result_msg = "🗑️ **已永久刪除專案**\n\n"
        result_msg += f"**專案名稱**: {name}\n"
        result_msg += f"**Slug**: {slug}\n\n"
        result_msg += "**已刪除的內容**:\n"
        if result.get("workflow_mode", DEFAULT_WORKFLOW_MODE) == "library-wiki":
            result_msg += f"  - 📥 Inbox notes: {stats.get('inbox', 0)} files\n"
            result_msg += f"  - 🧠 Concept notes: {stats.get('concepts', 0)} files\n"
            result_msg += f"  - 🗂️ Synthesis projects: {stats.get('projects', 0)} files\n"
            result_msg += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
        else:
            result_msg += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            result_msg += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            result_msg += f"  - 📊 資料: {stats.get('data_files', 0)} files\n"
        log_tool_result("delete_project", f"deleted {slug}", success=True)
        return result_msg
    else:
        error_msg = f"❌ {delete_result.get('error', '未知錯誤')}"
        log_tool_result("delete_project", error_msg, success=False)
        return error_msg
