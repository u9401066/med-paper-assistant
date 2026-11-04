"""Render the markdown body of the content.md of a reference."""

from typing import Any, Dict


class ContentBodyMixin:
    """Render the markdown body (after the frontmatter) of a reference."""

    def _body_header_block(self, article: Dict[str, Any]) -> str:
        pmid = article.get("pmid", "")
        unique_id = article.get("unique_id", pmid)
        title = article.get("title", "Unknown Title")

        content = f"# {title}\n\n"

        # Authors
        authors = article.get("authors", [])
        content += f"**Authors**: {', '.join(authors)}\n\n"

        # Journal info
        journal = article.get("journal", "Unknown Journal")
        year = article.get("year", "")
        volume = article.get("volume", "")
        issue = article.get("issue", "")
        pages = article.get("pages", "")

        journal_info = f"{journal}"
        if year:
            journal_info += f" ({year})"
        if volume:
            journal_info += f"; {volume}"
            if issue:
                journal_info += f"({issue})"
            if pages:
                journal_info += f": {pages}"
        content += f"**Journal**: {journal_info}\n\n"

        # IDs
        content += f"**Reference ID**: {unique_id}\n"
        content += f"**PMID**: {pmid}\n"
        if article.get("doi"):
            content += f"**DOI**: [{article['doi']}](https://doi.org/{article['doi']})\n"
        if article.get("pmc_id"):
            content += f"**PMC**: {article['pmc_id']}\n"
        if article.get("content_hash"):
            content += f"**Content Hash**: {article['content_hash']}\n"
        content += "\n"
        return content

    def _body_graph_and_abstract_block(self, article: Dict[str, Any]) -> str:
        content = ""
        graph_context = self._build_reference_graph_context(article)
        if graph_context:
            content += "## Graph Context\n\n"
            content += graph_context
            content += "\n\n"

        # Abstract FIRST - most useful for Foam hover preview!
        abstract = article.get("abstract", "")
        if abstract:
            content += "## Abstract\n\n"
            content += abstract
            content += "\n\n"
        return content

    def _body_key_findings_block(self, article: Dict[str, Any]) -> str:
        abstract = article.get("abstract", "")
        key_findings = (
            article.get("analysis_summary")
            or abstract
            or self._build_markdown_summary(article.get("extracted_markdown", ""), max_chars=320)
        ).strip()
        content = ""
        if key_findings:
            content += "## Key Findings\n\n"
            content += key_findings.replace("\n", " ")
            content += "\n\n"
            content += self._key_findings_anchor() + "\n\n"
        return content

    def _body_evidence_block(self, article: Dict[str, Any]) -> str:
        content = ""
        evidence_blocks = self._build_evidence_block_specs(article)
        if evidence_blocks:
            content += "## Evidence Blocks\n\n"
            for block in evidence_blocks:
                content += f"### {block['title']}\n\n"
                if block["content"]:
                    content += block["content"] + "\n\n"
                else:
                    content += "Section indexed from extracted fulltext.\n\n"
                content += self._evidence_anchor(block["title"]) + "\n\n"
        return content

    def _body_keywords_block(self, article: Dict[str, Any]) -> str:
        content = ""

        # Keywords
        keywords = article.get("keywords", [])
        if keywords:
            content += f"**Keywords**: {', '.join(keywords)}\n\n"

        # MeSH terms
        mesh_terms = article.get("mesh_terms", [])
        if mesh_terms:
            content += f"**MeSH Terms**: {', '.join(mesh_terms[:10])}"
            if len(mesh_terms) > 10:
                content += f" (+{len(mesh_terms) - 10} more)"
            content += "\n\n"
        return content

    def _body_citation_formats_block(self, article: Dict[str, Any]) -> str:
        # Citation formats (moved to bottom - less useful in hover)
        content = ""
        citation = article.get("citation", {})
        if citation:
            preferred_style = self._get_preferred_citation_style()
            content += "## 📋 Citation Formats\n\n"

            # Style order: preferred first, then others
            style_order = ["vancouver", "apa", "nature"]
            if preferred_style and preferred_style in style_order:
                style_order.remove(preferred_style)
                style_order.insert(0, preferred_style)

            style_labels = {
                "vancouver": "Vancouver",
                "apa": "APA",
                "nature": "Nature",
                "harvard": "Harvard",
                "ama": "AMA",
            }

            for style in style_order:
                if citation.get(style):
                    label = style_labels.get(style, style.title())
                    if style == preferred_style:
                        content += f"**⭐ {label}**: {citation[style]}\n\n"
                    else:
                        content += f"**{label}**: {citation[style]}\n\n"

            if citation.get("in_text"):
                content += f"**In-text**: ({citation['in_text']})\n\n"
        return content
