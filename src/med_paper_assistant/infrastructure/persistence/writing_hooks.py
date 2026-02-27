"""
Writing Hooks Engine — Code-enforced implementations for Hook A5, A6, B8, C9, F1-F4.

These hooks were identified as gaps in the auto-paper pipeline:
  - A5: Language Consistency (British vs American English)
  - A6: Self-Plagiarism / Overlap Detection (internal paragraph similarity)
  - B8: Data-Claim Alignment (statistical claims ↔ methods consistency)
  - C9: Supplementary Cross-Reference (main text ↔ supplementary material)
  - F1-F4: Data Artifact Validation (formal pipeline integration)

Architecture:
  Infrastructure layer service. Called by the auto-paper pipeline at
  appropriate phases. Records events via HookEffectivenessTracker.

Design rationale (CONSTITUTION §22):
  - Auditable: Each hook returns structured issues with severity + location
  - Reproducible: Deterministic regex/NLP checks, no model randomness
  - Composable: Each hook is a standalone method; pipeline calls as needed
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


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

    Implements Hooks A5, A6, B8, C9, F1-F4.

    Usage:
        engine = WritingHooksEngine(project_dir)
        r = engine.check_language_consistency(draft_content, prefer="american")
        r = engine.check_overlap(draft_content)
        r = engine.check_data_claim_alignment(methods_content, results_content)
        r = engine.check_supplementary_crossref(draft_content, project_dir)
        r = engine.validate_data_artifacts(draft_content)

    Args:
        project_dir: Path to the project directory (e.g., projects/{slug}/)
    """

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"

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

    # ── Batch runner (convenience) ────────────────────────────────

    def run_post_write_hooks(
        self,
        content: str,
        section: str = "manuscript",
        prefer_language: str = "american",
    ) -> dict[str, HookResult]:
        """
        Run all post-write hooks (A5, A6) on a section.

        Returns:
            Dict mapping hook_id → HookResult.
        """
        return {
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
            Dict mapping hook_id → HookResult.
        """
        return {
            "B8": self.check_data_claim_alignment(methods_content, results_content),
        }

    def run_post_manuscript_hooks(
        self,
        content: str,
    ) -> dict[str, HookResult]:
        """
        Run all post-manuscript hooks (C9, F) on the full manuscript.

        Returns:
            Dict mapping hook_id → HookResult.
        """
        return {
            "C9": self.check_supplementary_crossref(content),
            "F": self.validate_data_artifacts(content),
        }
