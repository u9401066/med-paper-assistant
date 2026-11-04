"""Pandoc input preparation: resource paths, YAML frontmatter, author block, temp files."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class PandocInputMixin:
    """Static builders for the inputs Pandoc needs besides the converted body."""

    @staticmethod
    def _build_resource_path_args(
        draft_path: str, extra_args: list[str] | None = None
    ) -> list[str]:
        """Build Pandoc ``--resource-path`` args so local figures/tables resolve.

        Args:
            draft_path: Absolute path to the markdown draft being exported.
            extra_args: Existing Pandoc arguments to preserve.

        Returns:
            A new argument list containing an appended ``--resource-path`` unless
            one was already provided by the caller.
        """
        args = list(extra_args or [])
        if any(arg == "--resource-path" or arg.startswith("--resource-path=") for arg in args):
            return args

        draft_dir = Path(draft_path).resolve().parent
        project_dir = draft_dir.parent
        resource_dirs = [
            draft_dir,
            project_dir / "results" / "figures",
            project_dir / "results" / "tables",
            project_dir / "results",
            project_dir,
        ]

        seen: set[str] = set()
        ordered_dirs: list[str] = []
        for directory in resource_dirs:
            directory_str = str(directory)
            if directory_str not in seen:
                ordered_dirs.append(directory_str)
                seen.add(directory_str)

        args.append(f"--resource-path={os.pathsep.join(ordered_dirs)}")
        return args

    @staticmethod
    def _build_yaml_frontmatter(
        title: str,
        authors: list[dict[str, Any]] | None = None,
        date: str | None = None,
    ) -> str:
        """Build YAML frontmatter for Pandoc metadata (title, authors, date).

        Pandoc uses YAML frontmatter to populate document properties and
        render title/author blocks in the output (Word, PDF, HTML).

        Args:
            title: Document title.
            authors: List of structured author dicts with 'name', 'affiliations',
                     'email', 'is_corresponding', 'orcid' fields.
            date: Optional date string.

        Returns:
            YAML frontmatter string (including ``---`` delimiters), or empty
            string if no metadata provided.
        """
        import yaml

        meta: dict[str, Any] = {}
        if title:
            meta["title"] = title
        if authors:
            # Pandoc author metadata: keep only 'name' for YAML.
            # Detailed author info (affiliations, email, ORCID) is rendered
            # in the content block via _build_author_content_block().
            pandoc_authors = []
            for a in authors:
                name = a.get("name", "")
                if not name:
                    continue
                pandoc_authors.append(name)
            if pandoc_authors:
                meta["author"] = pandoc_authors
        if date:
            meta["date"] = date

        if not meta:
            return ""

        return "---\n" + yaml.dump(meta, allow_unicode=True, default_flow_style=False) + "---\n\n"

    @staticmethod
    def _build_author_content_block(authors: list[dict[str, Any]]) -> str:
        """Build a rich author block as markdown content (with affiliations).

        Complements YAML frontmatter by injecting a visible author/affiliation
        section directly into the document body.  This ensures affiliations,
        ORCID, and corresponding-author info are visible in the output even
        when the Pandoc template doesn't render structured author metadata.

        Args:
            authors: List of structured author dicts.

        Returns:
            Markdown string with author line, affiliations, and corresponding
            author details.  Empty string if no authors provided.
        """
        from med_paper_assistant.domain.value_objects.author import Author, generate_author_block

        if not authors:
            return ""

        author_objs = [Author.from_dict(a) for a in authors if a.get("name")]
        if not author_objs:
            return ""

        return generate_author_block(author_objs) + "\n"

    @staticmethod
    def _strip_title_heading(content: str) -> tuple[str, str]:
        """Extract and remove the first H1 heading from markdown content.

        When we inject the title via YAML frontmatter, the original ``# Title``
        line would be duplicated.  This helper strips it.

        Args:
            content: Markdown content.

        Returns:
            (title_text, remaining_content) — title without ``# `` prefix,
            and the content with the H1 line removed.
        """
        import re

        match = re.match(r"^#\s+(.+?)(?:\n|$)", content)
        if match:
            title = match.group(1).strip()
            remaining = content[match.end() :]
            return title, remaining
        return "", content


def inject_pandoc_metadata(
    pipeline: PandocInputMixin, pandoc_content: str, metadata: dict[str, Any] | None
) -> str:
    """Prepend YAML frontmatter and the author block when project metadata is provided."""
    if not metadata:
        return pandoc_content

    authors = metadata.get("authors", [])
    date = metadata.get("date")

    # Extract title from H1 heading (avoid duplication)
    extracted_title, body = pipeline._strip_title_heading(pandoc_content)
    title = metadata.get("title") or extracted_title

    # Build YAML frontmatter (sets Word document properties)
    frontmatter = pipeline._build_yaml_frontmatter(title, authors, date)

    # Build visible author block (affiliations, corresponding author)
    author_block = pipeline._build_author_content_block(authors)

    return frontmatter + author_block + body


def write_temp_bibliography(bibliography: list[dict[str, Any]]) -> str:
    """Write CSL-JSON entries to a temporary file and return its path."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as bib_file:
        json.dump(bibliography, bib_file, ensure_ascii=False, indent=2)
        return bib_file.name


def remove_quietly(path: str) -> None:
    """Delete a temporary file, ignoring OS errors."""
    try:
        os.unlink(path)
    except OSError:
        pass
