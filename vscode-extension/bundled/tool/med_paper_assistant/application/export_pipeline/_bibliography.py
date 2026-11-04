"""Citation conversion and CSL-JSON bibliography building."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from med_paper_assistant.domain.services.citation_converter import (
    extract_citation_keys,
    wikilinks_to_pandoc,
)
from med_paper_assistant.domain.services.reference_key_resolution import (
    extract_pmid_from_key,
    resolve_reference_metadata,
)


def _resolve_bibliography(
    pipeline: BibliographyMixin, citation_keys: list[str], warnings: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve keys to CSL entries; record unresolved keys as warnings and missing keys."""
    bibliography = []
    missing_keys: list[str] = []

    for key in citation_keys:
        csl_entry = pipeline._resolve_citation_key(key)
        if csl_entry:
            bibliography.append(csl_entry)
        else:
            missing_keys.append(key)
            warnings.append(f"Citation key '{key}' not found in local references")

    return bibliography, missing_keys


def _raise_if_unresolved(strict: bool, missing_keys: list[str]) -> None:
    if strict and missing_keys:
        raise ValueError(
            f"Cannot export: {len(missing_keys)} unresolved citation(s): "
            + ", ".join(missing_keys)
            + ". Save these references first with save_reference_mcp()."
        )


class BibliographyMixin:
    """Converts wikilinks to Pandoc citations and resolves keys to CSL-JSON.

    Relies on ``self._ref_manager`` (a ``ReferenceMetadataPort``) set by ``ExportPipeline``.
    No class-level annotation is declared so ``dir(ExportPipeline)`` is unchanged.
    """

    def prepare_for_pandoc(self, content: str, *, strict: bool = False) -> dict[str, Any]:
        """
        Convert draft content to Pandoc-ready format.

        Steps:
          1. Convert [[wikilinks]] → [@key]
          2. Build CSL-JSON bibliography for all referenced keys
          3. Return converted content + bibliography data

        Args:
            content: Markdown with wikilink citations.
            strict: If True, raise ValueError when any citation key cannot be
                    resolved to a local reference (production export gate).

        Returns:
            {
                "content": str,          # Markdown with [@key] citations
                "bibliography": list,    # CSL-JSON entries
                "citation_keys": list,   # All citation keys found
                "conversion": ConversionResult,
                "warnings": list[str],
                "missing_keys": list[str],
            }

        Raises:
            ValueError: When strict=True and unresolved citation keys exist.
        """
        # Step 1: Convert wikilinks → [@key]
        conversion = wikilinks_to_pandoc(content)

        # Step 2: Build bibliography from all citation keys in the converted
        # content. Drafts may already contain Pandoc [@key] citations from a
        # previous export/knowledge-base pass, so do not rely only on keys
        # converted during this call.
        citation_keys = extract_citation_keys(conversion.content)
        warnings = list(conversion.warnings)
        bibliography, missing_keys = _resolve_bibliography(self, citation_keys, warnings)

        # Step 3: Strict mode — refuse to export with unresolved citations
        _raise_if_unresolved(strict, missing_keys)

        return {
            "content": conversion.content,
            "bibliography": bibliography,
            "citation_keys": citation_keys,
            "conversion": conversion,
            "warnings": warnings,
            "missing_keys": missing_keys,
        }

    def build_bibliography_json(
        self,
        content: str,
        output_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build a CSL-JSON bibliography file from draft content.

        Extracts all citation keys from the content and resolves them
        to CSL-JSON entries via the reference manager.

        Args:
            content: Markdown with any citation format.
            output_path: Optional path to write the .json file.

        Returns:
            List of CSL-JSON entries.
        """
        keys = extract_citation_keys(content)
        entries = []

        for key in keys:
            entry = self._resolve_citation_key(key)
            if entry:
                entries.append(entry)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(
                json.dumps(entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return entries

    def _resolve_citation_key(self, key: str) -> dict[str, Any] | None:
        """
        Resolve a citation key to a CSL-JSON entry.

        Tries multiple strategies:
          1. Extract PMID from key (e.g., tang2023_38049909 → 38049909)
          2. Look up metadata in reference manager
          3. Convert to CSL-JSON format

        Args:
            key: Citation key (e.g., "tang2023_38049909")

        Returns:
            CSL-JSON dict or None if not found.
        """
        resolved = resolve_reference_metadata(
            key,
            self._ref_manager.get_metadata,
            getattr(self._ref_manager, "list_references", None),
        )
        if not resolved:
            return None
        ref_id, metadata = resolved
        pmid = extract_pmid_from_key(key) or str(metadata.get("pmid") or "")

        # Build a domain Reference entity for CSL conversion.
        from med_paper_assistant.domain.entities.reference import Reference

        ref = Reference(
            unique_id=ref_id,
            title=metadata.get("title", ""),
            pmid=pmid,
            doi=metadata.get("doi", ""),
            authors=metadata.get("authors", []),
            authors_full=metadata.get("authors_full", []),
            journal=metadata.get("journal", ""),
            journal_abbrev=metadata.get("journal_abbrev", ""),
            year=int(metadata.get("year", 0) or 0),
            volume=metadata.get("volume", ""),
            issue=metadata.get("issue", ""),
            pages=metadata.get("pages", ""),
            citation_key=key,
        )

        # Use the citation_key as the CSL id so Pandoc can match [@key]
        return ref.to_csl_json(ref_id=key)

    @staticmethod
    def _extract_pmid(key: str) -> str | None:
        """
        Extract PMID from a citation key.

        Patterns:
          tang2023_38049909  → 38049909
          PMID:38049909      → 38049909
          38049909           → 38049909
        Zotero/DOI keys (``author2024_zot_ID``) never yield a PMID.
        """
        return extract_pmid_from_key(key)
