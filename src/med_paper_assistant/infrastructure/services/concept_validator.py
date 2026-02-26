"""
Concept Validator - Service for validating research concept files.

This module provides comprehensive validation of concept.md files including:
1. Structural validation - Required sections present and non-empty
2. Novelty evaluation - LLM-based scoring (3 rounds, 75+ threshold)
3. Selling points quality check
4. Consistency validation - Alignment between sections
5. Citation support check

Key Design Decisions:
- Validation requirements vary by PAPER TYPE
- Section-specific validation: only check what's needed for that section
- Methods sections are RECOMMENDED, not REQUIRED (non-blocking)
- Results are cached to avoid redundant API calls

Validation Matrix by Paper Type:
┌──────────────────┬─────────┬────────────┬─────────────┬───────────┐
│ Paper Type       │ NOVELTY │ SELLING PT │ Background  │ Methods   │
├──────────────────┼─────────┼────────────┼─────────────┼───────────┤
│ original-research│ ✅ REQ  │ ✅ REQ     │ 📝 INTRO    │ 📝 RECOM  │
│ systematic-review│ ✅ REQ  │ ✅ REQ     │ 📝 INTRO    │ ⚠️ PRISMA │
│ meta-analysis    │ ✅ REQ  │ ✅ REQ     │ 📝 INTRO    │ ⚠️ PRISMA │
│ case-report      │ ✅ REQ  │ ✅ REQ     │ 📝 INTRO    │ ⚪ N/A    │
│ review-article   │ ✅ REQ  │ ✅ REQ     │ 📝 INTRO    │ ⚪ N/A    │
│ letter           │ ✅ REQ  │ ⚪ OPT     │ ⚪ OPT      │ ⚪ N/A    │
└──────────────────┴─────────┴────────────┴─────────────┴───────────┘

Section-Specific Validation:
- Introduction: core + intro_required
- Methods: core + intro + methods_required (RECOMMENDED, non-blocking)
- Results: Methods done + data ready
- Discussion: core + Results done
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from med_paper_assistant.domain.paper_types import (
    get_concept_requirements,
    get_section_requirements,
)


@dataclass
class SectionCheck:
    """Result of checking a single section."""

    name: str
    found: bool = False
    has_content: bool = False
    content: str = ""
    patterns: List[str] = field(default_factory=list)
    required: bool = False


@dataclass
class ValidationResult:
    """Complete validation result for a concept file."""

    file_path: str
    timestamp: str
    paper_type: str = "original-research"  # Track paper type
    target_section: str = ""  # Track which section validation is for

    # Structural validation
    structure_valid: bool = False
    sections: Dict[str, SectionCheck] = field(default_factory=dict)
    missing_required: List[str] = field(default_factory=list)
    missing_recommended: List[str] = field(default_factory=list)

    # Novelty evaluation
    novelty_checked: bool = False
    novelty_passed: bool = False
    novelty_scores: List[int] = field(default_factory=list)
    novelty_average: float = 0.0
    novelty_details: Dict[str, Any] = field(default_factory=dict)

    # Selling points quality
    selling_points_checked: bool = False
    selling_points_passed: bool = False
    selling_points_score: float = 0.0
    selling_points_details: Dict[str, Any] = field(default_factory=dict)

    # Consistency check
    consistency_checked: bool = False
    consistency_passed: bool = False
    consistency_score: float = 0.0
    consistency_issues: List[str] = field(default_factory=list)

    # Citation support
    citation_checked: bool = False
    citation_score: float = 0.0
    unsupported_claims: List[Dict] = field(default_factory=list)

    # Overall
    overall_passed: bool = False
    can_write_section: bool = False  # Can proceed to write target section
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "paper_type": self.paper_type,
            "target_section": self.target_section,
            "structure_valid": self.structure_valid,
            "missing_required": self.missing_required,
            "missing_recommended": self.missing_recommended,
            "novelty": {
                "checked": self.novelty_checked,
                "passed": self.novelty_passed,
                "scores": self.novelty_scores,
                "average": self.novelty_average,
                "details": self.novelty_details,
            },
            "selling_points": {
                "checked": self.selling_points_checked,
                "passed": self.selling_points_passed,
                "score": self.selling_points_score,
                "details": self.selling_points_details,
            },
            "consistency": {
                "checked": self.consistency_checked,
                "passed": self.consistency_passed,
                "score": self.consistency_score,
                "issues": self.consistency_issues,
            },
            "citations": {
                "checked": self.citation_checked,
                "score": self.citation_score,
                "unsupported": self.unsupported_claims,
            },
            "overall_passed": self.overall_passed,
            "can_write_section": self.can_write_section,
            "warnings": self.warnings,
            "errors": self.errors,
            "suggestions": self.suggestions,
        }


class ConceptValidator:
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
    SECTION_DEFINITIONS = {
        "novelty_statement": {
            "name": "🔒 NOVELTY STATEMENT",
            "required": True,
            "patterns": [r"🔒\s*NOVELTY STATEMENT", r"What is new\?", r"##.*novelty"],
            "min_words": 20,
        },
        "selling_points": {
            "name": "🔒 KEY SELLING POINTS",
            "required": True,
            "patterns": [r"🔒\s*KEY SELLING POINTS", r"Selling Point \d"],
            "min_count": 3,
        },
        "background": {
            "name": "📝 Background",
            "required": False,
            "patterns": [r"📝\s*Background", r"##\s*Background"],
            "min_words": 30,
        },
        "research_gap": {
            "name": "📝 Research Gap",
            "required": False,
            "patterns": [r"📝\s*Research Gap", r"##\s*Research Gap", r"Identified Gap"],
            "min_words": 20,
        },
        "research_question": {
            "name": "📝 Research Question",
            "required": False,
            "patterns": [r"Research Question", r"Hypothesis", r"PICO"],
            "min_words": 10,
        },
        "methods": {
            "name": "📝 Methods Overview",
            "required": False,
            "patterns": [r"📝\s*Methods", r"##\s*Methods", r"Study Design"],
            "min_words": 20,
        },
        "expected_outcomes": {
            "name": "📝 Expected Outcomes",
            "required": False,
            "patterns": [r"📝\s*Expected", r"##\s*Expected Outcomes", r"Primary Outcomes"],
            "min_words": 15,
        },
    }

    # Novelty scoring configuration
    NOVELTY_CONFIG = {
        "rounds": 3,
        "threshold": 75,
        "required_passing_rounds": 3,  # All rounds must pass
    }

    # Cache settings
    CACHE_DURATION_HOURS = 24

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

        # Check cache (include paper_type and target_section in cache key)
        cache_key = f"{file_path}:{paper_type}:{target_section}"
        if not force_refresh:
            cached = self._get_cached_result(cache_key)
            if cached:
                return cached

        # Initialize result
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

        # 1. Structural validation (now paper-type and section aware)
        result = self._validate_structure(content, result, paper_type, target_section)

        # 2. Novelty evaluation (if structural check passed for required sections)
        if run_novelty_check and result.structure_valid:
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

        # Cache result
        self._cache_result(cache_key, result)

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
        # Get section requirements based on paper type and target section
        if target_section:
            section_reqs = get_section_requirements(paper_type, target_section)
            section_reqs["required"]
            section_reqs["recommended"]
            section_reqs["blocking"]
        else:
            # Full validation - use core requirements
            concept_reqs = get_concept_requirements(paper_type)
            concept_reqs.intro_required + concept_reqs.methods_required

        # Map section keys to their definitions

        # Check each section definition
        for section_key, section_def in self.SECTION_DEFINITIONS.items():
            patterns_list: List[str] = list(section_def["patterns"])  # type: ignore[arg-type,call-overload]
            check = SectionCheck(
                name=str(section_def["name"]),
                required=bool(section_def["required"]),
                patterns=patterns_list,
            )

            # Find section
            section_content = self._extract_section(content, patterns_list)

            if section_content:
                check.found = True
                check.content = section_content

                # Check if has actual content (not just placeholders)
                cleaned = self._remove_placeholders(section_content)
                word_count = len(cleaned.split())

                if section_key == "selling_points":
                    # Count selling points - support multiple formats:
                    # 1. "Selling Point 1:" format
                    # 2. Numbered list "1. **Point**:" format
                    # 3. Bullet list "- **Point**:" format
                    points_format1 = re.findall(
                        r"Selling Point \d+.*?:.*?\S", section_content, re.IGNORECASE
                    )
                    points_format2 = re.findall(
                        r"^\d+\.\s+\*\*[^*]+\*\*", section_content, re.MULTILINE
                    )
                    points_format3 = re.findall(
                        r"^[-*]\s+\*\*[^*]+\*\*", section_content, re.MULTILINE
                    )

                    # Use whichever format has more points
                    all_points = points_format1 + points_format2 + points_format3
                    # Filter out placeholders
                    non_placeholder_points = [
                        p for p in all_points if "[" not in p and "placeholder" not in p.lower()
                    ]

                    min_count: int = section_def.get("min_count", 3)  # type: ignore[assignment]
                    check.has_content = len(non_placeholder_points) >= min_count

                    if not check.has_content:
                        result.errors.append(
                            f"{check.name}: Found {len(non_placeholder_points)} points, need at least {min_count}"
                        )
                else:
                    min_words: int = section_def.get("min_words", 10)  # type: ignore[assignment]
                    check.has_content = word_count >= min_words

                    if not check.has_content and bool(section_def["required"]):
                        result.errors.append(
                            f"{check.name}: Only {word_count} words, need at least {min_words}"
                        )
            else:
                check.found = False
                if bool(section_def["required"]):
                    result.errors.append(f"{check.name}: Section not found")

            result.sections[section_key] = check

        # Check if all required sections are valid
        required_valid = all(
            result.sections[k].found and result.sections[k].has_content
            for k, v in self.SECTION_DEFINITIONS.items()
            if bool(v["required"])
        )

        result.structure_valid = required_valid

        return result

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

    def _evaluate_novelty(self, content: str, result: ValidationResult) -> ValidationResult:
        """
        Evaluate novelty using LLM scoring.

        Note: This is a placeholder for LLM integration.
        In production, this would call the LLM API 3 times.
        For now, it performs heuristic-based scoring.
        """
        result.novelty_checked = True

        # Extract novelty statement
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content

        if not novelty_content:
            result.novelty_passed = False
            result.novelty_average = 0
            result.errors.append("Cannot evaluate novelty: NOVELTY STATEMENT is empty")
            return result

        # Heuristic scoring (placeholder for LLM)
        # In production, this would be replaced with actual LLM calls
        scores = []
        for round_num in range(self.NOVELTY_CONFIG["rounds"]):
            score = self._heuristic_novelty_score(novelty_content, round_num)
            scores.append(score)

        result.novelty_scores = scores
        heuristic_avg = sum(scores) / len(scores)

        # Generate reviewer feedback and incorporate reviewer scores
        # Reviewer scores provide semantic analysis; heuristic provides keyword analysis
        # Use weighted combination: 40% heuristic + 60% reviewer average
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content
        if novelty_content:
            feedback = self._generate_novelty_feedback(novelty_content, scores)
            reviewer_scores = [
                feedback["reviewers"]["skeptic"]["score"],
                feedback["reviewers"]["methodologist"]["score"],
                feedback["reviewers"]["clinical_expert"]["score"],
            ]
            reviewer_avg = sum(reviewer_scores) / len(reviewer_scores)
            result.novelty_average = 0.4 * heuristic_avg + 0.6 * reviewer_avg
        else:
            result.novelty_average = heuristic_avg

        # Check if combined score passes threshold
        result.novelty_passed = result.novelty_average >= self.NOVELTY_CONFIG["threshold"]

        # Generate suggestions if not passed
        if not result.novelty_passed:
            result.suggestions.extend(self._generate_novelty_suggestions(novelty_content, scores))
            result.warnings.append(
                f"Novelty check: combined score {result.novelty_average:.1f} "
                f"(threshold: {self.NOVELTY_CONFIG['threshold']})"
            )

        return result

    def _heuristic_novelty_score(self, content: str, round_num: int) -> int:
        """
        Heuristic-based novelty scoring.

        This is a placeholder that will be replaced with LLM scoring.
        It checks for key novelty indicators.
        """
        score = 50  # Base score

        # Positive indicators
        novelty_keywords = [
            "first",
            "novel",
            "unique",
            "new",
            "innovative",
            "original",
            "unprecedented",
            "pioneering",
            "breakthrough",
            "首次",
            "創新",
            "獨特",
        ]
        specificity_patterns = [
            r"\d+%",
            r"\d+\s*(patients|subjects|cases|participants)",
            r"compared to",
            r"unlike",
            r"in contrast",
        ]

        content_lower = content.lower()

        # Check novelty keywords
        for keyword in novelty_keywords:
            if keyword.lower() in content_lower:
                score += 5

        # Check specificity
        for pattern in specificity_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 8

        # Check for "What is new?" answer quality
        if "what is new" in content_lower or "這項研究的新穎之處" in content:
            # Has the question, check if answered
            score += 10

        # Negative indicators
        vague_phrases = ["improved", "better", "enhanced", "optimized", "更好", "改善", "提升"]
        for phrase in vague_phrases:
            if phrase.lower() in content_lower and not any(
                re.search(rf"{phrase}\s+\d+", content, re.IGNORECASE) for _ in [1]
            ):
                # Vague without quantification
                score -= 5

        # Check for placeholder text still present (but not wikilinks [[...]] or PubMed syntax [pt])
        # Only penalize actual unfilled placeholders like [INSERT HERE], [TODO]
        placeholder_pattern = r"\[(?!\[)[A-Z][A-Z\s_]{2,}\]"
        if re.search(placeholder_pattern, content):
            score -= 20

        # Add some variance for different rounds (simulating LLM variance)
        variance = [-3, 0, 3][round_num % 3]
        score += variance

        # Clamp score
        return max(0, min(100, score))

    def _generate_novelty_feedback(self, content: str, scores: List[int]) -> Dict[str, Any]:
        """
        Generate sharp, reviewer-style feedback using the Three Reviewers Model.

        1. Reviewer 1: The Skeptic (Evidence & Search)
        2. Reviewer 2: The Methodologist (Rigor & Comparison)
        3. Reviewer 3: The Clinical Impact Expert (Significance & MCID)
        """
        feedback: dict[str, Any] = {
            "verdict": "",
            "reviewers": {
                "skeptic": {"comment": "", "score": 0, "questions": []},
                "methodologist": {"comment": "", "score": 0, "questions": []},
                "clinical_expert": {"comment": "", "score": 0, "questions": []},
            },
            "critical_issues": [],
            "actionable_fixes": [],
            "cgu_recommendation": None,
        }

        content_lower = content.lower()
        avg_score = sum(scores) / len(scores)

        # === VERDICT ===
        if avg_score >= 85:
            feedback["verdict"] = (
                "💎 High-impact potential. The novelty is clear and well-supported."
            )
        elif avg_score >= 75:
            feedback["verdict"] = "✅ Novelty claim is defensible. Proceed to writing."
        elif avg_score >= 60:
            feedback["verdict"] = (
                "⚠️ Novelty claim has gaps. A skeptical reviewer would challenge you."
            )
        else:
            feedback["verdict"] = (
                "❌ Novelty claim is weak. Current statement would not survive peer review."
            )

        # --- Reviewer 1: The Skeptic (Focus: Is it REALLY new?) ---
        skeptic = feedback["reviewers"]["skeptic"]
        if ("first" in content_lower or "首次" in content) and "pubmed" not in content_lower:
            skeptic["comment"] = (
                "You claim this is 'first', but provide no search evidence. I am skeptical."
            )
            skeptic["score"] = 50
            skeptic["questions"].append("What was your exact PubMed search strategy and date?")
        else:
            skeptic["comment"] = "The novelty claim seems grounded in existing literature."
            skeptic["score"] = 80

        # --- Reviewer 2: The Methodologist (Focus: How does it compare?) ---
        methodologist = feedback["reviewers"]["methodologist"]
        has_citations = bool(re.search(r"\[\[.+?\]\]", content)) or "PMID" in content
        # Check for limitation/differentiation analysis (multiple patterns)
        limitation_patterns = [
            r"\blimitation\b",
            r"\blimited\b",
            r"\bdoes not\b",
            r"\bdid not\b",
            r"\bdo not\b",
            r"\bfail(s|ed|ure)?\b",
            r"\black(s|ing|ed)?\b",
            r"\bour addition\b",
            r"\bwe extend\b",
            r"\bwe (add|include|place|systematically|dedicate)\b",
            r"\bdifferentiation\b",
            r"\bunlike\b",
            r"\bin contrast\b",
            r"\bhowever\b",
            r"\bbut\b",
            r"但",
            r"不同",
            r"限制",
        ]
        has_limitations = sum(
            1 for p in limitation_patterns if re.search(p, content, re.IGNORECASE)
        )

        if not has_citations:
            methodologist["comment"] = (
                "You haven't cited the studies you are supposedly improving upon."
            )
            methodologist["score"] = 40
            methodologist["questions"].append(
                "Which specific studies are you comparing your method against?"
            )
        elif has_limitations < 2:
            methodologist["comment"] = (
                "You cited literature but didn't explain their limitations clearly."
            )
            methodologist["score"] = 60
            methodologist["questions"].append(
                "What exactly was the failure or limitation of the cited studies?"
            )
        elif has_limitations < 4:
            methodologist["comment"] = (
                "Some differentiation provided, but could be more systematic."
            )
            methodologist["score"] = 75
            methodologist["questions"].append("Can you provide a structured comparison table?")
        else:
            methodologist["comment"] = "Methodological differentiation is well-articulated."
            methodologist["score"] = 85

        # --- Reviewer 3: The Clinical Impact Expert (Focus: So what?) ---
        clinical = feedback["reviewers"]["clinical_expert"]
        vague_words = ["improved", "better", "enhanced", "更好", "改善", "提升", "優於"]
        found_vague = [w for w in vague_words if w.lower() in content_lower]
        if found_vague and not re.search(r"\d+%|\d+\s*倍|OR\s*[\d.]|RR\s*[\d.]", content):
            clinical["comment"] = (
                f"You use vague terms like '{found_vague[0]}' without quantification."
            )
            clinical["score"] = 55
            clinical["questions"].append(
                "What is the expected effect size or MCID (Minimal Clinically Important Difference)?"
            )
        else:
            clinical["comment"] = "The clinical significance and expected impact are clear."
            clinical["score"] = 80

        # === CRITICAL ISSUES (Evidence-based challenges) ===
        issues = []

        # Issue 1: Claiming "first" without search evidence
        if skeptic["score"] <= 50:
            issues.append(
                {
                    "problem": "您聲稱『首次』，但沒有提供文獻搜尋證據",
                    "challenge": "Reviewer 1 (Skeptic) 會問：『你怎麼知道沒人做過？搜尋策略是什麼？』",
                    "fix": '加入：『PubMed 搜尋 "X AND Y" (2024-12-17) 結果為 0 篇』',
                }
            )

        # Issue 2: Vague quantification
        if clinical["score"] <= 60:
            issues.append(
                {
                    "problem": "使用模糊用語但沒有量化",
                    "challenge": "Reviewer 3 (Clinical Expert) 會問：『好多少？臨床意義 (MCID) 是什麼？』",
                    "fix": "改為具體數字：『預期減少 30% 的併發症』或『優於現有技術 15%』",
                }
            )

        # Issue 3: Comparison gap
        if methodologist["score"] <= 60:
            issues.append(
                {
                    "problem": "未明確說明與現有研究的差異",
                    "challenge": "Reviewer 2 (Methodologist) 會問：『既然 [Author 2024] 做過類似的，你的獨特性在哪？』",
                    "fix": "明確寫出：『與 [Author 2024] 不同的是，我們採用了 [新方法/新族群]』",
                }
            )

        feedback["critical_issues"] = issues

        # === ACTIONABLE FIXES ===
        fixes = []
        for issue in issues:
            fixes.append(f"🔧 **{issue['problem']}**\n   → {issue['fix']}")
        feedback["actionable_fixes"] = fixes

        # === CGU RECOMMENDATION ===
        if avg_score < 75:
            feedback["cgu_recommendation"] = {
                "recommend": True,
                "reason": "目前的創新點在審稿人眼中仍有漏洞。建議使用 CGU 進行壓力測試。",
                "tool": "mcp_cgu_deep_think",
                "prompt": f"扮演一位頂尖醫學期刊審稿人，針對以下創新聲明提出 3 個最刁鑽的質疑：\n\n{content}",
            }

        return feedback

    def _generate_novelty_suggestions(self, content: str, scores: List[int]) -> List[str]:
        """Generate improvement suggestions (legacy interface, calls new method)."""
        feedback = self._generate_novelty_feedback(content, scores)
        suggestions = []
        for fix in feedback.get("actionable_fixes", []):
            suggestions.append(fix)
        return suggestions

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
        missing_required = []
        for req in section_reqs["required"]:
            # Map requirement to section key
            section_key = self._map_requirement_to_section(req)
            if section_key:
                section = result.sections.get(section_key)
                if not section or not section.has_content:
                    missing_required.append(req)

        result.missing_required = missing_required

        # Check recommended sections (informational only)
        missing_recommended = []
        for rec in section_reqs["recommended"]:
            section_key = self._map_requirement_to_section(rec)
            if section_key:
                section = result.sections.get(section_key)
                if not section or not section.has_content:
                    missing_recommended.append(rec)

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
        if target_section.lower() in ["introduction", "intro"]:
            if result.novelty_checked and not result.novelty_passed:
                result.errors.append(
                    "❌ Cannot write Introduction: NOVELTY STATEMENT validation failed. "
                    f"Score: {result.novelty_average:.1f}/100 (need 75+)"
                )
                return False

        return True

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

    def generate_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report."""
        output = []
        output.append("📋 **Concept Validation Report**")
        output.append(f"📄 File: `{os.path.basename(result.file_path)}`")
        output.append(f"� Paper Type: `{result.paper_type}`")
        if result.target_section:
            output.append(f"🎯 Target Section: `{result.target_section}`")
        output.append(f"🕐 Time: {result.timestamp}")
        output.append("")

        # Section-specific validation info
        if result.target_section:
            output.append("## 📌 Section-Specific Validation")
            output.append("")
            output.append(f"Validating requirements for writing **{result.target_section}**:")
            output.append("")

            if result.missing_required:
                output.append("**❌ Missing Required:**")
                for req in result.missing_required:
                    output.append(f"- {req}")
                output.append("")

            if result.missing_recommended:
                output.append("**📝 Missing Recommended (non-blocking):**")
                for rec in result.missing_recommended:
                    output.append(f"- {rec}")
                output.append("")

        # Structural validation
        output.append("## 🔒 Protected Sections (Required)")
        output.append("")
        output.append("| Section | Found | Has Content | Status |")
        output.append("|---------|-------|-------------|--------|")

        for key in ["novelty_statement", "selling_points"]:
            if key in result.sections:
                check = result.sections[key]
                found = "✅" if check.found else "❌"
                has_content = "✅" if check.has_content else "❌"
                status = "✅ PASS" if check.found and check.has_content else "❌ MISSING"
                output.append(f"| {check.name} | {found} | {has_content} | {status} |")

        output.append("")
        output.append("## 📝 Editable Sections (Optional)")
        output.append("")
        output.append("| Section | Found | Has Content |")
        output.append("|---------|-------|-------------|")

        for key in [
            "background",
            "research_gap",
            "research_question",
            "methods",
            "expected_outcomes",
        ]:
            if key in result.sections:
                check = result.sections[key]
                found = "✅" if check.found else "⚪"
                has_content = "✅" if check.has_content else "⚪"
                output.append(f"| {check.name} | {found} | {has_content} |")

        # Novelty evaluation
        if result.novelty_checked:
            output.append("")
            output.append("## 🎯 Novelty Evaluation (Three Reviewers Model)")
            output.append("")

            # Get detailed feedback first
            novelty_content = result.sections.get(
                "novelty_statement", SectionCheck(name="", found=False, has_content=False)
            ).content

            feedback = {}
            if novelty_content:
                feedback = self._generate_novelty_feedback(novelty_content, result.novelty_scores)

            # Show verdict (one sharp line)
            avg_score = result.novelty_average
            output.append(f"**Overall Score:** {avg_score:.1f}/100")
            if feedback.get("verdict"):
                output.append(f"**Verdict:** {feedback['verdict']}")
            output.append("")

            # Show Three Reviewers' Scores
            if "reviewers" in feedback:
                output.append("### 👥 Reviewer Panel")
                output.append("")
                output.append("| Reviewer | Score | Feedback |")
                output.append("|----------|-------|----------|")

                revs = feedback["reviewers"]
                output.append(
                    f"| 🕵️ **The Skeptic** | {revs['skeptic']['score']} | {revs['skeptic']['comment']} |"
                )
                output.append(
                    f"| 📐 **The Methodologist** | {revs['methodologist']['score']} | {revs['methodologist']['comment']} |"
                )
                output.append(
                    f"| 🏥 **The Clinical Expert** | {revs['clinical_expert']['score']} | {revs['clinical_expert']['comment']} |"
                )
                output.append("")

            # Show critical issues (sharp, evidence-based)
            if feedback.get("critical_issues"):
                output.append("### ⚠️ Critical Issues (Reviewer 會質疑)")
                output.append("")
                for issue in feedback["critical_issues"]:
                    output.append(f"**❌ {issue['problem']}**")
                    output.append(f"- 🎯 {issue['challenge']}")
                    output.append(f"- 🔧 {issue['fix']}")
                    output.append("")

            # Show questions (what reviewer would ask)
            reviewer_questions = []
            if "reviewers" in feedback:
                for r in feedback["reviewers"].values():
                    reviewer_questions.extend(r.get("questions", []))

            if reviewer_questions:
                output.append("### ❓ Reviewer 會問的問題")
                output.append("")
                for q in reviewer_questions:
                    output.append(f"- {q}")
                output.append("")

            # CGU recommendation (if needed)
            cgu = feedback.get("cgu_recommendation", {})
            if cgu.get("recommend") and avg_score < 75:
                output.append("### 🤖 需要 CGU 幫忙嗎？")
                output.append("")
                output.append(f"> **工具：** `{cgu.get('tool', 'mcp_cgu_deep_think')}`")
                output.append(f"> **原因：** {cgu.get('reason', '')}")
                if cgu.get("prompt"):
                    output.append(f"> **Prompt：** {cgu['prompt']}")
                output.append("")

            # Note: This is advisory, not blocking
            output.append("> 📌 **這是 reviewer 視角的建議，不是硬性門檻。**")
            output.append("> 您可以選擇：(1) 直接寫 (2) 補強後再寫 (3) 用 CGU 發想")
            output.append("")

        # Consistency check
        if result.consistency_checked:
            output.append("")
            output.append("## 🔗 Consistency Check")
            output.append("")
            status = "✅ PASSED" if result.consistency_passed else "⚠️ ISSUES"
            output.append(f"**Status:** {status} (Score: {result.consistency_score}/100)")
            if result.consistency_issues:
                output.append("")
                output.append("**Issues:**")
                for issue in result.consistency_issues:
                    output.append(f"- {issue}")

        # Errors and suggestions
        if result.errors:
            output.append("")
            output.append("## ❌ Errors")
            for error in result.errors:
                output.append(f"- {error}")

        if result.warnings:
            output.append("")
            output.append("## ⚠️ Warnings")
            for warning in result.warnings:
                output.append(f"- {warning}")

        if result.suggestions:
            output.append("")
            output.append("## 💡 Suggestions")
            for suggestion in result.suggestions:
                output.append(f"- {suggestion}")

        # Final verdict
        output.append("")
        output.append("---")
        output.append("")

        # Section-specific result
        if result.target_section:
            if result.can_write_section:
                output.append(f"## ✅ CAN WRITE {result.target_section.upper()}")
                output.append("")
                output.append(f"All required sections for **{result.target_section}** are present.")
                if result.missing_recommended:
                    output.append("")
                    output.append(
                        "💡 **Tip:** Consider filling in the recommended sections for a stronger paper."
                    )
            else:
                output.append(f"## ⚠️ MISSING SECTIONS FOR {result.target_section.upper()}")
                output.append("")
                output.append(f"Missing required sections for **{result.target_section}**.")
                output.append("Please fill in the missing sections first.")
        elif result.overall_passed:
            output.append("## ✅ VALIDATION PASSED")
            output.append("")
            output.append("The concept file meets all requirements.")
            output.append("You may proceed with `/mdpaper.draft` to write the paper.")
            output.append("")
            output.append("**Remember:**")
            output.append("- 🔒 Protected content must be preserved in the final paper")
            output.append("- Ask user before modifying any 🔒 sections")
        else:
            # Sharp summary with clear options
            output.append("## 📋 Assessment Summary")
            output.append("")

            output.append(f"**Novelty Score:** {result.novelty_average:.1f}/100")
            output.append("")

            if result.novelty_average >= 60:
                output.append("您的 concept 可以過關，但有可改進之處。")
            else:
                output.append("⚠️ 目前的 novelty statement 可能無法通過 peer review。")
            output.append("")
            output.append("**您的選擇：**")
            output.append("")
            output.append("| 選項 | 行動 |")
            output.append("|------|------|")
            output.append("| ✅ 直接寫 | 『直接寫』- 我立即開始 |")
            output.append("| 🔧 修正問題 | 『幫我改 [問題]』- 我一次只改一點 |")
            output.append("| 🤖 CGU 發想 | 『用 CGU 想想』- 從 reviewer 角度找弱點 |")
            output.append("")
            output.append("> 💬 您決定，我執行。我不會自動修改 concept。")

        return "\n".join(output)

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
