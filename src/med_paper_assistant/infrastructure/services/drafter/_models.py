"""Citation style enumeration and journal-specific citation format configurations."""

from enum import Enum


class CitationStyle(Enum):
    VANCOUVER = "vancouver"  # [1] Author. Title. Journal (Year).
    APA = "apa"  # Author (Year). Title. Journal.
    HARVARD = "harvard"  # Author (Year) 'Title', Journal.
    NATURE = "nature"  # 1. Author. Title. Journal Year.
    AMA = "ama"  # 1. Author. Title. Journal. Year.
    MDPI = "mdpi"  # 1. Author. Title. Journal Year, Volume, Page.
    NLM = "nlm"  # National Library of Medicine style


# Journal-specific citation format configurations
JOURNAL_CITATION_CONFIGS = {
    "sensors": {
        "style": "mdpi",
        "format": "{number}. {authors}. {title}. {journal} {year}, {volume}, {pages}.",
        "author_format": "last_initials",  # "Kim, S.H.; Lee, J.W."
        "max_authors": 6,
        "et_al_threshold": 6,
    },
    "lancet": {
        "style": "vancouver",
        "format": "{number} {authors}. {title}. {journal} {year}; {volume}: {pages}.",
        "author_format": "full_first",  # "Kim SH, Lee JW"
        "max_authors": 6,
        "et_al_threshold": 3,
    },
    "bja": {  # British Journal of Anaesthesia
        "style": "vancouver",
        "format": "{number}. {authors}. {title}. {journal} {year}; {volume}: {pages}.",
        "author_format": "last_initials_space",  # "Kim S H, Lee J W"
        "max_authors": 6,
        "et_al_threshold": 6,
    },
    "anesthesiology": {
        "style": "ama",
        "format": "{number}. {authors}. {title}. {journal}. {year};{volume}:{pages}.",
        "author_format": "last_initials",
        "max_authors": 6,
        "et_al_threshold": 6,
    },
    "default": {
        "style": "vancouver",
        "format": "[{number}] {authors}. {title}. {journal} ({year}). PMID:{pmid}.",
        "author_format": "full",
        "max_authors": 10,
        "et_al_threshold": 3,
    },
}
