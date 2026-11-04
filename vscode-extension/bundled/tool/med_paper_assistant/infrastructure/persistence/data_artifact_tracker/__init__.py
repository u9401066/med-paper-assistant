"""
Data Artifact Tracker — Track data analysis outputs with provenance.

Records every data analysis tool call (create_plot, run_statistical_test,
generate_table_one, analyze_dataset) with full parameters, output paths,
and reproducibility code. Cross-validates against manifest.json and draft text.

Architecture:
  Infrastructure layer service. Called after each data analysis tool call.
  Persists to `.audit/data-artifacts.yaml` and generates `.md` reports.
  Consumed by validate_data_artifacts MCP tool and Phase 5/6 gate validators.

Design rationale (CONSTITUTION §22):
  - Auditable: Every data artifact has a provenance trail
  - Reproducible: Parameters + code saved for each output
  - Self-validating: Cross-reference checks between artifacts ↔ manifest ↔ draft
"""

from __future__ import annotations

from ._models import (
    _TRUSTED_DATA_SUFFIXES,
    _UNTRUSTED_ANCHOR_SOURCE_HINTS,
    ArtifactType,
    ContentIntegrityReinspector,
    logger,
)
from ._tracker import DataArtifactTracker

__all__ = [
    "_TRUSTED_DATA_SUFFIXES",
    "_UNTRUSTED_ANCHOR_SOURCE_HINTS",
    "ArtifactType",
    "ContentIntegrityReinspector",
    "DataArtifactTracker",
    "logger",
]
