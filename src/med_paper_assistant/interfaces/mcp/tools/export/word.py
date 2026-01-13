"""
Word Export Tools

Full Word export workflow with session management.
"""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter

# Global state for document editing sessions
_active_documents: dict[str, dict] = {}


def get_active_documents() -> dict:
    """Get the active document sessions dictionary."""
    return _active_documents


def register_word_export_tools(
    mcp: FastMCP, formatter: Formatter, template_reader: TemplateReader, word_writer: WordWriter
):
    """Register Word export tools."""

    # ============================================================
    # LEGACY EXPORT
    # ============================================================

    @mcp.tool()
    def export_word(draft_filename: str, template_name: str, output_filename: str) -> str:
        """
        [Legacy] Simple export. Use new workflow (start_document_session) for more control.

        Args:
            draft_filename: Markdown draft path
            template_name: Template file in templates/
            output_filename: Output path
        """
        try:
            path = formatter.apply_template(draft_filename, template_name, output_filename)
            return f"Word document exported successfully to: {path}"
        except Exception as e:
            return f"Error exporting Word document: {str(e)}"

    # ============================================================
    # NEW WORKFLOW
    # ============================================================

    @mcp.tool()
    def list_templates() -> str:
        """
        List all available Word templates in templates/ directory.
        """
        try:
            templates = template_reader.list_templates()
            if not templates:
                return "No templates found in templates/ directory."

            output = "📄 **Available Templates**\n\n"
            for t in templates:
                output += f"- {t}\n"
            return output
        except Exception as e:
            return f"Error listing templates: {str(e)}"

    @mcp.tool()
    def read_template(template_name: str) -> str:
        """
        Read a Word template's structure (sections, styles, word limits).

        Args:
            template_name: Template filename (e.g., "Type of the Paper.docx")
        """
        try:
            return template_reader.get_template_summary(template_name)
        except Exception as e:
            return f"Error reading template: {str(e)}"

    @mcp.tool()
    def start_document_session(template_name: str, session_id: str = "default") -> str:
        """
        Start a document editing session from a Word template.

        Args:
            template_name: Template filename
            session_id: Unique session identifier (default: "default")
        """
        try:
            template_path = os.path.join(template_reader.templates_dir, template_name)
            if not os.path.exists(template_path):
                return f"Error: Template not found: {template_name}"

            doc = word_writer.create_document_from_template(template_path)
            _active_documents[session_id] = {
                "doc": doc,
                "template": template_name,
                "modifications": [],
            }

            structure = template_reader.get_template_summary(template_name)

            return f"✅ Document session '{session_id}' started with template: {template_name}\n\n{structure}"
        except Exception as e:
            return f"Error starting session: {str(e)}"

    @mcp.tool()
    def insert_section(
        session_id: str, section_name: str, content: str, mode: str = "replace"
    ) -> str:
        """
        Insert content into a document section.

        Args:
            session_id: Session ID from start_document_session
            section_name: Target section (e.g., "Introduction")
            content: Text content to insert
            mode: "replace" or "append"
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'. Use start_document_session first."

        try:
            session = _active_documents[session_id]
            doc = session["doc"]

            # 🔧 Pre-check: 驗證並修復 wikilink 格式
            result, fixed_content = validate_wikilinks_in_content(content, auto_fix=True)
            wikilink_note = ""
            if result.auto_fixed > 0:
                wikilink_note = f"\n🔧 自動修復 {result.auto_fixed} 個 wikilink 格式錯誤"
            elif result.issues:
                wikilink_note = f"\n⚠️ 發現 {len(result.issues)} 個 wikilink 格式問題，請檢查"

            paragraphs = [p for p in fixed_content.split("\n") if p.strip()]
            clear_existing = mode == "replace"

            count = word_writer.insert_content_in_section(
                doc, section_name, paragraphs, clear_existing=clear_existing
            )

            session["modifications"].append(
                {"section": section_name, "paragraphs": count, "mode": mode}
            )

            word_count = word_writer.count_words_in_section(doc, section_name)

            return f"✅ Inserted {count} paragraphs into '{section_name}' ({word_count} words){wikilink_note}"
        except Exception as e:
            return f"Error inserting section: {str(e)}"

    @mcp.tool()
    def verify_document(session_id: str) -> str:
        """
        Get document summary with all sections and word counts.

        Args:
            session_id: Session ID from start_document_session
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'."

        try:
            session = _active_documents[session_id]
            doc = session["doc"]

            counts = word_writer.get_all_word_counts(doc)

            output = f"📊 **Document Verification: {session['template']}**\n\n"
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
        except Exception as e:
            return f"Error verifying document: {str(e)}"

    @mcp.tool()
    def check_word_limits(session_id: str, limits_json: Optional[str] = None) -> str:
        """
        Check if sections meet word limits.

        Args:
            session_id: Session ID from start_document_session
            limits_json: Optional JSON with custom limits (e.g., '{"Abstract": 300}')
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'."

        try:
            session = _active_documents[session_id]
            doc = session["doc"]

            counts = word_writer.get_all_word_counts(doc)

            limits = {
                "Abstract": 250,
                "Introduction": 800,
                "Methods": 1500,
                "Materials and Methods": 1500,
                "Results": 1500,
                "Discussion": 1500,
                "Conclusions": 300,
            }

            if limits_json:
                custom_limits = json.loads(limits_json)
                limits.update(custom_limits)

            output = "📏 **Word Limit Check**\n\n"
            output += "| Section | Words | Limit | Status |\n"
            output += "|---------|-------|-------|--------|\n"

            all_ok = True
            for section, count in counts.items():
                limit = None
                for limit_key, limit_val in limits.items():
                    if limit_key.lower() in section.lower() or section.lower() in limit_key.lower():
                        limit = limit_val
                        break

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
        except Exception as e:
            return f"Error checking word limits: {str(e)}"

    @mcp.tool()
    def save_document(session_id: str, output_filename: str) -> str:
        """
        Save the document to Word file and close session.

        Args:
            session_id: Session ID from start_document_session
            output_filename: Output file path
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'."

        try:
            session = _active_documents[session_id]
            doc = session["doc"]

            path = word_writer.save_document(doc, output_filename)

            del _active_documents[session_id]

            return f"✅ Document saved successfully to: {path}\n\nSession '{session_id}' closed."
        except Exception as e:
            return f"Error saving document: {str(e)}"
