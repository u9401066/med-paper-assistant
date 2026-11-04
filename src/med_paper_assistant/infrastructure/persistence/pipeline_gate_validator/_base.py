"""Shared state and helpers for the pipeline gate validator mixins."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import structlog
import yaml

from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE

from ._constants import _PIPELINE_PHASE_RANK
from ._io import UNREADABLE, read_json_value

logger = structlog.get_logger()


class GateBase:
    """Project directory layout plus helpers shared by every phase mixin."""

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"
        self._drafts_dir = self._project_dir / "drafts"
        self._exports_dir = self._project_dir / "exports"
        self._memory_dir = self._project_dir / ".memory"

    def _phase_rank(self, phase: int) -> int:
        """Return the logical phase order, independent of display numbering.

        Phase 2.1 is encoded as integer 21 and Phase 6.5 as 65 for MCP
        compatibility. Numeric comparisons such as ``21 >= 9`` are therefore
        incorrect; all ordering checks must go through this rank table.
        """
        return _PIPELINE_PHASE_RANK.get(phase, phase)

    def _get_section_content(self, manuscript: str, section_name: str) -> str:
        """Extract one named section from the manuscript."""
        pattern = re.compile(
            rf"^##\s+{re.escape(section_name)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(manuscript)
        if match:
            return match.group(1)

        fallback = re.compile(
            rf"^#\s+{re.escape(section_name)}\s*$([\s\S]*?)(?=^#\s+|\Z)",
            re.IGNORECASE | re.MULTILINE,
        )
        match = fallback.search(manuscript)
        return match.group(1) if match else ""

    def _get_workflow_mode(self) -> str:
        """Read workflow_mode from project.json, defaulting to manuscript."""
        project_json = self._project_dir / "project.json"
        if not project_json.is_file():
            return DEFAULT_WORKFLOW_MODE

        data = read_json_value(project_json)
        if data is UNREADABLE:
            return DEFAULT_WORKFLOW_MODE

        workflow_mode = str(data.get("workflow_mode") or DEFAULT_WORKFLOW_MODE).strip()
        return workflow_mode or DEFAULT_WORKFLOW_MODE

    def _compute_review_drafts_hash(self) -> str:
        """Match the review tools' hash of the canonical reviewed artifact."""
        if not self._drafts_dir.is_dir():
            return ""
        manuscript = self._drafts_dir / "manuscript.md"
        draft_files = (
            [manuscript] if manuscript.is_file() else sorted(self._drafts_dir.glob("*.md"))
        )
        if not draft_files:
            return ""

        digest = hashlib.sha256()
        try:
            for draft_file in draft_files:
                digest.update(draft_file.name.encode("utf-8"))
                digest.update(draft_file.read_bytes())
        except OSError:
            return ""
        return digest.hexdigest()

    def _find_concept_path(self) -> Path:
        """Return the preferred concept.md path for the project."""
        concept_in_drafts = self._drafts_dir / "concept.md"
        if concept_in_drafts.is_file():
            return concept_in_drafts
        return self._project_dir / "concept.md"

    def _get_paper_type_from_profile(self) -> str:
        """Read paper.type from journal-profile.yaml (default: 'original-research')."""
        jp_path = self._project_dir / "journal-profile.yaml"
        if jp_path.is_file():
            try:
                with open(jp_path, encoding="utf-8") as f:
                    profile = yaml.safe_load(f) or {}
                return profile.get("paper", {}).get("type", "original-research")
            except Exception:
                logger.warning("Failed to read paper type from journal-profile.yaml")
        return "original-research"

    def _resolve_min_references(self, paper_type: str) -> int:
        """Resolve minimum reference count for a paper type.

        Resolution order:
        1. journal-profile.yaml → references.minimum_reference_limits[paper_type]
        2. DEFAULT_MINIMUM_REFERENCES[paper_type]
        3. DEFAULT_MIN_REFERENCES (15)
        """
        from med_paper_assistant.infrastructure.persistence.writing_hooks._constants import (
            DEFAULT_MIN_REFERENCES,
            DEFAULT_MINIMUM_REFERENCES,
        )

        # 1. journal-profile.yaml override
        jp_path = self._project_dir / "journal-profile.yaml"
        if jp_path.is_file():
            try:
                with open(jp_path, encoding="utf-8") as f:
                    profile = yaml.safe_load(f)
                refs = profile.get("references") if isinstance(profile, dict) else None
                limits = refs.get("minimum_reference_limits") if isinstance(refs, dict) else None
                if isinstance(limits, dict):
                    val = limits.get(paper_type)
                    if val is not None:
                        return int(val)
            except (OSError, TypeError, ValueError, yaml.YAMLError):
                pass

        # 2. Built-in defaults per paper type
        if paper_type in DEFAULT_MINIMUM_REFERENCES:
            return DEFAULT_MINIMUM_REFERENCES[paper_type]

        # 3. Global fallback
        return DEFAULT_MIN_REFERENCES
