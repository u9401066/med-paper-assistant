"""Concept review artifact loading and approval-receipt validation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

from med_paper_assistant.infrastructure.external.approval_signatures import (
    CONCEPT_APPROVAL_SCHEMA,
)

from ._approval import check_receipt_identity, check_receipt_preamble
from ._base import GateBase
from ._io import load_yaml_mapping

_LABEL = "concept approval"


class ConceptReviewMixin(GateBase):
    """Structured concept-review loading, completeness and override checks."""

    def _load_concept_review(self) -> dict[str, Any]:
        """Load concept-review.yaml when available."""
        return load_yaml_mapping(self._audit_dir / "concept-review.yaml")

    def _load_concept_review_override(self) -> dict[str, Any]:
        """Load an externally issued concept review decision when available."""
        return load_yaml_mapping(self._audit_dir / "concept-review-override.yaml")

    def _validate_concept_review_override(
        self,
        *,
        readiness: str,
    ) -> tuple[bool, str]:
        """Validate a trusted-host receipt bound to the exact concept review."""
        review_path = self._audit_dir / "concept-review.yaml"
        override = self._load_concept_review_override()
        if not override:
            return False, "external human approval receipt is missing"
        try:
            review_hash = hashlib.sha256(review_path.read_bytes()).hexdigest()
            concept_hash = hashlib.sha256(self._find_concept_path().read_bytes()).hexdigest()
        except OSError:
            return False, "concept or concept review is unreadable"

        failure, signature_details = check_receipt_preamble(
            override, _LABEL, CONCEPT_APPROVAL_SCHEMA
        )
        if failure is None:
            failure = self._concept_binding_failure(override, readiness, review_hash, concept_hash)
        if failure is None:
            failure = check_receipt_identity(override, _LABEL, self._project_dir)
        if failure is None:
            failure = self._concept_timestamp_failure(override)
        if failure is not None:
            return False, failure
        return (
            True,
            f"external approval by {override.get('approved_by')} ({signature_details})",
        )

    @staticmethod
    def _concept_binding_failure(
        override: dict[str, Any], readiness: str, review_hash: str, concept_hash: str
    ) -> str | None:
        if override.get("accepted_readiness") != readiness:
            return "concept approval readiness does not match the current review"
        if override.get("concept_review_sha256") != review_hash:
            return "concept approval is stale for the current concept review"
        if override.get("concept_artifact_sha256") != concept_hash:
            return "concept approval is stale for the current concept artifact"
        return None

    @staticmethod
    def _concept_timestamp_failure(override: dict[str, Any]) -> str | None:
        try:
            approved_at = override.get("approved_at")
            if not isinstance(approved_at, str):
                raise TypeError
            approval_time = datetime.fromisoformat(approved_at)
            if approval_time.utcoffset() is None:
                raise ValueError
            if approval_time > datetime.now().astimezone() + timedelta(minutes=5):
                return "concept approval timestamp is in the future"
        except (TypeError, ValueError):
            return "concept approval timestamp is invalid"
        return None

    def _concept_review_is_complete(self, review: dict[str, Any]) -> tuple[bool, str]:
        """Check whether concept-review.yaml contains the minimum planning contract."""
        if not review:
            return False, "missing or unreadable"

        review_block = review.get("review")
        research_question = review.get("research_question")
        protected_content = review.get("protected_content")
        claims_required = review.get("claims_required")

        if not isinstance(review_block, dict):
            return False, "missing review block"
        if not isinstance(research_question, dict):
            return False, "missing research_question block"
        if not isinstance(protected_content, dict):
            return False, "missing protected_content block"
        if not isinstance(claims_required, list) or not claims_required:
            return False, "missing claims_required"

        canonical_question = str(research_question.get("canonical_question", "")).strip()
        readiness = str(review_block.get("readiness", "")).strip().lower()
        novelty_present = bool(protected_content.get("novelty_statement_locked", {}).get("present"))
        selling_points_present = bool(
            protected_content.get("selling_points_locked", {}).get("present")
        )

        if not canonical_question:
            return False, "research question is empty"
        if readiness not in {"ready", "revise", "blocked"}:
            return False, "invalid readiness"
        if not novelty_present:
            return False, "novelty statement not locked"
        if not selling_points_present:
            return False, "selling points not locked"

        return True, f"ready={readiness}, claims={len(claims_required)}"

    def _concept_review_is_actionable(self) -> tuple[bool, str]:
        """Check whether concept review is ready to unblock downstream phases."""
        review = self._load_concept_review()
        review_complete, review_details = self._concept_review_is_complete(review)
        if not review_complete:
            return False, review_details

        readiness = str(review.get("review", {}).get("readiness", "")).strip().lower()
        if readiness == "ready":
            return True, "ready"

        override_valid, override_details = self._validate_concept_review_override(
            readiness=readiness
        )
        if override_valid:
            return True, f"{override_details} (readiness={readiness})"
        return False, f"readiness={readiness}; {override_details}"
