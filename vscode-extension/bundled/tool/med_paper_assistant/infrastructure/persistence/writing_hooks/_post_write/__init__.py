"""Writing Hooks — Post-write hooks mixin (A-series: A1–A7, A3b, A3c)."""

from __future__ import annotations

from ._ai_phrases import AntiAiPhraseHooksMixin
from ._ai_signals import AiSignalHooksMixin
from ._counts import CountHooksMixin
from ._format import FormatHooksMixin
from ._overlap import OverlapHooksMixin
from ._references import ReferenceSufficiencyHooksMixin
from ._voice import VoiceConsistencyHooksMixin


class PostWriteHooksMixin(
    CountHooksMixin,
    AntiAiPhraseHooksMixin,
    AiSignalHooksMixin,
    VoiceConsistencyHooksMixin,
    FormatHooksMixin,
    OverlapHooksMixin,
    ReferenceSufficiencyHooksMixin,
):
    """A-series hooks: post-write quality checks on individual sections."""


__all__ = ["PostWriteHooksMixin"]
