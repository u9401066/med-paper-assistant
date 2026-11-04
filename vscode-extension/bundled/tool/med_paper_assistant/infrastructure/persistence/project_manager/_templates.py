"""Project config and workspace seed document builders for ProjectManager."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ....domain.paper_types import get_paper_type_dict
from ....shared.constants import WORKFLOW_MODES


class WorkspaceTemplateMixin:
    """Build project config dictionaries and initial workspace documents."""

    def _create_project_config(
        self,
        name: str,
        slug: str,
        description: str,
        authors: Optional[List[Any]],
        target_journal: str,
        paper_type: str,
        workflow_mode: str,
        interaction_preferences: Optional[Dict[str, Any]],
        memo: str,
    ) -> Dict[str, Any]:
        """Create project configuration dictionary.

        Authors can be:
        - List of strings (legacy): ["Name1", "Name2"]
        - List of dicts (structured): [{"name": "...", "affiliations": [...], ...}]
        """
        # Normalize authors to structured format
        normalized_authors = self._normalize_authors(authors or [])

        return {
            "name": name,
            "slug": slug,
            "description": description,
            "authors": normalized_authors,
            "target_journal": target_journal,
            "paper_type": paper_type,
            "paper_type_info": get_paper_type_dict(paper_type) if paper_type else {},
            "workflow_mode": workflow_mode,
            "workflow_mode_info": WORKFLOW_MODES.get(workflow_mode, {}),
            "interaction_preferences": interaction_preferences or {},
            "memo": memo,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "concept",
        }

    def _build_workspace_seed_document(
        self,
        project_name: str,
        paper_type: str,
        target_journal: str,
        memo: str,
        workflow_mode: str,
    ) -> str:
        """Create the initial concept/library workspace document."""
        if workflow_mode == "library-wiki":
            return self._build_library_workspace_seed(project_name, memo)

        return self.template_reader.get_concept_template(
            project_name=project_name,
            paper_type=paper_type,
            target_journal=target_journal,
            memo=memo,
        )

    def _build_library_workspace_seed(self, project_name: str, memo: str) -> str:
        """Create the initial library/wiki workspace document."""
        notes_block = memo.strip() if memo.strip() else "[No memo yet]"
        return f"""# Library Workspace: {project_name}

## Scope
<!-- What literature domain, corpus, or topic family should this workspace cover? -->

## Intake Priorities
<!-- Which papers, feeds, or local sources should be ingested first? -->

## Reading Queues
- Inbox
- Active reading
- Review worklists
- Synthesis targets

## Daily Capture
<!-- Use daily/ for journal-style capture pages and short-lived intake notes -->

## Knowledge Threads
<!-- Themes, methods, interventions, datasets, or claims to connect -->

## Open Questions
<!-- Questions the agent should answer from this library -->

## Optional Manuscript Paths
<!-- If a paper idea emerges later, outline it here before switching workflow_mode -->

## Author Notes
{notes_block}
"""

    def _build_conversion_message(self, workflow_mode: str, stats: Dict[str, int]) -> str:
        """Build a workflow-aware conversion summary for exploration workspaces."""
        if workflow_mode == "library-wiki":
            lines = [
                f"   - References: {stats.get('references', 0)}",
                f"   - Inbox notes: {stats.get('inbox', 0)}",
                f"   - Concept notes: {stats.get('concepts', 0)}",
                f"   - Synthesis projects: {stats.get('projects', 0)}",
                f"   - Review notes: {stats.get('review', 0)}",
                f"   - Daily notes: {stats.get('daily', 0)}",
            ]
        else:
            lines = [
                f"   - References: {stats.get('references', 0)}",
                f"   - Drafts: {stats.get('drafts', 0)}",
                f"   - Data files: {stats.get('data_files', 0)}",
            ]

        return "\n".join(lines)

    @staticmethod
    def _normalize_authors(authors: List[Any]) -> List[Dict[str, Any]]:
        """Normalize authors to structured format.

        Handles both legacy string entries and structured dicts.

        Args:
            authors: List of author names (str) or author dicts.

        Returns:
            List of structured author dicts.
        """
        from med_paper_assistant.domain.value_objects.author import Author

        result = []
        for i, entry in enumerate(authors):
            author = Author.from_dict(entry)
            # Assign order if not set
            if author.order == 0:
                author = Author(
                    name=author.name,
                    affiliations=list(author.affiliations),
                    orcid=author.orcid,
                    email=author.email,
                    is_corresponding=author.is_corresponding,
                    order=i + 1,
                )
            result.append(author.to_dict())
        return result
