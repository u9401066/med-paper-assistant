"""
Reference Manager Tools

save_reference, list, search, format, citation management, analysis
"""

import json
import os
from pathlib import Path
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
    mcp: FastMCP,
    ref_manager: ReferenceManager,
    drafter: Drafter,
    project_manager,
    *,
    register_public_verbs: bool = True,
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

    def _parse_metadata_json(metadata_json: str) -> tuple[Optional[dict], Optional[str]]:
        if not metadata_json.strip():
            return {}, None

        try:
            parsed_metadata = json.loads(metadata_json)
        except json.JSONDecodeError as exc:
            return None, f"❌ Invalid metadata_json: {exc}"

        if not isinstance(parsed_metadata, dict):
            return None, "❌ metadata_json must decode to a JSON object."

        return parsed_metadata, None

    def _parse_reference_ids(reference_ids: str) -> list[str]:
        return [
            item.strip()
            for line in reference_ids.splitlines()
            for item in line.split(",")
            if item.strip()
        ]

    @mcp.tool()
    def save_reference(article: Union[dict, str], project: Optional[str] = None) -> str:
        """
        ⚠️ DEPRECATED — Use save_reference_mcp(pmid) instead for verified data.

        This tool accepts unverified metadata that may be fabricated.
        Only use as fallback when pubmed-search API is unavailable.

        Args:
            article: Article metadata dict with 'pmid' field (from pubmed-search)
            project: Project slug (default: current)
        """
        # Log tool call with deprecation warning
        log_tool_call("save_reference", {"article": article, "project": project})

        # === GUARDRAIL: Deprecation warning ===
        # Always emit warning so even weak models notice
        deprecation_warning = (
            "\n\n⚠️ **DEPRECATION WARNING**: `save_reference()` accepts unverified metadata.\n"
            "✅ **Preferred**: `save_reference_mcp(pmid='<PMID>')` — fetches verified data from PubMed API.\n"
            "Only use `save_reference()` when pubmed-search API is confirmed unavailable.\n"
        )

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
                "`fetch_article_details()` or `unified_search()` tools."
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

        # Log as misuse for telemetry tracking
        pmid_val = article.get("pmid", "unknown") if isinstance(article, dict) else "unknown"
        log_agent_misuse(
            "save_reference",
            "save_reference_mcp(pmid)",
            {"pmid": pmid_val},
            "Agent used deprecated save_reference() instead of save_reference_mcp()",
        )

        return result + deprecation_warning + project_msg

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

    if register_public_verbs:

        @mcp.tool()
        def import_local_papers(
            paths: str, metadata_json: str = "", project: Optional[str] = None
        ) -> str:
            """
            Import one or more local files into the MedPaper reference registry.

            Args:
                paths: One path or multiple newline/comma-separated paths
                metadata_json: Optional JSON object or JSON list with extracted metadata
                project: Project slug (default: current)
            """
            log_tool_call(
                "import_local_papers",
                {"paths": paths, "metadata_json": metadata_json, "project": project},
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            project_msg = _ensure_project_exists()

            raw_paths = [p.strip() for chunk in paths.splitlines() for p in chunk.split(",")]
            parsed_paths = [p for p in raw_paths if p]
            if not parsed_paths:
                return "❌ No valid paths provided."

            metadata_items = []
            if metadata_json.strip():
                try:
                    parsed_metadata = json.loads(metadata_json)
                except json.JSONDecodeError as exc:
                    return f"❌ Invalid metadata_json: {exc}"

                if isinstance(parsed_metadata, list):
                    if len(parsed_metadata) != len(parsed_paths):
                        return "❌ metadata_json list length must match the number of provided paths."
                    metadata_items = parsed_metadata
                elif isinstance(parsed_metadata, dict):
                    metadata_items = [parsed_metadata for _ in parsed_paths]
                else:
                    return "❌ metadata_json must decode to a JSON object or JSON list."
            else:
                metadata_items = [{} for _ in parsed_paths]

            results = []
            for file_path, metadata in zip(parsed_paths, metadata_items):
                result = ref_manager.import_local_file(file_path, metadata=metadata)
                results.append(f"- {Path(file_path).name}: {result}")

            output = "\n".join(results)
            log_tool_result("import_local_papers", output)
            return output + project_msg

        @mcp.tool()
        def ingest_web_source(
            url: str,
            content: str,
            metadata_json: str = "",
            project: Optional[str] = None,
        ) -> str:
            """
            Import a fetched web page snapshot into the canonical wiki pipeline.

            Args:
                url: Original source URL
                content: Markdown/text content captured from the page
                metadata_json: Optional JSON metadata object
                project: Project slug (default: current)
            """
            log_tool_call(
                "ingest_web_source",
                {
                    "url": url,
                    "has_content": bool(content.strip()),
                    "project": project,
                },
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            if not url.strip():
                return "❌ URL is required."
            if not content.strip():
                return "❌ content is required."

            metadata, error = _parse_metadata_json(metadata_json)
            if error:
                return error

            project_msg = _ensure_project_exists()
            result = ref_manager.import_web_source(url, content, metadata=metadata)
            log_tool_result("ingest_web_source", result)
            return result + project_msg

        @mcp.tool()
        def ingest_markdown_source(
            markdown_text: str = "",
            source_path: str = "",
            metadata_json: str = "",
            project: Optional[str] = None,
        ) -> str:
            """
            Import markdown text or a markdown file into the canonical wiki pipeline.

            Args:
                markdown_text: Raw markdown content
                source_path: Optional local markdown path
                metadata_json: Optional JSON metadata object
                project: Project slug (default: current)
            """
            log_tool_call(
                "ingest_markdown_source",
                {
                    "source_path": source_path,
                    "has_markdown_text": bool(markdown_text.strip()),
                    "project": project,
                },
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            metadata, error = _parse_metadata_json(metadata_json)
            if error:
                return error

            if not markdown_text.strip() and not source_path.strip():
                return "❌ Provide either markdown_text or source_path."

            project_msg = _ensure_project_exists()
            if source_path.strip():
                result = ref_manager.import_markdown_file(source_path, metadata=metadata)
            else:
                result = ref_manager.import_markdown_content(
                    markdown_text,
                    source_name=metadata.get("imported_from", "") if metadata else "",
                    metadata=metadata,
                )
            log_tool_result("ingest_markdown_source", result)
            return result + project_msg

        @mcp.tool()
        def resolve_reference_identity(
            reference_id: str,
            pmid: str = "",
            verified_metadata_json: str = "",
            agent_notes: str = "",
            project: Optional[str] = None,
        ) -> str:
            """
            Upgrade a local/extracted reference to a canonical verified identity.

            Args:
                reference_id: Existing local reference id (for example local_abcd1234)
                pmid: Optional PubMed ID if MedPaper should fetch verified metadata directly
                verified_metadata_json: Optional verified metadata JSON supplied by the harness
                agent_notes: Optional notes to persist with the canonical record
                project: Project slug (default: current)
            """
            log_tool_call(
                "resolve_reference_identity",
                {
                    "reference_id": reference_id,
                    "pmid": pmid,
                    "project": project,
                    "has_verified_metadata_json": bool(verified_metadata_json.strip()),
                },
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            verified_article = None
            if verified_metadata_json.strip():
                try:
                    verified_article = json.loads(verified_metadata_json)
                except json.JSONDecodeError as exc:
                    return f"❌ Invalid verified_metadata_json: {exc}"

                if not isinstance(verified_article, dict):
                    return "❌ verified_metadata_json must decode to a JSON object."

            if not pmid and verified_article is None:
                return "❌ Provide either pmid or verified_metadata_json."

            result = ref_manager.resolve_reference_identity(
                reference_id,
                verified_article=verified_article,
                pmid=pmid or None,
                agent_notes=agent_notes,
            )
            log_tool_result("resolve_reference_identity", result)
            return result

        @mcp.tool()
        def build_knowledge_map(
            title: str,
            reference_ids: str = "",
            query: str = "",
            limit: int = 12,
            project: Optional[str] = None,
        ) -> str:
            """
            Build a materialized knowledge map page from saved references.

            Args:
                title: Title of the map page
                reference_ids: Optional comma/newline-separated reference ids
                query: Optional local search query when reference_ids omitted
                limit: Max references to include when selecting automatically
                project: Project slug (default: current)
            """
            log_tool_call(
                "build_knowledge_map",
                {
                    "title": title,
                    "reference_ids": reference_ids,
                    "query": query,
                    "limit": limit,
                    "project": project,
                },
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            project_msg = _ensure_project_exists()
            result = ref_manager.build_knowledge_map(
                title,
                reference_ids=_parse_reference_ids(reference_ids),
                query=query,
                limit=limit,
            )
            log_tool_result("build_knowledge_map", result)
            return result + project_msg

        @mcp.tool()
        def build_synthesis_page(
            title: str,
            reference_ids: str = "",
            query: str = "",
            focus: str = "",
            summary_markdown: str = "",
            limit: int = 12,
            project: Optional[str] = None,
        ) -> str:
            """
            Build a materialized synthesis page from saved references.

            Args:
                title: Title of the synthesis page
                reference_ids: Optional comma/newline-separated reference ids
                query: Optional local search query when reference_ids omitted
                focus: Optional synthesis focus
                summary_markdown: Optional prewritten synthesis markdown
                limit: Max references to include when selecting automatically
                project: Project slug (default: current)
            """
            log_tool_call(
                "build_synthesis_page",
                {
                    "title": title,
                    "reference_ids": reference_ids,
                    "query": query,
                    "focus": focus,
                    "has_summary_markdown": bool(summary_markdown.strip()),
                    "limit": limit,
                    "project": project,
                },
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            project_msg = _ensure_project_exists()
            result = ref_manager.build_synthesis_page(
                title,
                reference_ids=_parse_reference_ids(reference_ids),
                query=query,
                focus=focus,
                summary_markdown=summary_markdown,
                limit=limit,
            )
            log_tool_result("build_synthesis_page", result)
            return result + project_msg

        @mcp.tool()
        def materialize_agent_wiki(
            knowledge_map_title: str,
            synthesis_title: str = "",
            reference_ids: str = "",
            query: str = "",
            focus: str = "",
            summary_markdown: str = "",
            limit: int = 12,
            project: Optional[str] = None,
        ) -> str:
            """
            Materialize the second-stage agent wiki bundle in one step.

            Args:
                knowledge_map_title: Title for the knowledge map page
                synthesis_title: Optional title for the synthesis page
                reference_ids: Optional comma/newline-separated reference ids
                query: Optional local search query when reference_ids omitted
                focus: Optional synthesis focus
                summary_markdown: Optional prewritten synthesis markdown
                limit: Max references to include when selecting automatically
                project: Project slug (default: current)
            """
            log_tool_call(
                "materialize_agent_wiki",
                {
                    "knowledge_map_title": knowledge_map_title,
                    "synthesis_title": synthesis_title,
                    "reference_ids": reference_ids,
                    "query": query,
                    "focus": focus,
                    "has_summary_markdown": bool(summary_markdown.strip()),
                    "limit": limit,
                    "project": project,
                },
            )

            if project:
                is_valid, msg, project_info = ensure_project_context(project)
                if not is_valid:
                    return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

            project_msg = _ensure_project_exists()
            result = ref_manager.materialize_agent_wiki(
                knowledge_map_title=knowledge_map_title,
                synthesis_title=synthesis_title,
                reference_ids=_parse_reference_ids(reference_ids),
                query=query,
                focus=focus,
                summary_markdown=summary_markdown,
                limit=limit,
            )
            log_tool_result("materialize_agent_wiki", result)
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

    @mcp.tool()
    def get_reference_for_analysis(pmid: str, project: Optional[str] = None) -> str:
        """
        📖 Get reference content for subagent analysis (Phase 2.1).

        Returns structured reference data (abstract + fulltext if available)
        for a subagent to read and produce analysis. Use this to extract
        material before calling save_reference_analysis().

        Design: Each reference should be analyzed by a SEPARATE subagent
        to prevent context pollution across papers.

        Args:
            pmid: PubMed ID of saved reference
            project: Project slug (uses current if omitted)
        """
        log_tool_call("get_reference_for_analysis", {"pmid": pmid, "project": project})

        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"

        # Get reference metadata
        detail = ref_manager.get_reference_details(pmid)
        if not detail:
            return f"❌ Reference PMID:{pmid} not found in saved references."

        meta = detail.get("metadata", {})
        ref_dir = Path(detail.get("ref_dir", ""))

        lines = [
            f"# Reference Analysis Package: PMID {pmid}",
            f"**Title**: {meta.get('title', 'N/A')}",
            f"**Authors**: {', '.join(meta.get('authors', [])[:5])}",
            f"**Journal**: {meta.get('journal', 'N/A')} ({meta.get('year', 'N/A')})",
            f"**DOI**: {meta.get('doi', 'N/A')}",
            "",
            "## Abstract",
            meta.get("abstract", "(No abstract available)"),
            "",
        ]

        # Check for fulltext
        fulltext_available = False
        if ref_manager.has_fulltext(pmid):
            text = ref_manager.read_fulltext(pmid)
            if text and not text.startswith("Error"):
                fulltext_available = True
                lines.append("## Fulltext (from PDF)")
                # Limit to reasonable size for subagent context
                if len(text) > 30000:
                    lines.append(text[:30000])
                    lines.append(f"\n... [Truncated at 30000 chars. Total: {len(text)}]")
                else:
                    lines.append(text)
                lines.append("")

        # Check for normalized asset-aware parsed sections first
        normalized_sections_path = ref_dir / "artifacts" / "asset-aware" / "sections.md"
        if normalized_sections_path.is_file():
            content = normalized_sections_path.read_text(encoding="utf-8")
            lines.append("## Fulltext (asset-aware parsed)")
            lines.append(content[:10000])
            lines.append("")
            fulltext_available = True

        # Legacy fallback: older parsed section layout
        analysis_sections_dir = ref_dir / "sections"
        if analysis_sections_dir.is_dir():
            for section_file in sorted(analysis_sections_dir.iterdir()):
                if section_file.suffix == ".md":
                    section_name = section_file.stem
                    content = section_file.read_text(encoding="utf-8")
                    lines.append(f"## Section: {section_name} (asset-aware parsed)")
                    lines.append(content[:10000])
                    lines.append("")
                    fulltext_available = True

        lines.append("---")
        lines.append(
            f"**Fulltext available**: {'Yes' if fulltext_available else 'No (abstract only)'}"
        )
        lines.append(
            f"**Analysis status**: {'Completed' if meta.get('analysis_completed') else 'PENDING'}"
        )

        if not fulltext_available:
            lines.append("")
            lines.append(
                "⚠️ **Abstract-only reference**: Analysis will be limited. "
                "This reference can only support general background claims, "
                "NOT specific methodological or quantitative citations."
            )

        result = "\n".join(lines)
        log_tool_result("get_reference_for_analysis", f"pmid={pmid}, fulltext={fulltext_available}")
        return result

    @mcp.tool()
    def save_reference_analysis(
        pmid: str,
        summary: str,
        methodology: str = "",
        key_findings: str = "",
        limitations: str = "",
        usage_sections: str = "",
        relevance_score: int = 0,
        project: Optional[str] = None,
    ) -> str:
        """
        💾 Save subagent's analysis result for a reference (Phase 2.1).

        After a subagent reads and analyzes a reference (via get_reference_for_analysis),
        save the structured analysis back. This creates an analysis.json file in the
        reference directory and updates metadata.

        Args:
            pmid: PubMed ID of the reference
            summary: 2-3 sentence summary of what this paper contributes
            methodology: Study design, sample size, key methods (1-2 sentences)
            key_findings: Main results and conclusions (2-3 bullet points as text)
            limitations: Noted limitations or bias concerns
            usage_sections: Comma-separated sections where this ref is useful
                           (e.g., "Introduction,Discussion" or "Methods,Results")
            relevance_score: 1-5 relevance to current project (5=essential)
            project: Project slug (uses current if omitted)
        """
        log_tool_call("save_reference_analysis", {"pmid": pmid, "project": project})

        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}"

        # Find reference directory
        detail = ref_manager.get_reference_details(pmid)
        if not detail:
            return f"❌ Reference PMID:{pmid} not found."

        ref_dir = Path(detail.get("ref_dir", ""))

        # Parse usage sections
        sections_list = (
            [s.strip() for s in usage_sections.split(",") if s.strip()] if usage_sections else []
        )

        # Build analysis data
        analysis = {
            "pmid": pmid,
            "summary": summary,
            "methodology": methodology,
            "key_findings": key_findings,
            "limitations": limitations,
            "usage_sections": sections_list,
            "relevance_score": max(1, min(5, relevance_score)),
            "analyzed_at": __import__("datetime").datetime.now().isoformat(),
        }

        # Save analysis.json
        analysis_path = ref_dir / "analysis.json"
        analysis_path.write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        update_result = ref_manager.update_reference_analysis_status(
            pmid,
            summary,
            usage_sections=sections_list,
            analysis_completed=True,
        )
        if update_result != f"Updated {pmid}.":
            return f"⚠️ Analysis saved but metadata update failed: {update_result}"

        result = (
            f"✅ Analysis saved for PMID:{pmid}\n"
            f"**Summary**: {summary[:100]}...\n"
            f"**Usage sections**: {', '.join(sections_list) or 'Not specified'}\n"
            f"**Relevance**: {'⭐' * relevance_score}\n"
            f"📁 Saved to: {analysis_path}"
        )
        log_tool_result("save_reference_analysis", f"pmid={pmid}, sections={sections_list}")
        return result
