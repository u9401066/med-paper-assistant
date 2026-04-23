"""Writing Hooks — Journal configuration mixin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from med_paper_assistant.shared.constants import DEFAULT_WORD_LIMITS

from ._constants import DEFAULT_CITATION_DENSITY, DEFAULT_MIN_REFERENCES, DEFAULT_MINIMUM_REFERENCES

logger = structlog.get_logger()


class JournalConfigMixin:
    """Initialisation and journal-profile configuration helpers."""

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"
        self._journal_profile: dict[str, Any] | None = None
        self._load_journal_profile()

    def _load_journal_profile(self) -> None:
        """Load journal-profile.yaml if it exists."""
        profile_path = self._project_dir / "journal-profile.yaml"
        if profile_path.is_file():
            try:
                with open(profile_path, encoding="utf-8") as f:
                    self._journal_profile = yaml.safe_load(f) or {}
            except Exception:
                logger.warning("Failed to load journal-profile.yaml", path=str(profile_path))
                self._journal_profile = None

    def _get_section_word_limit(self, section_name: str) -> int | None:
        """Get word limit for a section (journal-profile -> DEFAULT_WORD_LIMITS fallback)."""
        if self._journal_profile:
            paper = self._journal_profile.get("paper", {})
            for sec in paper.get("sections", []):
                if sec.get("name", "").lower() == section_name.lower():
                    limit = sec.get("word_limit")
                    if limit is not None:
                        return int(limit)
        # Fallback to default — try exact then case-insensitive
        for key, val in DEFAULT_WORD_LIMITS.items():
            if key.lower() == section_name.lower():
                return val
        return None

    def _get_word_tolerance_pct(self) -> int:
        """Get word tolerance percentage (default 20)."""
        if self._journal_profile:
            pipeline = self._journal_profile.get("pipeline", {})
            tolerance = pipeline.get("tolerance", {})
            pct = tolerance.get("word_percent")
            if pct is not None:
                return int(pct)
        return 20

    def _get_citation_density_threshold(self, section_name: str) -> int:
        """Get citation density threshold (citations per N words, 0 = no check)."""
        if self._journal_profile:
            pipeline = self._journal_profile.get("pipeline", {})
            writing = pipeline.get("writing", {})
            density = writing.get("citation_density", {})
            val = density.get(section_name.lower())
            if val is not None:
                return int(val)
        return DEFAULT_CITATION_DENSITY.get(section_name.lower(), 0)

    def _get_language_preference(self, fallback: str = "american") -> str:
        """Get preferred English variant from journal-profile.yaml when available."""
        if not self._journal_profile:
            return fallback

        profile = self._journal_profile
        candidates = [
            profile.get("locale"),
            profile.get("language"),
            profile.get("language_preference"),
            profile.get("prefer_language"),
            profile.get("journal", {}).get("locale") if isinstance(profile.get("journal"), dict) else None,
            profile.get("journal", {}).get("language") if isinstance(profile.get("journal"), dict) else None,
            profile.get("pipeline", {}).get("writing", {}).get("prefer_language")
            if isinstance(profile.get("pipeline"), dict)
            else None,
        ]

        journal = profile.get("journal", {})
        journal_name = ""
        if isinstance(journal, dict):
            journal_name = str(journal.get("name") or journal.get("abbreviation") or "")
        else:
            journal_name = str(journal or "")
        if "british journal of anaesthesia" in journal_name.lower() or journal_name.lower() == "bja":
            return "british"

        for candidate in candidates:
            value = str(candidate or "").strip().lower().replace("_", "-")
            if value in {"british", "uk", "en-gb", "en-uk"}:
                return "british"
            if value in {"american", "us", "en-us"}:
                return "american"

        return fallback

    def _get_total_word_limit(self) -> int | None:
        """Get total manuscript word limit."""
        if self._journal_profile:
            wl = self._journal_profile.get("word_limits", {})
            total = wl.get("total_manuscript")
            if total is not None:
                return int(total)
        return None

    def _get_figure_table_limits(self) -> tuple[int | None, int | None]:
        """Get (figures_max, tables_max) from journal profile."""
        if self._journal_profile:
            assets = self._journal_profile.get("assets", {})
            fig = assets.get("figures_max")
            tbl = assets.get("tables_max")
            return (int(fig) if fig is not None else None, int(tbl) if tbl is not None else None)
        return (None, None)

    def _get_paper_type(self) -> str:
        """Get paper type from journal profile (default: 'original-research')."""
        if self._journal_profile:
            return self._journal_profile.get("paper", {}).get("type", "original-research")
        return "original-research"

    def _get_min_references(self, paper_type: str | None = None) -> int:
        """Get minimum reference count for the given paper type.

        Resolution order:
        1. journal-profile.yaml → references.minimum_reference_limits[paper_type]
        2. DEFAULT_MINIMUM_REFERENCES[paper_type]
        3. DEFAULT_MIN_REFERENCES (fallback: 15)

        Args:
            paper_type: Paper type key. If None, reads from journal profile.

        Returns:
            Minimum number of references required.
        """
        pt = paper_type or self._get_paper_type()

        # 1. journal-profile.yaml override
        if self._journal_profile:
            refs = self._journal_profile.get("references", {})
            min_limits = refs.get("minimum_reference_limits", {})
            if isinstance(min_limits, dict):
                val = min_limits.get(pt)
                if val is not None:
                    return int(val)

        # 2. Built-in defaults per paper type
        if pt in DEFAULT_MINIMUM_REFERENCES:
            return DEFAULT_MINIMUM_REFERENCES[pt]

        # 3. Global fallback
        return DEFAULT_MIN_REFERENCES

    def _get_max_references(self, paper_type: str | None = None) -> int | None:
        """Get maximum reference count for the given paper type.

        Resolution order:
        1. journal-profile.yaml → references.reference_limits[paper_type]
        2. journal-profile.yaml → references.max_references
        3. None (no limit)

        Args:
            paper_type: Paper type key. If None, reads from journal profile.

        Returns:
            Maximum number of references allowed, or None if no limit.
        """
        pt = paper_type or self._get_paper_type()

        if self._journal_profile:
            refs = self._journal_profile.get("references", {})
            # Per-type limit first
            limits = refs.get("reference_limits", {})
            if isinstance(limits, dict):
                val = limits.get(pt)
                if val is not None:
                    return int(val)
            # Global max
            max_ref = refs.get("max_references")
            if max_ref is not None:
                return int(max_ref)

        return None
