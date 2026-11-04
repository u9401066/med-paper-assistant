"""DomainConstraintEngine — base + learned constraints and content validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ._base_constraints import BASE_CONSTRAINTS
from ._learned_store import (
    LearnedConstraintStoreMixin,
    build_learned_constraint,
    validate_evolve_inputs,
)
from ._validation import collect_violations

logger = structlog.get_logger()

_SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}


class DomainConstraintEngine(LearnedConstraintStoreMixin):
    """
    Structured JSON constraint system for paper writing.

    Manages domain-specific constraints per paper type. Constraints can be:
    1. Base (built-in from paper_types.py, immutable)
    2. Learned (added by MetaLearningEngine from recurring hook patterns)
    3. Project-specific (added by user or pipeline for a specific project)

    The key evolution mechanism: when hooks detect a recurring error pattern
    across multiple pipeline runs, MetaLearningEngine calls evolve() to add
    a new constraint. This converts ephemeral hook feedback into permanent
    structured knowledge.

    Args:
        project_dir: Path to the project directory.
        paper_type: Paper type key (e.g., "original-research").
    """

    CONSTRAINTS_DIR = ".constraints"
    LEARNED_FILE = "learned-constraints.json"
    EVOLUTION_LOG = "constraint-evolution.json"

    def __init__(self, project_dir: str | Path, paper_type: str = "original-research") -> None:
        self._project_dir = Path(project_dir)
        self._paper_type = paper_type
        self._constraints_dir = self._project_dir / self.CONSTRAINTS_DIR
        self._learned_path = self._constraints_dir / self.LEARNED_FILE
        self._evolution_log_path = self._constraints_dir / self.EVOLUTION_LOG

    def get_active_constraints(self) -> list[dict[str, Any]]:
        """
        Get all active constraints: base + learned.

        Returns merged constraint list. Learned constraints are appended
        after base constraints. If a learned constraint has the same ID
        as a base constraint, the learned version takes precedence
        (severity escalation only — cannot weaken).

        Returns:
            List of constraint dicts.
        """
        base = self._get_base_constraints()
        learned = self._load_learned_constraints()

        # Merge: learned can escalate severity but not weaken
        base_by_id = {c["id"]: c for c in base}
        merged = list(base)  # Start with all base

        for lc in learned:
            lid = lc["id"]
            if lid in base_by_id:
                merged = self._escalate_severity(merged, base_by_id[lid], lc)
            else:
                # New learned constraint
                merged.append(lc)

        return merged

    @staticmethod
    def _escalate_severity(
        merged: list[dict[str, Any]], base_constraint: dict[str, Any], learned: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Replace a base constraint by its escalated version (never weakened)."""
        lid = learned["id"]
        base_sev = _SEVERITY_RANK.get(base_constraint.get("severity", ""), 0)
        learned_sev = _SEVERITY_RANK.get(learned.get("severity", ""), 0)
        if learned_sev <= base_sev:
            return merged
        logger.info(
            "constraint_severity_escalated",
            id=lid,
            old=base_constraint.get("severity"),
            new=learned["severity"],
        )
        return [c if c["id"] != lid else {**c, "severity": learned["severity"]} for c in merged]

    def _get_base_constraints(self) -> list[dict[str, Any]]:
        """Get base constraints for current paper type."""
        template = BASE_CONSTRAINTS.get(self._paper_type, {})
        return list(template.get("constraints", []))

    def evolve(
        self,
        constraint_id: str,
        rule: str,
        category: str,
        description: str,
        severity: str = "WARNING",
        params: dict[str, Any] | None = None,
        reason: str = "",
        source_hook: str = "",
    ) -> dict[str, Any]:
        """
        Add a new learned constraint from a recurring pattern.

        This is the core evolution mechanism. Called by MetaLearningEngine
        when it detects a pattern that should become a permanent constraint.

        Args:
            constraint_id: Unique ID (e.g., "L001" for learned).
            rule: Rule name (e.g., "no_passive_in_results").
            category: ConstraintCategory constant.
            description: What this constraint enforces.
            severity: "INFO", "WARNING", or "CRITICAL".
            params: Optional parameters for the constraint.
            reason: Why this constraint was added.
            source_hook: Which hook's pattern triggered this (e.g., "A5").

        Returns:
            The new constraint dict.

        Raises:
            ValueError: If constraint_id format or severity is invalid.
        """
        validate_evolve_inputs(severity, constraint_id)
        self._constraints_dir.mkdir(parents=True, exist_ok=True)
        new_constraint = build_learned_constraint(
            constraint_id, rule, category, description, severity, params, reason, source_hook
        )
        if self._add_learned_constraint(new_constraint):
            logger.info(
                "constraint_evolved",
                id=constraint_id,
                rule=rule,
                category=category,
                reason=reason,
            )
        return new_constraint

    def validate_against_constraints(
        self,
        content: str,
        section: str = "manuscript",
    ) -> dict[str, Any]:
        """
        Validate content against all active constraints.

        This is the 'Sand Spreader' — checks content against the
        epistemic boundary defined by the constraint set.

        Validates:
        - Vocabulary constraints (forbidden patterns)
        - Boundary constraints (word count, min references, overlap)
        - Structural constraints (section existence, ordering)
        - Evidential constraints (patient consent)

        Statistical/evidential constraints like claim_requires_citation and
        tense checks are handled by WritingHooksEngine (B8, A2, B9) and
        referenced here for completeness.

        Args:
            content: Text content to validate.
            section: Section name for context.

        Returns:
            Dict with violations, stats, and passed status.
        """
        constraints = self.get_active_constraints()
        violations = collect_violations(constraints, content, section)

        critical_count = sum(1 for v in violations if v.severity == "CRITICAL")
        return {
            "passed": critical_count == 0,
            "total_constraints": len(constraints),
            "violations": [v.to_dict() for v in violations],
            "violation_count": len(violations),
            "critical_count": critical_count,
            "paper_type": self._paper_type,
            "base_constraints": len(self._get_base_constraints()),
            "learned_constraints": len(self._load_learned_constraints()),
        }

    def get_constraint_summary(self) -> dict[str, Any]:
        """
        Get a summary of all active constraints for this project.

        Returns:
            Dict with constraint counts by category, provenance, and severity.
        """
        constraints = self.get_active_constraints()

        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_provenance: dict[str, int] = {}

        for c in constraints:
            cat = c.get("category", "unknown")
            sev = c.get("severity", "unknown")
            prov = c.get("provenance", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_provenance[prov] = by_provenance.get(prov, 0) + 1

        return {
            "paper_type": self._paper_type,
            "total_constraints": len(constraints),
            "by_category": by_category,
            "by_severity": by_severity,
            "by_provenance": by_provenance,
            "evolution_events": self._count_evolution_events(),
        }
