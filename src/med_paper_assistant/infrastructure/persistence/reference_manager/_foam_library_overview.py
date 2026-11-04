"""Statistics and markdown sections for the library overview page."""

from typing import Any, Dict, List


class FoamLibraryOverviewMixin:
    """Statistics and markdown sections for the library overview page."""

    def _collect_library_stats(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "trust_counts": {},
            "source_counts": {},
            "journal_counts": {},
            "topic_counts": {},
            "unresolved_identity": [],
            "analysis_queue": [],
            "fulltext_queue": [],
            "recent_additions": [],
        }
        for snapshot in snapshots:
            self._tally_library_snapshot(stats, snapshot)
        return stats

    def _tally_library_snapshot(self, stats: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        trust_counts: Dict[str, int] = stats["trust_counts"]
        source_counts: Dict[str, int] = stats["source_counts"]
        journal_counts: Dict[str, int] = stats["journal_counts"]
        topic_counts: Dict[str, int] = stats["topic_counts"]

        metadata = snapshot["metadata"]
        reference_id = snapshot["reference_id"]
        citation_key = metadata.get("citation_key") or reference_id
        title = metadata.get("title", reference_id)
        year = str(metadata.get("year", "")).strip()

        trust_level = str(metadata.get("trust_level", "unknown") or "unknown")
        trust_counts[trust_level] = trust_counts.get(trust_level, 0) + 1

        source = str(metadata.get("source", "unknown") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

        journal = str(metadata.get("journal", "")).strip()
        if journal:
            journal_counts[journal] = journal_counts.get(journal, 0) + 1

        for topic in self._dedupe_strings(metadata.get("keywords", []))[:5]:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        ref_entry = {
            "citation_key": citation_key,
            "title": title,
            "year": year,
        }
        stats["recent_additions"].append(ref_entry)

        if reference_id.startswith(("local_", "web_", "markdown_")) and not metadata.get("pmid"):
            stats["unresolved_identity"].append(ref_entry)
        if not metadata.get("analysis_completed"):
            stats["analysis_queue"].append(ref_entry)
        if not metadata.get("fulltext_ingested"):
            stats["fulltext_queue"].append(ref_entry)

    def _library_reference_bullets(self, items: List[Dict[str, str]], limit: int) -> List[str]:
        lines: List[str] = []
        for item in items[:limit]:
            year_text = f" ({item['year']})" if item["year"] else ""
            lines.append(f"- [[{item['citation_key']}]]: {item['title']}{year_text}")
        return lines

    def _library_status_lines(
        self,
        *,
        total_references: int,
        analyzed_count: int,
        fulltext_count: int,
        context_nodes: Dict[str, Any],
        stats: Dict[str, Any],
    ) -> List[str]:
        body_lines = [
            "## Library Status",
            "",
            f"- Total references: {total_references}",
            f"- Analysis completed: {analyzed_count}",
            f"- Fulltext ingested: {fulltext_count}",
            f"- Context hubs: {context_nodes.get('count', 0)}",
            "",
            "## Trust Distribution",
            "",
        ]

        trust_counts: Dict[str, int] = stats["trust_counts"]
        if trust_counts:
            for trust_level, count in sorted(
                trust_counts.items(), key=lambda item: (-item[1], item[0])
            ):
                body_lines.append(f"- {trust_level}: {count}")
        else:
            body_lines.append("- No references in the library yet")

        source_counts: Dict[str, int] = stats["source_counts"]
        body_lines.extend(["", "## Source Mix", ""])
        if source_counts:
            for source, count in sorted(
                source_counts.items(), key=lambda item: (-item[1], item[0])
            ):
                body_lines.append(f"- {source}: {count}")
        else:
            body_lines.append("- No source mix available yet")

        body_lines.extend(["", "## Identity Resolution Queue", ""])
        if stats["unresolved_identity"]:
            body_lines.extend(self._library_reference_bullets(stats["unresolved_identity"], 10))
        else:
            body_lines.append("- No unresolved local identities")
        return body_lines

    def _library_live_query_lines(self) -> List[str]:
        body_lines: List[str] = []
        body_lines.extend(["", "## Live Analysis Queue", ""])
        body_lines.extend(
            self._property_query_block("analysis_state", "pending", format_name="table")
        )

        body_lines.extend(["", "## Live Fulltext Queue", ""])
        body_lines.extend(
            self._property_query_block("fulltext_state", "missing", format_name="table")
        )

        body_lines.extend(["", "## Live Review Queue", ""])
        body_lines.extend(
            self._property_query_block("review_state", "pending", format_name="table")
        )

        body_lines.extend(["", "## Live Asset Counts", ""])
        body_lines.extend(self._type_query_block("figure-note", format_name="count"))
        body_lines.extend([""])
        body_lines.extend(self._type_query_block("table-note", format_name="count"))

        body_lines.extend(["", "## Live Library Dashboard Count", ""])
        body_lines.extend(self._type_query_block("library-dashboard", format_name="count"))
        return body_lines

    def _library_queue_lines(self, stats: Dict[str, Any]) -> List[str]:
        body_lines: List[str] = []
        body_lines.extend(["", "## Analysis Queue", ""])
        if stats["analysis_queue"]:
            body_lines.extend(self._library_reference_bullets(stats["analysis_queue"], 10))
        else:
            body_lines.append("- All references have saved analysis")

        body_lines.extend(["", "## Fulltext Queue", ""])
        if stats["fulltext_queue"]:
            body_lines.extend(self._library_reference_bullets(stats["fulltext_queue"], 10))
        else:
            body_lines.append("- Fulltext available for all references")

        body_lines.extend(["", "## Recent Additions", ""])
        if stats["recent_additions"]:
            body_lines.extend(self._library_reference_bullets(stats["recent_additions"], 12))
        else:
            body_lines.append("- No references added yet")
        return body_lines

    def _library_top_lines(self, context_nodes: Dict[str, Any], stats: Dict[str, Any]) -> List[str]:
        top_context_hubs = sorted(
            context_nodes.get("nodes", []),
            key=lambda node: (-int(node.get("reference_count", 0)), node.get("title", "")),
        )[:8]
        top_journals = sorted(
            stats["journal_counts"].items(), key=lambda item: (-item[1], item[0].lower())
        )[:8]
        top_topics = sorted(
            stats["topic_counts"].items(), key=lambda item: (-item[1], item[0].lower())
        )[:8]

        body_lines: List[str] = ["", "## Top Context Hubs", ""]
        if top_context_hubs:
            for node in top_context_hubs:
                body_lines.append(
                    f"- [[{node['alias']}]]: {node['title']} ({node.get('reference_count', 0)} refs)"
                )
        else:
            body_lines.append("- No context hubs materialized yet")

        body_lines.extend(["", "## Top Journals", ""])
        if top_journals:
            for journal, count in top_journals:
                body_lines.append(f"- {journal}: {count}")
        else:
            body_lines.append("- No journal metadata yet")

        body_lines.extend(["", "## Top Topics", ""])
        if top_topics:
            for topic, count in top_topics:
                body_lines.append(f"- {topic}: {count}")
        else:
            body_lines.append("- No keyword topics yet")
        return body_lines
