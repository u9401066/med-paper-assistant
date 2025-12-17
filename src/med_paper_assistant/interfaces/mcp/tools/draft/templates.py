"""
Draft Template and Utility Tools

get_section_template, count_words, insert_citation, sync_references
"""

import os
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter

from .._shared import ensure_project_context, get_project_list_for_prompt


def _validate_project_context(project: Optional[str]) -> tuple:
    """Validate project context before draft operations."""
    is_valid, msg, project_info = ensure_project_context(project)
    if not is_valid:
        return False, f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    return True, None


def register_template_tools(mcp: FastMCP, drafter: Drafter):
    """Register template and utility tools."""

    @mcp.tool()
    def get_section_template(section: str) -> str:
        """
        Get writing guidelines for a specific paper section.

        Args:
            section: "introduction", "methods", "results", "discussion", "abstract"
        """
        from med_paper_assistant.infrastructure.services import SECTION_PROMPTS

        return SECTION_PROMPTS.get(
            section.lower(), "Section not found. Available: " + ", ".join(SECTION_PROMPTS.keys())
        )

    @mcp.tool()
    def insert_citation(
        filename: str, target_text: str, pmid: str, project: Optional[str] = None
    ) -> str:
        """
        Insert a citation into an existing draft.

        Args:
            filename: The draft file name.
            target_text: The text segment after which the citation should be inserted.
            pmid: The PubMed ID to cite.
            project: Project slug. Agent should confirm with user before calling.
        """
        is_valid, error_msg = _validate_project_context(project)
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
        Synchronize references from [[wikilinks]] in a markdown file.

        This is like a citation manager (EndNote/Zotero) for markdown:
        1. Scans the document for [[citation_key]] wikilinks (e.g., [[pachecolopez2014_24891204]])
        2. Replaces them with formatted in-text citations (e.g., [1] or (Author, Year))
        3. Generates/updates the References section at the end
        4. Numbers are assigned by order of appearance

        Supported wikilink formats:
        - [[citation_key]] e.g., [[pachecolopez2014_24891204]]
        - [[PMID:12345678]]
        - [[12345678]]

        Args:
            filename: The markdown file name (e.g., "concept.md" or "draft.md").
                     Will search in project root first, then drafts folder.
            project: Project slug. Agent should confirm with user before calling.

        Returns:
            Summary of synchronized references with their assigned numbers.
        """
        is_valid, error_msg = _validate_project_context(project)
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
    def count_words(filename: str, section: Optional[str] = None) -> str:
        """
        Count words in a draft file. Essential for meeting journal word limits.

        Args:
            filename: Path to the markdown draft file (e.g., "drafts/draft.md").
            section: Optional specific section to count (e.g., "Introduction", "Abstract").
                    If not specified, counts all sections.

        Returns:
            Word count statistics including total words, words per section, and character count.
        """
        if not os.path.isabs(filename):
            filename = os.path.join("drafts", filename)

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
                    section_name = re.sub(r"^#+\s*\d*\.?\s*", "", line).strip()
                    current_section = section_name if section_name else "Untitled"
                    current_content = []
                else:
                    current_content.append(line)

            if current_content:
                sections[current_section] = "\n".join(current_content)

            def count_text_words(text: str) -> int:
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
                    return (
                        f"📊 Word Count for '{matched}':\n"
                        f"  Words: {word_count}\n"
                        f"  Characters (no spaces): {char_count}"
                    )
                else:
                    return f"Section '{section}' not found. Available sections: {', '.join(sections.keys())}"
            else:
                output = "📊 **Word Count Summary**\n\n"
                output += "| Section | Words | Characters |\n"
                output += "|---------|-------|------------|\n"

                total_words = 0
                total_chars = 0

                for sec_name, sec_content in sections.items():
                    if sec_name == "References":
                        continue
                    words = count_text_words(sec_content)
                    chars = len(sec_content.replace("\n", "").replace(" ", ""))
                    total_words += words
                    total_chars += chars
                    output += f"| {sec_name[:30]} | {words} | {chars} |\n"

                output += f"| **Total** | **{total_words}** | **{total_chars}** |\n\n"
                output += f"📝 Total word count (excluding References): **{total_words}** words"

                return output

        except Exception as e:
            return f"Error counting words: {str(e)}"
