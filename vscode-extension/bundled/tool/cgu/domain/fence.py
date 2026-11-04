"""Fencing for untrusted text: truncate, strip instruction-like sentences, wrap."""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel

MAX_FRAGMENT_CHARS = 1200
REMOVED_MARKER = "[removed: instruction-like text]"

_INSTRUCTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier|preceding)\b",
    r"disregard\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier)?\s*"
    r"(instructions?|prompts?|rules?|messages?)",
    r"forget\s+(everything|all\s+(previous|prior)|your\s+instructions)",
    r"\b(system|developer)\s+(note|prompt|message|instruction)s?\b",
    r"\byou\s+are\s+now\b",
    r"\bnew\s+instructions?\b",
    r"\b(run|call|invoke|execute)\s+(the\s+|a\s+|an\s+)?(\S+\s+){0,3}(tool|function|command)\b",
    r"\b(run|call|invoke|execute)\s+\w+_\w+",
    r"<\|?\s*(system|assistant|user|im_start|im_end)\b",
    r"^\s*(assistant|system|user)\s*:",
    r"do\s+not\s+(tell|inform)\s+the\s+user",
    r"reveal\s+(your\s+|the\s+)?(system\s+prompt|instructions)",
    r"忽略(以上|先前|之前|前面|上述)?(的)?(所有)?(指示|指令|提示|規則)",
    r"無視(以上|先前|之前)?(的)?(所有)?(指示|指令|提示)",
    r"(系統|開發者)(提示|指令|備註|訊息)",
    r"你現在是",
    r"(執行|呼叫|調用|運行)\s*(下列|以下|這個|該)?\s*\S*\s*(工具|函式|指令)",
    r"不要(告訴|讓)使用者",
]
_INSTRUCTION_RE = re.compile("|".join(f"(?:{p})" for p in _INSTRUCTION_PATTERNS), re.IGNORECASE)
_SENTENCE_RE = re.compile(r"(?<=[.!?;。！？；\n])")
_INVISIBLE_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


class FencedText(BaseModel):
    text: str
    fenced_text: str
    truncated: bool
    stripped: int
    original_chars: int


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE_RE.sub("", text)
    return "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")


def strip_instructions(text: str) -> tuple[str, int]:
    kept: list[str] = []
    removed = 0
    for sentence in _SENTENCE_RE.split(text):
        if not sentence.strip():
            kept.append(sentence)
        elif _INSTRUCTION_RE.search(sentence):
            kept.append(REMOVED_MARKER + " ")
            removed += 1
        else:
            kept.append(sentence)
    return "".join(kept).strip(), removed


def _label(source: str) -> str:
    return re.sub(r"[^\w\-.:/ ]", "", source)[:80] or "unknown"


def fence(text: str, source: str, max_chars: int = MAX_FRAGMENT_CHARS) -> FencedText:
    cleaned = _clean(text)
    original = len(cleaned)
    stripped_text, removed = strip_instructions(cleaned)
    truncated = len(stripped_text) > max_chars
    body = stripped_text[:max_chars].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return FencedText(
        text=body,
        fenced_text=f'<untrusted_data source="{_label(source)}">{body}</untrusted_data>',
        truncated=truncated,
        stripped=removed,
        original_chars=original,
    )
