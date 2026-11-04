"""Local file, markdown and web-source intake."""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class LocalIntakeMixin:
    """Local file, markdown and web-source intake."""

    def import_markdown_file(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Import a markdown file into the canonical reference registry."""
        if not os.path.exists(file_path):
            return f"Error: Markdown source not found: {file_path}"

        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception as exc:
            return f"Error reading markdown source: {exc}"

        source_metadata = dict(metadata or {})
        source_metadata.setdefault("imported_from", os.path.abspath(file_path))
        return self._import_text_source(
            source_kind="markdown",
            locator=os.path.abspath(file_path),
            content=content,
            metadata=source_metadata,
            log_event="markdown_intake",
        )

    def import_markdown_content(
        self,
        markdown_text: str,
        *,
        source_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Import raw markdown text into the canonical reference registry."""
        source_metadata = dict(metadata or {})
        if source_name:
            source_metadata.setdefault("imported_from", source_name)
        return self._import_text_source(
            source_kind="markdown",
            locator=source_name,
            content=markdown_text,
            metadata=source_metadata,
            log_event="markdown_intake",
        )

    def import_web_source(
        self,
        url: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Import a fetched web page snapshot into the canonical reference registry."""
        if not url.strip():
            return "Error: Web source URL is required."

        source_metadata = dict(metadata or {})
        source_metadata.setdefault("url", url)
        source_metadata.setdefault("imported_from", url)
        return self._import_text_source(
            source_kind="web",
            locator=url,
            content=content,
            metadata=source_metadata,
            log_event="web_intake",
        )

    def import_local_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Import a local file into the canonical reference registry."""
        if not os.path.exists(file_path):
            return f"Error: Local file not found: {file_path}"

        content_hash = self.compute_content_hash(file_path)
        duplicate = self._already_imported_message(content_hash, "Local")
        if duplicate:
            return duplicate

        source_metadata = dict(metadata or {})
        source_metadata.setdefault("imported_from", os.path.abspath(file_path))
        source_metadata.setdefault("content_hash", content_hash)
        source_metadata.setdefault("saved_at", __import__("datetime").datetime.now().isoformat())

        payload = self._build_local_import_payload(file_path, source_metadata, content_hash)

        self._ensure_workspace_scaffolding()
        ref_dir = self._reference_dir(payload["unique_id"])
        os.makedirs(ref_dir, exist_ok=True)
        payload["imported_from"] = self._copy_source_artifact(file_path, ref_dir)
        self._persist_reference_payload(payload, log_event="local_import")

        return (
            f"Successfully imported local source into {payload['unique_id']}. "
            f"Foam link: [[{payload['citation_key']}]]"
        )

    def _import_text_source(
        self,
        *,
        source_kind: str,
        locator: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        log_event: str,
    ) -> str:
        normalized_content = content.strip()
        if not normalized_content:
            return f"Error: Empty {source_kind} content."

        content_hash = self._compute_text_hash(normalized_content)
        duplicate = self._already_imported_message(content_hash, source_kind.title())
        if duplicate:
            return duplicate

        payload = self._build_text_source_payload(
            source_kind=source_kind,
            locator=locator,
            content=normalized_content,
            content_hash=content_hash,
            source_metadata=dict(metadata or {}),
            log_event=log_event,
        )

        self._ensure_workspace_scaffolding()
        ref_dir = self._reference_dir(payload["unique_id"])
        os.makedirs(ref_dir, exist_ok=True)
        file_name = "original.md" if source_kind == "markdown" else "captured.md"
        payload["imported_from"] = self._write_text_source_artifact(
            ref_dir, file_name, normalized_content
        )
        self._persist_reference_payload(payload, log_event=log_event)

        return (
            f"Successfully imported {source_kind} source into {payload['unique_id']}. "
            f"Foam link: [[{payload['citation_key']}]]"
        )

    def _write_text_source_artifact(self, ref_dir: str | Path, file_name: str, content: str) -> str:
        source_dir = os.path.join(os.fspath(ref_dir), "source")
        os.makedirs(source_dir, exist_ok=True)
        destination = os.path.join(source_dir, file_name)
        with open(destination, "w", encoding="utf-8") as handle:
            handle.write(content)
        return destination
