"""Consistency / citation checks, overall status and result caching."""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from ._models import SectionCheck, ValidationResult


class ChecksMixin:
    """Secondary quality checks, pass/fail aggregation and the validation cache."""

    CACHE_DURATION_HOURS: int
    _validation_cache: Dict[str, ValidationResult]

    def _check_consistency(self, content: str, result: ValidationResult) -> ValidationResult:
        """Check consistency between sections."""
        result.consistency_checked = True

        novelty = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content
        gap = result.sections.get(
            "research_gap", SectionCheck(name="", found=False, has_content=False)
        ).content
        selling = result.sections.get(
            "selling_points", SectionCheck(name="", found=False, has_content=False)
        ).content
        result.sections.get(
            "expected_outcomes", SectionCheck(name="", found=False, has_content=False)
        ).content

        consistency_score = 100
        issues = []

        # Check Gap-Novelty alignment
        if gap and novelty:
            # Simple keyword overlap check (placeholder for LLM)
            gap_keywords = set(re.findall(r"\b\w{4,}\b", gap.lower()))
            novelty_keywords = set(re.findall(r"\b\w{4,}\b", novelty.lower()))
            overlap = len(gap_keywords & novelty_keywords)

            if overlap < 3:
                consistency_score -= 20
                issues.append("Research Gap and Novelty Statement may not be well aligned")

        # Check if selling points reflect novelty
        if selling and novelty:
            # At least some keywords should appear in both
            selling_keywords = set(re.findall(r"\b\w{4,}\b", selling.lower()))
            novelty_keywords = set(re.findall(r"\b\w{4,}\b", novelty.lower()))
            overlap = len(selling_keywords & novelty_keywords)

            if overlap < 2:
                consistency_score -= 15
                issues.append("Key Selling Points should reflect the Novelty Statement")

        result.consistency_score = consistency_score
        result.consistency_passed = consistency_score >= 70
        result.consistency_issues = issues

        if not result.consistency_passed:
            result.warnings.append(f"Consistency check: Score {consistency_score}/100 (need 70+)")

        return result

    def _check_citation_support(self, content: str, result: ValidationResult) -> ValidationResult:
        """Check if claims are supported by citations."""
        result.citation_checked = True

        # Find claims that should have citations
        claim_patterns = [
            (r"studies have shown", "high"),
            (r"research indicates", "high"),
            (r"it is known that", "medium"),
            (r"according to", "high"),
            (r"\d+%\s+of\s+patients", "high"),
            (r"current guidelines", "high"),
        ]

        unsupported = []
        for pattern, severity in claim_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Check if followed by citation
                context_after = content[match.end() : match.end() + 50]
                if not re.search(r"\[.*?\]|\(PMID|\(\d{4}\)", context_after):
                    unsupported.append(
                        {
                            "claim": match.group(),
                            "severity": severity,
                            "suggestion": f"Add citation after: '{match.group()}'",
                        }
                    )

        result.unsupported_claims = unsupported

        # Calculate score
        total_claims = len([p for p, _ in claim_patterns])
        if total_claims > 0:
            result.citation_score = max(0, 100 - (len(unsupported) * 20))
        else:
            result.citation_score = 100

        return result

    def _determine_overall_status(self, result: ValidationResult) -> bool:
        """Determine if the concept passes overall validation."""
        # Must pass structural validation
        if not result.structure_valid:
            return False

        # If novelty check was run, it must pass
        if result.novelty_checked and not result.novelty_passed:
            return False

        # Consistency is a warning, not a hard fail
        # Citation is informational

        return True

    def _get_cached_result(self, cache_key: str) -> Optional[ValidationResult]:
        """Get cached validation result if still valid."""
        if cache_key in self._validation_cache:
            cached = self._validation_cache[cache_key]
            cached_time = datetime.fromisoformat(cached.timestamp)
            if datetime.now() - cached_time < timedelta(hours=self.CACHE_DURATION_HOURS):
                # Check if file was modified (extract file path from cache key)
                file_path = cache_key.split(":")[0]
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cached_time:
                        return cached
                except OSError:
                    pass  # File not found, don't use cache
        return None

    def _cache_result(self, cache_key: str, result: ValidationResult) -> None:
        """Cache validation result."""
        self._validation_cache[cache_key] = result
