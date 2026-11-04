"""Export artifact integrity checks used by the Phase 9 and Phase 11 gates."""

from __future__ import annotations

from pathlib import Path

from med_paper_assistant.shared.export_integrity import (
    inspect_docx_xml_smoke,
    inspect_pdf_smoke,
)

from ._base import GateBase
from ._types import GateCheck


class ExportIntegrityMixin(GateBase):
    """Release-gate smoke checks for exported DOCX and PDF deliverables."""

    @staticmethod
    def _check_docx_integrity(path: Path) -> tuple[bool, str]:
        """Validate a DOCX export enough for a release gate."""
        result = inspect_docx_xml_smoke(path)
        if result.get("passed"):
            stats = result.get("stats", {})
            return (
                True,
                "valid DOCX "
                f"({path.stat().st_size} bytes, "
                f"{stats.get('paragraphs', 0)} paragraph(s), "
                f"{stats.get('text_chars', 0)} text chars)",
            )
        failed = [
            f"{check.get('name')}: {check.get('details') or 'failed'}"
            for check in result.get("checks", [])
            if not check.get("passed")
        ]
        return False, "; ".join(failed[:5]) or "DOCX smoke failed"

    @staticmethod
    def _check_pdf_integrity(path: Path) -> tuple[bool, str]:
        """Validate a PDF export with lightweight structural checks."""
        result = inspect_pdf_smoke(path)
        if result.get("passed"):
            stats = result.get("stats", {})
            return (
                True,
                f"valid PDF ({stats.get('bytes', path.stat().st_size)} bytes, "
                f"{stats.get('pages', 'unknown')} page(s))",
            )
        failed = [
            f"{check.get('name')}: {check.get('details') or 'failed'}"
            for check in result.get("checks", [])
            if not check.get("passed")
        ]
        return False, "; ".join(failed[:5]) or "PDF smoke failed"

    def _build_export_integrity_check(self, ext: str, candidates: list[Path]) -> GateCheck:
        """Build an export integrity check for one deliverable type."""
        if not candidates:
            return GateCheck(
                name=f"export:{ext}:integrity",
                description=f"Exported {ext.upper()} file integrity",
                passed=False,
                details="MISSING",
            )

        checker = self._check_docx_integrity if ext == "docx" else self._check_pdf_integrity
        failures = []
        for candidate in sorted(candidates):
            passed, details = checker(candidate)
            if passed:
                return GateCheck(
                    name=f"export:{ext}:integrity",
                    description=f"Exported {ext.upper()} file integrity",
                    passed=True,
                    details=f"{candidate.name}: {details}",
                )
            failures.append(f"{candidate.name}: {details}")

        return GateCheck(
            name=f"export:{ext}:integrity",
            description=f"Exported {ext.upper()} file integrity",
            passed=False,
            details="; ".join(failures[:3]),
        )
