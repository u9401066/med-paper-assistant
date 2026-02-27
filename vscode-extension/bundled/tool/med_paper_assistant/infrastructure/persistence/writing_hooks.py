"""
Writing Hooks Engine — Code-enforced writing quality hooks.

29 Code-Enforced hooks (was 14, expanded from Agent-Driven):
  Post-Write:     A1 Word Count, A2 Citation Density, A3 Anti-AI,
                  A4 Wikilink Format, A5 Language, A6 Overlap
  Post-Section:   B8 Data-Claim Alignment
  Post-Manuscript: C3 N-value Consistency, C4 Abbreviation First-Use,
                  C5 Wikilink Resolvable, C6 Total Word Count,
                  C7a Figure/Table Counts, C7d Cross-References,
                  C9 Supplementary Cross-Ref, F1-F4 Data Artifacts
  Pre-Commit:     P1 Citation Integrity, P2 Anti-AI, P4 Word Count,
                  P5 Protected Content, P7 Reference Integrity

Architecture:
  Infrastructure layer service. Called by the auto-paper pipeline at
  appropriate phases. Records events via HookEffectivenessTracker.

Design rationale (CONSTITUTION §22):
  - Auditable: Each hook returns structured issues with severity + location
  - Reproducible: Deterministic regex/NLP checks, no model randomness
  - Composable: Each hook is a standalone method; pipeline calls as needed
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from med_paper_assistant.shared.constants import DEFAULT_WORD_LIMITS

logger = structlog.get_logger()


# ── Anti-AI phrase list (A3 / P2) ──────────────────────────────────
# Union of: auto-paper SKILL.md A3 (7), git-precommit SKILL.md P2 (10),
# DomainConstraintEngine V002 (16). Deduplicated.

ANTI_AI_PHRASES: list[str] = [
    "in recent years",
    "it is worth noting",
    "it is important to note",
    "it should be noted",
    "plays a crucial role",
    "has garnered significant attention",
    "a comprehensive understanding",
    "this groundbreaking",
    "groundbreaking",
    "delve into",
    "shed light on",
    "pave the way",
    "a myriad of",
    "in the realm of",
    "a testament to",
    "multifaceted",
    "underscores the importance",
    "notably",
    "comprehensive overview",
    "leveraging",
    "pivotal role",
    "in conclusion, our study",
    "it is widely recognized",
]

# These phrases are only flagged at paragraph start (not mid-sentence).
ANTI_AI_PARAGRAPH_START_ONLY: list[str] = [
    "furthermore",
]

# Common abbreviations that should NOT require first-use definition.
COMMON_ABBREVIATIONS: set[str] = {
    "DNA",
    "RNA",
    "ICU",
    "OR",
    "CI",
    "SD",
    "IQR",
    "HR",
    "RR",
    "BMI",
    "CT",
    "MRI",
    "ECG",
    "EEG",
    "EMG",
    "IV",
    "IM",
    "SC",
    "PO",
    "ICU",
    "ED",
    "ER",
    "WHO",
    "FDA",
    "NIH",
    "CDC",
    "IRB",
    "GCP",
    "ITT",
    "PP",
    "CONSORT",
    "STROBE",
    "PRISMA",
    "CARE",
    "STARD",
    "TRIPOD",
    "ANOVA",
    "GEE",
    "ROC",
    "AUC",
    "NNT",
    "NNH",
    "RCT",
    "CPR",
    "INR",
    "PT",
    "APTT",
    "VAS",
    "GCS",
    "ASA",
    "NYHA",
    "APACHE",
    "SOFA",
    "MELD",
    "CRP",
    "WBC",
    "RBC",
    "HB",
    "PLT",
    "ALT",
    "AST",
    "BUN",
    "II",
    "III",
    "IV",
}

# Default citation density thresholds (citations per N words).
# A section needing >= 1 citation per 100 words has threshold 100.
# 0 means no minimum requirement for that section.
DEFAULT_CITATION_DENSITY: dict[str, int] = {
    "introduction": 100,
    "discussion": 150,
    "methods": 0,
    "results": 0,
}


# ── British vs American English dictionary (A5) ────────────────────

# Key = British spelling, Value = American spelling
# Covers the most common medical/scientific divergences.
BRIT_VS_AMER: dict[str, str] = {
    # -ise / -ize
    "randomise": "randomize",
    "randomised": "randomized",
    "randomisation": "randomization",
    "randomising": "randomizing",
    "standardise": "standardize",
    "standardised": "standardized",
    "standardisation": "standardization",
    "characterise": "characterize",
    "characterised": "characterized",
    "characterisation": "characterization",
    "categorise": "categorize",
    "categorised": "categorized",
    "categorisation": "categorization",
    "optimise": "optimize",
    "optimised": "optimized",
    "optimisation": "optimization",
    "minimise": "minimize",
    "minimised": "minimized",
    "utilise": "utilize",
    "utilised": "utilized",
    "utilisation": "utilization",
    "analyse": "analyze",
    "analysed": "analyzed",
    "analysing": "analyzing",
    "recognise": "recognize",
    "recognised": "recognized",
    "summarise": "summarize",
    "summarised": "summarized",
    "generalise": "generalize",
    "generalised": "generalized",
    "generalisation": "generalization",
    "hospitalise": "hospitalize",
    "hospitalised": "hospitalized",
    "hospitalisation": "hospitalization",
    "specialise": "specialize",
    "specialised": "specialized",
    "specialisation": "specialization",
    "normalise": "normalize",
    "normalised": "normalized",
    "normalisation": "normalization",
    "visualise": "visualize",
    "visualised": "visualized",
    "visualisation": "visualization",
    "hypothesise": "hypothesize",
    "hypothesised": "hypothesized",
    "prioritise": "prioritize",
    "prioritised": "prioritized",
    "sensitise": "sensitize",
    "sensitised": "sensitized",
    "immunise": "immunize",
    "immunised": "immunized",
    "immunisation": "immunization",
    "localise": "localize",
    "localised": "localized",
    "localisation": "localization",
    "stabilise": "stabilize",
    "stabilised": "stabilized",
    "stabilisation": "stabilization",
    # -our / -or
    "colour": "color",
    "colours": "colors",
    "favour": "favor",
    "favourable": "favorable",
    "favourably": "favorably",
    "behaviour": "behavior",
    "behaviours": "behaviors",
    "behavioural": "behavioral",
    "tumour": "tumor",
    "tumours": "tumors",
    "honour": "honor",
    "labour": "labor",
    "neighbour": "neighbor",
    "neighbourhood": "neighborhood",
    "humour": "humor",
    "vigour": "vigor",
    "vapour": "vapor",
    "odour": "odor",
    "rumour": "rumor",
    "savour": "savor",
    # -re / -er
    "centre": "center",
    "centres": "centers",
    "fibre": "fiber",
    "fibres": "fibers",
    "litre": "liter",
    "litres": "liters",
    "metre": "meter",
    "metres": "meters",
    "theatre": "theater",
    "theatres": "theaters",
    # -ae / -e, -oe / -e
    "anaesthesia": "anesthesia",
    "anaesthetic": "anesthetic",
    "anaesthetist": "anesthetist",
    "anaesthetised": "anesthetized",
    "haemorrhage": "hemorrhage",
    "haemoglobin": "hemoglobin",
    "haematology": "hematology",
    "haemodynamic": "hemodynamic",
    "haemodynamics": "hemodynamics",
    "haemostasis": "hemostasis",
    "leukaemia": "leukemia",
    "paediatric": "pediatric",
    "paediatrics": "pediatrics",
    "oedema": "edema",
    "oesophagus": "esophagus",
    "oesophageal": "esophageal",
    "foetus": "fetus",
    "foetal": "fetal",
    "orthopaedic": "orthopedic",
    "gynaecology": "gynecology",
    "gynaecological": "gynecological",
    # -ence / -ense
    "defence": "defense",
    "offence": "offense",
    "licence": "license",
    # -lled / -led, -lling / -ling
    "cancelled": "canceled",
    "cancelling": "canceling",
    "labelled": "labeled",
    "labelling": "labeling",
    "modelled": "modeled",
    "modelling": "modeling",
    "travelled": "traveled",
    "travelling": "traveling",
    "counselled": "counseled",
    "counselling": "counseling",
    "signalled": "signaled",
    "signalling": "signaling",
    "channelled": "channeled",
    "channelling": "channeling",
    # Other common pairs
    "programme": "program",
    "programmes": "programs",
    "practise": "practice",
    "practised": "practiced",
    "ageing": "aging",
    "artefact": "artifact",
    "artefacts": "artifacts",
    "grey": "gray",
    "judgement": "judgment",
    "manoeuvre": "maneuver",
    "manoeuvres": "maneuvers",
    "catalogue": "catalog",
    "dialogue": "dialog",
    "plough": "plow",
    "sceptical": "skeptical",
    "sulphate": "sulfate",
    "aluminium": "aluminum",
    "diarrhoea": "diarrhea",
    "coeliac": "celiac",
    "caesarean": "cesarean",
}

# Build reverse dictionary (American → British)
AMER_VS_BRIT: dict[str, str] = {v: k for k, v in BRIT_VS_AMER.items()}

# Sanity check: mapping must be bijective (no ambiguous reversals)
assert len(AMER_VS_BRIT) == len(BRIT_VS_AMER), (
    f"BRIT_VS_AMER has duplicate values — reverse map lost {len(BRIT_VS_AMER) - len(AMER_VS_BRIT)} entries"
)


@dataclass
class HookIssue:
    """A single issue found by a writing hook."""

    hook_id: str
    severity: str  # CRITICAL, WARNING, INFO
    section: str  # Which section (e.g., "Methods", "Results")
    message: str
    location: str = ""  # Line/paragraph hint
    suggestion: str = ""  # How to fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "severity": self.severity,
            "section": self.section,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class HookResult:
    """Result of a hook evaluation."""

    hook_id: str
    passed: bool
    issues: list[HookIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "passed": self.passed,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }


class WritingHooksEngine:
    """
    Code-enforced writing hooks for the auto-paper pipeline.

    Implements 29 hooks: A1-A6, B8, C3-C7d, C9, F1-F4, P1/P2/P4/P5/P7.

    Args:
        project_dir: Path to the project directory (e.g., projects/{slug}/)
    """

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"
        self._journal_profile: dict[str, Any] | None = None
        self._load_journal_profile()

    def _load_journal_profile(self) -> None:
        """Load journal-profile.yaml if it exists."""
        profile_path = self._project_dir / "journal-profile.yaml"
        if profile_path.is_file():
            try:
                with open(profile_path) as f:
                    self._journal_profile = yaml.safe_load(f) or {}
            except Exception:
                logger.warning("Failed to load journal-profile.yaml", path=str(profile_path))
                self._journal_profile = None

    def _get_section_word_limit(self, section_name: str) -> int | None:
        """Get word limit for a section (journal-profile -> DEFAULT_WORD_LIMITS fallback)."""
        if self._journal_profile:
            paper = self._journal_profile.get("paper", {})
            for sec in paper.get("sections", []):
                if sec.get("name", "").lower() == section_name.lower():
                    limit = sec.get("word_limit")
                    if limit is not None:
                        return int(limit)
        # Fallback to default — try exact then case-insensitive
        for key, val in DEFAULT_WORD_LIMITS.items():
            if key.lower() == section_name.lower():
                return val
        return None

    def _get_word_tolerance_pct(self) -> int:
        """Get word tolerance percentage (default 20)."""
        if self._journal_profile:
            pipeline = self._journal_profile.get("pipeline", {})
            tolerance = pipeline.get("tolerance", {})
            pct = tolerance.get("word_percent")
            if pct is not None:
                return int(pct)
        return 20

    def _get_citation_density_threshold(self, section_name: str) -> int:
        """Get citation density threshold (citations per N words, 0 = no check)."""
        if self._journal_profile:
            pipeline = self._journal_profile.get("pipeline", {})
            writing = pipeline.get("writing", {})
            density = writing.get("citation_density", {})
            val = density.get(section_name.lower())
            if val is not None:
                return int(val)
        return DEFAULT_CITATION_DENSITY.get(section_name.lower(), 0)

    def _get_total_word_limit(self) -> int | None:
        """Get total manuscript word limit."""
        if self._journal_profile:
            wl = self._journal_profile.get("word_limits", {})
            total = wl.get("total_manuscript")
            if total is not None:
                return int(total)
        return None

    def _get_figure_table_limits(self) -> tuple[int | None, int | None]:
        """Get (figures_max, tables_max) from journal profile."""
        if self._journal_profile:
            assets = self._journal_profile.get("assets", {})
            fig = assets.get("figures_max")
            tbl = assets.get("tables_max")
            return (int(fig) if fig is not None else None, int(tbl) if tbl is not None else None)
        return (None, None)

    # ── Shared helpers ─────────────────────────────────────────────

    @staticmethod
    def _count_words(text: str) -> int:
        """Count words in text, stripping markdown formatting."""
        # Strip wikilinks
        cleaned = re.sub(r"\[\[[^\]]*\]\]", "CITE", text)
        # Strip markdown links [text](url)
        cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
        # Strip bold/italic markers
        cleaned = re.sub(r"[*_]{1,3}", "", cleaned)
        # Strip headings markers
        cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
        return len(re.findall(r"\b\w+\b", cleaned))

    @staticmethod
    def _parse_sections(content: str) -> dict[str, str]:
        """Parse markdown content into {section_name: section_text} dict."""
        sections: dict[str, str] = {}
        current_name: str | None = None
        current_lines: list[str] = []

        for line in content.split("\n"):
            heading_match = re.match(r"^#{1,3}\s+(.+)", line)
            if heading_match:
                if current_name is not None:
                    sections[current_name] = "\n".join(current_lines).strip()
                current_name = heading_match.group(1).strip()
                current_lines = []
            elif current_name is not None:
                current_lines.append(line)

        if current_name is not None:
            sections[current_name] = "\n".join(current_lines).strip()

        return sections

    # ── Hook A1: Word Count Compliance ─────────────────────────────

    def check_word_count_compliance(
        self,
        content: str,
        section_name: str | None = None,
        critical_threshold_pct: int = 50,
    ) -> HookResult:
        """
        Hook A1: Check section word counts against targets.

        If section_name is provided, checks that single section.
        If None, parses content into sections and checks each.

        Args:
            content: Section text or full manuscript.
            section_name: If provided, treat content as a single section.
            critical_threshold_pct: Deviation % that triggers CRITICAL (default 50).
        """
        issues: list[HookIssue] = []
        tolerance_pct = self._get_word_tolerance_pct()

        if section_name:
            sections_to_check = {section_name: content}
        else:
            sections_to_check = self._parse_sections(content)

        checked: list[dict[str, Any]] = []

        for sec_name, sec_text in sections_to_check.items():
            target = self._get_section_word_limit(sec_name)
            if target is None:
                continue
            word_count = self._count_words(sec_text)
            deviation_pct = ((word_count - target) / target) * 100 if target > 0 else 0

            if abs(deviation_pct) > critical_threshold_pct:
                severity = "CRITICAL"
            elif abs(deviation_pct) > tolerance_pct:
                severity = "WARNING"
            else:
                severity = None

            if severity:
                direction = "over" if deviation_pct > 0 else "under"
                issues.append(
                    HookIssue(
                        hook_id="A1",
                        severity=severity,
                        section=sec_name,
                        message=(
                            f"{sec_name}: {word_count} words ({deviation_pct:+.0f}% {direction} "
                            f"target {target}, tolerance ±{tolerance_pct}%)"
                        ),
                        suggestion=f"{'Trim' if deviation_pct > 0 else 'Expand'} the {sec_name} section",
                    )
                )

            checked.append(
                {
                    "section": sec_name,
                    "word_count": word_count,
                    "target": target,
                    "deviation_pct": round(deviation_pct, 1),
                }
            )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {"sections_checked": checked, "tolerance_pct": tolerance_pct}

        logger.info("Hook A1 complete", passed=passed, sections=len(checked))
        return HookResult(hook_id="A1", passed=passed, issues=issues, stats=stats)

    # ── Hook A2: Citation Density ──────────────────────────────────

    def check_citation_density(
        self,
        content: str,
        section_name: str = "manuscript",
    ) -> HookResult:
        """
        Hook A2: Check citation density (wikilinks per N words).

        Args:
            content: Section text.
            section_name: Section name for threshold lookup.
        """
        issues: list[HookIssue] = []

        threshold = self._get_citation_density_threshold(section_name)
        if threshold == 0:
            # No citation density requirement for this section
            return HookResult(
                hook_id="A2",
                passed=True,
                stats={"section": section_name, "threshold": 0, "skipped": True},
            )

        citation_count = len(re.findall(r"\[\[[^\]]+\]\]", content))
        word_count = self._count_words(content)

        if word_count == 0:
            return HookResult(
                hook_id="A2",
                passed=True,
                stats={"section": section_name, "word_count": 0},
            )

        # threshold = N means "at least 1 citation per N words"
        # So required citations = word_count / threshold
        required = word_count / threshold
        density_per_100w = (citation_count / word_count) * 100 if word_count else 0

        if citation_count < required:
            issues.append(
                HookIssue(
                    hook_id="A2",
                    severity="WARNING",
                    section=section_name,
                    message=(
                        f"{section_name}: {citation_count} citations in {word_count} words "
                        f"(density {density_per_100w:.1f}/100w, need ≥1/{threshold}w = {required:.0f} citations)"
                    ),
                    suggestion=f"Add more citations to {section_name} (need ≥{required:.0f})",
                )
            )

        passed = len(issues) == 0
        stats = {
            "section": section_name,
            "citation_count": citation_count,
            "word_count": word_count,
            "density_per_100w": round(density_per_100w, 2),
            "threshold_per_nw": threshold,
        }

        logger.info("Hook A2 complete", passed=passed, density=density_per_100w)
        return HookResult(hook_id="A2", passed=passed, issues=issues, stats=stats)

    # ── Hook A3: Anti-AI Pattern Detection ─────────────────────────

    def check_anti_ai_patterns(
        self,
        content: str,
        section: str = "manuscript",
        warn_threshold: int = 1,
        critical_threshold: int = 3,
    ) -> HookResult:
        """
        Hook A3: Detect AI-characteristic phrasing.

        Scans for forbidden phrases from the unified ANTI_AI_PHRASES list.
        "Furthermore" is only flagged at paragraph start.

        Args:
            content: Text to scan.
            section: Section name for reporting.
            warn_threshold: Total matches to trigger WARNING (default 1).
            critical_threshold: Total matches to trigger CRITICAL (default 3).
        """
        issues: list[HookIssue] = []
        content_lower = content.lower()
        phrase_counts: dict[str, int] = {}
        total_matches = 0

        for phrase in ANTI_AI_PHRASES:
            count = len(re.findall(rf"\b{re.escape(phrase)}\b", content_lower))
            if count > 0:
                phrase_counts[phrase] = count
                total_matches += count

        # Paragraph-start-only phrases
        for phrase in ANTI_AI_PARAGRAPH_START_ONLY:
            count = len(re.findall(rf"(?:^|\n\n)\s*{re.escape(phrase)}\b", content, re.IGNORECASE))
            if count > 0:
                phrase_counts[f"{phrase} (paragraph start)"] = count
                total_matches += count

        for phrase, count in phrase_counts.items():
            severity = "CRITICAL" if total_matches >= critical_threshold else "WARNING"
            issues.append(
                HookIssue(
                    hook_id="A3",
                    severity=severity,
                    section=section,
                    message=f"AI-characteristic phrase '{phrase}' found ({count}x)",
                    suggestion="Replace with specific, concrete language",
                )
            )

        passed = total_matches < warn_threshold
        stats = {
            "total_matches": total_matches,
            "unique_phrases_found": len(phrase_counts),
            "phrase_counts": phrase_counts,
        }

        logger.info("Hook A3 complete", passed=passed, total_matches=total_matches)
        return HookResult(hook_id="A3", passed=passed, issues=issues, stats=stats)

    # ── Hook A4: Wikilink Format Validation ────────────────────────

    def check_wikilink_format(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook A4: Validate wikilink format in draft text.

        Checks that all [[wikilinks]] follow the correct format:
        [[author2024_12345678]] (lowercase author + year + underscore + PMID).

        Args:
            content: Text to check.
            section: Section name for reporting.
        """
        issues: list[HookIssue] = []

        # Find all wikilinks
        all_wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)
        if not all_wikilinks:
            return HookResult(
                hook_id="A4",
                passed=True,
                stats={"total_wikilinks": 0, "valid_count": 0, "issue_count": 0},
            )

        valid_pattern = re.compile(r"^[a-z]+\d{4}_\d{7,8}$")
        valid_count = 0

        for wl in all_wikilinks:
            if valid_pattern.match(wl):
                valid_count += 1
            else:
                # Determine issue type
                if re.match(r"^\d{7,8}$", wl):
                    issue_type = "PMID-only (missing author prefix)"
                    severity = "WARNING"
                elif re.match(r"^PMID:\s*\d+$", wl, re.IGNORECASE):
                    issue_type = "PMID: prefix format"
                    severity = "WARNING"
                else:
                    issue_type = "non-standard format"
                    severity = "WARNING"

                issues.append(
                    HookIssue(
                        hook_id="A4",
                        severity=severity,
                        section=section,
                        message=f"Wikilink [[{wl}]] has {issue_type}",
                        suggestion=f"Use format [[author2024_12345678]] for '{wl}'",
                    )
                )

        passed = len(issues) == 0
        stats = {
            "total_wikilinks": len(all_wikilinks),
            "valid_count": valid_count,
            "issue_count": len(issues),
        }

        logger.info("Hook A4 complete", passed=passed, total=len(all_wikilinks), valid=valid_count)
        return HookResult(hook_id="A4", passed=passed, issues=issues, stats=stats)

    # ── Hook A5: Language Consistency ──────────────────────────────

    def check_language_consistency(
        self,
        content: str,
        prefer: str = "american",
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook A5: Detect British vs American English mixing.

        Scans the draft for words that belong to the *non-preferred* variant.
        A manuscript should use one variant consistently.

        Args:
            content: Full text or section text to check.
            prefer: "american" or "british" — the expected variant.
            section: Section name for issue reporting.

        Returns:
            HookResult with issues listing each non-preferred word found.
        """
        issues: list[HookIssue] = []

        if prefer == "american":
            # Look for British spellings
            target_dict = BRIT_VS_AMER
            variant_found = "British"
            variant_preferred = "American"
        elif prefer == "british":
            # Look for American spellings
            target_dict = AMER_VS_BRIT
            variant_found = "American"
            variant_preferred = "British"
        else:
            return HookResult(
                hook_id="A5", passed=True, stats={"error": f"Unknown preference: {prefer}"}
            )

        found_words: dict[str, list[int]] = {}

        lines = content.split("\n")
        in_code_block = False
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # Toggle code block state
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            # Skip headings, code block content, and full-line wikilinks
            if in_code_block or stripped.startswith("#") or stripped.startswith("[["):
                continue
            # Strip inline wikilinks before word extraction
            line = re.sub(r"\[\[[^\]]*\]\]", "", line)
            words = re.findall(r"\b[a-zA-Z]+\b", line.lower())
            for word in words:
                if word in target_dict:
                    found_words.setdefault(word, []).append(line_num)

        for word, line_nums in sorted(found_words.items()):
            replacement = target_dict[word]
            issues.append(
                HookIssue(
                    hook_id="A5",
                    severity="WARNING",
                    section=section,
                    message=f"{variant_found} spelling '{word}' found ({len(line_nums)} occurrence(s))",
                    location=f"lines: {', '.join(str(n) for n in line_nums[:5])}{'...' if len(line_nums) > 5 else ''}",
                    suggestion=f"Replace with {variant_preferred} spelling '{replacement}'",
                )
            )

        passed = len(issues) == 0
        stats = {
            "preferred_variant": prefer,
            "non_preferred_words_found": len(found_words),
            "total_occurrences": sum(len(v) for v in found_words.values()),
        }

        logger.info(
            "Hook A5 complete",
            passed=passed,
            non_preferred_count=stats["non_preferred_words_found"],
            prefer=prefer,
        )
        return HookResult(hook_id="A5", passed=passed, issues=issues, stats=stats)

    # ── Hook A6: Self-Plagiarism / Overlap Detection ──────────────

    def check_overlap(
        self,
        content: str,
        min_ngram: int = 6,
        threshold: int = 3,
    ) -> HookResult:
        """
        Hook A6: Detect internal paragraph overlap (copy-paste residue).

        Splits content into paragraphs, extracts n-grams, and finds
        n-grams that appear in multiple paragraphs. This catches
        copy-paste artifacts and repetitive phrasing.

        Args:
            content: Full manuscript text.
            min_ngram: Minimum n-gram size (words). Default 6.
            threshold: Minimum shared n-grams between two paragraphs
                       to flag as WARNING. Default 3.

        Returns:
            HookResult with issues for overlapping paragraph pairs.
        """
        issues: list[HookIssue] = []

        # Split into paragraphs (non-empty, non-heading blocks)
        paragraphs: list[tuple[str, str]] = []  # (section_label, text)
        current_section = "Unknown"
        for block in re.split(r"\n{2,}", content):
            block = block.strip()
            if not block:
                continue
            # Track section headings
            heading_match = re.match(r"^#{1,3}\s+(.+)", block)
            if heading_match:
                current_section = heading_match.group(1).strip()
                continue
            # Skip very short paragraphs
            words = block.split()
            if len(words) < min_ngram:
                continue
            paragraphs.append((current_section, block))

        if len(paragraphs) < 2:
            return HookResult(
                hook_id="A6", passed=True, stats={"paragraphs_checked": len(paragraphs)}
            )

        def _extract_ngrams(text: str, n: int) -> set[str]:
            words = re.findall(r"\b[a-z]+\b", text.lower())
            return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}

        # Extract n-grams for each paragraph
        para_ngrams: list[set[str]] = [_extract_ngrams(text, min_ngram) for _, text in paragraphs]

        flagged_pairs: list[tuple[int, int, int]] = []  # (i, j, shared_count)

        for i in range(len(paragraphs)):
            for j in range(i + 1, len(paragraphs)):
                shared = para_ngrams[i] & para_ngrams[j]
                if len(shared) >= threshold:
                    flagged_pairs.append((i, j, len(shared)))

        for i, j, shared_count in flagged_pairs:
            sec_i, text_i = paragraphs[i]
            sec_j, text_j = paragraphs[j]
            preview_i = text_i[:80].replace("\n", " ") + "..."
            preview_j = text_j[:80].replace("\n", " ") + "..."

            severity = "CRITICAL" if shared_count >= threshold * 2 else "WARNING"
            issues.append(
                HookIssue(
                    hook_id="A6",
                    severity=severity,
                    section=f"{sec_i} ↔ {sec_j}",
                    message=f"{shared_count} shared {min_ngram}-grams between paragraphs",
                    location=f"P{i + 1} ({sec_i}): '{preview_i}' vs P{j + 1} ({sec_j}): '{preview_j}'",
                    suggestion="Rephrase one of the paragraphs to avoid repetitive phrasing",
                )
            )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "paragraphs_checked": len(paragraphs),
            "flagged_pairs": len(flagged_pairs),
            "max_shared_ngrams": max((s for _, _, s in flagged_pairs), default=0),
        }

        logger.info(
            "Hook A6 complete",
            passed=passed,
            paragraphs=len(paragraphs),
            flagged_pairs=len(flagged_pairs),
        )
        return HookResult(hook_id="A6", passed=passed, issues=issues, stats=stats)

    # ── Hook B8: Data-Claim Alignment ─────────────────────────────

    def check_data_claim_alignment(
        self,
        methods_content: str,
        results_content: str,
    ) -> HookResult:
        """
        Hook B8: Verify statistical claims in Results align with Methods.

        Checks:
        1. Statistical tests mentioned in Results must appear in Methods
        2. P-value thresholds should be consistent
        3. Outcome measures mentioned in Results should match Methods
        4. Common statistical tests in Results must be declared in Methods

        Args:
            methods_content: Text of the Methods section.
            results_content: Text of the Results section.

        Returns:
            HookResult with alignment issues.
        """
        issues: list[HookIssue] = []

        methods_lower = methods_content.lower()
        results_lower = results_content.lower()

        # Statistical test patterns (test name → regex)
        stat_tests = {
            "t-test": r"\bt[\s-]*test\b",
            "chi-square": r"chi[\s-]*square|χ2|χ²",
            "Fisher exact": r"fisher(?:'s)?\s+exact",
            "Mann-Whitney": r"mann[\s-]*whitney",
            "Wilcoxon": r"wilcoxon",
            "ANOVA": r"\banova\b",
            "Kruskal-Wallis": r"kruskal[\s-]*wallis",
            "logistic regression": r"logistic\s+regression",
            "linear regression": r"linear\s+regression",
            "Cox regression": r"cox\s+(?:proportional\s+hazards?|regression)",
            "Kaplan-Meier": r"kaplan[\s-]*meier",
            "log-rank": r"log[\s-]*rank",
            "McNemar": r"mcnemar",
            "Spearman": r"spearman",
            "Pearson": r"pearson",
            "ANCOVA": r"\bancova\b",
            "mixed model": r"mixed[\s-]*(?:effect|model)",
            "GEE": r"\bgee\b|generalized?\s+estim",
            "Bland-Altman": r"bland[\s-]*altman",
            "ROC": r"\broc\b|receiver\s+operating",
            "AUC": r"\bauc\b|area\s+under\s+(?:the\s+)?curve",
            "sensitivity analysis": r"sensitivity\s+analysis",
            "propensity score": r"propensity\s+score",
            "bootstrap": r"\bbootstrap",
            "Bayesian": r"\bbayesian\b",
            "multiple comparison": r"multiple\s+comparison|bonferroni|holm|tukey|šidák|sidak",
        }

        # Check 1: Tests mentioned in Results but not in Methods
        for test_name, pattern in stat_tests.items():
            in_results = bool(re.search(pattern, results_lower))
            in_methods = bool(re.search(pattern, methods_lower))
            if in_results and not in_methods:
                issues.append(
                    HookIssue(
                        hook_id="B8",
                        severity="CRITICAL",
                        section="Results ↔ Methods",
                        message=f"'{test_name}' used in Results but not described in Methods",
                        suggestion=f"Add '{test_name}' description to Methods, or remove from Results",
                    )
                )

        # Check 2: P-value threshold consistency
        # Extract alpha levels from Methods
        alpha_methods = set(
            re.findall(
                r"(?:significance|alpha|α)\s*(?:level)?\s*(?:of|=|:)?\s*(0\.\d+)", methods_lower
            )
        )
        # Extract thresholds from Results (e.g., "p < 0.05")
        p_thresholds_results = set(re.findall(r"p\s*[<>]\s*(0\.\d+)", results_lower))

        if alpha_methods and p_thresholds_results:
            for threshold in p_thresholds_results:
                if threshold not in alpha_methods:
                    # Only warn if it's a different significance level
                    issues.append(
                        HookIssue(
                            hook_id="B8",
                            severity="WARNING",
                            section="Results ↔ Methods",
                            message=(
                                f"Results uses p-value threshold {threshold} "
                                f"but Methods declares alpha = {', '.join(sorted(alpha_methods))}"
                            ),
                            suggestion="Ensure p-value thresholds in Results match the alpha level declared in Methods",
                        )
                    )

        # Check 3: CI width consistency
        ci_methods = set(re.findall(r"(\d+)%\s*(?:confidence\s+interval|ci)", methods_lower))
        ci_results = set(re.findall(r"(\d+)%\s*(?:confidence\s+interval|ci)", results_lower))

        if ci_methods and ci_results:
            mismatch = ci_results - ci_methods
            for ci in mismatch:
                issues.append(
                    HookIssue(
                        hook_id="B8",
                        severity="WARNING",
                        section="Results ↔ Methods",
                        message=f"Results reports {ci}% CI but Methods declares {', '.join(sorted(ci_methods))}% CI",
                        suggestion="Ensure CI percentages are consistent between Methods and Results",
                    )
                )

        # Check 4: Software mentioned in Results but not Methods
        software_patterns = {
            "SPSS": r"\bspss\b",
            "SAS": r"\bsas\b",
            "Stata": r"\bstata\b",
            "R": r"\bR\s+(?:version|software|package|v\d|\(v\d|Foundation|Core\s+Team)",
            "Python": r"\bpython\b",
            "MATLAB": r"\bmatlab\b",
            "GraphPad": r"graphpad",
            "MedCalc": r"medcalc",
        }
        for sw_name, pattern in software_patterns.items():
            in_results = bool(re.search(pattern, results_lower))
            in_methods = bool(re.search(pattern, methods_lower))
            if in_results and not in_methods:
                issues.append(
                    HookIssue(
                        hook_id="B8",
                        severity="WARNING",
                        section="Results ↔ Methods",
                        message=f"Software '{sw_name}' referenced in Results but not declared in Methods",
                        suggestion=f"Add '{sw_name}' to the statistical software section of Methods",
                    )
                )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "stat_tests_in_results": sum(
                1 for _, p in stat_tests.items() if re.search(p, results_lower)
            ),
            "stat_tests_in_methods": sum(
                1 for _, p in stat_tests.items() if re.search(p, methods_lower)
            ),
            "undeclared_tests": sum(1 for i in issues if "not described in Methods" in i.message),
        }

        logger.info(
            "Hook B8 complete",
            passed=passed,
            undeclared_tests=stats["undeclared_tests"],
        )
        return HookResult(hook_id="B8", passed=passed, issues=issues, stats=stats)

    # ── Hook C9: Supplementary Cross-Reference ────────────────────

    def check_supplementary_crossref(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C9: Verify main text references to supplementary material.

        Checks:
        1. Every "Supplementary Table N" / "Supplementary Figure N" referenced
           in the main text has a matching supplementary file or section.
        2. Every supplementary file has at least one reference in the main text
           (orphan detection).

        Args:
            content: Full manuscript text.

        Returns:
            HookResult with cross-reference issues.
        """
        issues: list[HookIssue] = []

        # Extract supplementary references from text
        supp_patterns = [
            (r"[Ss]upplementary\s+(?:Table|Tbl\.?)\s+(\w+)", "Supplementary Table"),
            (r"[Ss]upplementary\s+(?:Figure|Fig\.?)\s+(\w+)", "Supplementary Figure"),
            (
                r"[Ss]upplementary\s+(?:Material|Data|File|Appendix)\s+(\w+)",
                "Supplementary Material",
            ),
            (r"[Ss]\d+\s+(?:Table|Fig)", "S-prefix reference"),
            (r"[Aa]ppendix\s+(\w+)", "Appendix"),
            (r"[Oo]nline\s+[Ss]upplement(?:ary)?\s+(\w+)", "Online Supplement"),
            (r"e(?:Table|Figure|Appendix)\s*(\d+)", "e-prefix reference"),
        ]

        text_refs: dict[str, list[str]] = {}  # type → list of identifiers
        for pattern, ref_type in supp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                text_refs.setdefault(ref_type, []).extend(matches)

        # Check supplementary directory
        supp_dir = self._project_dir / "supplementary"
        supp_files: set[str] = set()
        if supp_dir.is_dir():
            for f in supp_dir.rglob("*"):
                if f.is_file():
                    supp_files.add(f.name)

        # Also check exports/supplementary
        exports_supp = self._project_dir / "exports" / "supplementary"
        if exports_supp.is_dir():
            for f in exports_supp.rglob("*"):
                if f.is_file():
                    supp_files.add(f.name)

        # Issue 1: References exist but no supplementary directory
        total_refs = sum(len(v) for v in text_refs.values())
        if total_refs > 0 and not supp_files:
            issues.append(
                HookIssue(
                    hook_id="C9",
                    severity="CRITICAL",
                    section="Supplementary",
                    message=(
                        f"Main text references {total_refs} supplementary item(s) "
                        f"but no supplementary files exist"
                    ),
                    location=", ".join(
                        f"{rtype} {', '.join(ids[:3])}" for rtype, ids in text_refs.items()
                    ),
                    suggestion="Create supplementary files in 'supplementary/' directory, or remove references from main text",
                )
            )

        # Issue 2: Phantom supplementary references (in text, no matching file)
        if supp_files and total_refs > 0:
            # Simple heuristic: check if supp files contain the referenced identifiers
            for ref_type, ids in text_refs.items():
                for ref_id in ids:
                    # Check if any file matches this ref (e.g., "table_s1.docx" for "S1")
                    ref_escaped = re.escape(ref_id.lower())
                    has_match = any(
                        re.search(rf"(?:^|[_\-.]){ref_escaped}(?:[_\-.]|$)", fname.lower())
                        for fname in supp_files
                    )
                    if not has_match:
                        issues.append(
                            HookIssue(
                                hook_id="C9",
                                severity="WARNING",
                                section="Supplementary",
                                message=f"'{ref_type} {ref_id}' referenced in text but no matching supplementary file found",
                                suggestion=f"Create supplementary file for {ref_type} {ref_id}, or verify the reference identifier",
                            )
                        )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "text_references": total_refs,
            "supplementary_files": len(supp_files),
            "reference_types": {k: len(v) for k, v in text_refs.items()},
        }

        logger.info(
            "Hook C9 complete",
            passed=passed,
            text_refs=total_refs,
            supp_files=len(supp_files),
        )
        return HookResult(hook_id="C9", passed=passed, issues=issues, stats=stats)

    # ── Hook F: Data Artifact Validation (formal pipeline integration) ─

    def validate_data_artifacts(
        self,
        draft_content: str | None = None,
    ) -> HookResult:
        """
        Hook F1-F4: Formal data artifact validation for pipeline integration.

        Wraps DataArtifactTracker.validate_cross_references() and adds
        severity classification matching the hook framework.

        F1: Provenance tracking (every artifact has tool + params + code)
        F2: Manifest ↔ file consistency (no phantom/orphan files)
        F3: Draft ↔ manifest cross-reference (no phantom/orphan references)
        F4: Statistical claim verification (claims backed by artifacts)

        Args:
            draft_content: Full manuscript text. If None, skips draft checks (F3, F4).

        Returns:
            HookResult with structured issues from all F sub-checks.
        """
        from .data_artifact_tracker import DataArtifactTracker

        audit_dir = self._audit_dir
        tracker = DataArtifactTracker(audit_dir, self._project_dir)
        validation = tracker.validate_cross_references(draft_content)

        issues: list[HookIssue] = []
        for raw_issue in validation.get("issues", []):
            category = raw_issue.get("category", "")
            # Map categories to hook sub-IDs
            if category in ("provenance_missing", "no_provenance_code"):
                hook_sub = "F1"
            elif category in ("manifest_missing", "phantom_file"):
                hook_sub = "F2"
            elif category in ("phantom_reference", "orphan_asset"):
                hook_sub = "F3"
            elif category == "unverified_stats":
                hook_sub = "F4"
            else:
                hook_sub = "F"

            issues.append(
                HookIssue(
                    hook_id=hook_sub,
                    severity=raw_issue.get("severity", "WARNING"),
                    section="Data Artifacts",
                    message=raw_issue.get("message", ""),
                )
            )

        passed = validation.get("passed", True)
        stats = validation.get("summary", {})

        logger.info(
            "Hook F complete",
            passed=passed,
            critical=stats.get("critical_issues", 0),
            warnings=stats.get("warning_issues", 0),
        )
        return HookResult(hook_id="F", passed=passed, issues=issues, stats=stats)

    # ── Hook C3: N-value Cross-Section Consistency ─────────────────

    def check_n_value_consistency(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C3: Verify N-values (sample sizes) are consistent across sections.

        Methods section is the source of truth. Any N-value appearing in
        other sections that differs from Methods is flagged.
        """
        issues: list[HookIssue] = []
        sections = self._parse_sections(content)

        # Patterns to extract N-values with context
        n_patterns = [
            (r"\b[Nn]\s*=\s*(\d+)\b", "N="),
            (
                r"(\d+)\s+(?:patients|subjects|participants|individuals|cases|controls|samples|enrolled)",
                "count of",
            ),
        ]

        def _extract_n_values(text: str) -> dict[str, set[str]]:
            """Extract N-values grouped by pattern type."""
            result: dict[str, set[str]] = {}
            for pattern, label in n_patterns:
                values = set(re.findall(pattern, text, re.IGNORECASE))
                if values:
                    result[label] = values
            return result

        # Find Methods section (source of truth)
        methods_key = None
        for key in sections:
            if re.match(r"(?:materials?\s+and\s+)?methods", key, re.IGNORECASE):
                methods_key = key
                break

        if methods_key is None:
            return HookResult(
                hook_id="C3",
                passed=True,
                stats={"note": "No Methods section found, skipping N-value check"},
            )

        methods_n = _extract_n_values(sections[methods_key])
        all_methods_values: set[str] = set()
        for vals in methods_n.values():
            all_methods_values |= vals

        if not all_methods_values:
            return HookResult(
                hook_id="C3",
                passed=True,
                stats={"note": "No N-values found in Methods"},
            )

        inconsistencies = 0
        for sec_name, sec_text in sections.items():
            if sec_name == methods_key:
                continue
            sec_n = _extract_n_values(sec_text)
            for label, values in sec_n.items():
                for val in values:
                    if val not in all_methods_values and int(val) > 1:
                        inconsistencies += 1
                        issues.append(
                            HookIssue(
                                hook_id="C3",
                                severity="CRITICAL",
                                section=sec_name,
                                message=(
                                    f"N-value {label}{val} in {sec_name} "
                                    f"not found in Methods (Methods has: {sorted(all_methods_values)})"
                                ),
                                suggestion=f"Verify {label}{val} is correct or add to Methods",
                            )
                        )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "methods_n_values": sorted(all_methods_values),
            "sections_checked": len(sections) - 1,
            "inconsistencies": inconsistencies,
        }

        logger.info("Hook C3 complete", passed=passed, inconsistencies=inconsistencies)
        return HookResult(hook_id="C3", passed=passed, issues=issues, stats=stats)

    # ── Hook C4: Abbreviation First-Use Definition ─────────────────

    def check_abbreviation_first_use(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C4: Verify abbreviations are defined at first use.

        Scans for uppercase abbreviations (2+ letters) and checks that each
        is defined with its full form before or at first occurrence.
        Common medical/statistical abbreviations are excluded.
        """
        issues: list[HookIssue] = []

        # Find all abbreviations (2+ uppercase letters)
        all_abbrs = re.findall(r"\b([A-Z]{2,})\b", content)
        if not all_abbrs:
            return HookResult(
                hook_id="C4",
                passed=True,
                stats={"abbreviations_found": 0},
            )

        # Deduplicate, preserving order of first appearance
        seen: set[str] = set()
        unique_abbrs: list[str] = []
        for abbr in all_abbrs:
            if abbr not in seen and abbr not in COMMON_ABBREVIATIONS:
                seen.add(abbr)
                unique_abbrs.append(abbr)

        defined: list[str] = []
        undefined: list[str] = []

        for abbr in unique_abbrs:
            # Check for definition pattern: "Full Name (ABBR)" before or at first use
            # Pattern: any words followed by (ABBR) — within 200 chars before first occurrence
            first_pos = content.find(abbr)
            if first_pos == -1:
                continue

            # Look for "(ABBR)" near the first occurrence — the definition pattern
            definition_pattern = rf"\b[\w\s]{{3,}}\({re.escape(abbr)}\)"
            context_start = max(0, first_pos - 200)
            context_end = min(len(content), first_pos + len(abbr) + 50)
            context = content[context_start:context_end]

            if re.search(definition_pattern, context):
                defined.append(abbr)
            else:
                undefined.append(abbr)
                issues.append(
                    HookIssue(
                        hook_id="C4",
                        severity="WARNING",
                        section="manuscript",
                        message=f"Abbreviation '{abbr}' used without definition at first occurrence",
                        suggestion=f"Add 'Full Name ({abbr})' at first use",
                    )
                )

        passed = len(issues) == 0
        stats = {
            "abbreviations_found": len(unique_abbrs),
            "defined_count": len(defined),
            "undefined_count": len(undefined),
            "undefined": undefined[:10],  # Cap for readability
        }

        logger.info("Hook C4 complete", passed=passed, undefined=len(undefined))
        return HookResult(hook_id="C4", passed=passed, issues=issues, stats=stats)

    # ── Hook C5: Wikilink Resolvable ───────────────────────────────

    def check_wikilink_resolvable(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C5: Verify all wikilinks resolve to saved references.

        Checks that every [[wikilink]] in the draft has a corresponding
        reference directory under references/.
        """
        issues: list[HookIssue] = []

        all_wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)
        if not all_wikilinks:
            return HookResult(
                hook_id="C5",
                passed=True,
                stats={"total_wikilinks": 0, "resolved": 0, "unresolved": 0},
            )

        refs_dir = self._project_dir / "references"
        existing_refs: set[str] = set()
        if refs_dir.is_dir():
            for d in refs_dir.iterdir():
                if d.is_dir():
                    existing_refs.add(d.name)

        resolved = 0
        unresolved = 0

        for wl in all_wikilinks:
            # Try to match against reference directory names
            if wl in existing_refs:
                resolved += 1
            else:
                # Try extracting PMID and matching
                pmid_match = re.search(r"(\d{7,8})", wl)
                if pmid_match:
                    pmid = pmid_match.group(1)
                    if any(pmid in ref_name for ref_name in existing_refs):
                        resolved += 1
                        continue
                unresolved += 1
                issues.append(
                    HookIssue(
                        hook_id="C5",
                        severity="CRITICAL",
                        section="manuscript",
                        message=f"Wikilink [[{wl}]] cannot be resolved to a saved reference",
                        suggestion="Save this reference with save_reference_mcp or fix the wikilink",
                    )
                )

        passed = unresolved == 0
        stats = {
            "total_wikilinks": len(all_wikilinks),
            "resolved": resolved,
            "unresolved": unresolved,
        }

        logger.info("Hook C5 complete", passed=passed, unresolved=unresolved)
        return HookResult(hook_id="C5", passed=passed, issues=issues, stats=stats)

    # ── Hook C6: Total Word Count ──────────────────────────────────

    def check_total_word_count(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C6: Check total manuscript word count against journal limit.

        Excludes the References section from the count.
        """
        issues: list[HookIssue] = []

        limit = self._get_total_word_limit()
        if limit is None:
            return HookResult(
                hook_id="C6",
                passed=True,
                stats={"note": "No total word limit configured"},
            )

        # Strip References section
        stripped = re.split(r"\n#{1,2}\s+References\b", content, flags=re.IGNORECASE)[0]
        total_words = self._count_words(stripped)

        deviation_pct = ((total_words - limit) / limit) * 100 if limit > 0 else 0

        if deviation_pct > 20:
            severity = "CRITICAL"
        elif deviation_pct > 10:
            severity = "WARNING"
        else:
            severity = None

        if severity:
            issues.append(
                HookIssue(
                    hook_id="C6",
                    severity=severity,
                    section="manuscript",
                    message=f"Total word count {total_words} exceeds limit {limit} by {deviation_pct:.0f}%",
                    suggestion="Trim the longest section(s) to meet the word limit",
                )
            )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "total_words": total_words,
            "limit": limit,
            "deviation_pct": round(deviation_pct, 1),
            "excludes_references": True,
        }

        logger.info("Hook C6 complete", passed=passed, total_words=total_words, limit=limit)
        return HookResult(hook_id="C6", passed=passed, issues=issues, stats=stats)

    # ── Hook C7a: Figure/Table Count Limits ────────────────────────

    def check_figure_table_counts(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C7a: Check figure and table counts against journal limits.
        """
        issues: list[HookIssue] = []

        fig_limit, tbl_limit = self._get_figure_table_limits()
        if fig_limit is None and tbl_limit is None:
            return HookResult(
                hook_id="C7a",
                passed=True,
                stats={"note": "No figure/table limits configured"},
            )

        # Count distinct references in text
        fig_refs = set(re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE))
        tbl_refs = set(re.findall(r"Table\s+(\d+)", content, re.IGNORECASE))

        # Also check manifest if it exists
        manifest_path = self._project_dir / "results" / "manifest.json"
        if manifest_path.is_file():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                manifest_figs = {
                    a["id"] for a in manifest.get("assets", []) if a.get("type") == "figure"
                }
                manifest_tbls = {
                    a["id"] for a in manifest.get("assets", []) if a.get("type") == "table"
                }
                fig_count = max(len(fig_refs), len(manifest_figs))
                tbl_count = max(len(tbl_refs), len(manifest_tbls))
            except Exception:
                fig_count = len(fig_refs)
                tbl_count = len(tbl_refs)
        else:
            fig_count = len(fig_refs)
            tbl_count = len(tbl_refs)

        if fig_limit is not None and fig_count > fig_limit:
            issues.append(
                HookIssue(
                    hook_id="C7a",
                    severity="WARNING",
                    section="manuscript",
                    message=f"Figure count ({fig_count}) exceeds limit ({fig_limit})",
                    suggestion="Move excess figures to supplementary materials",
                )
            )

        if tbl_limit is not None and tbl_count > tbl_limit:
            issues.append(
                HookIssue(
                    hook_id="C7a",
                    severity="WARNING",
                    section="manuscript",
                    message=f"Table count ({tbl_count}) exceeds limit ({tbl_limit})",
                    suggestion="Move excess tables to supplementary materials",
                )
            )

        passed = len(issues) == 0
        stats = {
            "figure_count": fig_count,
            "table_count": tbl_count,
            "figure_limit": fig_limit,
            "table_limit": tbl_limit,
        }

        logger.info("Hook C7a complete", passed=passed, figs=fig_count, tbls=tbl_count)
        return HookResult(hook_id="C7a", passed=passed, issues=issues, stats=stats)

    # ── Hook C7d: Orphan/Phantom Cross-References ──────────────────

    def check_cross_references(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C7d: Detect orphan and phantom figure/table cross-references.

        - Phantom: referenced in text but not in manifest (CRITICAL)
        - Orphan: in manifest but not referenced in text (WARNING)
        """
        issues: list[HookIssue] = []

        # Extract references from text
        fig_refs = set(re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE))
        tbl_refs = set(re.findall(r"Table\s+(\d+)", content, re.IGNORECASE))

        manifest_path = self._project_dir / "results" / "manifest.json"
        if not manifest_path.is_file():
            # Without manifest, we can only report what's in the text
            return HookResult(
                hook_id="C7d",
                passed=True,
                stats={
                    "note": "No manifest.json found",
                    "text_figure_refs": sorted(fig_refs),
                    "text_table_refs": sorted(tbl_refs),
                },
            )

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception:
            return HookResult(
                hook_id="C7d",
                passed=True,
                stats={"note": "Failed to read manifest.json"},
            )

        manifest_figs = {
            str(a.get("number", a.get("id", "")))
            for a in manifest.get("assets", [])
            if a.get("type") == "figure"
        }
        manifest_tbls = {
            str(a.get("number", a.get("id", "")))
            for a in manifest.get("assets", [])
            if a.get("type") == "table"
        }

        # Phantom: in text but not in manifest
        phantom_figs = fig_refs - manifest_figs
        phantom_tbls = tbl_refs - manifest_tbls

        for f in phantom_figs:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="CRITICAL",
                    section="manuscript",
                    message=f"Phantom: Figure {f} referenced in text but not in manifest",
                    suggestion=f"Add Figure {f} to manifest or remove from text",
                )
            )
        for t in phantom_tbls:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="CRITICAL",
                    section="manuscript",
                    message=f"Phantom: Table {t} referenced in text but not in manifest",
                    suggestion=f"Add Table {t} to manifest or remove from text",
                )
            )

        # Orphan: in manifest but not in text
        orphan_figs = manifest_figs - fig_refs
        orphan_tbls = manifest_tbls - tbl_refs

        for f in orphan_figs:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="WARNING",
                    section="manifest",
                    message=f"Orphan: Figure {f} in manifest but not referenced in text",
                    suggestion=f"Add Figure {f} reference to text or remove from manifest",
                )
            )
        for t in orphan_tbls:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="WARNING",
                    section="manifest",
                    message=f"Orphan: Table {t} in manifest but not referenced in text",
                    suggestion=f"Add Table {t} reference to text or remove from manifest",
                )
            )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "phantom_count": len(phantom_figs) + len(phantom_tbls),
            "orphan_count": len(orphan_figs) + len(orphan_tbls),
            "text_figure_refs": sorted(fig_refs),
            "text_table_refs": sorted(tbl_refs),
            "manifest_figures": sorted(manifest_figs),
            "manifest_tables": sorted(manifest_tbls),
        }

        logger.info(
            "Hook C7d complete",
            passed=passed,
            phantoms=stats["phantom_count"],
            orphans=stats["orphan_count"],
        )
        return HookResult(hook_id="C7d", passed=passed, issues=issues, stats=stats)

    # ── Hook P5: Protected Content ─────────────────────────────────

    def check_protected_content(
        self,
        concept_path: Path | None = None,
    ) -> HookResult:
        """
        Hook P5: Verify 🔒-marked blocks in concept.md are non-empty.
        """
        issues: list[HookIssue] = []

        if concept_path is None:
            concept_path = self._project_dir / "concept.md"

        if not concept_path.is_file():
            return HookResult(
                hook_id="P5",
                passed=True,
                stats={"note": "No concept.md found"},
            )

        try:
            concept_text = concept_path.read_text(encoding="utf-8")
        except Exception:
            return HookResult(
                hook_id="P5",
                passed=True,
                stats={"note": "Failed to read concept.md"},
            )

        # Find 🔒-marked headings
        protected_blocks: list[tuple[str, str]] = []
        lines = concept_text.split("\n")
        current_heading: str | None = None
        current_content: list[str] = []

        for line in lines:
            heading_match = re.match(r"^#{1,3}\s+(.+)", line)
            if heading_match:
                if current_heading is not None:
                    protected_blocks.append((current_heading, "\n".join(current_content).strip()))
                heading_text = heading_match.group(1).strip()
                if "\U0001f512" in heading_text:  # 🔒
                    current_heading = heading_text
                    current_content = []
                else:
                    current_heading = None
                    current_content = []
            elif current_heading is not None:
                current_content.append(line)

        # Don't forget last block
        if current_heading is not None:
            protected_blocks.append((current_heading, "\n".join(current_content).strip()))

        empty_blocks: list[str] = []
        for heading, block_content in protected_blocks:
            # Check if content is empty or just placeholder text
            stripped = re.sub(r"\[.*?\]", "", block_content).strip()
            stripped = re.sub(r">\s*\[.*?\]", "", stripped).strip()
            stripped = re.sub(r"^[-*]\s*$", "", stripped, flags=re.MULTILINE).strip()

            if not stripped:
                empty_blocks.append(heading)
                issues.append(
                    HookIssue(
                        hook_id="P5",
                        severity="CRITICAL",
                        section="concept.md",
                        message=f"Protected block '{heading}' is empty or only has placeholder text",
                        suggestion=f"Fill in the content for '{heading}' before proceeding",
                    )
                )

        passed = len(empty_blocks) == 0
        stats = {
            "protected_blocks_found": len(protected_blocks),
            "non_empty_count": len(protected_blocks) - len(empty_blocks),
            "empty_blocks": empty_blocks,
        }

        logger.info(
            "Hook P5 complete", passed=passed, blocks=len(protected_blocks), empty=len(empty_blocks)
        )
        return HookResult(hook_id="P5", passed=passed, issues=issues, stats=stats)

    # ── Hook P7: Reference Integrity ───────────────────────────────

    def check_reference_integrity(
        self,
        content: str | None = None,
    ) -> HookResult:
        """
        Hook P7: Verify saved references have VERIFIED status.

        Optionally checks that wikilinks in content map to reference dirs.
        """
        issues: list[HookIssue] = []

        refs_dir = self._project_dir / "references"
        if not refs_dir.is_dir():
            return HookResult(
                hook_id="P7",
                passed=True,
                stats={"note": "No references directory found"},
            )

        total_refs = 0
        verified_count = 0
        unverified_refs: list[str] = []

        for ref_dir in sorted(refs_dir.iterdir()):
            if not ref_dir.is_dir():
                continue
            total_refs += 1
            metadata_path = ref_dir / "metadata.json"
            if not metadata_path.is_file():
                unverified_refs.append(ref_dir.name)
                continue
            try:
                with open(metadata_path) as f:
                    meta = json.load(f)
                data_source = meta.get("_data_source", "")
                if data_source == "pubmed_api" or meta.get("verified", False):
                    verified_count += 1
                else:
                    unverified_refs.append(ref_dir.name)
            except Exception:
                unverified_refs.append(ref_dir.name)

        for ref_name in unverified_refs:
            issues.append(
                HookIssue(
                    hook_id="P7",
                    severity="WARNING",
                    section="references",
                    message=f"Reference '{ref_name}' is not verified (not from PubMed API)",
                    suggestion="Re-save with save_reference_mcp for verified metadata",
                )
            )

        passed = len(issues) == 0
        stats = {
            "total_refs": total_refs,
            "verified_count": verified_count,
            "unverified_count": len(unverified_refs),
            "unverified_refs": unverified_refs[:10],
        }

        logger.info("Hook P7 complete", passed=passed, verified=verified_count, total=total_refs)
        return HookResult(hook_id="P7", passed=passed, issues=issues, stats=stats)

    # ── Batch runners (convenience) ───────────────────────────────

    def run_post_write_hooks(
        self,
        content: str,
        section: str = "manuscript",
        prefer_language: str = "american",
    ) -> dict[str, HookResult]:
        """
        Run all post-write hooks (A1-A6) on a section.

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        return {
            "A1": self.check_word_count_compliance(content, section_name=section),
            "A2": self.check_citation_density(content, section_name=section),
            "A3": self.check_anti_ai_patterns(content, section=section),
            "A4": self.check_wikilink_format(content, section=section),
            "A5": self.check_language_consistency(content, prefer=prefer_language, section=section),
            "A6": self.check_overlap(content),
        }

    def run_post_section_hooks(
        self,
        methods_content: str,
        results_content: str,
    ) -> dict[str, HookResult]:
        """
        Run post-section hooks (B8) — only applies when both Methods and Results exist.

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        return {
            "B8": self.check_data_claim_alignment(methods_content, results_content),
        }

    def run_post_manuscript_hooks(
        self,
        content: str,
    ) -> dict[str, HookResult]:
        """
        Run all post-manuscript hooks (C3, C4, C5, C6, C7a, C7d, C9, F) on the full manuscript.

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        return {
            "C3": self.check_n_value_consistency(content),
            "C4": self.check_abbreviation_first_use(content),
            "C5": self.check_wikilink_resolvable(content),
            "C6": self.check_total_word_count(content),
            "C7a": self.check_figure_table_counts(content),
            "C7d": self.check_cross_references(content),
            "C9": self.check_supplementary_crossref(content),
            "F": self.validate_data_artifacts(content),
        }

    def run_precommit_hooks(
        self,
        content: str,
        prefer_language: str = "american",
    ) -> dict[str, HookResult]:
        """
        Run all pre-commit hooks (P1, P2, P4, P5, P7).

        P1 delegates to C5 (wikilink resolvable).
        P2 delegates to A3 (anti-AI, with P2 thresholds).
        P4 delegates to A1 (word count, with 50% critical threshold).

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        # P1: Citation integrity — delegate to C5 with hook_id remap
        p1_result = self.check_wikilink_resolvable(content)
        p1_result.hook_id = "P1"
        for issue in p1_result.issues:
            issue.hook_id = "P1"

        # P2: Anti-AI scan — delegate to A3 with P2 thresholds
        p2_result = self.check_anti_ai_patterns(
            content,
            section="precommit",
            warn_threshold=1,
            critical_threshold=3,
        )
        p2_result.hook_id = "P2"
        for issue in p2_result.issues:
            issue.hook_id = "P2"

        # P4: Word count — delegate to A1 with 50% critical threshold
        p4_result = self.check_word_count_compliance(content, critical_threshold_pct=50)
        p4_result.hook_id = "P4"
        for issue in p4_result.issues:
            issue.hook_id = "P4"

        return {
            "P1": p1_result,
            "P2": p2_result,
            "P4": p4_result,
            "P5": self.check_protected_content(),
            "P7": self.check_reference_integrity(content),
        }
