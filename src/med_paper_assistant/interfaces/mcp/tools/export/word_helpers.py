"""
Word Export Helpers

Session, verification and save helpers for the Word export tools.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.infrastructure.services import TemplateReader, WordWriter
from med_paper_assistant.shared.path_guard import resolve_child_path

_DEFAULT_WORD_LIMITS = {
    "Abstract": 250,
    "Introduction": 800,
    "Methods": 1500,
    "Materials and Methods": 1500,
    "Results": 1500,
    "Discussion": 1500,
    "Conclusions": 300,
}


def _project_label(project_info: Optional[dict]) -> str:
    return (project_info or {}).get("name", (project_info or {}).get("slug", "Unknown"))


def _create_session_document(
    template_reader: TemplateReader, word_writer: WordWriter, template_name: str
) -> tuple[Any, str, str]:
    """Create the session document; return (doc, safe template name, error)."""
    if not template_name:
        return word_writer.create_blank_document(), "", ""

    template_path = resolve_child_path(
        template_reader.templates_dir,
        template_name,
        field_name="template name",
        default_suffix=".docx",
        allowed_suffixes={".docx"},
    )
    if not template_path.exists():
        return None, "", f"Error: Template not found: {template_name}"
    doc = word_writer.create_document_from_template(str(template_path))
    return doc, template_path.name, ""


def _session_started_message(
    template_reader: TemplateReader,
    project_info: Optional[dict],
    session_id: str,
    safe_template_name: str,
) -> str:
    if safe_template_name:
        structure = template_reader.get_template_summary(safe_template_name)
        return (
            f"✅ Document session '{session_id}' started with template: {safe_template_name}\n\n"
            f"Project: {_project_label(project_info)}\n\n"
            f"{structure}"
        )
    else:
        return (
            f"✅ Document session '{session_id}' started with blank document. "
            f"Project: {_project_label(project_info)}. "
            "Use insert_section to add content."
        )


def _wikilink_note(content: str) -> tuple[str, str]:
    """Validate/repair wikilinks; return (fixed content, user-facing note)."""
    # 🔧 Pre-check: 驗證並修復 wikilink 格式
    result, fixed_content = validate_wikilinks_in_content(content, auto_fix=True)
    wikilink_note = ""
    if result.auto_fixed > 0:
        wikilink_note = f"\n🔧 自動修復 {result.auto_fixed} 個 wikilink 格式錯誤"
    elif result.issues:
        wikilink_note = f"\n⚠️ 發現 {len(result.issues)} 個 wikilink 格式問題，請檢查"
    return fixed_content, wikilink_note


def _verification_summary(session: dict, project_info: Optional[dict], counts: dict) -> str:
    output = (
        f"📊 **Document Verification: {session['template']}**\n\n"
        f"Project: {_project_label(project_info)}\n\n"
    )
    output += "| Section | Word Count |\n"
    output += "|---------|------------|\n"

    total = 0
    for section, count in counts.items():
        output += f"| {section} | {count} |\n"
        total += count

    output += f"| **TOTAL** | **{total}** |\n\n"

    output += f"**Modifications made:** {len(session['modifications'])}\n"
    for mod in session["modifications"]:
        output += f"- {mod['section']}: {mod['paragraphs']} paragraphs ({mod['mode']})\n"
    return output


def _section_limit(section: str, limits: dict) -> Optional[int]:
    for limit_key, limit_val in limits.items():
        if limit_key.lower() in section.lower() or section.lower() in limit_key.lower():
            return limit_val
    return None


def _word_limit_report(counts: dict, limits_json: str) -> str:
    limits = dict(_DEFAULT_WORD_LIMITS)

    custom_limits = json.loads(limits_json)
    limits.update(custom_limits)

    output = "\n📏 **Word Limit Check**\n\n"
    output += "| Section | Words | Limit | Status |\n"
    output += "|---------|-------|-------|--------|\n"

    all_ok = True
    for section, count in counts.items():
        limit = _section_limit(section, limits)

        if limit:
            if count <= limit:
                status = "✅"
            else:
                status = f"⚠️ Over by {count - limit}"
                all_ok = False
            output += f"| {section} | {count} | {limit} | {status} |\n"
        else:
            output += f"| {section} | {count} | - | - |\n"

    if all_ok:
        output += "\n✅ **All sections within word limits!**"
    else:
        output += "\n⚠️ **Some sections exceed word limits.**"
    return output


def _residual_wikilink_warning(doc: Any) -> str:
    """Safety check: scan for residual [[wikilink]] citations."""
    residual_wikilinks: list[str] = []
    for paragraph in doc.paragraphs:
        found = re.findall(r"\[\[([^\]]+)\]\]", paragraph.text)
        residual_wikilinks.extend(found)

    warning_msg = ""
    if residual_wikilinks:
        unique = sorted(set(residual_wikilinks))
        warning_msg = (
            f"\n\n⚠️ **Warning: {len(unique)} unresolved wikilink(s) "
            f"found in document**\n"
            f"These will appear as raw `[[...]]` text in the Word file:\n"
        )
        for wl in unique:
            warning_msg += f"  - `[[{wl}]]`\n"
        warning_msg += "\nConsider using `sync_references()` to convert wikilinks before export."
    return warning_msg


def _prepare_output_path(project_info: Optional[dict], output_filename: str) -> Path:
    project_paths = (project_info or {}).get("paths", {})
    project_root = Path(project_paths.get("root") or Path.cwd())
    exports_dir = project_root / "exports"
    output_path = resolve_child_path(
        exports_dir,
        output_filename,
        field_name="output filename",
        default_suffix=".docx",
        allowed_suffixes={".docx"},
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path
