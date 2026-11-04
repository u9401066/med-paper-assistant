"""Phase 2.1 gate: fulltext ingestion, per-reference analysis, source materials."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ._base import GateBase
from ._types import GateCheck, GateResult


@dataclass
class _FulltextSurvey:
    """Aggregated per-reference fulltext and analysis evidence."""

    total_refs: int = 0
    ingested_count: int = 0
    not_ingested_count: int = 0
    analyzed_count: int = 0
    not_analyzed_count: int = 0
    analysis_failures: list[str] = field(default_factory=list)
    fulltext_failures: list[str] = field(default_factory=list)


class FulltextPhaseMixin(GateBase):
    """Phase 2.1 (fulltext ingestion + per-reference analysis) validation."""

    def _validate_phase_2_1(self) -> GateResult:
        """Phase 2.1: Fulltext ingestion + per-reference analysis."""
        checks = []
        refs_dir = self._project_dir / "references"
        records, invalid_records, legacy_count = self._reference_records(refs_dir)

        checks.append(self._fulltext_status_file_check(refs_dir))

        survey = self._survey_references(records)
        if invalid_records:
            survey.analysis_failures.extend(invalid_records)
            survey.fulltext_failures.extend(invalid_records)
        if legacy_count:
            migration_error = f"{legacy_count} legacy references require structured migration"
            survey.analysis_failures.append(migration_error)
            survey.fulltext_failures.append(migration_error)

        checks.append(self._fulltext_coverage_check(survey))
        checks.append(self._fulltext_evidence_check(survey))
        checks.append(self._analysis_coverage_check(survey))

        # Warning if majority lacks fulltext
        if survey.total_refs > 0 and survey.not_ingested_count > survey.total_refs * 0.5:
            checks.append(
                GateCheck(
                    name="fulltext_coverage_warning",
                    description="Majority of references should have fulltext",
                    passed=False,
                    details=f">50% references ({survey.not_ingested_count}/{survey.total_refs}) lack fulltext. Consider adding Open Access references.",
                    severity="WARNING",
                )
            )

        checks.extend(self._source_material_checks())
        return GateResult(phase=21, phase_name="Fulltext Ingestion", checks=checks, passed=False)

    @staticmethod
    def _fulltext_status_file_check(refs_dir: Path) -> GateCheck:
        status_file = refs_dir / "fulltext-ingestion-status.md"
        try:
            status_exists = status_file.is_file() and status_file.stat().st_size > 0
        except OSError:
            status_exists = False
        return GateCheck(
            name="fulltext_ingestion_status",
            description="Fulltext ingestion status file created",
            passed=status_exists,
            details="exists and is non-empty" if status_exists else "MISSING or empty",
        )

    def _survey_references(self, records: list[tuple[Path, dict[str, Any]]]) -> _FulltextSurvey:
        """Check individual reference metadata for fulltext and analysis status."""
        survey = _FulltextSurvey()
        for ref_dir, metadata in records:
            survey.total_refs += 1
            (
                fulltext_valid,
                fulltext_details,
                source_revision_sha256,
                source_kind,
            ) = self._validate_fulltext_status(ref_dir, metadata)
            if fulltext_valid and metadata.get("fulltext_ingested") is True:
                survey.ingested_count += 1
            else:
                survey.not_ingested_count += 1
            if not fulltext_valid:
                survey.fulltext_failures.append(f"{ref_dir.name}: {fulltext_details}")

            analysis_valid = False
            analysis_details = "source evidence is invalid"
            if fulltext_valid:
                analysis_valid, analysis_details = self._validate_reference_analysis(
                    ref_dir,
                    metadata,
                    source_revision_sha256=source_revision_sha256,
                    source_kind=source_kind,
                )
            if metadata.get("analysis_completed") is True and analysis_valid:
                survey.analyzed_count += 1
            else:
                survey.not_analyzed_count += 1
                if metadata.get("analysis_completed") is not True:
                    survey.analysis_failures.append(
                        f"{ref_dir.name}: analysis_completed is not true"
                    )
                else:
                    survey.analysis_failures.append(f"{ref_dir.name}: {analysis_details}")
        return survey

    @staticmethod
    def _fulltext_coverage_check(survey: _FulltextSurvey) -> GateCheck:
        return GateCheck(
            name="fulltext_coverage",
            description="References with fulltext ingested",
            passed=survey.total_refs == 0 or survey.ingested_count > 0,
            details=f"{survey.ingested_count}/{survey.total_refs} ingested, {survey.not_ingested_count} metadata-only",
            severity="WARNING",
        )

    @staticmethod
    def _fulltext_evidence_check(survey: _FulltextSurvey) -> GateCheck:
        return GateCheck(
            name="fulltext_evidence",
            description="Every reference has ingestion evidence or an explicit fallback reason",
            passed=not survey.fulltext_failures and survey.total_refs > 0,
            details=(
                f"{survey.total_refs} reference fulltext statuses verified"
                if not survey.fulltext_failures and survey.total_refs > 0
                else "; ".join(survey.fulltext_failures[:5]) or "no structured references"
            ),
            severity="CRITICAL",
        )

    @staticmethod
    def _analysis_coverage_check(survey: _FulltextSurvey) -> GateCheck:
        """Analysis coverage check (CRITICAL — every ref must be analyzed)."""
        total_refs = survey.total_refs
        all_analyzed = (
            total_refs > 0 and not survey.analysis_failures and survey.not_analyzed_count == 0
        )
        return GateCheck(
            name="analysis_coverage",
            description="Every saved reference has a completed analysis bound to its source evidence",
            passed=all_analyzed,
            details=(
                f"{survey.analyzed_count}/{total_refs} analysis artifacts verified"
                if all_analyzed
                else "; ".join(survey.analysis_failures[:5])
                or f"{survey.analyzed_count}/{total_refs} analyzed, {survey.not_analyzed_count} pending"
            ),
            severity="CRITICAL",
        )

    def _source_material_checks(self) -> list[GateCheck]:
        """Flag source materials that still await asset-aware ingestion."""
        source_materials_path = self._audit_dir / "source-materials.yaml"
        if not source_materials_path.is_file():
            return []
        try:
            source_manifest = (
                yaml.safe_load(source_materials_path.read_text(encoding="utf-8")) or {}
            )
        except (yaml.YAMLError, OSError):
            source_manifest = {}
        materials = source_manifest.get("materials", [])
        if not isinstance(materials, list):
            materials = []
        pending_primary, pending_advisory = self._split_pending_materials(materials)

        if pending_primary:
            return [self._pending_primary_check(pending_primary)]
        if pending_advisory:
            return [
                GateCheck(
                    name="source-materials:asset-aware",
                    description="Non-primary source materials still pending asset-aware ingestion",
                    passed=False,
                    severity="WARNING",
                    details=(
                        f"{len(pending_advisory)} non-primary source material(s) still "
                        "pending asset-aware ingestion"
                    ),
                )
            ]
        return []

    @staticmethod
    def _split_pending_materials(
        materials: list[Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        pending_primary: list[dict[str, Any]] = []
        pending_advisory: list[dict[str, Any]] = []
        for material in materials:
            if not isinstance(material, dict):
                continue
            raw_ingestion = material.get("ingestion")
            ingestion: dict[str, Any] = raw_ingestion if isinstance(raw_ingestion, dict) else {}
            if ingestion.get("status") != "pending_asset_aware":
                continue
            role = str(
                material.get("evidence_priority")
                or material.get("evidence_role")
                or material.get("role")
                or ""
            ).lower()
            if role in {"primary_user_material", "primary_data", "source_data"}:
                pending_primary.append(material)
            else:
                pending_advisory.append(material)
        return pending_primary, pending_advisory

    @staticmethod
    def _pending_primary_check(pending_primary: list[dict[str, Any]]) -> GateCheck:
        examples = ", ".join(
            str(item.get("id") or item.get("relative_path") or item.get("filename"))
            for item in pending_primary[:5]
        )
        return GateCheck(
            name="source-materials:asset-aware",
            description="Primary source materials requiring asset-aware ingestion are completed",
            passed=False,
            severity="CRITICAL",
            details=(
                f"{len(pending_primary)} primary source material(s) still pending "
                f"asset-aware ingestion: {examples}"
            ),
            expected_pattern=(
                "materials[].ingestion.status != pending_asset_aware for primary_user_material"
            ),
            search_path=".audit/source-materials.yaml",
            fix_hint=(
                "Call asset-aware ingest_documents, then "
                'project_action(action="record_asset_ingestion", '
                'source_material_id="source-001", asset_aware_doc_id="...").'
            ),
        )
