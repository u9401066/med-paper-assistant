"""
Figure & Table Tool Shells

MCP-facing signatures and docstrings for review_asset_for_insertion, insert_figure,
insert_table and list_assets. Each shell delegates to an implementation injected by
``figures.register_figure_tools``.
"""

from collections.abc import Callable
from typing import Any, Optional

from med_paper_assistant.infrastructure.services import Drafter


def _register_review_tool(
    tool: Callable[..., Any], review_impl: Callable[..., str]
) -> dict[str, Callable[..., Any]]:
    @tool()
    def review_asset_for_insertion(
        asset_type: str,
        filename: str,
        observations: str,
        rationale: str,
        proposed_caption: str,
        evidence_excerpt: str = "",
        project: Optional[str] = None,
        visible_watermark_review: str = "",
    ) -> str:
        """
        Record an auditable asset review receipt before inserting a figure/table.

        This is the hard-gated proof that the agent reviewed the asset before
        writing a caption or legend. `insert_figure`/`insert_table` will refuse
        to proceed unless a matching receipt exists.

        Args:
            asset_type: "figure" or "table"
            filename: Asset filename inside results/figures or results/tables
            observations: Pipe-separated observations, e.g. "2 groups|error bars shown"
            rationale: Why the proposed caption accurately represents the asset
            proposed_caption: The caption to be used later in insert_figure/table
            evidence_excerpt: Optional verbatim excerpt from a table or source note
            project: Project slug (uses current if omitted)
            visible_watermark_review: Required documented human conclusion when the
                conservative image heuristic returns HUMAN_REVIEW or UNCERTAIN
        """
        return review_impl(
            asset_type,
            filename,
            observations,
            rationale,
            proposed_caption,
            evidence_excerpt,
            project,
            visible_watermark_review,
        )

    return {"review_asset_for_insertion": review_asset_for_insertion}


def _register_insert_figure_tool(
    tool: Callable[..., Any], drafter: Drafter, insert_figure_impl: Callable[..., str]
) -> dict[str, Callable[..., Any]]:
    @tool()
    def insert_figure(
        filename: str,
        caption: str,
        figure_number: Optional[int] = None,
        draft_filename: Optional[str] = None,
        after_section: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Register a figure in the manifest and optionally insert a reference into a draft.

        The figure file must already exist in results/figures/.
        Use create_plot or save_diagram first to generate the file.

        Args:
            filename: Figure filename in results/figures/ (e.g., "boxplot_age.png")
            caption: Figure caption text
            figure_number: Figure number (auto-assigned if omitted)
            draft_filename: Draft file to insert reference into (optional)
            after_section: Insert after this heading (e.g., "Results"). Used with draft_filename.
            project: Project slug (uses current if omitted)
        """
        return insert_figure_impl(
            drafter, filename, caption, figure_number, draft_filename, after_section, project
        )

    return {"insert_figure": insert_figure}


def _register_insert_table_tool(
    tool: Callable[..., Any], drafter: Drafter, insert_table_impl: Callable[..., str]
) -> dict[str, Callable[..., Any]]:
    @tool()
    def insert_table(
        filename: str,
        caption: str,
        table_number: Optional[int] = None,
        table_content: Optional[str] = None,
        draft_filename: Optional[str] = None,
        after_section: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Register a table in the manifest and optionally insert into a draft.

        For generated tables (generate_table_one), pass the markdown content directly.
        For file-based tables, the file must exist in results/tables/.

        Args:
            filename: Table filename in results/tables/ (e.g., "table1.md")
            caption: Table caption text
            table_number: Table number (auto-assigned if omitted)
            table_content: Markdown table content to save (optional, creates the file)
            draft_filename: Draft file to insert into (optional)
            after_section: Insert after this heading (e.g., "Results")
            project: Project slug (uses current if omitted)
        """
        return insert_table_impl(
            drafter,
            filename,
            caption,
            table_number,
            table_content,
            draft_filename,
            after_section,
            project,
        )

    return {"insert_table": insert_table}


def _register_list_assets_tool(
    tool: Callable[..., Any], list_assets_impl: Callable[..., str]
) -> dict[str, Callable[..., Any]]:
    @tool()
    def list_assets(project: Optional[str] = None) -> str:
        """
        List all registered figures and tables from the manifest.

        Args:
            project: Project slug (uses current if omitted)
        """
        return list_assets_impl(project)

    return {"list_assets": list_assets}


def register_asset_tools(
    tool: Callable[..., Any],
    drafter: Drafter,
    *,
    review_impl: Callable[..., str],
    insert_figure_impl: Callable[..., str],
    insert_table_impl: Callable[..., str],
    list_assets_impl: Callable[..., str],
) -> dict[str, Callable[..., Any]]:
    """Register the four asset tools in their canonical order."""
    return {
        **_register_review_tool(tool, review_impl),
        **_register_insert_figure_tool(tool, drafter, insert_figure_impl),
        **_register_insert_table_tool(tool, drafter, insert_table_impl),
        **_register_list_assets_tool(tool, list_assets_impl),
    }
