"""Draft creation and PMID citation insertion."""

import os
import re
from pathlib import Path
from typing import Dict

from med_paper_assistant.domain.services.references_section import split_references_section
from med_paper_assistant.shared.path_guard import resolve_child_path

from ._filenames import normalize_draft_filename
from ._formatting import CitationFormattingMixin
from ._models import CitationStyle


def _parse_pmid_bibliography(references_content: str) -> Dict[str, str]:
    """Map ``[n]`` bibliography numbers to PMIDs; reject wikilink-only bibliographies."""
    # Guard against mixing incompatible citation workflows.
    # insert_citation expects PMID-based bibliography entries, while
    # sync_references_from_wikilinks produces wikilink-based references.
    has_pmid_bib = bool(re.search(r"\[\d+\].*?PMID:\d+", references_content))
    has_wikilink_bib = bool(re.search(r"\[\[[^\]]+\]\]", references_content))
    if has_wikilink_bib and not has_pmid_bib:
        raise ValueError(
            "This draft uses wikilink-synced references. "
            "insert_citation() only works with PMID-numbered bibliographies. "
            "Add [[citation_key]] in the draft body and run "
            "sync_references_from_wikilinks() (or the MCP sync_references tool) instead."
        )

    # Regex to parse bib: \[(\d+)\] .*? PMID:(\d+)
    # Note: This only works for numbered styles (Vancouver).
    # For Author-Date styles, we need a different strategy or just rely on PMID presence.
    # For now, we assume if we are inserting, we might be disrupting the order.
    # But if we use Author-Date, order doesn't matter as much (alphabetical usually).

    bib_pattern = r"\[(\d+)\] .*? PMID:(\d+)"
    existing_refs = {}
    for ref_num, ref_pmid in re.findall(bib_pattern, references_content):
        existing_refs[ref_num] = ref_pmid
    return existing_refs


def _restore_pmid_placeholders(
    body_content: str, existing_refs: Dict[str, str], citation_style: str
) -> str:
    """Replace ``[n]`` in the body with ``[PMID:xxx]`` (numbered styles only)."""
    # If style is APA/Harvard, citations are (Author, Year).
    # We need to reverse-engineer them too? Or just leave them?
    # If we leave them, `_compile_draft` won't touch them unless they match `(PMID:...)`.
    # So we only need to revert if we want to re-number.
    if citation_style in [
        CitationStyle.VANCOUVER.value,
        CitationStyle.NATURE.value,
        CitationStyle.AMA.value,
    ]:
        for ref_num, ref_pmid in existing_refs.items():
            # Handle brackets [1] or superscript ^1 (if we implemented that)
            # For now assuming [1] for Vancouver
            body_content = body_content.replace(f"[{ref_num}]", f"[PMID:{ref_pmid}]")
    return body_content


def _content_with_inserted_citation(
    drafter: CitationFormattingMixin, content: str, target_text: str, pmid: str
) -> str:
    # 1. Extract and Parse Bibliography to map [n] -> PMID
    split = split_references_section(content)
    body_content = split.body.strip()
    existing_refs: Dict[str, str] = {}

    if split.has_references:
        existing_refs = _parse_pmid_bibliography(split.references)

    # 2. Replace [n] in body with [PMID:xxx] (Only for numbered styles)
    body_content = _restore_pmid_placeholders(body_content, existing_refs, drafter.citation_style)

    # 3. Find target text and insert new placeholder
    if target_text not in body_content:
        raise ValueError(f"Target text '{target_text}' not found in draft.")

    insertion = f" [PMID:{pmid}]"
    new_content = body_content.replace(target_text, target_text + insertion, 1)

    # 4. Re-compile (trailing sections such as Figure Legends are preserved)
    return split.with_tail(drafter._compile_draft(new_content))


class DraftWritingMixin(CitationFormattingMixin):
    # Creates drafts and inserts PMID citations into existing drafts (no docstring: see
    # CitationFormattingMixin).

    def create_draft(self, filename: str, content: str) -> str:
        """
        Create a draft file with formatted citations.

        Args:
            filename: Name of the draft file (e.g., "introduction.md").
            content: Content with placeholders like (PMID:123456).

        Returns:
            Path to the created draft file.
        """
        filename = normalize_draft_filename(filename)

        final_content = self._compile_draft(content)

        drafts_path = Path(self.drafts_dir).resolve()
        drafts_path.mkdir(parents=True, exist_ok=True)
        filepath = resolve_child_path(
            drafts_path,
            filename,
            field_name="Draft filename",
            allowed_suffixes={".md"},
        )

        # Auto-snapshot before overwrite
        self.snapshot_manager.snapshot_before_write(filename, reason="create_draft")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)

        self.ref_manager.refresh_foam_graph()

        # Auto-commit after successful write
        self.git_committer.commit_draft(filename, reason="create_draft")

        return str(filepath)

    def insert_citation(self, filename: str, target_text: str, pmid: str) -> str:
        """
        Insert a citation after the target text in an existing draft.

        Args:
            filename: Name of the draft file.
            target_text: Text segment to locate insertion point.
            pmid: PubMed ID to cite.

        Returns:
            Path to the updated draft file.
        """
        filename = normalize_draft_filename(filename)

        filepath = str(resolve_child_path(self.drafts_dir, filename, field_name="Draft filename"))

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Draft file {filename} not found.")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        final_content = _content_with_inserted_citation(self, content, target_text, pmid)

        # Auto-snapshot before overwrite
        self.snapshot_manager.snapshot_before_write(filename, reason="insert_citation")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)

        self.ref_manager.refresh_foam_graph()

        # Auto-commit after successful write
        self.git_committer.commit_draft(filename, reason="insert_citation")

        return filepath
