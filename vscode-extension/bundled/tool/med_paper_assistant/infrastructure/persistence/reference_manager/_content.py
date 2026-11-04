"""Render the human-readable content.md of a reference.

檔案結構重構 (2025-12):
- aliases 放在 frontmatter 中，供 Foam 識別
- citation formats 也放在 frontmatter
- 人類可讀內容在 body

Layered Trust Architecture (2025-01)::

    ---
    # 🔒 VERIFIED (PubMed, immutable)
    source: pubmed
    verified: true
    ...

    # 🤖 AGENT (AI-generated, editable by AI)
    agent_notes: "..."

    # ✏️ USER (Human-only, never AI-touched)
    user_tags: []
    user_notes: ""
    ---
"""

from typing import Any, Dict


class ContentMarkdownMixin:
    """Render the frontmatter and body of the content.md of a reference."""

    def _generate_content_md(self, article: Dict[str, Any]) -> str:
        """
        Generate markdown content for the reference.
        Optimized for Foam hover preview - shows citation formats at the top.

        Args:
            article: Article metadata dictionary.

        Returns:
            Markdown formatted content string.
        """
        content = "---\n"
        content += self._frontmatter_verified_block(article)
        content += self._frontmatter_aliases_block(article)
        content += self._frontmatter_note_state_block(article)
        content += self._frontmatter_bibliographic_block(article)
        content += self._frontmatter_status_block(article)
        content += self._frontmatter_cite_block(article)
        content += self._frontmatter_trust_layers_block(article)
        content += self._body_header_block(article)
        content += self._body_graph_and_abstract_block(article)
        content += self._body_key_findings_block(article)
        content += self._body_evidence_block(article)
        content += self._body_keywords_block(article)
        content += self._body_citation_formats_block(article)
        return content

    def _frontmatter_verified_block(self, article: Dict[str, Any]) -> str:
        pmid = article.get("pmid", "")
        unique_id = article.get("unique_id", pmid)
        title = article.get("title", "Unknown Title")

        # Check if this is MCP-to-MCP verified data
        is_verified = article.get("verified", article.get("_verified", False))
        data_source = article.get("data_source", article.get("_data_source", "agent"))
        trust_level = article.get("trust_level", "agent")

        # ========== 🔒 VERIFIED SECTION (from PubMed, immutable) ==========
        content = "# 🔒 VERIFIED DATA (from PubMed - do not modify)\n"
        content += f'source: "{article.get("source", "pubmed")}"\n'
        content += f"verified: {str(is_verified).lower()}\n"
        content += f'data_source: "{self._yaml_escape(str(data_source))}"\n'
        if article.get("retrieved_at"):
            content += f'retrieved_at: "{self._yaml_escape(str(article["retrieved_at"]))}"\n'
        if article.get("source_url"):
            content += f'source_url: "{self._yaml_escape(str(article["source_url"]))}"\n'
        if article.get("payload_hash"):
            content += f'payload_hash: "{self._yaml_escape(str(article["payload_hash"]))}"\n'
        content += f"provenance_count: {len(article.get('provenance', []))}\n\n"
        content += f'reference_id: "{unique_id}"\n'
        content += f'trust_level: "{trust_level}"\n'

        # Title for Foam completion label display
        content += f'title: "{title}"\n'
        return content

    def _frontmatter_aliases_block(self, article: Dict[str, Any]) -> str:
        pmid = article.get("pmid", "")
        unique_id = article.get("unique_id", pmid)
        citation_key = article.get("citation_key", "")

        # Aliases for Foam wikilinks - critical for [[citation_key]] to work
        content = "aliases:\n"
        if citation_key:
            content += f"  - {citation_key}\n"  # e.g., greer2017_27345583
        if unique_id:
            content += f'  - "{unique_id}"\n'
        if pmid:
            content += f'  - "PMID:{pmid}"\n'  # e.g., PMID:27345583
            content += f'  - "{pmid}"\n'  # e.g., 27345583
        if article.get("doi"):
            content += f'  - "DOI:{article["doi"]}"\n'
        for alias in article.get("legacy_aliases", []):
            escaped_alias = alias.replace('"', '\\"')
            content += f'  - "{escaped_alias}"\n'
        content += f'type: "{article.get("foam_type", "reference")}"\n'
        content += "tags:\n"
        for tag in article.get("tags", []):
            content += f'  - "{tag}"\n'
        content += "\n"
        return content

    def _frontmatter_note_state_block(self, article: Dict[str, Any]) -> str:
        trust_level = article.get("trust_level", "agent")

        content = (
            f'note_class: "{article.get("note_class", article.get("foam_type", "reference"))}"\n'
        )
        content += f'note_domain: "{article.get("note_domain", "literature")}"\n'
        if article.get("project"):
            content += f'project: "{article.get("project")}"\n'
        content += f'source_kind: "{article.get("source", "pubmed")}"\n'
        content += f'trust_state: "{trust_level}"\n'
        content += f'analysis_state: "{"completed" if article.get("analysis_completed", False) else "pending"}"\n'
        content += f'fulltext_state: "{"ingested" if article.get("fulltext_ingested", False) else "missing"}"\n'
        content += f'review_state: "{article.get("review_state", "n/a")}"\n'
        if article.get("journal_slug"):
            content += f'journal_slug: "{article.get("journal_slug")}"\n'
        return content

    def _frontmatter_bibliographic_block(self, article: Dict[str, Any]) -> str:
        pmid = article.get("pmid", "")

        # Bibliographic info
        content = f'pmid: "{pmid}"\n'
        content += f"year: {article.get('year', '')}\n"
        if article.get("doi"):
            content += f'doi: "{article["doi"]}"\n'
        if article.get("pmc_id"):
            content += f'pmc: "{article["pmc_id"]}"\n'
        if article.get("content_hash"):
            content += f'content_hash: "{article["content_hash"]}"\n'
        if article.get("imported_from"):
            content += f'imported_from: "{article["imported_from"].replace("\\", "\\\\")}"\n'

        # First author last name for easy referencing
        authors_full = article.get("authors_full", [])
        if authors_full and isinstance(authors_full[0], dict):
            first_author = authors_full[0].get("last_name", "")
            content += f'first_author: "{first_author}"\n'

        # Journal info
        content += f'\njournal: "{article.get("journal", "")}"\n'
        if article.get("volume"):
            content += f'volume: "{article.get("volume")}"\n'
        if article.get("issue"):
            content += f'issue: "{article.get("issue")}"\n'
        if article.get("pages"):
            content += f'pages: "{article.get("pages")}"\n'
        return content

    def _frontmatter_status_block(self, article: Dict[str, Any]) -> str:
        content = "\n# Ingestion status\n"
        content += f"fulltext_ingested: {str(article.get('fulltext_ingested', False)).lower()}\n"
        content += (
            f'fulltext_unavailable_reason: "{article.get("fulltext_unavailable_reason", "")}"\n'
        )
        if article.get("asset_aware_doc_id"):
            content += f'asset_aware_doc_id: "{article.get("asset_aware_doc_id")}"\n'
        if article.get("fulltext_sections"):
            content += "fulltext_sections:\n"
            for section in article.get("fulltext_sections", []):
                content += f'  - "{section}"\n'
        else:
            content += "fulltext_sections: []\n"

        content += "\n# Analysis status\n"
        content += f"analysis_completed: {str(article.get('analysis_completed', False)).lower()}\n"
        content += (
            f'analysis_summary: "{article.get("analysis_summary", "").replace('"', '\\"')}"\n'
        )
        if article.get("usage_sections"):
            content += "usage_sections:\n"
            for section in article.get("usage_sections", []):
                content += f'  - "{section}"\n'
        else:
            content += "usage_sections: []\n"
        content += f"note_materialized: {str(article.get('note_materialized', True)).lower()}\n"
        return content

    def _frontmatter_cite_block(self, article: Dict[str, Any]) -> str:
        # Pre-formatted citations in frontmatter (easy to copy)
        content = ""
        citation = article.get("citation", {})
        if citation:
            content += "\n# Pre-formatted citations\n"
            content += "cite:\n"
            if citation.get("vancouver"):
                # Escape quotes in citation
                vancouver = citation["vancouver"].replace('"', '\\"')
                content += f'  vancouver: "{vancouver}"\n'
            if citation.get("apa"):
                apa = citation["apa"].replace('"', '\\"')
                content += f'  apa: "{apa}"\n'
            if citation.get("nature"):
                nature = citation["nature"].replace('"', '\\"')
                content += f'  nature: "{nature}"\n'
            if citation.get("in_text"):
                content += f'  inline: "{citation["in_text"]}"\n'
            content += "  number: null  # Assigned during export\n"
        return content

    def _frontmatter_trust_layers_block(self, article: Dict[str, Any]) -> str:
        agent_notes = article.get("agent_notes", article.get("_agent_notes", ""))
        user_notes = article.get("user_notes", article.get("_user_notes", ""))
        user_tags = article.get("user_tags", article.get("_user_tags", []))

        # ========== 🤖 AGENT SECTION (AI-generated, can be updated by AI) ==========
        content = "\n# 🤖 AGENT DATA (AI-generated, AI can update)\n"
        content += f'agent_notes: "{agent_notes.replace('"', '\\"')}"\n'
        content += 'agent_summary: ""\n'  # Can be filled by AI summarization
        content += "agent_relevance: null\n"  # 1-5 relevance score

        # ========== ✏️ USER SECTION (Human-only, never touched by AI) ==========
        content += "\n# ✏️ USER DATA (human-only, AI should never modify)\n"
        content += f'user_notes: "{user_notes.replace('"', '\\"')}"\n'
        if user_tags:
            content += "user_tags:\n"
            for tag in user_tags:
                content += f'  - "{tag}"\n'
        else:
            content += "user_tags: []\n"
        content += "user_rating: null  # 1-5 personal rating\n"
        content += "user_read_status: unread  # unread, reading, read\n"

        # Metadata
        saved_at = article.get("saved_at") or __import__("datetime").datetime.now().isoformat()
        content += f'\nsaved_at: "{saved_at}"\n'
        content += "---\n\n"
        return content
