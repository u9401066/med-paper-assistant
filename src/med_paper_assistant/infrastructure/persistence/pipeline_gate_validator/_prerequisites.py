"""Prerequisite checks shared by every phase gate."""

from __future__ import annotations

from ._export_integrity import ExportIntegrityMixin
from ._types import GateCheck


class PrerequisitesMixin(ExportIntegrityMixin):
    """Artifacts from earlier phases that a later phase gate depends on."""

    def _check_prerequisites(self, phase: int) -> list[GateCheck]:
        """
        Check prerequisite artifacts for a given phase.

        Each phase depends on artifacts from earlier phases.
        Returns CRITICAL-level checks for missing prerequisites to enforce
        sequential execution — the agent cannot skip phases.

        Note: Phase 65 (Evolution Gate) is numerically 65 but logically sits
        between Phase 6 and Phase 7.  The numeric comparisons (>=) happen to be
        correct for Phase 65 in all cases except exports — ``65 >= 7`` (manuscript)
        and ``65 >= 9`` (scorecard) are both True, which is desired because
        Phase 65 comes after Phase 5 (Writing) and Phase 6 (Audit).
        Only exports uses ``== 11`` to avoid Phase 65 triggering it.
        """
        checks = self._early_prerequisites(phase)
        checks.extend(self._mid_prerequisites(phase))

        # Phase 11 only — exports (docx + pdf).  Uses == to exclude Phase 65.
        if phase == 11:
            checks.extend(self._prereq_final_delivery())

        return checks

    def _early_prerequisites(self, phase: int) -> list[GateCheck]:
        checks = []
        phase_rank = self._phase_rank(phase)

        # Phase 2+ needs project.json
        if phase_rank >= self._phase_rank(2):
            checks.append(self._prereq_project_json())

        # Phase 2.1+ needs references (paper-type-aware minimum)
        if phase_rank >= self._phase_rank(21):
            checks.append(self._prereq_references())

        # Phase 5+ needs concept.md
        if phase_rank >= self._phase_rank(5):
            checks.append(self._prereq_concept())

        # Phase 4+ needs structured concept review artifact
        if phase_rank >= self._phase_rank(4):
            checks.append(self._prereq_concept_review())

        return checks

    def _mid_prerequisites(self, phase: int) -> list[GateCheck]:
        checks = []
        phase_rank = self._phase_rank(phase)

        # Phase 6.5 and Phase 7+ need manuscript.
        if phase == 65 or phase_rank >= self._phase_rank(7):
            checks.append(self._prereq_manuscript())

        # Phase 6.5 and Phase 9+ need the Phase 6 quality scorecard.
        if phase == 65 or phase_rank >= self._phase_rank(9):
            checks.append(self._prereq_scorecard())

        # Phase 8+ needs completed review loop (Phase 7 prerequisite)
        # Uses logical order, but NOT for Phase 65 (which is between 6 and 7).
        if phase_rank >= self._phase_rank(8) and phase != 65:
            checks.append(self._prereq_review_completed())

        # Phase 9+ depends on Phase 8 reference sync being materially complete.
        if phase_rank >= self._phase_rank(9) and phase != 65:
            checks.append(self._prereq_reference_sync())

        return checks

    def _prereq_project_json(self) -> GateCheck:
        pj = self._project_dir / "project.json"
        return GateCheck(
            name="prereq:project.json",
            description="Project config required",
            passed=pj.is_file(),
            details="exists" if pj.is_file() else "MISSING — complete Phase 0 first",
            severity="CRITICAL",
        )

    def _prereq_references(self) -> GateCheck:
        refs_dir = self._project_dir / "references"
        ref_count = self._count_references(refs_dir)
        paper_type = self._get_paper_type_from_profile()
        min_refs = self._resolve_min_references(paper_type)
        return GateCheck(
            name="prereq:references",
            description=f"References from Phase 2 (min {min_refs} for {paper_type})",
            passed=ref_count >= min_refs,
            details=f"{ref_count}/{min_refs} references"
            if ref_count > 0
            else "No references — complete Phase 2 first",
            severity="CRITICAL",
        )

    def _prereq_concept(self) -> GateCheck:
        concept = self._find_concept_path()
        has_concept = concept.is_file()
        return GateCheck(
            name="prereq:concept.md",
            description="Concept from Phase 3",
            passed=has_concept,
            details="exists" if has_concept else "MISSING — complete Phase 3 first",
            severity="CRITICAL",
        )

    def _prereq_concept_review(self) -> GateCheck:
        review_complete, review_details = self._concept_review_is_actionable()
        return GateCheck(
            name="prereq:audit:concept-review.yaml",
            description="Structured concept review from Phase 3",
            passed=review_complete,
            details=review_details
            if review_complete
            else f"MISSING — complete Phase 3 concept review first ({review_details})",
            severity="CRITICAL",
        )

    def _prereq_manuscript(self) -> GateCheck:
        ms = self._drafts_dir / "manuscript.md"
        return GateCheck(
            name="prereq:manuscript.md",
            description="Manuscript from Phase 5",
            passed=ms.is_file(),
            details="exists" if ms.is_file() else "MISSING — complete Phase 5 first",
            severity="CRITICAL",
        )

    def _prereq_scorecard(self) -> GateCheck:
        scorecard = self._audit_dir / "quality-scorecard.md"
        return GateCheck(
            name="prereq:quality-scorecard",
            description="Quality scorecard from Phase 6",
            passed=scorecard.is_file(),
            details="exists" if scorecard.is_file() else "MISSING — complete Phase 6 first",
            severity="CRITICAL",
        )

    def _prereq_review_completed(self) -> GateCheck:
        review_passed, review_details = self._check_review_completed()
        return GateCheck(
            name="prereq:review_completed",
            description="Review loop from Phase 7 (code-enforced)",
            passed=review_passed,
            details=review_details,
            severity="CRITICAL",
        )

    def _prereq_reference_sync(self) -> GateCheck:
        phase8_result = self._validate_phase_8()
        phase8_failures = phase8_result.critical_failures
        return GateCheck(
            name="prereq:phase8_reference_sync",
            description="Phase 8 reference sync gate has no critical failures",
            passed=not phase8_failures,
            details="passed"
            if not phase8_failures
            else "Phase 8 failed: " + ", ".join(c.name for c in phase8_failures[:5]),
            severity="CRITICAL",
        )

    def _prereq_final_delivery(self) -> list[GateCheck]:
        export_dir = self._project_dir / "exports"
        docx_candidates = list(export_dir.glob("*.docx")) if export_dir.is_dir() else []
        pdf_candidates = list(export_dir.glob("*.pdf")) if export_dir.is_dir() else []
        has_docx = bool(docx_candidates)
        has_pdf = bool(pdf_candidates)
        checks = [
            GateCheck(
                name="prereq:exports",
                description="Export files from Phase 9 (docx + pdf)",
                passed=has_docx and has_pdf,
                details="docx+pdf exist"
                if (has_docx and has_pdf)
                else f"MISSING — {'no docx' if not has_docx else ''}"
                f"{'no pdf' if not has_pdf else ''} — complete Phase 9 first",
                severity="CRITICAL",
            ),
            self._build_export_integrity_check("docx", docx_candidates),
            self._build_export_integrity_check("pdf", pdf_candidates),
        ]

        phase10_result = self._validate_phase_10()
        phase10_failures = phase10_result.critical_failures
        checks.append(
            GateCheck(
                name="prereq:phase10_retrospective",
                description="Phase 10 retrospective gate has no critical failures",
                passed=not phase10_failures,
                details="passed"
                if not phase10_failures
                else "Phase 10 failed: " + ", ".join(c.name for c in phase10_failures[:5]),
                severity="CRITICAL",
            )
        )
        return checks
