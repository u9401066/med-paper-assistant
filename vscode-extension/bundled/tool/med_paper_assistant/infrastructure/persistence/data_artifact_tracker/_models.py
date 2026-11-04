"""Data Artifact Tracker — shared constants, types, and logger."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

import structlog

from med_paper_assistant.domain.value_objects.content_integrity import ContentIntegrityReceipt

# Bind the package name explicitly so log records keep the logger name they had
# when the tracker lived in a single module.
logger = structlog.get_logger(__package__)

ArtifactType = Literal["figure", "table", "statistics", "descriptive"]
_TRUSTED_DATA_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".yaml", ".yml", ".sav", ".dta"}
_UNTRUSTED_ANCHOR_SOURCE_HINTS = {
    "agent",
    "assumption",
    "concept",
    "draft",
    "estimated",
    "generated",
    "inferred",
    "llm",
    "summary",
}


class ContentIntegrityReinspector(Protocol):
    """Injected port for validating the current bytes of a reviewed asset."""

    def __call__(
        self,
        path: str | Path,
        *,
        asset_path: str | None = None,
    ) -> ContentIntegrityReceipt: ...
