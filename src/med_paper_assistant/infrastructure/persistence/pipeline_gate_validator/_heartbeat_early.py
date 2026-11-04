"""Heartbeat snapshots for phases 0-5: cheap artifact checks without side effects."""

from __future__ import annotations

from ._base import GateBase
from ._io import read_text_or_empty
from ._types import GateCheck

_REQUIRED_SECTIONS = ["Abstract", "Introduction", "Methods", "Results", "Discussion"]


class HeartbeatEarlyMixin(GateBase):
    """Heartbeat checks for configuration, literature, concept, planning and writing."""

    def _heartbeat_phase_0(self) -> list[GateCheck]:
        jp = self._project_dir / "journal-profile.yaml"
        return [
            GateCheck(
                name="journal-profile.yaml",
                description="Journal profile configuration file",
                passed=jp.is_file(),
                details="exists" if jp.is_file() else "MISSING",
            )
        ]

    def _heartbeat_phase_1(self) -> list[GateCheck]:
        return [
            GateCheck(
                name=f"dir:{subdir}",
                description=f"Project subdirectory {subdir}",
                passed=(self._project_dir / subdir).is_dir(),
                details="exists" if (self._project_dir / subdir).is_dir() else "MISSING",
            )
            for subdir in ["drafts", "references", "data", "results", ".audit", ".memory"]
        ]

    def _heartbeat_phase_2(self) -> list[GateCheck]:
        refs_dir = self._project_dir / "references"
        ref_count = self._count_references(refs_dir)
        paper_type = self._get_paper_type_from_profile()
        min_refs = self._resolve_min_references(paper_type)
        passed = ref_count >= min_refs
        return [
            GateCheck(
                name="references_count",
                description=f"At least {min_refs} references saved (paper type: {paper_type})",
                passed=passed,
                details=f"{ref_count}/{min_refs} references found"
                + ("" if passed else f" — need {min_refs - ref_count} more"),
            )
        ]

    def _heartbeat_phase_21(self) -> list[GateCheck]:
        status_file = self._project_dir / "references" / "fulltext-ingestion-status.md"
        return [
            GateCheck(
                name="fulltext_ingestion_status",
                description="Fulltext ingestion status file created",
                passed=status_file.is_file(),
                details="exists" if status_file.is_file() else "MISSING",
            )
        ]

    def _heartbeat_phase_3(self) -> list[GateCheck]:
        concept = self._find_concept_path()
        checks = [
            GateCheck(
                name="concept.md",
                description="Concept document exists",
                passed=concept.is_file(),
                details="exists" if concept.is_file() else "MISSING",
            )
        ]
        if concept.is_file():
            content = read_text_or_empty(concept)
            for marker in ["NOVELTY", "KEY SELLING POINTS"]:
                found = marker in content
                checks.append(
                    GateCheck(
                        name=f"concept:{marker}",
                        description=f"Protected {marker} section present",
                        passed=found,
                        details="found" if found else "MISSING",
                    )
                )
        review_complete, review_details = self._concept_review_is_complete(
            self._load_concept_review()
        )
        checks.append(
            GateCheck(
                name="audit:concept-review.yaml",
                description="Structured concept review artifact",
                passed=review_complete,
                details=review_details if review_complete else f"MISSING — {review_details}",
            )
        )
        return checks

    def _heartbeat_phase_4(self) -> list[GateCheck]:
        plan_yaml = self._project_dir / "manuscript-plan.yaml"
        plan_md = self._drafts_dir / "manuscript-plan.md"
        plan_exists = plan_yaml.is_file() or plan_md.is_file()
        return [
            GateCheck(
                name="manuscript-plan",
                description="Manuscript plan (yaml or md)",
                passed=plan_exists,
                details="exists" if plan_exists else "MISSING",
            )
        ]

    def _heartbeat_phase_5(self) -> list[GateCheck]:
        ms = self._drafts_dir / "manuscript.md"
        checks = [
            GateCheck(
                name="manuscript.md",
                description="Manuscript draft exists",
                passed=ms.is_file(),
                details="exists" if ms.is_file() else "MISSING",
            )
        ]
        if ms.is_file():
            content = read_text_or_empty(ms)
            for section in _REQUIRED_SECTIONS:
                found = f"## {section}" in content or f"# {section}" in content
                checks.append(
                    GateCheck(
                        name=f"section:{section}",
                        description=f"{section} section present",
                        passed=found,
                        details="found" if found else "MISSING",
                    )
                )
        return checks
