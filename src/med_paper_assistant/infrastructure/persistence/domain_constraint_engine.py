"""
Domain Constraint Engine — Structured JSON constraint system for paper writing.

Inspired by Triad Engine's JSON Domain Guide approach:
  Instead of relying solely on natural language instructions (SKILL.md),
  we enforce paper-type-specific constraints via structured JSON files.
  These constraints are **evolvable** — the MetaLearningEngine can add
  new constraints when hooks detect recurring error patterns.

Architecture:
  Infrastructure layer service. Works alongside WritingHooksEngine.
  - Constraints are stored as JSON files in `.constraints/` per project
  - Base constraints come from paper_types.py + built-in templates
  - Project-specific learned constraints are appended via evolve()
  - Each constraint has a provenance trail (source, timestamp, reason)

Triad Engine Mapping:
  - JSON Domain Guide → DomainConstraint files (per paper type)
  - Multi-Agent Deliberation → Hook layers A/B/C/E/F (already exist)
  - Sand Spreader → validate_against_constraints() (epistemic boundary check)

CONSTITUTION §22 Compliance:
  - Auditable: every constraint has provenance (who added it, why)
  - Decomposable: constraints are independent, testable units
  - Recomposable: JSON merge across base + project-learned

CONSTITUTION §23 Boundaries:
  - L1 (auto): Add learned constraints from hook patterns
  - L2 (auto): Adjust constraint severity within bounds
  - FORBIDDEN: Remove base constraints, weaken safety constraints
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


# ── Constraint Categories ─────────────────────────────────────────


class ConstraintCategory:
    """Constants for constraint categories."""

    STATISTICAL = "statistical"  # What tests/methods are valid
    STRUCTURAL = "structural"  # Required sections, ordering
    VOCABULARY = "vocabulary"  # Allowed/forbidden terms
    EVIDENTIAL = "evidential"  # What claims need what evidence level
    TEMPORAL = "temporal"  # Tense rules per section
    REPORTING = "reporting"  # EQUATOR guideline requirements
    BOUNDARY = "boundary"  # Hard limits (word count, figures, etc.)


# ── Base Constraint Templates ─────────────────────────────────────


def _build_base_constraints() -> dict[str, dict[str, Any]]:
    """
    Build base constraint templates per paper type.

    These are the 'knowledge boundaries' — analogous to Triad Engine's
    JSON Domain Guide that defines what exists and what doesn't.

    Returns:
        Dict mapping paper_type → constraint_set
    """
    return {
        "original-research": {
            "meta": {
                "paper_type": "original-research",
                "version": "1.0.0",
                "description": "Constraints for original research articles (RCT, cohort, cross-sectional)",
            },
            "constraints": [
                {
                    "id": "S001",
                    "category": ConstraintCategory.STATISTICAL,
                    "rule": "statistical_test_must_be_declared",
                    "description": "Every statistical test in Results must be declared in Methods",
                    "severity": "CRITICAL",
                    "hook_ref": "B8",
                    "provenance": "base",
                },
                {
                    "id": "S002",
                    "category": ConstraintCategory.STATISTICAL,
                    "rule": "alpha_level_consistency",
                    "description": "P-value thresholds in Results must match alpha declared in Methods",
                    "severity": "WARNING",
                    "hook_ref": "B8",
                    "provenance": "base",
                },
                {
                    "id": "S003",
                    "category": ConstraintCategory.STATISTICAL,
                    "rule": "ci_width_consistency",
                    "description": "Confidence interval width must be consistent between Methods and Results",
                    "severity": "WARNING",
                    "hook_ref": "B8",
                    "provenance": "base",
                },
                {
                    "id": "S004",
                    "category": ConstraintCategory.STATISTICAL,
                    "rule": "software_must_be_declared",
                    "description": "Statistical software in Results must be declared in Methods",
                    "severity": "WARNING",
                    "hook_ref": "B8",
                    "provenance": "base",
                },
                {
                    "id": "R001",
                    "category": ConstraintCategory.STRUCTURAL,
                    "rule": "required_sections",
                    "description": "Must have Introduction, Methods, Results, Discussion, Conclusion",
                    "params": {
                        "sections": [
                            "Introduction",
                            "Methods",
                            "Results",
                            "Discussion",
                            "Conclusion",
                        ]
                    },
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "R002",
                    "category": ConstraintCategory.STRUCTURAL,
                    "rule": "methods_before_results",
                    "description": "Methods section must appear before Results",
                    "severity": "CRITICAL",
                    "hook_ref": "B6",
                    "provenance": "base",
                },
                {
                    "id": "V001",
                    "category": ConstraintCategory.VOCABULARY,
                    "rule": "language_consistency",
                    "description": "Must use consistent British or American English throughout",
                    "severity": "WARNING",
                    "hook_ref": "A5",
                    "provenance": "base",
                },
                {
                    "id": "V002",
                    "category": ConstraintCategory.VOCABULARY,
                    "rule": "anti_ai_vocabulary",
                    "description": "Forbidden AI-typical phrases that trigger reviewer suspicion",
                    "params": {
                        "forbidden_patterns": [
                            "it is worth noting",
                            "it is important to note",
                            "in conclusion, our study",
                            "delve into",
                            "shed light on",
                            "pave the way",
                            "a myriad of",
                            "in the realm of",
                            "a testament to",
                            "multifaceted",
                            "underscores the importance",
                            "notably",
                            "groundbreaking",
                            "comprehensive overview",
                            "leveraging",
                            "pivotal role",
                        ],
                    },
                    "severity": "WARNING",
                    "hook_ref": "A3",
                    "provenance": "base",
                },
                {
                    "id": "E001",
                    "category": ConstraintCategory.EVIDENTIAL,
                    "rule": "claim_requires_citation",
                    "description": "Factual claims in Introduction/Discussion must have citations",
                    "params": {"min_citations_per_paragraph": 1},
                    "severity": "WARNING",
                    "hook_ref": "A2",
                    "provenance": "base",
                },
                {
                    "id": "E002",
                    "category": ConstraintCategory.EVIDENTIAL,
                    "rule": "results_no_unsupported_claims",
                    "description": "Results section must not contain claims without data support",
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "T001",
                    "category": ConstraintCategory.TEMPORAL,
                    "rule": "methods_past_tense",
                    "description": "Methods section should primarily use past tense",
                    "severity": "INFO",
                    "provenance": "base",
                },
                {
                    "id": "T002",
                    "category": ConstraintCategory.TEMPORAL,
                    "rule": "results_past_tense",
                    "description": "Results section should primarily use past tense",
                    "severity": "INFO",
                    "provenance": "base",
                },
                {
                    "id": "B001",
                    "category": ConstraintCategory.BOUNDARY,
                    "rule": "word_count_range",
                    "description": "Total word count should be within typical range",
                    "params": {"min_words": 2000, "max_words": 5000},
                    "severity": "WARNING",
                    "hook_ref": "A1",
                    "provenance": "base",
                },
                {
                    "id": "B002",
                    "category": ConstraintCategory.BOUNDARY,
                    "rule": "no_overlap_between_sections",
                    "description": "Paragraphs should not be duplicated across sections",
                    "severity": "WARNING",
                    "hook_ref": "A6",
                    "provenance": "base",
                },
                {
                    "id": "P001",
                    "category": ConstraintCategory.REPORTING,
                    "rule": "equator_guideline_required",
                    "description": "Must declare and follow appropriate EQUATOR reporting guideline",
                    "params": {
                        "guidelines": ["CONSORT", "STROBE", "PRISMA", "CARE", "STARD", "TRIPOD"]
                    },
                    "severity": "CRITICAL",
                    "hook_ref": "E1",
                    "provenance": "base",
                },
            ],
        },
        "case-report": {
            "meta": {
                "paper_type": "case-report",
                "version": "1.0.0",
                "description": "Constraints for case reports and case series",
            },
            "constraints": [
                {
                    "id": "R001",
                    "category": ConstraintCategory.STRUCTURAL,
                    "rule": "required_sections",
                    "description": "Must have Introduction, Case Presentation, Discussion, Conclusion",
                    "params": {
                        "sections": [
                            "Introduction",
                            "Case Presentation",
                            "Discussion",
                            "Conclusion",
                        ]
                    },
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "V001",
                    "category": ConstraintCategory.VOCABULARY,
                    "rule": "language_consistency",
                    "description": "Must use consistent British or American English",
                    "severity": "WARNING",
                    "hook_ref": "A5",
                    "provenance": "base",
                },
                {
                    "id": "V002",
                    "category": ConstraintCategory.VOCABULARY,
                    "rule": "anti_ai_vocabulary",
                    "description": "Forbidden AI-typical phrases",
                    "params": {
                        "forbidden_patterns": [
                            "it is worth noting",
                            "delve into",
                            "shed light on",
                            "a myriad of",
                            "multifaceted",
                        ],
                    },
                    "severity": "WARNING",
                    "hook_ref": "A3",
                    "provenance": "base",
                },
                {
                    "id": "E001",
                    "category": ConstraintCategory.EVIDENTIAL,
                    "rule": "patient_consent_mentioned",
                    "description": "Case report should mention patient consent/IRB waiver",
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "B001",
                    "category": ConstraintCategory.BOUNDARY,
                    "rule": "word_count_range",
                    "description": "Case reports are typically shorter",
                    "params": {"min_words": 800, "max_words": 2500},
                    "severity": "WARNING",
                    "hook_ref": "A1",
                    "provenance": "base",
                },
                {
                    "id": "P001",
                    "category": ConstraintCategory.REPORTING,
                    "rule": "equator_guideline_required",
                    "description": "CARE checklist required for case reports",
                    "params": {"guidelines": ["CARE"]},
                    "severity": "CRITICAL",
                    "hook_ref": "E1",
                    "provenance": "base",
                },
            ],
        },
        "systematic-review": {
            "meta": {
                "paper_type": "systematic-review",
                "version": "1.0.0",
                "description": "Constraints for systematic reviews",
            },
            "constraints": [
                {
                    "id": "R001",
                    "category": ConstraintCategory.STRUCTURAL,
                    "rule": "required_sections",
                    "params": {
                        "sections": [
                            "Introduction",
                            "Methods",
                            "Results",
                            "Discussion",
                            "Conclusion",
                        ]
                    },
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "S001",
                    "category": ConstraintCategory.STRUCTURAL,
                    "rule": "prisma_flow_required",
                    "description": "PRISMA flow diagram must be included",
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "S002",
                    "category": ConstraintCategory.STRUCTURAL,
                    "rule": "search_strategy_documented",
                    "description": "Full search strategy with databases and terms must be in Methods",
                    "severity": "CRITICAL",
                    "provenance": "base",
                },
                {
                    "id": "V001",
                    "category": ConstraintCategory.VOCABULARY,
                    "rule": "language_consistency",
                    "severity": "WARNING",
                    "hook_ref": "A5",
                    "provenance": "base",
                },
                {
                    "id": "B001",
                    "category": ConstraintCategory.BOUNDARY,
                    "rule": "word_count_range",
                    "params": {"min_words": 3000, "max_words": 8000},
                    "severity": "WARNING",
                    "provenance": "base",
                },
                {
                    "id": "P001",
                    "category": ConstraintCategory.REPORTING,
                    "rule": "equator_guideline_required",
                    "params": {"guidelines": ["PRISMA"]},
                    "severity": "CRITICAL",
                    "hook_ref": "E1",
                    "provenance": "base",
                },
            ],
        },
    }


# Pre-build at module load
BASE_CONSTRAINTS = _build_base_constraints()


class ConstraintViolation:
    """A single constraint violation found during validation."""

    def __init__(
        self,
        constraint_id: str,
        rule: str,
        category: str,
        severity: str,
        message: str,
        section: str = "",
        suggestion: str = "",
    ) -> None:
        self.constraint_id = constraint_id
        self.rule = rule
        self.category = category
        self.severity = severity
        self.message = message
        self.section = section
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "rule": self.rule,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "section": self.section,
            "suggestion": self.suggestion,
        }


class DomainConstraintEngine:
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

        severity_rank = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}

        for lc in learned:
            lid = lc["id"]
            if lid in base_by_id:
                # Only allow escalation
                base_sev = severity_rank.get(base_by_id[lid].get("severity", ""), 0)
                learned_sev = severity_rank.get(lc.get("severity", ""), 0)
                if learned_sev > base_sev:
                    # Replace base with escalated version
                    merged = [
                        c if c["id"] != lid else {**c, "severity": lc["severity"]} for c in merged
                    ]
                    logger.info(
                        "constraint_severity_escalated",
                        id=lid,
                        old=base_by_id[lid].get("severity"),
                        new=lc["severity"],
                    )
            else:
                # New learned constraint
                merged.append(lc)

        return merged

    def _get_base_constraints(self) -> list[dict[str, Any]]:
        """Get base constraints for current paper type."""
        template = BASE_CONSTRAINTS.get(self._paper_type, {})
        return list(template.get("constraints", []))

    def _load_learned_constraints(self) -> list[dict[str, Any]]:
        """Load project-specific learned constraints from disk."""
        if not self._learned_path.is_file():
            return []
        try:
            data = json.loads(self._learned_path.read_text(encoding="utf-8"))
            return data.get("constraints", [])
        except (json.JSONDecodeError, OSError):
            logger.warning("constraint_load_failed", path=str(self._learned_path))
            return []

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
        """
        self._constraints_dir.mkdir(parents=True, exist_ok=True)

        new_constraint: dict[str, Any] = {
            "id": constraint_id,
            "category": category,
            "rule": rule,
            "description": description,
            "severity": severity,
            "provenance": "learned",
            "source_hook": source_hook,
            "reason": reason,
            "learned_at": datetime.now().isoformat(),
        }
        if params:
            new_constraint["params"] = params

        # Append to learned constraints
        current = self._load_learned_constraints()
        # Don't duplicate
        existing_ids = {c["id"] for c in current}
        if constraint_id in existing_ids:
            logger.info("constraint_already_exists", id=constraint_id)
            return new_constraint

        current.append(new_constraint)
        self._save_learned_constraints(current)

        # Append to evolution log
        self._append_evolution_log(new_constraint)

        logger.info(
            "constraint_evolved",
            id=constraint_id,
            rule=rule,
            category=category,
            reason=reason,
        )
        return new_constraint

    def _save_learned_constraints(self, constraints: list[dict[str, Any]]) -> None:
        """Persist learned constraints to disk."""
        self._constraints_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "paper_type": self._paper_type,
            "updated_at": datetime.now().isoformat(),
            "constraints": constraints,
        }
        self._learned_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _append_evolution_log(self, constraint: dict[str, Any]) -> None:
        """Append to evolution audit trail."""
        log: list[dict[str, Any]] = []
        if self._evolution_log_path.is_file():
            try:
                log = json.loads(self._evolution_log_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        log.append(
            {
                "action": "add",
                "constraint": constraint,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._evolution_log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def validate_against_constraints(
        self,
        content: str,
        section: str = "manuscript",
    ) -> dict[str, Any]:
        """
        Validate content against all active constraints.

        This is the 'Sand Spreader' — checks content against the
        epistemic boundary defined by the constraint set.

        Currently validates:
        - Vocabulary constraints (forbidden patterns)
        - Boundary constraints (word count)
        - Structural constraints (section existence)

        Statistical/evidential constraints are handled by WritingHooksEngine
        (B8, A2) and referenced here for completeness.

        Args:
            content: Text content to validate.
            section: Section name for context.

        Returns:
            Dict with violations, stats, and passed status.
        """
        constraints = self.get_active_constraints()
        violations: list[ConstraintViolation] = []

        content_lower = content.lower()
        word_count = len(content.split())

        for c in constraints:
            rule = c.get("rule", "")
            params = c.get("params", {})
            severity = c.get("severity", "WARNING")
            cid = c.get("id", "")
            category = c.get("category", "")

            # Anti-AI vocabulary check
            if rule == "anti_ai_vocabulary":
                forbidden = params.get("forbidden_patterns", [])
                for pattern in forbidden:
                    if pattern.lower() in content_lower:
                        violations.append(
                            ConstraintViolation(
                                constraint_id=cid,
                                rule=rule,
                                category=category,
                                severity=severity,
                                message=f"AI-typical phrase detected: '{pattern}'",
                                section=section,
                                suggestion=f"Rephrase to avoid '{pattern}'",
                            )
                        )

            # Word count boundary check
            elif rule == "word_count_range":
                min_w = params.get("min_words", 0)
                max_w = params.get("max_words", 999999)
                if word_count < min_w:
                    violations.append(
                        ConstraintViolation(
                            constraint_id=cid,
                            rule=rule,
                            category=category,
                            severity=severity,
                            message=f"Word count {word_count} below minimum {min_w}",
                            section=section,
                            suggestion=f"Expand content to at least {min_w} words",
                        )
                    )
                elif word_count > max_w:
                    violations.append(
                        ConstraintViolation(
                            constraint_id=cid,
                            rule=rule,
                            category=category,
                            severity=severity,
                            message=f"Word count {word_count} exceeds maximum {max_w}",
                            section=section,
                            suggestion=f"Reduce content to at most {max_w} words",
                        )
                    )

            # Required sections check
            elif rule == "required_sections" and section == "manuscript":
                required = params.get("sections", [])
                for req_section in required:
                    # Check if section heading exists in content
                    patterns = [
                        f"# {req_section}",
                        f"## {req_section}",
                        f"### {req_section}",
                    ]
                    found = any(p.lower() in content_lower for p in patterns)
                    if not found:
                        violations.append(
                            ConstraintViolation(
                                constraint_id=cid,
                                rule=rule,
                                category=category,
                                severity=severity,
                                message=f"Required section '{req_section}' not found",
                                section="manuscript",
                                suggestion=f"Add '## {req_section}' section",
                            )
                        )

        critical_count = sum(1 for v in violations if v.severity == "CRITICAL")
        passed = critical_count == 0

        return {
            "passed": passed,
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

        # Load evolution log
        evolution_count = 0
        if self._evolution_log_path.is_file():
            try:
                log = json.loads(self._evolution_log_path.read_text(encoding="utf-8"))
                evolution_count = len(log)
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "paper_type": self._paper_type,
            "total_constraints": len(constraints),
            "by_category": by_category,
            "by_severity": by_severity,
            "by_provenance": by_provenance,
            "evolution_events": evolution_count,
        }

    def get_evolution_history(self) -> list[dict[str, Any]]:
        """
        Get the full constraint evolution log.

        Returns:
            List of evolution events (constraint additions/modifications).
        """
        if not self._evolution_log_path.is_file():
            return []
        try:
            return json.loads(self._evolution_log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
