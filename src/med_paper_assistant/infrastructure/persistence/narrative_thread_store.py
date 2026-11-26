"""Persistent whole-manuscript narrative thread store (.memory/narrative-thread.yaml)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_LOCK_MARK = "\U0001f512"
_SECTION_HEADING_RE = re.compile(r"^#{1,2}\s+\d*\.?\s*(.+?)\s*$", re.MULTILINE)
_NUMERIC_ANCHOR_RE = re.compile(
    r"(?:\b[np]\s*[<=>]\s*0?\.\d+\b|\bn\s*=\s*\d[\d,]*\b|\b\d+(?:\.\d+)?\s*%"
    r"|\b(?:RR|OR|HR|aOR|aHR|MD|SMD)\s*[:=]?\s*\d+(?:\.\d+)?\b)",
    re.IGNORECASE,
)
_ABBR_DEF_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9\s\-]{3,55}?)\s*\(([A-Z][A-Z0-9\-]{1,9})\)")
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _clip(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split()).strip()
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _canonical_section_key(raw: str) -> str:
    low = raw.strip().lower().replace("_", " ").replace("-", " ")
    for key in ("abstract", "introduction", "methods", "results", "discussion", "conclusions"):
        if key in low or (key == "methods" and "material" in low):
            return key
    return low.split()[0] if low else "manuscript"


def extract_concept_anchors(project_dir: Path) -> dict[str, Any]:
    """Extract Research Question, 🔒 NOVELTY STATEMENT, and 🔒 KEY SELLING POINTS from concept.md."""
    concept_path = project_dir / "concept.md"
    if not concept_path.is_file():
        return {"novelty_statement": "", "selling_points": [], "research_question": ""}
    text = concept_path.read_text(encoding="utf-8", errors="replace")
    blocks = _split_heading_blocks(text)
    novelty = _find_block(blocks, lambda h: _LOCK_MARK in h and "novelty" in h.lower())
    selling_raw = _find_block(blocks, lambda h: _LOCK_MARK in h and "selling" in h.lower())
    rq = _find_block(
        blocks,
        lambda h: any(k in h.lower() for k in ("research question", "hypothesis", "objective")),
    )
    return {
        "novelty_statement": _strip_placeholders(novelty),
        "selling_points": _parse_bullet_points(selling_raw),
        "research_question": _strip_placeholders(rq),
    }


def _split_heading_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    heading: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,3}\s+(.+)$", line)
        if match:
            if heading is not None:
                blocks.append((heading, "\n".join(buf).strip()))
            heading = match.group(1).strip()
            buf = []
        elif heading is not None:
            buf.append(line)
    if heading is not None:
        blocks.append((heading, "\n".join(buf).strip()))
    return blocks


def _find_block(blocks: list[tuple[str, str]], predicate: Any) -> str:
    for heading, body in blocks:
        if predicate(heading):
            return body
    return ""


def _strip_placeholders(text: str) -> str:
    cleaned = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = [ln.lstrip("> ").strip() for ln in cleaned.splitlines()]
    kept = [ln for ln in lines if ln and not (ln.startswith("[") and ln.endswith("]"))]
    return " ".join(kept).strip()


def _parse_bullet_points(raw: str) -> list[str]:
    points: list[str] = []
    for line in raw.splitlines():
        stripped = line.lstrip("> ").strip()
        match = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", stripped)
        if match:
            item = match.group(1).strip()
            if item and not (item.startswith("[") and item.endswith("]")):
                points.append(item)
    if not points:
        fallback = _strip_placeholders(raw)
        if fallback:
            points.append(fallback)
    return points


def _prose_paragraphs(text: str) -> list[str]:
    cleaned = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.MULTILINE)
    paras = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    return [p for p in paras if not p.startswith("|") and not p.startswith("![")]


def extract_section_handoff(section_key: str, text: str) -> dict[str, Any]:
    """Summarize one drafted section into a compact cross-section handoff card."""
    paras = _prose_paragraphs(text)
    words = len(re.findall(r"\b\w+\b", text))
    anchors = list(dict.fromkeys(m.group(0).strip() for m in _NUMERIC_ANCHOR_RE.finditer(text)))
    abbrs = {m.group(2): m.group(1).strip() for m in _ABBR_DEF_RE.finditer(text)}
    cited = list(dict.fromkeys(_WIKILINK_RE.findall(text)))
    return {
        "section": section_key,
        "word_count": words,
        "opening_paragraph": _clip(paras[0]) if paras else "",
        "closing_paragraph": _clip(paras[-1]) if paras else "",
        "numeric_anchors": anchors[:12],
        "abbreviations": abbrs,
        "cited_keys": cited[:25],
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def split_manuscript_sections(content: str, fallback_section: str = "manuscript") -> dict[str, str]:
    """Split a markdown draft into canonical section keys."""
    matches = list(_SECTION_HEADING_RE.finditer(content))
    if not matches:
        return {_canonical_section_key(fallback_section): content.strip()}
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if not body:
            continue
        key = _canonical_section_key(match.group(1))
        sections[key] = (sections[key] + "\n\n" + body).strip() if key in sections else body
    return sections or {_canonical_section_key(fallback_section): content.strip()}


class NarrativeThreadStore:
    """Persist and refresh `.memory/narrative-thread.yaml` for a manuscript project."""

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir
        self._path = project_dir / ".memory" / "narrative-thread.yaml"

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict[str, Any]:
        """Load the stored thread or bootstrap from concept.md + existing drafts."""
        existing: dict[str, Any] = {}
        if self._path.is_file():
            try:
                parsed = yaml.safe_load(self._path.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    existing = parsed
            except (OSError, yaml.YAMLError):
                existing = {}
        anchors = extract_concept_anchors(self._project_dir)
        handoffs = dict(existing.get("section_handoffs") or {})
        if not handoffs:
            handoffs = self._scan_existing_drafts()
        return {
            "schema": "mdpaper.narrative_thread.v1",
            "central_thesis": str(
                existing.get("central_thesis") or anchors["novelty_statement"] or ""
            ),
            "research_question": anchors["research_question"],
            "novelty_statement": anchors["novelty_statement"],
            "selling_points": anchors["selling_points"],
            "canonical_terms": dict(existing.get("canonical_terms") or {}),
            "selling_point_map": dict(existing.get("selling_point_map") or {}),
            "section_handoffs": handoffs,
            "notes": str(existing.get("notes") or ""),
        }

    def save(self, data: dict[str, Any]) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return self._path

    def update(
        self,
        *,
        central_thesis: str = "",
        canonical_terms: dict[str, list[str]] | None = None,
        selling_point_map: dict[str, Any] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Merge explicit narrative thread decisions and refresh anchors/handoffs."""
        thread = self.load()
        if central_thesis.strip():
            thread["central_thesis"] = central_thesis.strip()
        if canonical_terms is not None:
            merged = dict(thread.get("canonical_terms") or {})
            merged.update(canonical_terms)
            thread["canonical_terms"] = merged
        if selling_point_map is not None:
            merged_map = dict(thread.get("selling_point_map") or {})
            merged_map.update(selling_point_map)
            thread["selling_point_map"] = merged_map
        if notes.strip():
            thread["notes"] = notes.strip()
        thread["section_handoffs"] = self._scan_existing_drafts(thread.get("section_handoffs"))
        self.save(thread)
        return thread

    def refresh_from_draft(
        self, filename: str, content: str, section_hint: str = ""
    ) -> dict[str, Any]:
        """Update section handoff card(s) after a draft write or patch."""
        thread = self.load()
        handoffs = dict(thread.get("section_handoffs") or {})
        fallback = section_hint or Path(filename).stem
        for sec_key, sec_body in split_manuscript_sections(content, fallback).items():
            handoffs[sec_key] = extract_section_handoff(sec_key, sec_body)
        thread["section_handoffs"] = handoffs
        self.save(thread)
        return thread

    def _scan_existing_drafts(self, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        handoffs = dict(existing or {})
        drafts_dir = self._project_dir / "drafts"
        if not drafts_dir.is_dir():
            return handoffs
        files = sorted(
            p for p in drafts_dir.glob("*.md") if p.is_file() and p.name.lower() != "concept.md"
        )
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            for sec_key, sec_body in split_manuscript_sections(text, path.stem).items():
                handoffs[sec_key] = extract_section_handoff(sec_key, sec_body)
        return handoffs
