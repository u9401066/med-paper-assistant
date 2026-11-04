"""Claim, selling-point and asset extraction for the concept-review artifact."""

import re
from typing import Any, Dict, List

from ._models import SectionCheck, ValidationResult


class ClaimsExtractionMixin:
    """Derive research question, claims, evidence and asset obligations from concept text."""

    def _extract_research_question(self, result: ValidationResult, content: str) -> Dict[str, Any]:
        """Extract a canonical research question block."""
        question_content = result.sections.get(
            "research_question", SectionCheck(name="", found=False, has_content=False)
        ).content.strip() or self._extract_markdown_section(content, "RESEARCH QUESTION")
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content.strip() or self._extract_markdown_section(content, "NOVELTY")
        fallback_sentence = ""
        source_text = question_content or novelty_content or content
        sentence_match = re.search(r"([^.!?\n]{15,}[.!?])", source_text)
        if sentence_match:
            fallback_sentence = sentence_match.group(1).strip()

        return {
            "canonical_question": question_content or fallback_sentence,
            "study_objective": fallback_sentence,
            "target_population": "",
            "comparator": "",
            "outcomes_primary": [],
            "outcomes_secondary": [],
        }

    def _extract_claims_required(
        self, result: ValidationResult, content: str
    ) -> List[Dict[str, Any]]:
        """Extract required claims from novelty and selling point sections."""
        claims: List[Dict[str, Any]] = []
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content.strip() or self._extract_markdown_section(content, "NOVELTY")
        if novelty_content:
            claims.append(
                {
                    "id": "claim-1",
                    "text": novelty_content.splitlines()[0].strip(),
                    "priority": "critical",
                    "section_targets": ["Introduction", "Discussion"],
                }
            )

        for idx, point in enumerate(self._extract_selling_points(result, content), start=2):
            claims.append(
                {
                    "id": f"claim-{idx}",
                    "text": point,
                    "priority": "important",
                    "section_targets": ["Discussion"],
                }
            )

        return claims

    def _extract_selling_points(self, result: ValidationResult, content: str) -> List[str]:
        """Extract individual selling points from the protected section."""
        selling_content = result.sections.get(
            "selling_points", SectionCheck(name="", found=False, has_content=False)
        ).content or self._extract_markdown_section(content, "KEY SELLING POINTS")
        lines = [line.strip(" -*\t") for line in selling_content.splitlines() if line.strip()]
        points: List[str] = []
        for line in lines:
            cleaned = re.sub(r"^(Selling Point\s*\d+[:：]?|\d+[.)]\s*)", "", line, flags=re.I)
            cleaned = cleaned.strip("* ")
            if cleaned and cleaned not in points:
                points.append(cleaned)
        return points[:10]

    def _extract_markdown_section(self, content: str, heading: str) -> str:
        """Extract content under a markdown heading using a simple fallback parser."""
        pattern = re.compile(
            rf"^#+\s*{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^#|\Z)",
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(content)
        if not match:
            return ""
        return match.group("body").strip()

    def _build_evidence_requirements(
        self,
        claims_required: List[Dict[str, Any]],
        content: str,
        result: ValidationResult,
    ) -> List[Dict[str, Any]]:
        """Build evidence requirements for each claim."""
        has_any_citation = bool(re.search(r"\[\[[^\]]+\]\]", content))
        requirements: List[Dict[str, Any]] = []
        for claim in claims_required:
            requirements.append(
                {
                    "claim_id": claim["id"],
                    "evidence_type": "literature",
                    "required": True,
                    "description": f"Evidence needed to support: {claim['text']}",
                    "currently_satisfied": has_any_citation and result.citation_score >= 0,
                }
            )
        return requirements

    def _extract_asset_obligations(self, content: str) -> List[Dict[str, Any]]:
        """Infer mandatory assets mentioned in concept text."""
        obligations: List[Dict[str, Any]] = []
        normalized = content.lower()
        if "flow diagram" in normalized or "流程圖" in content:
            obligations.append(
                {
                    "id": "figure-1",
                    "required": True,
                    "type": "flow_diagram",
                    "target_section": "Methods",
                    "purpose": "Study flow or patient selection",
                    "minimum_caption_requirements": [],
                    "exportable_required": True,
                }
            )
        if any(
            token in normalized for token in ["table 1", "baseline characteristics", "基線特徵"]
        ):
            obligations.append(
                {
                    "id": "table-1",
                    "required": True,
                    "type": "table_one",
                    "target_section": "Results",
                    "purpose": "Baseline characteristics",
                    "minimum_caption_requirements": [],
                    "exportable_required": False,
                }
            )
        if any(token in normalized for token in ["roc", "forest plot", "plot", "figure"]):
            obligations.append(
                {
                    "id": f"figure-{len(obligations) + 1}",
                    "required": True,
                    "type": "plot",
                    "target_section": "Results",
                    "purpose": "Quantitative visual evidence",
                    "minimum_caption_requirements": [],
                    "exportable_required": True,
                }
            )
        return obligations
