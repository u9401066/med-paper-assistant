"""Phase 8-9 gates: reference sync and export deliverables."""

from __future__ import annotations

from ._export_integrity import ExportIntegrityMixin
from ._types import GateCheck, GateResult

_WIKILINK_DESCRIPTION = "All manuscript citation wikilinks resolve to saved references"


class ExportPhasesMixin(ExportIntegrityMixin):
    """Validation of Phase 8 (reference sync) and Phase 9 (export)."""

    def _validate_phase_8(self) -> GateResult:
        """Phase 8: References synced in manuscript."""
        checks = []

        ms = self._drafts_dir / "manuscript.md"
        if ms.is_file():
            content = ms.read_text(encoding="utf-8")
            has_references = "## References" in content or "# References" in content
            checks.append(
                GateCheck(
                    name="manuscript:references_section",
                    description="References section in manuscript",
                    passed=has_references,
                    details="found" if has_references else "MISSING",
                )
            )
            checks.append(self._wikilink_sync_check(content))
        else:
            checks.append(
                GateCheck(
                    name="manuscript.md",
                    description="Manuscript exists for ref sync",
                    passed=False,
                    details="MISSING",
                )
            )

        return GateResult(phase=8, phase_name="Reference Sync", checks=checks, passed=False)

    def _wikilink_sync_check(self, content: str) -> GateCheck:
        try:
            from med_paper_assistant.infrastructure.persistence.writing_hooks import (
                WritingHooksEngine,
            )

            c5 = WritingHooksEngine(project_dir=self._project_dir).check_wikilink_resolvable(
                content
            )
            critical_messages = [
                issue.message for issue in c5.issues if issue.severity == "CRITICAL"
            ]
            return GateCheck(
                name="reference-sync:wikilinks",
                description=_WIKILINK_DESCRIPTION,
                passed=c5.passed,
                details=(
                    "all citation wikilinks resolve"
                    if c5.passed
                    else "; ".join(critical_messages[:5])
                ),
            )
        except Exception as exc:
            return GateCheck(
                name="reference-sync:wikilinks",
                description=_WIKILINK_DESCRIPTION,
                passed=False,
                details=f"wikilink validation failed: {exc}",
            )

    def _validate_phase_9(self) -> GateResult:
        """Phase 9: Export files exist (CRITICAL — mandatory deliverables)."""
        checks = []

        for ext in ["docx", "pdf"]:
            candidates = (
                list(self._exports_dir.glob(f"*.{ext}")) if self._exports_dir.is_dir() else []
            )
            checks.append(
                GateCheck(
                    name=f"export:{ext}",
                    description=f"Exported {ext.upper()} file (mandatory)",
                    passed=len(candidates) > 0,
                    details=f"{len(candidates)} {ext} file(s)" if candidates else "MISSING",
                )
            )
            checks.append(self._build_export_integrity_check(ext, candidates))

        return GateResult(phase=9, phase_name="Export", checks=checks, passed=False)
