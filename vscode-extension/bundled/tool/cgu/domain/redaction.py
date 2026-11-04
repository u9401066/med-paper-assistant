"""Best-effort, deterministic de-identification of captured questions. Standard library only.

The rules are fixed and ordered; every hit is replaced and counted. Names and clinical details
are NOT detected: callers must say so wherever they report redactions.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

MAX_INQUIRY_CHARS = 2000
MAX_GIST_CHARS = 500
MAX_RAW_CHARS = 20000
REDACTION_KEYS = ("email", "phone", "id", "number", "url")
NOT_DETECTED_NOTE = (
    "姓名與臨床細節未被偵測；去識別只是盡力而為，不保證。"
    "含病人資訊的提問請先改寫成不含個資的版本再送出。"
)

_URL = re.compile(r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_TW_ID = re.compile(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?!\d)")
_PHONE_INTL = re.compile(r"\+\d{1,3}(?:[\s\-.]?(?:\(\d{1,4}\)|\d{1,4})){2,5}")
_PHONE_TW_MOBILE = re.compile(r"(?<!\d)(?:886[\s\-]?|0)9\d{2}[\s\-]?\d{3}[\s\-]?\d{3}(?!\d)")
_PHONE_TW_LANDLINE = re.compile(
    r"(?<!\d)(?:\(0?[2-8]\d{0,2}\)|0[2-8]\d{0,2})[\s\-]?\d{3,4}[\s\-]?\d{3,4}(?!\d)"
)
_LONG_DIGITS = re.compile(r"\d{7,}")
_MIN_PHONE_DIGITS = 7


@dataclass(frozen=True)
class PreparedText:
    text: str
    redactions: dict[str, int]
    truncated: bool


def _strip_url(match: re.Match[str]) -> str:
    url = match.group(0)
    cut = min((i for i in (url.find("?"), url.find("#")) if i >= 0), default=-1)
    return url if cut < 0 else url[:cut]


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Replace emails, phones, Taiwan national ids, long digit runs and URL queries."""
    counts = dict.fromkeys(REDACTION_KEYS, 0)

    def url(match: re.Match[str]) -> str:
        stripped = _strip_url(match)
        if stripped != match.group(0):
            counts["url"] += 1
        return stripped

    def phone(match: re.Match[str]) -> str:
        if sum(ch.isdigit() for ch in match.group(0)) < _MIN_PHONE_DIGITS:
            return match.group(0)
        counts["phone"] += 1
        return "[phone]"

    def simple(key: str, replacement: str) -> Callable[[re.Match[str]], str]:
        def replace(_match: re.Match[str]) -> str:
            counts[key] += 1
            return replacement

        return replace

    text = _URL.sub(url, text)
    text = _EMAIL.sub(simple("email", "[email]"), text)
    text = _TW_ID.sub(simple("id", "[id]"), text)
    for pattern in (_PHONE_INTL, _PHONE_TW_MOBILE, _PHONE_TW_LANDLINE):
        text = pattern.sub(phone, text)
    text = _LONG_DIGITS.sub(simple("number", "[number]"), text)
    return text, counts


def merge_counts(*parts: dict[str, int]) -> dict[str, int]:
    total = dict.fromkeys(REDACTION_KEYS, 0)
    for part in parts:
        for key, value in part.items():
            total[key] = total.get(key, 0) + value
    return total


def prepare_text(text: str, limit: int = MAX_INQUIRY_CHARS) -> PreparedText:
    """Redact first, then cap, so a cut can never leave half of an identifier behind."""
    raw = text.strip()
    capped = raw[:MAX_RAW_CHARS]
    redacted, counts = redact(capped)
    truncated = len(raw) > MAX_RAW_CHARS or len(redacted) > limit
    return PreparedText(text=redacted[:limit].rstrip(), redactions=counts, truncated=truncated)
