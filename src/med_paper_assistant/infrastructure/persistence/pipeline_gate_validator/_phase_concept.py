"""Phase 3-4 gates: concept and planning."""

from __future__ import annotations

from pathlib import Path

from ._base import GateBase
from ._types import GateCheck, GateResult


class ConceptPhasesMixin(GateBase):
    """Validation of Phase 3 (concept) and Phase 4 (planning)."""

    def _validate_phase_3(self) -> GateResult:
        """Phase 3: concept.md exists with required sections."""
        checks = []

        concept = self._find_concept_path()

        checks.append(
            GateCheck(
                name="concept.md",
                description="Concept document exists",
                passed=concept.is_file(),
                details="exists" if concept.is_file() else "MISSING",
            )
        )

        if concept.is_file():
            checks.extend(self._protected_marker_checks(concept))

        # Audit artifact
        p = self._audit_dir / "concept-validation.md"
        checks.append(
            GateCheck(
                name="audit:concept-validation.md",
                description="Concept validation record",
                passed=p.is_file(),
                details="exists" if p.is_file() else "MISSING",
                severity="WARNING",
            )
        )

        checks.extend(self._concept_review_checks())
        return GateResult(phase=3, phase_name="Concept", checks=checks, passed=False)

    @staticmethod
    def _protected_marker_checks(concept: Path) -> list[GateCheck]:
        content = concept.read_text(encoding="utf-8")
        checks = []
        for marker in ["NOVELTY", "KEY SELLING POINTS"]:
            found = marker in content
            checks.append(
                GateCheck(
                    name=f"concept:{marker}",
                    description=f"🔒 {marker} section present",
                    passed=found,
                    details="found" if found else "MISSING — protected content required",
                )
            )
        return checks

    def _concept_review_checks(self) -> list[GateCheck]:
        concept_review = self._load_concept_review()
        review_complete, review_details = self._concept_review_is_complete(concept_review)
        checks = [
            GateCheck(
                name="audit:concept-review.yaml",
                description="Structured concept review artifact",
                passed=review_complete,
                details=review_details if review_complete else f"MISSING — {review_details}",
            )
        ]

        review_actionable, actionable_details = self._concept_review_is_actionable()
        checks.append(
            GateCheck(
                name="concept-review-decision",
                description="Concept review must be ready or manually approved",
                passed=review_actionable,
                details=actionable_details
                if review_actionable
                else f"BLOCKED — {actionable_details}",
            )
        )
        return checks

    def _validate_phase_4(self) -> GateResult:
        """Phase 4: manuscript-plan exists after concept review normalization."""
        checks = []

        review_complete, review_details = self._concept_review_is_actionable()
        checks.append(
            GateCheck(
                name="concept-review-ready",
                description="Concept review artifact available for planning",
                passed=review_complete,
                details=review_details if review_complete else f"MISSING — {review_details}",
            )
        )

        # Check both .yaml and .md variants
        plan_yaml = self._project_dir / "manuscript-plan.yaml"
        plan_md = self._drafts_dir / "manuscript-plan.md"
        plan_exists = plan_yaml.is_file() or plan_md.is_file()

        checks.append(
            GateCheck(
                name="manuscript-plan",
                description="Manuscript plan (yaml or md)",
                passed=plan_exists,
                details="exists" if plan_exists else "MISSING",
            )
        )

        return GateResult(phase=4, phase_name="Planning", checks=checks, passed=False)
