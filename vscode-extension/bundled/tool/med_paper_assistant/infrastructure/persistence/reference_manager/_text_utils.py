"""Stateless text, hashing and markdown helpers."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from med_paper_assistant.shared.slug import slugify_token
from med_paper_assistant.shared.yaml_escape import escape_yaml_value


class TextUtilsMixin:
    """Stateless text, hashing and markdown helpers."""

    def _dedupe_strings(self, values: Any) -> List[str]:
        candidates: list[Any]
        if isinstance(values, str):
            candidates = [values]
        elif isinstance(values, list):
            candidates = values
        else:
            candidates = []

        deduped: List[str] = []
        seen: set[str] = set()
        for value in candidates:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _dedupe_provenance(self, entries: Any) -> List[Dict[str, Any]]:
        if not isinstance(entries, list):
            return []

        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            marker = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(entry)
        return deduped

    def _yaml_escape(self, value: str) -> str:
        return escape_yaml_value(value)

    def _slugify(self, value: str, fallback: str = "untitled") -> str:
        return slugify_token(value, fallback)

    def _compute_text_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_content_hash(self, file_path: str) -> str:
        """Compute a stable SHA256 hash for a local artifact."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _extract_markdown_headings(self, markdown_text: str) -> List[str]:
        headings: List[str] = []
        seen: set[str] = set()

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue

            heading = stripped.lstrip("#").strip()
            if not heading or heading in seen:
                continue

            seen.add(heading)
            headings.append(heading)

        return headings

    def _infer_markdown_title(self, markdown_text: str, fallback: str) -> str:
        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    return title
        return fallback

    def _build_markdown_summary(self, markdown_text: str, max_chars: int = 400) -> str:
        summary_parts: List[str] = []
        current_length = 0

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            summary_parts.append(stripped)
            current_length += len(stripped) + 1
            if current_length >= max_chars:
                break

        if not summary_parts:
            return ""

        summary = " ".join(summary_parts).strip()
        if len(summary) > max_chars:
            return summary[: max_chars - 3].rstrip() + "..."
        return summary

    def _extract_wikilinks(self, content: str) -> List[str]:
        seen: set[str] = set()
        links: List[str] = []
        for match in re.findall(r"\[\[([^\]]+)\]\]", content):
            normalized = str(match).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            links.append(normalized)
        return links

    def _read_text_preview(self, file_path: str, max_chars: int = 1200) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix not in {".md", ".csv", ".html", ".txt"}:
            return ""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return ""
        return content[:max_chars].strip()

    def _normalize_match_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()
