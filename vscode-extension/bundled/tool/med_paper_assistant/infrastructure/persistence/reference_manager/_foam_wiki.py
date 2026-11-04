"""Public knowledge-map, synthesis and agent-wiki materialization."""

from typing import List, Optional


class FoamWikiMixin:
    """Public knowledge-map, synthesis and agent-wiki materialization."""

    def build_knowledge_map(
        self,
        title: str,
        *,
        reference_ids: Optional[List[str]] = None,
        query: str = "",
        limit: int = 12,
    ) -> str:
        """Materialize a knowledge map note from selected references."""
        clean_title = title.strip() or "Knowledge Map"
        snapshots = self._resolve_reference_snapshots(reference_ids, query=query, limit=limit)
        if not snapshots:
            return "Error: No references available to build a knowledge map."

        body = self._build_knowledge_map_body(snapshots, query=query)
        page_path = self._write_materialized_page(
            page_type="knowledge_map",
            title=clean_title,
            query=query,
            focus="",
            reference_ids=[snapshot["reference_id"] for snapshot in snapshots],
            body=body,
            log_event="knowledge_map_materialized",
        )
        alias = self._materialized_page_alias("knowledge_map", self._slugify(clean_title))
        return f"Knowledge map materialized at {page_path}. Foam link: [[{alias}]]"

    def build_synthesis_page(
        self,
        title: str,
        *,
        reference_ids: Optional[List[str]] = None,
        query: str = "",
        focus: str = "",
        summary_markdown: str = "",
        limit: int = 12,
    ) -> str:
        """Materialize a synthesis note from selected references."""
        clean_title = title.strip() or "Synthesis Page"
        snapshots = self._resolve_reference_snapshots(reference_ids, query=query, limit=limit)
        if not snapshots:
            return "Error: No references available to build a synthesis page."

        body = self._build_synthesis_body(
            snapshots,
            focus=focus,
            summary_markdown=summary_markdown,
        )
        page_path = self._write_materialized_page(
            page_type="synthesis_page",
            title=clean_title,
            query=query,
            focus=focus,
            reference_ids=[snapshot["reference_id"] for snapshot in snapshots],
            body=body,
            log_event="synthesis_page_materialized",
        )
        alias = self._materialized_page_alias("synthesis_page", self._slugify(clean_title))
        return f"Synthesis page materialized at {page_path}. Foam link: [[{alias}]]"

    def materialize_agent_wiki(
        self,
        *,
        knowledge_map_title: str,
        synthesis_title: str = "",
        reference_ids: Optional[List[str]] = None,
        query: str = "",
        focus: str = "",
        summary_markdown: str = "",
        limit: int = 12,
    ) -> str:
        """Materialize the second-stage agent wiki bundle for a reference set."""
        clean_map_title = knowledge_map_title.strip() or "Knowledge Map"
        clean_synthesis_title = synthesis_title.strip() or f"{clean_map_title} synthesis"

        snapshots = self._resolve_reference_snapshots(reference_ids, query=query, limit=limit)
        if not snapshots:
            return "Error: No references available to materialize the agent wiki."

        selected_ids = [snapshot["reference_id"] for snapshot in snapshots]
        knowledge_map_result = self.build_knowledge_map(
            clean_map_title,
            reference_ids=selected_ids,
            query=query,
            limit=limit,
        )
        if knowledge_map_result.startswith("Error:"):
            return knowledge_map_result

        synthesis_result = self.build_synthesis_page(
            clean_synthesis_title,
            reference_ids=selected_ids,
            query=query,
            focus=focus,
            summary_markdown=summary_markdown,
            limit=limit,
        )
        if synthesis_result.startswith("Error:"):
            return synthesis_result

        return self._agent_wiki_result(clean_map_title, clean_synthesis_title)

    def _agent_wiki_result(self, clean_map_title: str, clean_synthesis_title: str) -> str:
        knowledge_alias = self._materialized_page_alias(
            "knowledge_map", self._slugify(clean_map_title)
        )
        synthesis_alias = self._materialized_page_alias(
            "synthesis_page", self._slugify(clean_synthesis_title)
        )
        return (
            "Agent wiki materialized. "
            f"Knowledge map: [[{knowledge_alias}]]. "
            f"Synthesis page: [[{synthesis_alias}]]."
        )
