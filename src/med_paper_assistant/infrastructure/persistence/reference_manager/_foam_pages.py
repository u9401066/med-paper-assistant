"""Body builders for knowledge-map and synthesis pages."""

from typing import Any, Dict, List


class FoamPageBodyMixin:
    """Body builders for knowledge-map and synthesis pages."""

    def _extract_markdown_section_blocks(self, markdown_text: str) -> List[Dict[str, str]]:
        if not markdown_text.strip():
            return []

        blocks: List[Dict[str, str]] = []
        current_title = ""
        current_lines: List[str] = []

        def flush() -> None:
            title = current_title.strip()
            content = "\n".join(current_lines).strip()
            if not title and not content:
                return
            blocks.append({"title": title or "Evidence Summary", "content": content})

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    flush()
                    current_title = heading
                    current_lines = []
                    continue
            current_lines.append(line.rstrip())

        flush()
        return blocks

    def _key_findings_anchor(self) -> str:
        return "^key-findings"

    def _evidence_anchor(self, title: str) -> str:
        return f"^evidence-{self._slugify(title, 'section')}"

    def _build_evidence_block_specs(self, article: Dict[str, Any]) -> List[Dict[str, str]]:
        article_title = str(article.get("title", "")).strip().lower()
        parsed_blocks = self._extract_markdown_section_blocks(article.get("extracted_markdown", ""))

        parsed_by_key: Dict[str, str] = {}
        ordered_parsed: List[Dict[str, str]] = []
        for block in parsed_blocks:
            title = block.get("title", "").strip()
            if not title or title.lower() == article_title:
                continue

            key = self._slugify(title, "section")
            snippet = self._build_markdown_summary(block.get("content", ""), max_chars=480)
            ordered_parsed.append({"title": title, "content": snippet})
            parsed_by_key[key] = snippet

        specs: List[Dict[str, str]] = []
        seen: set[str] = set()
        for section in self._dedupe_strings(article.get("fulltext_sections", [])):
            if section.lower() == article_title:
                continue

            key = self._slugify(section, "section")
            if key in seen:
                continue

            seen.add(key)
            specs.append({"title": section, "content": parsed_by_key.get(key, "")})

        for block in ordered_parsed:
            key = self._slugify(block["title"], "section")
            if key in seen:
                continue

            seen.add(key)
            specs.append(block)

        return specs[:6]

    def _clip_summary_text(self, text: str, limit: int) -> str:
        text = text.replace("\n", " ").strip()
        if len(text) > limit:
            text = text[: limit - 3].rstrip() + "..."
        return text

    def _embedded_evidence_lines(self, snapshots: List[Dict[str, Any]]) -> List[str]:
        if not snapshots:
            return []
        lines = ["", "## Embedded Evidence", ""]
        for snapshot in snapshots[:4]:
            metadata = snapshot["metadata"]
            citation_key = metadata.get("citation_key") or snapshot["reference_id"]
            evidence_blocks = self._build_evidence_block_specs(metadata)
            lines.append(f"### [[{citation_key}]]")
            lines.append("")
            lines.append(f"content-card![[{citation_key}#{self._key_findings_anchor()}]]")
            if evidence_blocks:
                lines.append("")
                lines.append(
                    f"content-inline![[{citation_key}#{self._evidence_anchor(evidence_blocks[0]['title'])}]]"
                )
            lines.append("")
        return lines

    def _build_knowledge_map_body(
        self,
        snapshots: List[Dict[str, Any]],
        *,
        query: str = "",
    ) -> str:
        trust_counts: Dict[str, int] = {}
        missing_analysis: List[str] = []
        unresolved_identity: List[str] = []

        lines = ["## Scope", ""]
        if query:
            lines.append(f"- Query: {query}")
        lines.append(f"- References included: {len(snapshots)}")
        lines.append("")
        lines.append("## Coverage")
        lines.append("")

        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            trust_level = metadata.get("trust_level", "unknown")
            trust_counts[trust_level] = trust_counts.get(trust_level, 0) + 1
            if not metadata.get("analysis_completed"):
                missing_analysis.append(snapshot["reference_id"])
            if str(snapshot["reference_id"]).startswith(("local_", "web_", "markdown_")):
                unresolved_identity.append(snapshot["reference_id"])

        if trust_counts:
            for trust_level, count in sorted(trust_counts.items()):
                lines.append(f"- {trust_level}: {count}")
        else:
            lines.append("- No references selected")

        lines.extend(["", "## Live Reference Count", ""])
        lines.extend(self._linked_reference_query_block(format_name="count"))
        lines.extend(["", "## Live Reference Table", ""])
        lines.extend(self._linked_reference_query_block(format_name="table"))

        lines.extend(["", "## Reference Graph", ""])
        lines.extend(self._reference_graph_lines(snapshots))
        lines.extend(self._embedded_evidence_lines(snapshots))
        lines.extend(self._knowledge_map_action_lines(missing_analysis, unresolved_identity))
        return "\n".join(lines)

    def _reference_graph_lines(self, snapshots: List[Dict[str, Any]]) -> List[str]:
        lines: List[str] = []
        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            analysis = snapshot["analysis"]
            citation_key = metadata.get("citation_key") or snapshot["reference_id"]
            title = metadata.get("title", snapshot["reference_id"])
            year = metadata.get("year", "")
            year_text = f" ({year})" if year else ""
            source = metadata.get("source", "")
            trust_level = metadata.get("trust_level", "")
            summary = (
                analysis.get("summary")
                or metadata.get("analysis_summary")
                or metadata.get("abstract")
                or "No summary available yet."
            )
            summary = self._clip_summary_text(summary, 260)
            lines.append(f"- [[{citation_key}]]: {title}{year_text} [{source}/{trust_level}]")
            lines.append(f"  Evidence: {summary}")
        return lines

    def _knowledge_map_action_lines(
        self, missing_analysis: List[str], unresolved_identity: List[str]
    ) -> List[str]:
        if not (missing_analysis or unresolved_identity):
            return []
        lines = ["", "## Next Actions", ""]
        if unresolved_identity:
            lines.append(
                "- Resolve canonical identity for: " + ", ".join(sorted(set(unresolved_identity)))
            )
        if missing_analysis:
            lines.append(
                "- Add structured analysis for: " + ", ".join(sorted(set(missing_analysis)))
            )
        return lines

    def _working_synthesis_text(self, snapshots: List[Dict[str, Any]], focus: str) -> str:
        synthesis_lines = ["## Working Synthesis", ""]
        if focus:
            synthesis_lines.append(f"Focus: {focus}")
            synthesis_lines.append("")

        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            analysis = snapshot["analysis"]
            citation_key = metadata.get("citation_key") or snapshot["reference_id"]
            contribution = (
                analysis.get("summary")
                or metadata.get("analysis_summary")
                or metadata.get("abstract")
                or "No synthesis text available."
            )
            contribution = self._clip_summary_text(contribution, 320)
            synthesis_lines.append(f"- [[{citation_key}]]: {contribution}")

        return "\n".join(synthesis_lines)

    def _build_synthesis_body(
        self,
        snapshots: List[Dict[str, Any]],
        *,
        focus: str = "",
        summary_markdown: str = "",
    ) -> str:
        if summary_markdown.strip():
            synthesis_text = summary_markdown.strip()
        else:
            synthesis_text = self._working_synthesis_text(snapshots, focus)

        gaps = [
            snapshot["reference_id"]
            for snapshot in snapshots
            if not snapshot["metadata"].get("analysis_completed")
        ]
        no_fulltext = [
            snapshot["reference_id"]
            for snapshot in snapshots
            if not snapshot["metadata"].get("fulltext_ingested")
        ]

        lines = [synthesis_text, "", "## Evidence Base", ""]
        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            citation_key = metadata.get("citation_key") or snapshot["reference_id"]
            year = metadata.get("year", "")
            title = metadata.get("title", snapshot["reference_id"])
            year_text = f" ({year})" if year else ""
            lines.append(f"- [[{citation_key}]]: {title}{year_text}")

        lines.extend(["", "## Live Evidence Table", ""])
        lines.extend(self._linked_reference_query_block(format_name="table"))
        lines.extend(self._embedded_evidence_lines(snapshots))

        if gaps or no_fulltext:
            lines.extend(["", "## Gaps", ""])
            if gaps:
                lines.append("- Missing structured analysis: " + ", ".join(sorted(set(gaps))))
            if no_fulltext:
                lines.append("- Fulltext not yet ingested: " + ", ".join(sorted(set(no_fulltext))))

        return "\n".join(lines)
