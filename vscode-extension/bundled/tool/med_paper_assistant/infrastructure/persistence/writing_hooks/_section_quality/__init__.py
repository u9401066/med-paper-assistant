"""Writing Hooks — Section-quality hooks mixin (B-series: B8–B16)."""

from __future__ import annotations

from ._data_claims import DataClaimHooksMixin
from ._reporting import ReportingHooksMixin
from ._structure import SectionStructureHooksMixin
from ._style import SectionStyleHooksMixin


class SectionQualityMixin(
    DataClaimHooksMixin,
    SectionStyleHooksMixin,
    SectionStructureHooksMixin,
    ReportingHooksMixin,
):
    """B-series hooks: post-section quality checks."""


__all__ = ["SectionQualityMixin"]
