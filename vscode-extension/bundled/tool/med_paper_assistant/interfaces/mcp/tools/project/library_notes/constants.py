"""Constants shared by the library note tools."""

from __future__ import annotations

import re

ALLOWED_LIBRARY_SECTIONS = ("inbox", "concepts", "projects", "review", "daily")


SECTION_ALIASES = {
    "inbox": "inbox",
    "concept": "concepts",
    "concepts": "concepts",
    "project": "projects",
    "projects": "projects",
    "review": "review",
    "reviews": "review",
    "daily": "daily",
    "day": "daily",
    "journal": "daily",
}


QUEUE_LABELS = {
    "capture": "Capture Queue",
    "active-reading": "Active Reading",
    "concept-build": "Concept Building",
    "synthesis": "Synthesis Queue",
    "review": "Review Queue",
    "daily": "Daily Capture",
    "blocked": "Blocked",
}


TRIAGE_PROGRESSION = {
    "inbox": "concepts",
    "concepts": "projects",
    "projects": "review",
    "review": "review",
    "daily": "inbox",
}


FRONTMATTER_FIELD_ORDER = (
    "title",
    "type",
    "section",
    "status",
    "tags",
    "related_notes",
    "updated_at",
)


TEMPLATE_ALIASES = {
    "capture": "capture",
    "inbox": "capture",
    "inbox-capture": "capture",
    "concept": "concept",
    "concept-page": "concept",
    "review": "review",
    "review-note": "review",
    "daily": "daily",
    "daily-note": "daily",
    "journal": "daily",
}


TEMPLATE_NOTE_TYPES = {
    "capture": "library-capture",
    "concept": "library-concept",
    "review": "library-review",
    "daily": "library-daily",
}


PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b|\[(?:Add|TODO|TBD|Claim|Gap|Open question|Question)[^\]]*\]",
    flags=re.IGNORECASE,
)


ASSET_LINK_PATTERN = re.compile(
    r"(?:content-(?:card|inline)!|!)?\[\[([^\]]+)\]\]",
    flags=re.IGNORECASE,
)
