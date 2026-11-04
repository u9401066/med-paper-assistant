"""Phase 0-2 gates: configuration, project setup, literature."""

from __future__ import annotations

from typing import Any

from ._base import GateBase
from ._types import GateCheck, GateResult


class EarlyPhasesMixin(GateBase):
    """Validation of Phase 0 (configuration), 1 (setup) and 2 (literature)."""

    def _validate_phase_0(self) -> GateResult:
        """Phase 0: journal profile and source-material scan must exist."""
        checks = []
        jp = self._project_dir / "journal-profile.yaml"
        source_materials = self._audit_dir / "source-materials.yaml"
        checks.append(
            GateCheck(
                name="journal-profile.yaml",
                description="Journal profile configuration file",
                passed=jp.is_file(),
                details=str(jp) if not jp.is_file() else "exists",
                expected_pattern="journal-profile.yaml",
                search_path="project root",
                fix_hint='Run project_action(action="journal_profile", ...).',
            )
        )
        checks.append(
            GateCheck(
                name=".audit/source-materials.yaml",
                description="Workspace source-material scan manifest, including user-provided DOCX/XLSX/PDF inputs",
                passed=source_materials.is_file(),
                details=(
                    "exists"
                    if source_materials.is_file()
                    else "MISSING — run Phase 0 source-material intake before literature search/writing"
                ),
                expected_pattern=".audit/source-materials.yaml",
                search_path=".audit/",
                fix_hint='Run project_action(action="source_materials") so local DOCX/XLSX/PDF inputs are registered and asset-aware ingestion can be triggered.',
            )
        )
        return GateResult(phase=0, phase_name="Configuration", checks=checks, passed=False)

    def _validate_phase_1(self) -> GateResult:
        """Phase 1: Project directory structure must exist."""
        checks = []
        for subdir in ["drafts", "references", "data", "results", ".audit", ".memory"]:
            p = self._project_dir / subdir
            checks.append(
                GateCheck(
                    name=f"dir:{subdir}",
                    description=f"Project subdirectory {subdir}",
                    passed=p.is_dir(),
                    details="exists" if p.is_dir() else "MISSING",
                )
            )
        return GateResult(phase=1, phase_name="Setup", checks=checks, passed=False)

    def _validate_phase_2(self) -> GateResult:
        """Phase 2: references must meet paper-type-specific minimum.

        Resolution order for minimum count:
        1. journal-profile.yaml → references.minimum_reference_limits[paper_type]
        2. DEFAULT_MINIMUM_REFERENCES[paper_type]
        3. DEFAULT_MIN_REFERENCES fallback (15)
        """

        checks = []
        refs_dir = self._project_dir / "references"
        records, invalid_records, legacy_count = self._reference_records(refs_dir)
        ref_count = self._count_references(refs_dir)

        # Determine paper type and minimum
        paper_type = self._get_paper_type_from_profile()
        min_refs = self._resolve_min_references(paper_type)

        passed = ref_count >= min_refs
        checks.append(
            GateCheck(
                name="references_count",
                description=f"At least {min_refs} references saved (paper type: {paper_type})",
                passed=passed,
                details=f"{ref_count}/{min_refs} references found"
                + ("" if passed else f" — need {min_refs - ref_count} more"),
            )
        )
        checks.append(self._references_integrity_check(records, invalid_records, legacy_count))
        checks.extend(self._search_audit_checks())

        return GateResult(phase=2, phase_name="Literature", checks=checks, passed=False)

    @staticmethod
    def _references_integrity_check(
        records: list[Any], invalid_records: list[str], legacy_count: int
    ) -> GateCheck:
        return GateCheck(
            name="references_integrity",
            description="Reference metadata has stable identity and honest trust provenance",
            passed=not invalid_records,
            details=(
                f"{len(records)} structured + {legacy_count} legacy references validated"
                if not invalid_records
                else "; ".join(invalid_records[:5])
            ),
        )

    def _search_audit_checks(self) -> list[GateCheck]:
        """Audit artifacts."""
        checks = []
        for artifact in ["search-strategy.md", "reference-selection.md"]:
            p = self._audit_dir / artifact
            checks.append(
                GateCheck(
                    name=f"audit:{artifact}",
                    description="Search audit artifact",
                    passed=p.is_file(),
                    details="exists" if p.is_file() else "MISSING",
                    severity="WARNING",
                )
            )
        return checks
