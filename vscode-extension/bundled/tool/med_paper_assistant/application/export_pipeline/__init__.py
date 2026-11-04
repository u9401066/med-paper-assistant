"""
Export Pipeline — Orchestrates citation conversion + bibliography generation + Pandoc export.

Bridges the gap between the wikilink-based editing workflow and
Pandoc --citeproc's [@key] + CSL-JSON bibliography requirement.

Pipeline:
  1. Read draft (wikilink format)
  2. Convert wikilinks → [@key] (CitationConverter)
  3. Build CSL-JSON bibliography from referenced keys
  4. Call Pandoc with --citeproc --bibliography --csl
  5. Return formatted document

Architecture:
  Application layer service. Orchestrates domain + infrastructure services.
  No direct file I/O for conversion logic — delegates to lower layers.
"""

from __future__ import annotations

from ._pipeline import ExportPipeline
from ._ports import DocumentExporterPort, ReferenceMetadataPort

__all__ = [
    "DocumentExporterPort",
    "ExportPipeline",
    "ReferenceMetadataPort",
]
