"""Writing Hooks — Manuscript-level hooks mixin (C-series: C2–C14)."""

from __future__ import annotations

from pathlib import Path

from .._asset_manifest import AssetManifestMixin
from ._assets import AssetCoverageHooksMixin
from ._checklist import SubmissionChecklistHooksMixin
from ._citations import CitationHooksMixin
from ._claims import ClaimEvidenceHooksMixin
from ._consistency import ConsistencyHooksMixin
from ._figure_quality import FigureQualityHooksMixin
from ._limits import CountLimitHooksMixin
from ._reference_status import ReferenceStatusHooksMixin
from ._supplementary import SupplementaryHooksMixin


class ManuscriptHooksMixin(
    ClaimEvidenceHooksMixin,
    ConsistencyHooksMixin,
    ReferenceStatusHooksMixin,
    CountLimitHooksMixin,
    AssetCoverageHooksMixin,
    SupplementaryHooksMixin,
    CitationHooksMixin,
    FigureQualityHooksMixin,
    SubmissionChecklistHooksMixin,
    AssetManifestMixin,
):
    """C-series hooks: post-manuscript quality checks."""

    # Declared by JournalConfigMixin / _engine.py
    _project_dir: Path
    _audit_dir: Path


__all__ = ["ManuscriptHooksMixin"]
