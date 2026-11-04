"""Foam index rebuild and graph refresh."""

import os
from typing import Any, Dict, List


class FoamIndexMixin:
    """Foam index rebuild and graph refresh."""

    def _rebuild_index(self) -> Dict[str, Any]:
        index_path = os.path.join(self._notes_dir(), "index.md")
        context_nodes = self._materialize_reference_context_notes()
        library_overview = self._materialize_library_overview(context_nodes)
        asset_nodes = self._materialize_asset_graph_notes()
        draft_section_nodes = self._materialize_draft_section_notes(asset_nodes.get("aliases", {}))
        library_pages = self._iter_library_pages()
        lines = self._index_live_count_lines(context_nodes)
        lines.extend(self._index_reference_lines())

        knowledge_maps = self._iter_materialized_pages("knowledge_map")
        synthesis_pages = self._iter_materialized_pages("synthesis_page")
        lines.extend(self._index_materialized_page_lines(knowledge_maps, synthesis_pages))
        lines.extend(self._index_draft_and_context_lines(draft_section_nodes, context_nodes))
        lines.extend(self._index_library_lines(library_pages, library_overview))
        lines.extend(self._index_asset_lines(asset_nodes))

        publish_pages = self._write_publish_safe_bundle(
            library_pages=library_pages,
            knowledge_maps=knowledge_maps,
            synthesis_pages=synthesis_pages,
            draft_section_nodes=draft_section_nodes,
            asset_nodes=asset_nodes,
        )
        lines.extend(["", "## Publish-Safe Views", ""])
        for page in publish_pages:
            lines.append(f"- [[{page['alias']}]]: {page['title']} [publish]")

        with open(index_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return {
            "references": len(self.list_references()),
            "draft_sections": len(draft_section_nodes),
            "context_hubs": context_nodes["count"],
            "library_views": len(library_pages),
            "figures": len(asset_nodes["figures"]),
            "tables": len(asset_nodes["tables"]),
            "publish_pages": len(publish_pages),
        }

    def _index_live_count_lines(self, context_nodes: Dict[str, Any]) -> List[str]:
        lines = [
            "# Knowledge Base Index",
            "",
            "## Live Graph Counts",
            "",
            "### References",
            "",
        ]
        lines.extend(self._type_query_block("reference", format_name="count"))
        lines.extend(["", "### Draft Sections", ""])
        lines.extend(self._type_query_block("draft-section", format_name="count"))
        lines.extend(["", "### Figures", ""])
        lines.extend(self._type_query_block("figure-note", format_name="count"))
        lines.extend(["", "### Tables", ""])
        lines.extend(self._type_query_block("table-note", format_name="count"))
        lines.extend(["", "### Library Views", ""])
        lines.extend(self._type_query_block("library-overview", format_name="count"))
        lines.extend([""])
        lines.extend(self._type_query_block("library-dashboard", format_name="count"))
        lines.extend([""])
        lines.extend(self._type_query_block("publish-index", format_name="count"))
        lines.extend([""])
        lines.extend(self._type_query_block("publish-links", format_name="count"))
        lines.extend(["", f"- Context hubs: {context_nodes['count']}"])
        return lines

    def _index_reference_lines(self) -> List[str]:
        lines = ["", "## References", ""]

        for ref_id in sorted(self.list_references()):
            metadata = self.get_metadata(ref_id)
            if not metadata:
                continue

            citation_key = metadata.get("citation_key") or ref_id
            title = metadata.get("title", ref_id)
            year = metadata.get("year", "")
            source = metadata.get("source", "")
            trust_level = metadata.get("trust_level", "")
            year_text = f" ({year})" if year else ""
            lines.append(f"- [[{citation_key}]]: {title}{year_text} [{source}/{trust_level}]")
        return lines

    def _index_materialized_page_lines(
        self,
        knowledge_maps: List[Dict[str, str]],
        synthesis_pages: List[Dict[str, str]],
    ) -> List[str]:
        lines: List[str] = ["", "## Knowledge Maps", ""]
        if knowledge_maps:
            for page in knowledge_maps:
                lines.append(f"- [[{page['alias']}]]: {page['title']} [knowledge_map]")
        else:
            lines.append("- None materialized yet")

        lines.extend(["", "## Synthesis Pages", ""])
        if synthesis_pages:
            for page in synthesis_pages:
                lines.append(f"- [[{page['alias']}]]: {page['title']} [synthesis_page]")
        else:
            lines.append("- None materialized yet")
        return lines

    def _index_draft_and_context_lines(
        self,
        draft_section_nodes: List[Dict[str, str]],
        context_nodes: Dict[str, Any],
    ) -> List[str]:
        lines: List[str] = ["", "## Draft Sections", ""]
        if draft_section_nodes:
            for node in sorted(draft_section_nodes, key=lambda item: item["title"]):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [draft-section]")
        else:
            lines.append("- No draft sections materialized yet")

        lines.extend(["", "## Context Hubs", ""])
        if context_nodes["nodes"]:
            for node in sorted(
                context_nodes["nodes"], key=lambda item: (item["kind"], item["title"])
            ):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [{node['kind']}]")
        else:
            lines.append("- No context hubs materialized yet")
        return lines

    def _index_library_lines(
        self,
        library_pages: List[Dict[str, str]],
        library_overview: Dict[str, Any],
    ) -> List[str]:
        lines: List[str] = ["", "## Library Views", ""]
        if library_pages:
            for page in library_pages:
                lines.append(f"- [[{page['alias']}]]: {page['title']} [library]")
        else:
            lines.append(
                f"- [[{library_overview['alias']}]]: {library_overview['title']} [library]"
            )
        return lines

    def _index_asset_lines(self, asset_nodes: Dict[str, Any]) -> List[str]:
        lines: List[str] = ["", "## Figures", ""]
        if asset_nodes["figures"]:
            for node in sorted(asset_nodes["figures"], key=lambda item: item["title"]):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [figure]")
        else:
            lines.append("- No figures registered yet")

        lines.extend(["", "## Tables", ""])
        if asset_nodes["tables"]:
            for node in sorted(asset_nodes["tables"], key=lambda item: item["title"]):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [table]")
        else:
            lines.append("- No tables registered yet")
        return lines

    def refresh_foam_graph(self) -> Dict[str, Any]:
        """Regenerate index and graph-facing note nodes for the active project."""
        self._ensure_workspace_scaffolding()
        return self._rebuild_index()
