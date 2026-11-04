"""Library overview pages and Foam query blocks."""

import os
from typing import Any, Dict, List


class FoamLibraryMixin:
    """Library overview pages and Foam query blocks."""

    def _property_query_block(
        self,
        property_name: str,
        value: str,
        *,
        format_name: str = "count",
    ) -> List[str]:
        lines = [
            "```foam-query",
            "filter:",
            "  and:",
            f'    - {self._yaml_escape(property_name)}: "{self._yaml_escape(value)}"',
        ]
        if format_name == "count":
            lines.append("format: count")
        else:
            lines.extend(
                [
                    "select: [title, type, tags, backlink-count]",
                    "sort: title ASC",
                    f"format: {format_name}",
                ]
            )
        lines.append("```")
        return lines

    def _type_query_block(self, note_type: str, *, format_name: str = "count") -> List[str]:
        return self._property_query_block("type", note_type, format_name=format_name)

    def _linked_reference_query_block(self, *, format_name: str) -> List[str]:
        lines = [
            "```foam-query",
            "filter:",
            "  and:",
            '    - type: "reference"',
            '    - links_from: "$current"',
        ]
        if format_name == "count":
            lines.append("format: count")
        else:
            lines.extend(
                [
                    "select: [title, type, tags, backlink-count]",
                    "sort: title ASC",
                    f"format: {format_name}",
                ]
            )
        lines.append("```")
        return lines

    def _materialize_library_overview(self, context_nodes: Dict[str, Any]) -> Dict[str, Any]:
        note_path = os.path.join(self._library_pages_dir(), "overview.md")
        project_slug = self._current_project_slug()

        snapshots = self._resolve_reference_snapshots(limit=max(len(self.list_references()), 1))
        total_references = len(snapshots)
        analyzed_count = sum(
            1 for snapshot in snapshots if snapshot["metadata"].get("analysis_completed")
        )
        fulltext_count = sum(
            1 for snapshot in snapshots if snapshot["metadata"].get("fulltext_ingested")
        )

        stats = self._collect_library_stats(snapshots)

        body_lines = self._library_status_lines(
            total_references=total_references,
            analyzed_count=analyzed_count,
            fulltext_count=fulltext_count,
            context_nodes=context_nodes,
            stats=stats,
        )
        body_lines.extend(self._library_live_query_lines())
        body_lines.extend(self._library_queue_lines(stats))
        body_lines.extend(self._library_top_lines(context_nodes, stats))

        self._write_graph_note(
            note_path,
            title="Library Overview",
            note_type="library-overview",
            aliases=["library-overview"],
            tags=self._build_graph_note_tags(
                "library-overview",
                "library",
                ["dashboard/library", "workflow/library-first"],
            ),
            extra_fields=self._library_overview_fields(
                project_slug, total_references, analyzed_count, fulltext_count, context_nodes, stats
            ),
            body="\n".join(body_lines),
        )

        return {"alias": "library-overview", "title": "Library Overview", "path": note_path}

    def _library_overview_fields(
        self,
        project_slug: str,
        total_references: int,
        analyzed_count: int,
        fulltext_count: int,
        context_nodes: Dict[str, Any],
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "note_class": "library-overview",
            "note_domain": "library",
            "project": project_slug,
            "reference_count": total_references,
            "analysis_completed_count": analyzed_count,
            "analysis_pending_count": len(stats["analysis_queue"]),
            "fulltext_available_count": fulltext_count,
            "fulltext_missing_count": len(stats["fulltext_queue"]),
            "identity_resolution_count": len(stats["unresolved_identity"]),
            "context_hub_count": context_nodes.get("count", 0),
            "review_state": "n/a",
        }
