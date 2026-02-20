"""
Reference Manager Tools

save_reference, list, search, format, citation management
"""

import json
import os
from typing import Optional, Union

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_agent_misuse,
    log_tool_call,
    log_tool_result,
)


def register_reference_manager_tools(
    mcp: FastMCP, ref_manager: ReferenceManager, drafter: Drafter, project_manager
):
    """Register reference management tools."""

    # Get project manager for auto-project creation
    project_manager = ref_manager._project_manager

    def _ensure_project_exists() -> str:
        """Ensure a project exists for saving references."""
        if project_manager is None:
            return ""

        current = project_manager.get_current_project()
        if current:
            return ""

        result = project_manager.get_or_create_temp_project()
        if result.get("success"):
            return "\n\n💡 *已自動建立文獻探索工作區。找到研究方向後，使用 `convert_exploration_to_project` 轉換為正式專案。*"
        return ""

    @mcp.tool()
    def save_reference(article: Union[dict, str], project: Optional[str] = None) -> str:
        """
        Save reference with metadata from pubmed-search. Use save_reference_mcp instead for verified data.

        Args:
            article: Article metadata dict with 'pmid' field (from pubmed-search)
            project: Project slug (default: current)
        """
        # Log tool call
        log_tool_call("save_reference", {"article": article, "project": project})

        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "save_reference",
                    "valid project slug",
                    {"article": article, "project": project},
                    error_msg,
                )
                return error_msg

        # Handle JSON string input (MCP sometimes passes dict as JSON string)
        if isinstance(article, str):
            try:
                article = json.loads(article)
            except json.JSONDecodeError as e:
                error_msg = (
                    f"❌ Invalid JSON string for article parameter: {e}\n\n"
                    "**Correct workflow:**\n"
                    "1. Use pubmed-search MCP: `fetch_article_details(pmids='12345678')`\n"
                    "2. Use mdpaper MCP: `save_reference(article=<metadata from step 1>)`"
                )
                log_agent_misuse(
                    "save_reference",
                    "valid JSON or dict",
                    {"article_type": type(article).__name__},
                    error_msg,
                )
                return error_msg

        if not isinstance(article, dict):
            error_msg = (
                f"❌ Invalid input: article must be a dictionary, got {type(article).__name__}.\n\n"
                "**Correct workflow:**\n"
                "1. Use pubmed-search MCP: `fetch_article_details(pmids='12345678')`\n"
                "2. Use mdpaper MCP: `save_reference(article=<metadata from step 1>)`"
            )
            log_agent_misuse(
                "save_reference", "dict type", {"article_type": type(article).__name__}, error_msg
            )
            return error_msg

        if not article.get("pmid"):
            error_msg = (
                "❌ Article metadata must contain 'pmid' field.\n\n"
                "Ensure you're using metadata from pubmed-search MCP's "
                "`fetch_article_details()` or `search_literature()` tools."
            )
            log_agent_misuse(
                "save_reference",
                "article with pmid field",
                {"article_keys": list(article.keys())},
                error_msg,
            )
            return error_msg

        project_msg = _ensure_project_exists()
        result = ref_manager.save_reference(article)
        log_tool_result("save_reference", result)
        return result + project_msg

    @mcp.tool()
    def save_reference_mcp(pmid: str, agent_notes: str = "", project: Optional[str] = None) -> str:
        """
        🔒 Save reference by PMID with verified metadata from pubmed-search API (RECOMMENDED).

        Args:
            pmid: PubMed ID (e.g., "12345678")
            agent_notes: Optional AI notes about this reference
            project: Project slug (default: current)
        """
        log_tool_call(
            "save_reference_mcp", {"pmid": pmid, "agent_notes": agent_notes, "project": project}
        )

        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "save_reference_mcp",
                    "valid project slug",
                    {"pmid": pmid, "project": project},
                    error_msg,
                )
                return error_msg

        project_msg = _ensure_project_exists()
        result = ref_manager.save_reference_mcp(pmid, agent_notes=agent_notes)
        log_tool_result("save_reference_mcp", result)
        return result + project_msg

    @mcp.tool()
    def list_saved_references(project: Optional[str] = None) -> str:
        """
        List saved references with title, year, and PDF availability.

        Args:
            project: Project slug (default: current)
        """
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        refs = ref_manager.list_references()
        if not refs:
            return "No references saved."

        output = f"📚 **Saved References ({len(refs)} total)**\n\n"

        for pmid in refs:
            summary = ref_manager.get_reference_summary(pmid)
            title = summary.get("title", "Unknown")[:60]
            if len(summary.get("title", "")) > 60:
                title += "..."
            year = summary.get("year", "")
            has_pdf = "📄" if summary.get("has_fulltext_pdf") else ""

            output += f"- **{pmid}** {has_pdf}: {title} ({year})\n"

        output += "\n*📄 = PDF fulltext available*"
        return output

    @mcp.tool()
    def search_local_references(query: str) -> str:
        """
        Search within saved references by keyword in titles and abstracts.

        Args:
            query: Search keyword
        """
        results = ref_manager.search_local(query)

        if not results:
            return f"No local references found matching '{query}'"

        output = f"Found {len(results)} matching references:\n\n"
        for meta in results:
            pmid = meta.get("pmid", "")
            title = meta.get("title", "Unknown")
            year = meta.get("year", "")
            citation = meta.get("citation", {})

            output += f"**PMID:{pmid}** ({year})\n"
            output += f"  {title}\n"
            if citation.get("in_text"):
                output += f"  *Cite as: {citation['in_text']}*\n"
            output += "\n"

        return output

    @mcp.tool()
    def get_reference_details(pmid: str) -> str:
        """
        Get detailed info and pre-formatted citations for a saved reference.

        Args:
            pmid: PubMed ID
        """
        summary = ref_manager.get_reference_summary(pmid)

        if "error" in summary:
            return summary["error"]

        output = f"# Reference Details: PMID {pmid}\n\n"
        output += f"**Title**: {summary.get('title', '')}\n\n"
        output += f"**Authors**: {', '.join(summary.get('authors', []))}\n\n"
        output += f"**Journal**: {summary.get('journal', '')} ({summary.get('year', '')})\n\n"

        if summary.get("doi"):
            output += f"**DOI**: {summary['doi']}\n\n"

        output += f"**Has Abstract**: {'Yes' if summary.get('has_abstract') else 'No'}\n"
        output += (
            f"**Has PDF Fulltext**: {'Yes 📄' if summary.get('has_fulltext_pdf') else 'No'}\n\n"
        )

        citation = summary.get("citation", {})
        if citation:
            output += "## Pre-formatted Citations\n\n"
            output += f"**Vancouver**: {citation.get('vancouver', '')}\n\n"
            output += f"**APA**: {citation.get('apa', '')}\n\n"
            output += f"**Nature**: {citation.get('nature', '')}\n\n"
            output += f"**In-text**: {citation.get('in_text', '')}\n"

        return output

    @mcp.tool()
    def read_reference_fulltext(pmid: str, max_chars: int = 10000) -> str:
        """
        Read PDF fulltext of a saved reference (PMC Open Access only).

        Args:
            pmid: PubMed ID
            max_chars: Max characters to return (default 10000)
        """
        if not ref_manager.has_fulltext(pmid):
            return f"No fulltext PDF available for PMID {pmid}. Only Open Access articles from PMC have downloadable PDFs."

        text = ref_manager.read_fulltext(pmid)
        if text is None:
            return f"Could not read fulltext for PMID {pmid}."

        if text.startswith("Error"):
            return text

        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n... [Truncated. Total length: {len(text)} characters]"

        return f"# Fulltext: PMID {pmid}\n\n{text}"

    @mcp.tool()
    def save_reference_pdf(pmid: str, pdf_content: str) -> str:
        """
        Save base64-encoded PDF content for an existing reference.

        Args:
            pmid: PubMed ID
            pdf_content: Base64 encoded PDF
        """
        import base64

        try:
            decoded = base64.b64decode(pdf_content)
            return ref_manager.save_pdf(pmid, decoded)
        except Exception as e:
            return f"❌ Error decoding PDF: {str(e)}"

    @mcp.tool()
    def format_references(
        pmids: str, style: str = "vancouver", journal: Optional[str] = None
    ) -> str:
        """
        Format references for insertion into manuscript.

        Args:
            pmids: Comma-separated PMIDs (e.g., "31645286,28924371")
            style: "vancouver", "apa", "harvard", "nature", "ama", "mdpi", "nlm"
            journal: Optional journal name for specific formatting
        """
        pmid_list = [p.strip() for p in pmids.split(",") if p.strip()]

        if not pmid_list:
            return "Error: No PMIDs provided."

        style_name = journal.upper() if journal else style.upper()
        output = f"📚 **Formatted References ({style_name})**\n\n"

        for i, pmid in enumerate(pmid_list, 1):
            metadata = ref_manager.get_metadata(pmid)

            if not metadata:
                output += f"[{i}] PMID:{pmid} - Reference not found. Use save_reference first.\n"
                continue

            citation = metadata.get("citation", {})

            if style.lower() == "vancouver" and citation.get("vancouver"):
                output += f"[{i}] {citation['vancouver']}\n"
            elif style.lower() == "apa" and citation.get("apa"):
                output += f"{citation['apa']}\n"
            elif style.lower() == "nature" and citation.get("nature"):
                output += f"{i}. {citation['nature']}\n"
            else:
                authors = metadata.get("authors", [])
                title = metadata.get("title", "Unknown Title")
                journal_name = metadata.get("journal", "Unknown Journal")
                year = metadata.get("year", "")

                if len(authors) > 3:
                    author_str = f"{authors[0]} et al"
                else:
                    author_str = ", ".join(authors)

                output += f"[{i}] {author_str}. {title}. {journal_name}. {year}. PMID:{pmid}\n"

        output += f"\n*Total: {len(pmid_list)} references*"
        return output

    @mcp.tool()
    def rebuild_foam_aliases(project: Optional[str] = None) -> str:
        """
        Rebuild Foam-compatible markdown files for all references (2025-12 format).

        Args:
            project: Project slug (uses current project if omitted)
        """
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        refs_dir = ref_manager.base_dir
        if not os.path.exists(refs_dir):
            return f"❌ References directory not found: {refs_dir}"

        migrated = []
        skipped = []
        errors = []

        for pmid_dir in os.listdir(refs_dir):
            pmid_path = os.path.join(refs_dir, pmid_dir)
            if not os.path.isdir(pmid_path):
                continue

            metadata = ref_manager.get_metadata(pmid_dir)
            if not metadata:
                continue

            citation_key = metadata.get("citation_key") or ref_manager._generate_citation_key(
                metadata
            )
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

        # Clean up old root-level alias files
        root_aliases_removed = 0
        for filename in os.listdir(refs_dir):
            if filename.endswith(".md") and not os.path.isdir(os.path.join(refs_dir, filename)):
                try:
                    os.remove(os.path.join(refs_dir, filename))
                    root_aliases_removed += 1
                except Exception:  # nosec B110 - ignore cleanup errors
                    pass

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

    @mcp.tool()
    def delete_reference(pmid: str, confirm: bool = False, project: Optional[str] = None) -> str:
        """
        ⚠️ DESTRUCTIVE: Delete a reference and all associated files.

        Args:
            pmid: PubMed ID to delete
            confirm: False=preview, True=actually delete
            project: Project slug (uses current if omitted)
        """
        log_tool_call("delete_reference", {"pmid": pmid, "confirm": confirm, "project": project})

        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                error_msg = f"❌ {msg}\n\n{get_project_list_for_prompt()}"
                log_agent_misuse(
                    "delete_reference",
                    "valid project slug",
                    {"pmid": pmid, "project": project},
                    error_msg,
                )
                return error_msg

        result = ref_manager.delete_reference(pmid, confirm=confirm)
        log_tool_result("delete_reference", result)

        if result.get("requires_confirmation"):
            # Preview mode
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

        elif result.get("success"):
            # Deletion successful
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

        else:
            # Error
            return f"❌ {result.get('error', '未知錯誤')}"
