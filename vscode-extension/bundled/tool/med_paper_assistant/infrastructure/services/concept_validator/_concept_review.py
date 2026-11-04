"""Concept-review artifact: structured YAML review plus persisted audit files."""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml

from ._claims_extraction import ClaimsExtractionMixin
from ._models import SectionCheck, ValidationResult


def _downstream_contract() -> Dict[str, Any]:
    """Inputs later pipeline phases read from the concept review."""
    return {
        "phase4_inputs": [
            "research_question.canonical_question",
            "claims_required",
            "evidence_requirements",
            "asset_obligations",
        ],
        "phase5_inputs": [
            "protected_content",
            "risk_register",
            "asset_obligations",
        ],
    }


class ConceptReviewMixin(ClaimsExtractionMixin):
    """Build and persist the machine-readable concept-review artifact."""

    NOVELTY_CONFIG: Dict[str, int]

    if TYPE_CHECKING:

        def generate_report(self, result: ValidationResult) -> str: ...

    def build_concept_review(self, result: ValidationResult) -> Dict[str, Any]:
        """Build a structured concept review artifact from a validation result.

        The concept review normalizes free-form concept text into stable fields
        that later phases can consume. It is intentionally source-agnostic:
        human-authored, agent-authored, and hybrid concepts all map to the same
        downstream contract.

        Args:
            result: Validation result produced by validate().

        Returns:
            A serializable dictionary for concept-review.yaml.
        """
        content = ""
        try:
            content = Path(result.file_path).read_text(encoding="utf-8")
        except OSError:
            content = ""

        claims_required = self._extract_claims_required(result, content)

        return {
            "metadata": self._review_metadata(result, content),
            "review": self._review_block(result),
            "research_question": self._extract_research_question(result, content),
            "paper_type_fit": {
                "recommended_type": result.paper_type,
                "alternatives": [],
                "rationale": f"Validated under paper type '{result.paper_type}'.",
            },
            "claims_required": claims_required,
            "evidence_requirements": self._build_evidence_requirements(
                claims_required, content, result
            ),
            "asset_obligations": self._extract_asset_obligations(content),
            "dataset_requirements": [],
            "protected_content": self._protected_content(result, content),
            "risk_register": self._build_risk_register(result),
            "open_questions": self._build_open_questions(result),
            "downstream_contract": _downstream_contract(),
        }

    def _protected_content(self, result: ValidationResult, content: str) -> Dict[str, Any]:
        """Locked novelty statement and selling points block."""
        novelty_summary = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content.strip() or self._extract_markdown_section(content, "NOVELTY")
        selling_points = self._extract_selling_points(result, content)

        return {
            "novelty_statement_locked": {
                "present": bool(novelty_summary),
                "summary": novelty_summary,
            },
            "selling_points_locked": {
                "present": len(selling_points) > 0,
                "items": selling_points,
            },
        }

    def _review_metadata(self, result: ValidationResult, content: str) -> Dict[str, Any]:
        """Provenance block of the concept review."""
        return {
            "generated_at": result.timestamp,
            "generated_by": "concept_validator",
            "source_mode": self._infer_source_mode(content),
            "source_files": [os.path.basename(result.file_path)],
            "based_on": {
                "paper_type": result.paper_type,
                "target_section": result.target_section,
                "validation_rounds": self.NOVELTY_CONFIG["rounds"],
            },
        }

    def _review_block(self, result: ValidationResult) -> Dict[str, Any]:
        """Readiness verdict block of the concept review."""
        readiness = "ready" if result.overall_passed else "revise"
        if result.errors and not result.structure_valid:
            readiness = "blocked"

        return {
            "readiness": readiness,
            "gate_passed": result.overall_passed,
            "summary": self._build_review_summary(result),
            "blocking_reasons": result.errors[:10],
            "warnings": result.warnings[:10],
        }

    def save_validation_artifacts(
        self,
        result: ValidationResult,
        project_dir: Optional[str | Path] = None,
    ) -> Dict[str, str]:
        """Persist concept validation artifacts to the project audit directory.

        Writes both the human-readable concept-validation.md report and the
        machine-readable concept-review.yaml artifact.

        Args:
            result: Validation result produced by validate().
            project_dir: Optional project root. If omitted, inferred from the
                concept file location.

        Returns:
            Mapping of artifact names to saved file paths. Empty if the project
            root cannot be determined.
        """
        resolved_project_dir = Path(project_dir) if project_dir else self._infer_project_dir(result)
        if resolved_project_dir is None:
            return {}

        audit_dir = resolved_project_dir / ".audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        validation_report_path = audit_dir / "concept-validation.md"
        validation_report_path.write_text(self.generate_report(result), encoding="utf-8")

        concept_review_path = audit_dir / "concept-review.yaml"
        concept_review = self.build_concept_review(result)
        concept_review_path.write_text(
            yaml.dump(
                concept_review, default_flow_style=False, allow_unicode=True, sort_keys=False
            ),
            encoding="utf-8",
        )

        return {
            "concept_validation": str(validation_report_path),
            "concept_review": str(concept_review_path),
        }

    def _infer_project_dir(self, result: ValidationResult) -> Optional[Path]:
        """Infer project root from a concept file path."""
        concept_path = Path(result.file_path)
        if concept_path.name != "concept.md":
            return None
        if concept_path.parent.name == "drafts":
            return concept_path.parent.parent
        return concept_path.parent

    def _infer_source_mode(self, content: str) -> str:
        """Infer the broad authorship mode for a concept document.

        This intentionally uses conservative heuristics. If authorship is not
        obvious, return ``hybrid``.
        """
        lower = content.lower()
        has_placeholders = bool(re.search(r"\[(insert|todo|placeholder)", lower))
        has_structured_markers = any(marker in content for marker in ["🔒", "📝", "Selling Point"])

        if has_structured_markers and not has_placeholders:
            return "agent-authored"
        if has_placeholders and not has_structured_markers:
            return "human-authored"
        return "hybrid"

    def _build_risk_register(self, result: ValidationResult) -> List[Dict[str, Any]]:
        """Convert validation issues into a risk register."""
        risks: List[Dict[str, Any]] = []
        for idx, issue in enumerate(result.errors[:10], start=1):
            risks.append(
                {
                    "id": f"risk-{idx}",
                    "category": "concept",
                    "severity": "critical",
                    "description": issue,
                    "mitigation": "Revise concept and re-run concept review.",
                }
            )
        start_idx = len(risks) + 1
        for offset, issue in enumerate(result.consistency_issues[:10], start=start_idx):
            risks.append(
                {
                    "id": f"risk-{offset}",
                    "category": "consistency",
                    "severity": "warning",
                    "description": issue,
                    "mitigation": "Align claims across concept sections before planning.",
                }
            )
        return risks

    def _build_open_questions(self, result: ValidationResult) -> List[Dict[str, Any]]:
        """Convert suggestions into explicit open questions."""
        questions: List[Dict[str, Any]] = []
        for idx, suggestion in enumerate(result.suggestions[:10], start=1):
            questions.append(
                {
                    "id": f"q-{idx}",
                    "question": suggestion,
                    "owner": "user",
                    "blocking": False,
                }
            )
        return questions

    def _build_review_summary(self, result: ValidationResult) -> str:
        """Create a short review summary string."""
        if result.overall_passed:
            return "Concept passed validation and is ready for downstream planning."
        if result.errors:
            return f"Concept has {len(result.errors)} blocking issue(s) requiring revision."
        return "Concept needs revision before downstream planning."
