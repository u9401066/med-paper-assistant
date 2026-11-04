"""Structural validation: section extraction, content checks and writability."""

import re
from typing import Dict, List, Optional

from med_paper_assistant.domain.paper_types import (
    get_concept_requirements,
    get_section_requirements,
)

from ._definitions import SECTION_DEFINITIONS
from ._models import SectionCheck, ValidationResult


class StructureMixin:
    """Checks that required concept sections exist, have content and unlock a target section."""

    SECTION_DEFINITIONS = SECTION_DEFINITIONS

    def _validate_structure(
        self,
        content: str,
        result: ValidationResult,
        paper_type: str = "original-research",
        target_section: str = "",
    ) -> ValidationResult:
        """
        Validate the structural presence of required sections.

        Now paper-type and section aware:
        - Gets requirements from paper_types.py
        - Only validates what's needed for target_section
        """
        required_keys = self._required_section_keys(paper_type, target_section)

        # Check each section definition
        for section_key, section_def in self.SECTION_DEFINITIONS.items():
            patterns_list: List[str] = list(section_def["patterns"])  # type: ignore[arg-type,call-overload]
            check = SectionCheck(
                name=str(section_def["name"]),
                required=section_key in required_keys,
                patterns=patterns_list,
            )

            # Find section
            section_content = self._extract_section(content, patterns_list)

            if section_content:
                check.found = True
                check.content = section_content
                self._check_section_content(section_key, section_def, check, result)
            else:
                check.found = False
                if check.required:
                    result.errors.append(f"{check.name}: Section not found")

            result.sections[section_key] = check

        # Check if all required sections are valid
        required_valid = all(
            result.sections[k].found and result.sections[k].has_content for k in required_keys
        )

        result.structure_valid = required_valid

        return result

    def _check_section_content(
        self,
        section_key: str,
        section_def: Dict[str, object],
        check: SectionCheck,
        result: ValidationResult,
    ) -> None:
        """Set ``check.has_content`` for a found section and record errors for required ones."""
        section_content = check.content

        # Check if has actual content (not just placeholders)
        cleaned = self._remove_placeholders(section_content)
        word_count = len(cleaned.split())

        if section_key == "selling_points":
            non_placeholder_points = self._count_selling_points(section_content)

            min_count: int = section_def.get("min_count", 3)  # type: ignore[assignment]
            check.has_content = len(non_placeholder_points) >= min_count

            if not check.has_content and check.required:
                result.errors.append(
                    f"{check.name}: Found {len(non_placeholder_points)} points, need at least {min_count}"
                )
        else:
            min_words: int = section_def.get("min_words", 10)  # type: ignore[assignment]
            check.has_content = word_count >= min_words

            if not check.has_content and check.required:
                result.errors.append(
                    f"{check.name}: Only {word_count} words, need at least {min_words}"
                )

    @staticmethod
    def _count_selling_points(section_content: str) -> List[str]:
        """Non-placeholder selling points; supports multiple formats.

        1. "Selling Point 1:" format
        2. Numbered list "1. **Point**:" format
        3. Bullet list "- **Point**:" format
        """
        points_format1 = re.findall(r"Selling Point \d+.*?:.*?\S", section_content, re.IGNORECASE)
        points_format2 = re.findall(r"^\d+\.\s+\*\*[^*]+\*\*", section_content, re.MULTILINE)
        points_format3 = re.findall(r"^[-*]\s+\*\*[^*]+\*\*", section_content, re.MULTILINE)

        # Use whichever format has more points
        all_points = points_format1 + points_format2 + points_format3
        # Filter out placeholders
        return [p for p in all_points if "[" not in p and "placeholder" not in p.lower()]

    def _required_section_keys(self, paper_type: str, target_section: str = "") -> set[str]:
        """Resolve paper-type requirements to validator section keys."""
        if target_section:
            requirements = get_section_requirements(paper_type, target_section)["required"]
        else:
            requirements = get_concept_requirements(paper_type).core_required

        return {
            section_key
            for requirement in requirements
            if (section_key := self._map_requirement_to_section(requirement)) is not None
        }

    def _extract_section(self, content: str, patterns: List[str]) -> str:
        """Extract content between a section header and the next major section.

        Includes sub-sections (###) until the next major section (## or emoji markers).
        """
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start = match.end()

                # Find next major section (## level, emoji markers, or ---)
                # BUT NOT sub-sections (###)
                next_section = re.search(
                    r"\n(?:##\s+(?!#)|🔒|📝|---)",  # ## but not ###
                    content[start:],
                    re.MULTILINE,
                )

                if next_section:
                    end = start + next_section.start()
                else:
                    end = len(content)

                return content[start:end].strip()

        return ""

    def _remove_placeholders(self, content: str) -> str:
        """Remove placeholder text like [Your text here]."""
        # Remove [...] placeholders
        content = re.sub(r"\[.*?\]", "", content)
        # Remove HTML comments
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        # Remove quoted placeholders
        content = re.sub(r">\s*\[.*?\]", "", content)
        return content.strip()

    def _can_write_section(self, result: ValidationResult, target_section: str) -> bool:
        """
        Determine if the target section can be written.

        This is more lenient than overall_passed:
        - For Introduction: needs NOVELTY + Background basics
        - For Methods: RECOMMENDED sections don't block
        - For Results/Discussion: more flexible

        Args:
            result: The validation result
            target_section: The section to write

        Returns:
            True if can proceed to write the section
        """
        if not target_section:
            return result.overall_passed

        # Get section requirements
        section_reqs = get_section_requirements(result.paper_type, target_section)

        # Check required sections
        missing_required = self._missing_requirements(result, section_reqs["required"])
        result.missing_required = missing_required

        # Check recommended sections (informational only)
        missing_recommended = self._missing_requirements(result, section_reqs["recommended"])
        result.missing_recommended = missing_recommended

        # Add warnings for missing recommended
        if missing_recommended:
            result.warnings.append(
                f"📝 RECOMMENDED sections missing for {target_section}: {', '.join(missing_recommended)}. "
                "You can still proceed, but consider filling these for a stronger paper."
            )

        # Blocking logic based on section_reqs["blocking"]
        if section_reqs.get("blocking", True):
            # Only block if required sections are missing
            if missing_required:
                result.errors.append(
                    f"❌ Cannot write {target_section}: missing required sections: {', '.join(missing_required)}"
                )
                return False

        # For Introduction: also need novelty check to pass
        return not self._introduction_novelty_blocked(result, target_section)

    @staticmethod
    def _introduction_novelty_blocked(result: ValidationResult, target_section: str) -> bool:
        """True (and records the error) when a failed novelty check blocks the Introduction."""
        if target_section.lower() in ["introduction", "intro"]:
            if result.novelty_checked and not result.novelty_passed:
                result.errors.append(
                    "❌ Cannot write Introduction: NOVELTY STATEMENT validation failed. "
                    f"Score: {result.novelty_average:.1f}/100 (need 75+)"
                )
                return True
        return False

    def _missing_requirements(self, result: ValidationResult, requirements: List[str]) -> List[str]:
        """Requirements whose mapped section is absent or has no content."""
        missing: List[str] = []
        for req in requirements:
            # Map requirement to section key
            section_key = self._map_requirement_to_section(req)
            if section_key:
                section = result.sections.get(section_key)
                if not section or not section.has_content:
                    missing.append(req)
        return missing

    def _map_requirement_to_section(self, requirement: str) -> Optional[str]:
        """Map a requirement name to a section definition key."""
        mapping = {
            "novelty_statement": "novelty_statement",
            "selling_points": "selling_points",
            "background": "background",
            "research_gap": "research_gap",
            "research_question": "research_question",
            "study_design": "methods",
            "participants": "methods",
            "outcomes": "methods",
            "methods": "methods",
            "expected_outcomes": "expected_outcomes",
            # Special requirements that don't map to standard sections
            "prisma_protocol": None,
            "search_strategy": None,
            "eligibility_criteria": None,
            "statistical_analysis": None,
            "data_analysis_completed": None,
            "results_completed": None,
        }
        return mapping.get(requirement)
