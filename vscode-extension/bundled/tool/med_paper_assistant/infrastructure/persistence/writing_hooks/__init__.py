"""Writing Hooks package — quality checks for academic paper writing.

Re-exports all public symbols for backward compatibility.
Consumers can continue to use:

    from ...writing_hooks import WritingHooksEngine, HookIssue, HookResult
    from ...writing_hooks import BODY_SECTIONS, ANTI_AI_PHRASES, ...
"""

from ._constants import (
    AI_TRANSITION_WORDS,
    AMER_VS_BRIT,
    ANTI_AI_PARAGRAPH_START_ONLY,
    ANTI_AI_PHRASES,
    BODY_SECTIONS,
    BRIT_VS_AMER,
    COMMON_ABBREVIATIONS,
    DEFAULT_CITATION_DENSITY,
)
from ._engine import WritingHooksEngine
from ._models import HookIssue, HookResult

__all__ = [
    # Engine
    "WritingHooksEngine",
    # Models
    "HookIssue",
    "HookResult",
    # Constants
    "AMER_VS_BRIT",
    "ANTI_AI_PARAGRAPH_START_ONLY",
    "ANTI_AI_PHRASES",
    "AI_TRANSITION_WORDS",
    "BODY_SECTIONS",
    "BRIT_VS_AMER",
    "COMMON_ABBREVIATIONS",
    "DEFAULT_CITATION_DENSITY",
]
