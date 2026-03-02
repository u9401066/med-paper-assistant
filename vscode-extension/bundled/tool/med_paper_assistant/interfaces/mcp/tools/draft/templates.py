"""
Draft Template and Utility Tools

get_section_template, count_words, insert_citation, sync_references
"""

import os
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.writing_hooks import BODY_SECTIONS
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    get_drafts_dir,
    validate_project_for_tool,
)


def register_template_tools(mcp: FastMCP, drafter: Drafter):
    """Register template and utility tools."""

    @mcp.tool()
    def insert_citation(
        filename: str, target_text: str, pmid: str, project: Optional[str] = None
    ) -> str:
        """
        Insert a citation after specific text in a draft file.

        Args:
            filename: Draft filename
            target_text: Text segment after which to insert citation
            pmid: PubMed ID to cite
            project: Project slug (uses current if omitted)
        """
        is_valid, error_msg = validate_project_for_tool(project)
        if not is_valid:
            return error_msg

        try:
            path = drafter.insert_citation(filename, target_text, pmid)
            return f"Citation inserted successfully in: {path}"
        except Exception as e:
            return f"Error inserting citation: {str(e)}"

    @mcp.tool()
    def sync_references(filename: str, project: Optional[str] = None) -> str:
        """
        Scan [[wikilinks]] and generate References section (like EndNote/Zotero).

        Args:
            filename: Markdown file (e.g., "concept.md")
            project: Project slug (uses current if omitted)
        """
        is_valid, error_msg = validate_project_for_tool(project)
        if not is_valid:
            return error_msg

        try:
            result = drafter.sync_references_from_wikilinks(filename)

            if not result.get("success"):
                return f"❌ Error: {result.get('error', 'Unknown error')}"

            if result.get("citations_found", 0) == 0:
                return f"ℹ️ {result.get('message')}\n\nFile: {result.get('filepath')}"

            output = "✅ **References Synchronized**\n\n"
            output += f"📄 File: `{result.get('filepath')}`\n"
            output += f"🎨 Style: {result.get('style', 'vancouver')}\n"
            output += f"📚 Citations found: {result.get('citations_found')}\n\n"

            output += "| # | Citation Key | Title |\n"
            output += "|---|--------------|-------|\n"

            for cite in result.get("citations", []):
                output += f"| {cite['number']} | `{cite['wikilink']}` | {cite['title']} |\n"

            if result.get("not_found"):
                output += f"\n⚠️ **Not found in library**: {', '.join(result['not_found'])}\n"
                output += "Use `save_reference` to add these to your library first.\n"

            return output

        except FileNotFoundError as e:
            return f"❌ File not found: {str(e)}"
        except Exception as e:
            return f"❌ Error syncing references: {str(e)}"

    @mcp.tool()
    def count_words(
        filename: str, section: Optional[str] = None, project: Optional[str] = None
    ) -> str:
        """
        Count words by section. Essential for journal word limits.

        Per ICMJE convention, total manuscript word count includes only body
        sections (Introduction through Conclusion). Abstract, References,
        Tables, Acknowledgments, etc. are reported separately.

        Args:
            filename: Draft filename (e.g., "draft.md")
            section: Specific section to count (optional, counts all if omitted)
            project: Project slug (uses current if omitted)
        """
        is_valid, error_msg = validate_project_for_tool(project)
        if not is_valid:
            return error_msg

        if not os.path.isabs(filename):
            drafts_dir = get_drafts_dir()
            if not drafts_dir:
                drafts_dir = "drafts"
            filename = os.path.join(drafts_dir, filename)

        if not os.path.exists(filename):
            return f"Error: File not found: {filename}"

        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse sections
            sections: dict[str, str] = {}
            current_section = "Header"
            current_content: list[str] = []

            for line in content.split("\n"):
                if line.startswith("#"):
                    if current_content:
                        sections[current_section] = "\n".join(current_content)
                    section_name = re.sub(r"^#+\\s*\\d*\\.?\\s*", "", line).strip()
                    current_section = section_name if section_name else "Untitled"
                    current_content = []
                else:
                    current_content.append(line)

            if current_content:
                sections[current_section] = "\n".join(current_content)

            def count_text_words(text: str) -> int:
                # Strip markdown tables (display items)
                lines = text.split("\n")
                text = "\n".join(line for line in lines if not re.match(r"^\s*\|.*\|\s*$", line))
                text = re.sub(r"\[.*?\]\(.*?\)", "", text)
                text = re.sub(r"[*_`#\[\]()]", "", text)
                text = re.sub(r"\s+", " ", text)
                words = [w for w in text.split() if w.strip()]
                return len(words)

            if section:
                matched = None
                for sec_name in sections:
                    if section.lower() in sec_name.lower():
                        matched = sec_name
                        break

                if matched:
                    word_count = count_text_words(sections[matched])
                    char_count = len(sections[matched].replace("\n", "").replace(" ", ""))
                    is_body = matched.lower() in BODY_SECTIONS
                    return (
                        f"📊 Word Count for '{matched}':\n"
                        f"  Words: {word_count}\n"
                        f"  Characters (no spaces): {char_count}\n"
                        f"  Counts toward total: {'Yes (body section)' if is_body else 'No'}"
                    )
                else:
                    return f"Section '{section}' not found. Available sections: {', '.join(sections.keys())}"
            else:
                output = "📊 **Word Count Summary**\n\n"
                output += "| Section | Words | Body? |\n"
                output += "|---------|-------|-------|\n"

                body_words = 0
                other_words = 0

                for sec_name, sec_content in sections.items():
                    words = count_text_words(sec_content)
                    is_body = sec_name.lower() in BODY_SECTIONS

                    if is_body:
                        body_words += words
                        output += f"| {sec_name[:30]} | {words} | ✅ |\n"
                    else:
                        other_words += words
                        output += f"| {sec_name[:30]} | {words} | — |\n"

                output += f"| **Body total** | **{body_words}** | |\n\n"
                output += f"📝 **Manuscript word count (ICMJE): {body_words}** words\n"
                output += "   (Body sections only — excludes Abstract, References, Tables, etc.)\n"
                if other_words:
                    output += f"   Non-body sections: {other_words} words"

                return output

        except Exception as e:
            return f"Error counting words: {str(e)}"
