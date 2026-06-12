"""Slug helpers shared across domain and infrastructure layers.

Two distinct, intentionally different slug algorithms are used in this codebase:

- :func:`slugify_name` — project/name slugs. Spaces and underscores become
  hyphens, and every *other* non-alphanumeric character is DROPPED (so dots
  disappear: ``"a.b.c"`` -> ``"abc"``).
- :func:`slugify_token` — generic tokens. Every run of non-alphanumeric
  characters becomes a single hyphen (so dots are KEPT as separators:
  ``"a.b.c"`` -> ``"a-b-c"``).

They are NOT interchangeable; pick the one matching the caller's prior
behavior.
"""

from __future__ import annotations

import re


def slugify_name(name: str, fallback: str = "untitled") -> str:
    """Slugify a human name into a URL-safe project slug.

    Collapses whitespace/underscores to hyphens and drops all other
    non-alphanumeric characters. Returns ``fallback`` when the result is empty.
    """
    slug = name.lower().strip()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or fallback


def slugify_token(value: str, fallback: str = "untitled") -> str:
    """Slugify an arbitrary token by mapping non-alphanumeric runs to hyphens.

    Returns ``fallback`` when the normalized result is empty.
    """
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or fallback
