"""Data Artifact Tracker — composed tracker class."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.external import reinspect_content_integrity

from ._models import ContentIntegrityReinspector
from ._report import _ReportMixin
from ._validation import _ValidationMixin


class DataArtifactTracker(_ValidationMixin, _ReportMixin):
    """
    Track data analysis artifacts with provenance and reproducibility code.

    Usage:
        tracker = DataArtifactTracker(audit_dir, project_dir)
        tracker.record_artifact(
            tool_name="create_plot",
            artifact_type="figure",
            parameters={"filename": "data.csv", "plot_type": "boxplot", ...},
            output_path="results/figures/boxplot_age.png",
            data_source="data.csv",
            provenance_code="...",
        )
        report = tracker.generate_report()
        validation = tracker.validate_cross_references(draft_content)
    """

    DATA_FILE = "data-artifacts.yaml"
    REPORT_FILE = "data-artifacts.md"

    def __init__(
        self,
        audit_dir: str | Path,
        project_dir: str | Path,
        *,
        content_integrity_reinspector: ContentIntegrityReinspector = reinspect_content_integrity,
    ) -> None:
        self._audit_dir = Path(audit_dir)
        self._project_dir = Path(project_dir)
        self._data_path = self._audit_dir / self.DATA_FILE
        self._report_path = self._audit_dir / self.REPORT_FILE
        self._data: dict[str, Any] | None = None
        self._content_integrity_reinspector = content_integrity_reinspector
