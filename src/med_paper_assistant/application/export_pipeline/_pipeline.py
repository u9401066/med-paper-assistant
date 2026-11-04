"""ExportPipeline: orchestrates citation conversion, bibliography and Pandoc export."""

from __future__ import annotations

from ._exporters import ExportFormatsMixin
from ._ports import DocumentExporterPort, ReferenceMetadataPort


class ExportPipeline(ExportFormatsMixin):
    """
    End-to-end export: Markdown (wikilinks) → formatted document.

    Usage:
        pipeline = ExportPipeline(ref_manager, pandoc_exporter)

        # Export to Word
        pipeline.export_docx(
            draft_path="projects/my-paper/drafts/introduction.md",
            output_path="exports/introduction.docx",
            csl_style="vancouver",
        )

        # Or just convert citations without exporting
        result = pipeline.prepare_for_pandoc(content, ref_manager)
    """

    def __init__(
        self,
        ref_manager: ReferenceMetadataPort,
        pandoc_exporter: DocumentExporterPort,
    ) -> None:
        self._ref_manager = ref_manager
        self._pandoc = pandoc_exporter
