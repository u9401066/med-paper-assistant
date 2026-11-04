"""Ports (structural interfaces) the export pipeline depends on."""

from __future__ import annotations

from typing import Any, Protocol


class ReferenceMetadataPort(Protocol):
    """Metadata lookup required by the export application service."""

    def get_metadata(self, reference_id: str) -> dict[str, Any] | None: ...


class DocumentExporterPort(Protocol):
    """Document conversion capabilities supplied by an infrastructure adapter."""

    @property
    def available(self) -> bool: ...

    def markdown_to_docx(self, **kwargs: Any) -> str: ...

    def markdown_to_pdf(self, **kwargs: Any) -> str: ...

    def convert(self, **kwargs: Any) -> str: ...

    def resolve_csl(self, csl: str | None) -> str | None: ...

    def detect_pdf_engine(self) -> str: ...
