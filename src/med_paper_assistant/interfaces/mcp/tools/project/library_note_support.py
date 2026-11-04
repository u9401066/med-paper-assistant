"""Small pure helpers for library-wiki notes."""

from __future__ import annotations

_DEFAULT_STATUS = {
    "inbox": "captured",
    "concepts": "curated",
    "projects": "synthesized",
    "review": "reviewing",
    "daily": "logged",
}
_DEFAULT_QUEUE_BUCKET = {
    "inbox": "capture",
    "concepts": "concept-build",
    "projects": "synthesis",
    "review": "review",
    "daily": "daily",
}


def default_status(section: str) -> str:
    return _DEFAULT_STATUS.get(section, "active")


def default_queue_bucket(section: str) -> str:
    return _DEFAULT_QUEUE_BUCKET.get(section, "capture")


__all__ = ["default_queue_bucket", "default_status"]
