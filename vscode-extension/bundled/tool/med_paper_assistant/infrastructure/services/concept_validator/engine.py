"""ConceptValidator: composes the structure, novelty, check, review and report mixins."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import _definitions
from ._checks import ChecksMixin
from ._concept_review import ConceptReviewMixin
from ._models import ValidationResult
from ._novelty import NoveltyMixin
from ._report import ReportMixin
from ._structure import StructureMixin


class ConceptValidator(
    StructureMixin,
    NoveltyMixin,
    ChecksMixin,
    ConceptReviewMixin,
    ReportMixin,
):
    """
    Validates research concept files with structural and semantic checks.

    The validator enforces quality standards for concept files before
    they can be used for draft writing. It uses multi-round LLM evaluation
    for novelty scoring to ensure reliability.

    Usage:
        validator = ConceptValidator()
        result = validator.validate(concept_path)
        if result.overall_passed:
            # Proceed with draft writing
        else:
            # Show errors and suggestions
    """

    # Section definitions for structural validation
    SECTION_DEFINITIONS = _definitions.SECTION_DEFINITIONS

    # Novelty scoring configuration
    NOVELTY_CONFIG = _definitions.NOVELTY_CONFIG

    # Cache settings
    CACHE_DURATION_HOURS = _definitions.CACHE_DURATION_HOURS

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the ConceptValidator.

        Args:
            cache_dir: Directory to store validation cache. If None, uses .cache/
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._validation_cache: Dict[str, ValidationResult] = {}

    def validate(
        self,
        file_path: str,
        paper_type: str = "original-research",
        target_section: str = "",
        run_novelty_check: bool = True,
        run_consistency_check: bool = True,
        run_citation_check: bool = False,
        force_refresh: bool = False,
    ) -> ValidationResult:
        """
        Validate a concept file comprehensively.

        Validation is now context-aware:
        - paper_type: Different paper types have different requirements
        - target_section: Validates only what's needed for that section

        Args:
            file_path: Path to the concept.md file
            paper_type: The paper type (original-research, meta-analysis, etc.)
            target_section: Which section to validate for (Introduction, Methods, etc.)
                           If empty, validates all core requirements
            run_novelty_check: Whether to run LLM-based novelty scoring
            run_consistency_check: Whether to check section consistency
            run_citation_check: Whether to check citation support
            force_refresh: Ignore cache and re-validate

        Returns:
            ValidationResult with all check results
        """
        file_path = str(Path(file_path).resolve())
        checks = (run_novelty_check, run_consistency_check, run_citation_check)
        cache_key = self._build_cache_key(file_path, paper_type, target_section, checks)
        if not force_refresh:
            cached = self._get_cached_result(cache_key)
            if cached:
                return cached

        return self._validate_uncached(cache_key, file_path, paper_type, target_section, checks)

    @staticmethod
    def _build_cache_key(
        file_path: str, paper_type: str, target_section: str, checks: Tuple[bool, bool, bool]
    ) -> str:
        """Cache key includes paper_type, target_section and the enabled checks."""
        run_novelty_check, run_consistency_check, run_citation_check = checks
        return (
            f"{file_path}:{paper_type}:{target_section}:"
            f"novelty={run_novelty_check}:consistency={run_consistency_check}:"
            f"citations={run_citation_check}"
        )

    def _validate_uncached(
        self,
        cache_key: str,
        file_path: str,
        paper_type: str,
        target_section: str,
        checks: Tuple[bool, bool, bool],
    ) -> ValidationResult:
        """Read the concept file, run the checks and cache the result."""
        result = ValidationResult(
            file_path=file_path,
            timestamp=datetime.now().isoformat(),
            paper_type=paper_type,
            target_section=target_section,
        )

        # Check file exists
        if not os.path.exists(file_path):
            result.errors.append(f"Concept file not found: {file_path}")
            return result

        # Read content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            result.errors.append(f"Failed to read file: {e}")
            return result

        result = self._run_checks(content, result, paper_type, target_section, checks)

        # Cache result
        self._cache_result(cache_key, result)

        return result

    def _run_checks(
        self,
        content: str,
        result: ValidationResult,
        paper_type: str,
        target_section: str,
        checks: Tuple[bool, bool, bool],
    ) -> ValidationResult:
        """Run the structure, novelty, consistency and citation checks in order."""
        run_novelty_check, run_consistency_check, run_citation_check = checks

        # 1. Structural validation (now paper-type and section aware)
        result = self._validate_structure(content, result, paper_type, target_section)

        # 2. Novelty evaluation (if structural check passed for required sections)
        required_section_keys = self._required_section_keys(paper_type, target_section)
        if (
            run_novelty_check
            and result.structure_valid
            and "novelty_statement" in required_section_keys
        ):
            result = self._evaluate_novelty(content, result)

        # 3. Consistency check
        if run_consistency_check and result.structure_valid:
            result = self._check_consistency(content, result)

        # 4. Citation support check
        if run_citation_check and result.structure_valid:
            result = self._check_citation_support(content, result)

        # 5. Determine overall pass/fail
        result.overall_passed = self._determine_overall_status(result)

        # 6. Determine if can write target section (separate from overall)
        result.can_write_section = self._can_write_section(result, target_section)

        return result

    def validate_for_section(
        self, file_path: str, section: str, paper_type: str = "original-research"
    ) -> ValidationResult:
        """
        Validate concept file for writing a specific section.

        This is the recommended entry point for section-specific validation.
        It only checks what's needed for that section.

        Args:
            file_path: Path to concept.md
            section: Section to write (Introduction, Methods, etc.)
            paper_type: The paper type

        Returns:
            ValidationResult with can_write_section indicating if OK to proceed
        """
        return self.validate(
            file_path,
            paper_type=paper_type,
            target_section=section,
            run_novelty_check=True,
            run_consistency_check=False,  # Skip for section validation
            run_citation_check=False,
        )

    def validate_structure_only(
        self, file_path: str, paper_type: str = "original-research"
    ) -> ValidationResult:
        """Quick structural validation without LLM calls."""
        return self.validate(
            file_path,
            paper_type=paper_type,
            run_novelty_check=False,
            run_consistency_check=False,
            run_citation_check=False,
        )

    def must_validate_before_processing(
        self, file_path: str, paper_type: str = "original-research", target_section: str = ""
    ) -> Tuple[bool, str]:
        """
        Mandatory validation check before any concept file processing.

        This method should be called at the start of any function that
        processes concept files (e.g., draft writing, export).

        Args:
            file_path: Path to concept.md
            paper_type: The paper type
            target_section: Optional section to validate for

        Returns:
            Tuple of (can_proceed, message)
        """
        result = self.validate(file_path, paper_type=paper_type, target_section=target_section)

        # Use section-specific result if target_section specified
        if target_section:
            if result.can_write_section:
                return True, f"✅ Can write {target_section}."
            else:
                report = self.generate_report(result)
                return False, f"Cannot write {target_section}. Please fix issues:\n\n{report}"
        else:
            if result.overall_passed:
                return True, "Concept validation passed."
            else:
                report = self.generate_report(result)
                return False, f"Concept validation failed. Please fix issues:\n\n{report}"
