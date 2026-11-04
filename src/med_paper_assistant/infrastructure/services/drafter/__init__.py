"""Citation-aware draft writing service (package form of the former ``drafter`` module)."""

from ._core import Drafter
from ._filenames import draft_filename_from_section, normalize_draft_filename
from ._models import JOURNAL_CITATION_CONFIGS, CitationStyle

__all__ = [
    "JOURNAL_CITATION_CONFIGS",
    "CitationStyle",
    "Drafter",
    "draft_filename_from_section",
    "normalize_draft_filename",
]
