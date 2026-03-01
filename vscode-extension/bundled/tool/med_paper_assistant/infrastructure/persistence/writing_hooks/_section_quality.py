"""Writing Hooks — Section-quality hooks mixin (B-series: B8–B16)."""

from __future__ import annotations

import re
from typing import Any

import structlog

from ._models import HookIssue, HookResult

logger = structlog.get_logger()


class SectionQualityMixin:
    """B-series hooks: post-section quality checks."""

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
        alpha_methods = set(
            re.findall(
                r"(?:significance|alpha|α)\s*(?:level)?\s*(?:of|=|:)?\s*(0\.\d+)", methods_lower
            )
        )
        p_thresholds_results = set(re.findall(r"p\s*[<>]\s*(0\.\d+)", results_lower))

        if alpha_methods and p_thresholds_results:
            for threshold in p_thresholds_results:
                if threshold not in alpha_methods:
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

    # ── Hook B9: Section Tense Consistency ─────────────────────────

    def check_section_tense(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook B9: Verify verb tense matches section conventions.

        Scientific writing convention:
        - Methods / Results → past tense
        - Introduction / Discussion → present tense for established facts
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {"section": section, "present_verbs": 0, "past_verbs": 0}

        sec_lower = section.lower()

        present_study_verbs = re.compile(
            r"\b(?:we\s+(?:measure|analyze|collect|record|assess|evaluate|perform|conduct"
            r"|administer|randomize|enroll|recruit|include|exclude|calculate|compare"
            r"|observe|monitor|determine|identify|classify|divide|assign|screen"
            r"|select|extract|obtain|gather|test|examine|sample|survey))\b",
            re.IGNORECASE,
        )

        results_present_patterns = re.compile(
            r"(?:^|\.\s+)(?:The\s+(?:result|data|analysis|finding|outcome|difference|comparison)"
            r"\s+(?:show|indicate|demonstrate|reveal|suggest|confirm|yield)s?\b)",
            re.IGNORECASE,
        )

        if sec_lower in ("methods", "materials and methods", "study design"):
            matches = present_study_verbs.findall(content)
            stats["present_verbs"] = len(matches)
            if matches:
                unique = set(m.lower() for m in matches)
                issues.append(
                    HookIssue(
                        hook_id="B9",
                        severity="CRITICAL" if len(matches) >= 3 else "WARNING",
                        section=section,
                        message=f"Methods should use past tense. Found {len(matches)} present-tense study verb(s): {', '.join(list(unique)[:5])}",
                        suggestion="Change to past tense (e.g., 'we measured', 'patients received')",
                    )
                )

        elif sec_lower in ("results",):
            we_present = present_study_verbs.findall(content)
            data_present = results_present_patterns.findall(content)
            total = len(we_present) + len(data_present)
            stats["present_verbs"] = total
            if total:
                issues.append(
                    HookIssue(
                        hook_id="B9",
                        severity="CRITICAL" if total >= 3 else "WARNING",
                        section=section,
                        message=f"Results should use past tense. Found {total} present-tense verb(s)",
                        suggestion="Change to past tense (e.g., 'showed', 'demonstrated', 'was observed')",
                    )
                )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B9", passed=passed, issues=issues, stats=stats)

    # ── Hook B10: Paragraph Quality ────────────────────────────────

    def check_paragraph_quality(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook B10: Check paragraph structure quality.

        Checks paragraph length (too short / too long) and single-sentence paragraphs.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {"total_paragraphs": 0, "too_short": 0, "too_long": 0}

        paragraphs: list[str] = []
        current: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                if current:
                    paragraphs.append("\n".join(current))
                    current = []
                continue
            if not stripped:
                if current:
                    paragraphs.append("\n".join(current))
                    current = []
            else:
                current.append(line)
        if current:
            paragraphs.append("\n".join(current))

        stats["total_paragraphs"] = len(paragraphs)

        for i, para in enumerate(paragraphs, 1):
            text = para.strip()
            if not text or text.startswith("|") or text.startswith("- "):
                continue

            word_count = self._count_words(text)
            sentences = re.split(r"[.!?]+\s+|[.!?]+$", text)
            sentences = [s for s in sentences if s.strip()]
            n_sentences = len(sentences)

            if word_count > 250:
                stats["too_long"] = stats.get("too_long", 0) + 1
                issues.append(
                    HookIssue(
                        hook_id="B10",
                        severity="WARNING",
                        section=section,
                        message=f"Paragraph {i} is very long ({word_count} words, {n_sentences} sentences). Consider splitting.",
                        location=text[:80] + "...",
                        suggestion="Split into smaller paragraphs, each focused on one idea",
                    )
                )

            if n_sentences <= 1 and word_count > 10:
                if section.lower() not in ("results",):
                    stats["too_short"] = stats.get("too_short", 0) + 1
                    issues.append(
                        HookIssue(
                            hook_id="B10",
                            severity="INFO",
                            section=section,
                            message=f"Paragraph {i} has only 1 sentence. Consider merging or expanding.",
                            location=text[:80],
                            suggestion="Develop the idea further or merge with adjacent paragraph",
                        )
                    )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B10", passed=passed, issues=issues, stats=stats)

    # ── Hook B11: Results Interpretive Language Guard ──────────────

    def check_results_interpretation(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B11: Detect interpretive/speculative language in Results.

        Results section should present data objectively without interpretation.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {"interpretive_count": 0}

        sections = self._parse_sections(content)
        results_text = ""
        for name, text in sections.items():
            if name.lower().startswith("result"):
                results_text = text
                break

        if not results_text:
            return HookResult(hook_id="B11", passed=True, issues=issues, stats=stats)

        interpretive_patterns = [
            (r"\bsuggesting\s+(?:that|a|an|the)\b", "suggesting that..."),
            (r"\bindicating\s+(?:that|a|an|the)\b", "indicating that..."),
            (r"\bdemonstrating\s+(?:that|a|an|the)\b", "demonstrating that..."),
            (r"\bimplying\s+(?:that|a|an|the)\b", "implying that..."),
            (
                r"\bthis\s+(?:suggests|indicates|implies|demonstrates)\b",
                "this suggests/indicates...",
            ),
            (
                r"\b(?:may|might|could)\s+(?:be|have|suggest|indicate|reflect|represent)\b",
                "may/might/could (speculative)",
            ),
            (r"\bpossibly\b", "possibly"),
            (r"\bpresumably\b", "presumably"),
            (r"\bapparently\b", "apparently"),
            (r"\binterestingly\b", "interestingly"),
            (r"\bsurprisingly\b", "surprisingly"),
            (r"\bremarkably\b", "remarkably"),
            (r"\bunexpectedly\b", "unexpectedly"),
            (
                r"\b(?:it is|these are)\s+(?:likely|possible|probable|plausible)\b",
                "it is likely/possible...",
            ),
            (
                r"\bthis (?:finding|result|observation)\s+(?:is consistent with|supports|corroborates)\b",
                "this finding supports... (belongs in Discussion)",
            ),
            (
                r"\b(?:we believe|we speculate|we hypothesize|in our opinion)\b",
                "we believe/speculate (opinion)",
            ),
        ]

        found_items: list[str] = []
        for pattern, label in interpretive_patterns:
            matches = re.findall(pattern, results_text, re.IGNORECASE)
            if matches:
                found_items.extend([label] * len(matches))

        stats["interpretive_count"] = len(found_items)

        if found_items:
            unique_labels = list(dict.fromkeys(found_items))
            severity = "CRITICAL" if len(found_items) >= 5 else "WARNING"
            issues.append(
                HookIssue(
                    hook_id="B11",
                    severity=severity,
                    section="Results",
                    message=f"Results contains {len(found_items)} interpretive/speculative phrase(s): {', '.join(unique_labels[:6])}",
                    suggestion="Move interpretation to Discussion. Results should only state observed data and statistical outcomes.",
                )
            )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B11", passed=passed, issues=issues, stats=stats)

    # ── Hook B12: Introduction Funnel Structure ────────────────────

    def check_intro_structure(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B12: Verify Introduction follows the funnel structure.

        Expected: (1) Broad context → (2) Evidence with citations →
        (3) Knowledge gap → (4) Study objective.
        Also checks: no results preview in Introduction.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        sections = self._parse_sections(content)
        intro_text = ""
        for name, text in sections.items():
            if name.lower().startswith("introduction"):
                intro_text = text
                break

        if not intro_text:
            return HookResult(hook_id="B12", passed=True, issues=issues, stats=stats)

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", intro_text) if p.strip()]
        paragraphs = [p for p in paragraphs if not p.startswith("|") and not p.startswith("- ")]
        stats["paragraph_count"] = len(paragraphs)

        if len(paragraphs) < 3:
            issues.append(
                HookIssue(
                    hook_id="B12",
                    severity="WARNING",
                    section="Introduction",
                    message=f"Introduction has only {len(paragraphs)} paragraph(s). Typically needs ≥3 for proper funnel structure.",
                    suggestion="Structure: (1) Broad context → (2) Evidence with citations → (3) Gap → (4) Objective",
                )
            )

        # Check: last paragraph should contain objective markers
        if paragraphs:
            last_para = paragraphs[-1].lower()
            objective_markers = [
                r"\b(?:aim|objective|purpose|goal)\s+(?:of|was|is)\b",
                r"\bwe\s+(?:aimed|sought|investigated|hypothesized|examined)\b",
                r"\bthis\s+study\s+(?:aimed|sought|examined|investigated|evaluated)\b",
                r"\bthe\s+(?:aim|objective|purpose)\b",
                r"\bherein\b",
                r"\bpresent\s+study\b",
                r"\bto\s+(?:evaluate|investigate|examine|assess|determine|compare|explore)\b",
            ]
            has_objective = any(re.search(p, last_para) for p in objective_markers)
            stats["has_objective"] = has_objective
            if not has_objective:
                issues.append(
                    HookIssue(
                        hook_id="B12",
                        severity="WARNING",
                        section="Introduction",
                        message="Last paragraph of Introduction should state the study objective/aim",
                        suggestion="Add a clear objective statement: 'This study aimed to...' or 'We sought to...'",
                    )
                )

        # Check: gap/limitation markers
        if len(paragraphs) >= 2:
            gap_zone = (
                " ".join(p.lower() for p in paragraphs[-3:])
                if len(paragraphs) >= 3
                else paragraphs[-1].lower()
            )
            gap_markers = [
                r"\b(?:however|nevertheless|yet|despite|although)\b",
                r"\b(?:gap|limitation|lacking|unknown|unclear|understudied|unexplored)\b",
                r"\b(?:no\s+(?:study|data|evidence|report)|remains?\s+(?:unclear|unknown|elusive))\b",
                r"\b(?:limited|scarce|sparse|insufficient)\s+(?:data|evidence|information|research)\b",
                r"\b(?:has|have)\s+not\s+been\s+(?:studied|examined|explored|investigated)\b",
            ]
            has_gap = any(re.search(p, gap_zone) for p in gap_markers)
            stats["has_gap_statement"] = has_gap
            if not has_gap:
                issues.append(
                    HookIssue(
                        hook_id="B12",
                        severity="WARNING",
                        section="Introduction",
                        message="Introduction should identify a knowledge gap or limitation of prior work",
                        suggestion="Add gap language: 'However, no study has...', 'It remains unclear whether...'",
                    )
                )

        # Check: no results preview in Introduction
        results_preview_patterns = [
            r"\bour\s+(?:results|findings|data)\s+(?:show|demonstrate|reveal|indicate)\b",
            r"\bwe\s+(?:found|observed|demonstrated|showed)\s+(?:that|a|an|the|significant)\b",
            r"\bthe\s+results?\s+(?:of|from)\s+(?:this|our|the\s+(?:present|current))\s+study\b",
        ]
        for pattern in results_preview_patterns:
            if re.search(pattern, intro_text, re.IGNORECASE):
                issues.append(
                    HookIssue(
                        hook_id="B12",
                        severity="CRITICAL",
                        section="Introduction",
                        message="Introduction should NOT preview study results",
                        suggestion="Remove results from Introduction. Results belong in the Results section.",
                    )
                )
                break

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B12", passed=passed, issues=issues, stats=stats)

    # ── Hook B13: Discussion Structure Completeness ────────────────

    def check_discussion_structure(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B13: Verify Discussion has required structural components.

        Required: main findings, literature comparison, limitations (CRITICAL),
        implications. Limitations is CRITICAL if missing.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        sections = self._parse_sections(content)
        discussion_text = ""
        for name, text in sections.items():
            if name.lower().startswith("discussion"):
                discussion_text = text
                break

        if not discussion_text:
            return HookResult(hook_id="B13", passed=True, issues=issues, stats=stats)

        disc_lower = discussion_text.lower()
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", discussion_text) if p.strip()]
        paragraphs = [p for p in paragraphs if not p.startswith("|")]
        stats["paragraph_count"] = len(paragraphs)

        # 1. Main findings mentioned early
        first_para = paragraphs[0].lower() if paragraphs else ""
        findings_markers = [
            r"\b(?:main|principal|key|major|primary|important)\s+(?:finding|result|outcome)\b",
            r"\b(?:our|this|the\s+present)\s+study\s+(?:found|showed|demonstrated|revealed)\b",
            r"\b(?:we\s+(?:found|observed|demonstrated))\b",
            r"\bto\s+(?:our|the)\s+(?:best\s+of\s+)?knowledge\b",
        ]
        has_main_finding = any(re.search(p, first_para) for p in findings_markers)
        stats["has_main_finding"] = has_main_finding
        if not has_main_finding and paragraphs:
            issues.append(
                HookIssue(
                    hook_id="B13",
                    severity="WARNING",
                    section="Discussion",
                    message="First paragraph should summarize the main findings",
                    suggestion="Start with: 'The main/principal finding of this study was...' or 'Our study demonstrated...'",
                )
            )

        # 2. Literature comparison (needs citations)
        citation_count = len(re.findall(r"\[\[[^\]]+\]\]", discussion_text))
        stats["citation_count"] = citation_count
        if citation_count < 3:
            issues.append(
                HookIssue(
                    hook_id="B13",
                    severity="WARNING",
                    section="Discussion",
                    message=f"Discussion has only {citation_count} citation(s). Should compare findings with prior literature.",
                    suggestion="Add comparisons: 'Consistent with Smith et al. [[ref]], we found...' or 'In contrast to...'",
                )
            )

        # 3. Limitations (CRITICAL if missing)
        limitation_markers = [
            r"\blimitation",
            r"\bweakness",
            r"\bshortcoming",
            r"\bdrawback",
            r"\bcaveat",
            r"\b(?:should|must)\s+be\s+interpreted\s+with\s+caution\b",
            r"\bseveral\s+(?:potential\s+)?limitations?\b",
        ]
        has_limitations = any(re.search(p, disc_lower) for p in limitation_markers)
        stats["has_limitations"] = has_limitations
        if not has_limitations:
            issues.append(
                HookIssue(
                    hook_id="B13",
                    severity="CRITICAL",
                    section="Discussion",
                    message="Discussion MUST contain a Limitations paragraph",
                    suggestion="Add: 'This study has several limitations. First, ...' Discuss design constraints, generalizability, etc.",
                )
            )

        # 4. Clinical/practical implications
        implication_markers = [
            r"\bimplication",
            r"\bclinical\s+(?:practice|significance|relevance|utility)\b",
            r"\bpractical\s+(?:implication|application|relevance)\b",
            r"\bfuture\s+(?:research|studies|investigation|direction)\b",
            r"\btranslational\b",
            r"\b(?:may|could)\s+(?:help|improve|enhance|facilitate|guide|inform)\b",
        ]
        has_implications = any(re.search(p, disc_lower) for p in implication_markers)
        stats["has_implications"] = has_implications
        if not has_implications:
            issues.append(
                HookIssue(
                    hook_id="B13",
                    severity="WARNING",
                    section="Discussion",
                    message="Discussion should mention clinical/practical implications or future directions",
                    suggestion="Add: 'These findings suggest that...' or 'Future studies should...'",
                )
            )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B13", passed=passed, issues=issues, stats=stats)

    # ── Hook B14: Ethical & Registration Statements ────────────────

    def check_ethical_statements(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B14: Verify presence of ethical approval and trial registration.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        content_lower = content.lower()

        # Check IRB / Ethics approval
        ethics_markers = [
            r"\b(?:irb|institutional\s+review\s+board)\b",
            r"\bethics\s+committee\b",
            r"\bethical\s+(?:approval|clearance|review)\b",
            r"\bapproved\s+by\b.*\b(?:committee|board|ethics)\b",
            r"\b(?:protocol|study)\s+was\s+approved\b",
            r"\bhuman\s+(?:subjects?|research)\s+(?:committee|protection)\b",
            r"\bdeclaration\s+of\s+helsinki\b",
        ]
        has_ethics = any(re.search(p, content_lower) for p in ethics_markers)
        stats["has_ethics_approval"] = has_ethics
        if not has_ethics:
            issues.append(
                HookIssue(
                    hook_id="B14",
                    severity="CRITICAL",
                    section="Methods",
                    message="No ethical approval statement found",
                    suggestion="Add: 'This study was approved by the Institutional Review Board of [institution] (approval no. XXX)'",
                )
            )

        # Check informed consent
        consent_markers = [
            r"\binformed\s+consent\b",
            r"\bwritten\s+consent\b",
            r"\bconsent\s+was\s+obtained\b",
            r"\bconsent\s+(?:form|process|procedure)\b",
            r"\bwaiver\s+of\s+(?:informed\s+)?consent\b",
            r"\bexempt(?:ed|ion)?\b.*\bconsent\b",
        ]
        has_consent = any(re.search(p, content_lower) for p in consent_markers)
        stats["has_informed_consent"] = has_consent
        if not has_consent:
            issues.append(
                HookIssue(
                    hook_id="B14",
                    severity="WARNING",
                    section="Methods",
                    message="No informed consent statement found",
                    suggestion="Add: 'Written informed consent was obtained from all participants' or 'The requirement for informed consent was waived due to...'",
                )
            )

        # Check trial registration (if interventional study)
        intervention_markers = [
            r"\brandom(?:ized|ised|ization|isation)\b",
            r"\bclinical\s+trial\b",
            r"\bintervention(?:al)?\b",
            r"\bplacebo\b",
            r"\btreatment\s+(?:arm|group)\b",
            r"\bcontrol\s+(?:arm|group)\b",
        ]
        is_interventional = any(re.search(p, content_lower) for p in intervention_markers)

        if is_interventional:
            registration_markers = [
                r"\b(?:NCT\d{8}|ISRCTN\d+|UMIN\d+|ACTRN\d+|ChiCTR\d+)\b",
                r"\b(?:clinicaltrials\.gov|trial\s+regist(?:ry|ration|ered))\b",
                r"\bregistered\s+(?:at|with|in)\b",
                r"\bregistration\s+(?:number|no\.?|#)\b",
            ]
            has_registration = any(re.search(p, content_lower) for p in registration_markers)
            stats["has_registration"] = has_registration
            stats["is_interventional"] = True
            if not has_registration:
                issues.append(
                    HookIssue(
                        hook_id="B14",
                        severity="CRITICAL",
                        section="Methods",
                        message="Interventional study detected but no trial registration found",
                        suggestion="Add trial registration number (e.g., NCT12345678) and registry name",
                    )
                )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B14", passed=passed, issues=issues, stats=stats)

    # ── Hook B15: Hedging Language Density ─────────────────────────

    def check_hedging_density(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook B15: Detect overuse of hedging / weak language.

        Thresholds: > 3 per 1000 words = WARNING, > 6 = CRITICAL.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        hedging_patterns = [
            r"\bmay\s+(?:be|have|suggest|indicate|play|contribute)\b",
            r"\bmight\s+(?:be|have|suggest|indicate|play|contribute)\b",
            r"\bcould\s+(?:be|have|suggest|indicate|play|contribute)\b",
            r"\bpossibly\b",
            r"\bpotentially\b",
            r"\bperhaps\b",
            r"\bseems?\s+to\b",
            r"\bappears?\s+to\b",
            r"\btends?\s+to\b",
            r"\bit\s+is\s+(?:possible|conceivable|plausible)\b",
            r"\bto\s+some\s+(?:extent|degree)\b",
            r"\bin\s+part\b",
            r"\brelatively\b",
            r"\bsomewhat\b",
        ]

        total_words = self._count_words(content)
        total_hedges = 0
        found_phrases: list[str] = []

        for pattern in hedging_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_hedges += len(matches)
            found_phrases.extend(matches)

        stats["hedge_count"] = total_hedges
        stats["words"] = total_words
        stats["density_per_1000"] = round(total_hedges * 1000 / max(total_words, 1), 1)

        if total_words > 100:
            density = total_hedges * 1000 / total_words
            if density > 6:
                issues.append(
                    HookIssue(
                        hook_id="B15",
                        severity="CRITICAL",
                        section=section,
                        message=f"Excessive hedging: {total_hedges} hedging phrases ({density:.1f}/1000 words). Weakens the manuscript.",
                        location="; ".join(list(dict.fromkeys(found_phrases))[:8]),
                        suggestion="Replace hedges with direct statements. E.g., 'may suggest' → 'suggests', 'could be' → 'is'",
                    )
                )
            elif density > 3:
                issues.append(
                    HookIssue(
                        hook_id="B15",
                        severity="WARNING",
                        section=section,
                        message=f"High hedging density: {total_hedges} hedging phrases ({density:.1f}/1000 words).",
                        location="; ".join(list(dict.fromkeys(found_phrases))[:8]),
                        suggestion="Consider strengthening some hedged statements with direct language",
                    )
                )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B15", passed=passed, issues=issues, stats=stats)

    # ── Hook B16: Effect Size & Statistical Reporting ──────────────

    def check_effect_size_reporting(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B16: Verify statistical reporting completeness.

        Modern standards require effect sizes, CI, exact p-values.
        No "p = 0.000" (should be p < 0.001).
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        sections = self._parse_sections(content)
        results_text = ""
        for name, text in sections.items():
            if name.lower().startswith("result"):
                results_text = text
                break

        if not results_text:
            return HookResult(hook_id="B16", passed=True, issues=issues, stats=stats)

        # Count p-values
        p_values = re.findall(r"p\s*[<=>\u2264\u2265]\s*[\d.]+", results_text, re.IGNORECASE)
        stats["p_value_count"] = len(p_values)

        # Check for "p = 0.000"
        p_zero = re.findall(r"p\s*=\s*0\.000\b", results_text, re.IGNORECASE)
        if p_zero:
            issues.append(
                HookIssue(
                    hook_id="B16",
                    severity="CRITICAL",
                    section="Results",
                    message=f"Found 'p = 0.000' ({len(p_zero)} occurrence(s)). This is statistically incorrect.",
                    suggestion="Use 'p < 0.001' instead of 'p = 0.000'",
                )
            )

        # Check for vague p-values
        vague_p = re.findall(r"p\s*<\s*0\.05\b", results_text, re.IGNORECASE)
        exact_p = re.findall(r"p\s*=\s*0\.\d+", results_text, re.IGNORECASE)
        stats["exact_p_count"] = len(exact_p)
        stats["vague_p_count"] = len(vague_p)

        if vague_p and not exact_p:
            issues.append(
                HookIssue(
                    hook_id="B16",
                    severity="WARNING",
                    section="Results",
                    message="Only vague p-values (p < 0.05) with no exact p-values reported",
                    suggestion="Report exact p-values (e.g., p = 0.032) alongside threshold comparisons",
                )
            )

        # Check for effect size measures
        effect_size_patterns = [
            r"\b(?:odds\s+ratio|OR)\s*[=:]\s*[\d.]+\b",
            r"\b(?:hazard\s+ratio|HR)\s*[=:]\s*[\d.]+\b",
            r"\b(?:relative\s+risk|risk\s+ratio|RR)\s*[=:]\s*[\d.]+\b",
            r"\b(?:mean\s+difference|MD)\s*[=:]\s*[\d.]+\b",
            r"\b(?:Cohen'?s?\s+d|effect\s+size)\s*[=:]\s*[\d.]+\b",
            r"\br²?\s*=\s*[\d.]+\b",
            r"\b(?:η²|eta\s*squared)\s*=\s*[\d.]+\b",
            r"\b(?:NNT|number\s+needed\s+to\s+treat)\s*[=:]\s*[\d.]+\b",
            r"\b(?:AUC|area\s+under)\s*[=:]\s*[\d.]+\b",
        ]
        effect_sizes_found = sum(
            len(re.findall(p, results_text, re.IGNORECASE)) for p in effect_size_patterns
        )
        stats["effect_size_count"] = effect_sizes_found

        # Check for CI alongside effect sizes
        ci_patterns = re.findall(
            r"\b(?:95%?\s*CI|confidence\s+interval)\s*[=:,]?\s*[\[(]?\s*[\d.]+\s*[-–]\s*[\d.]+",
            results_text,
            re.IGNORECASE,
        )
        stats["ci_count"] = len(ci_patterns)

        if len(p_values) >= 3 and effect_sizes_found == 0:
            issues.append(
                HookIssue(
                    hook_id="B16",
                    severity="WARNING",
                    section="Results",
                    message=f"Found {len(p_values)} p-values but no effect size measures",
                    suggestion="Report effect sizes (OR, HR, RR, Cohen's d, etc.) alongside p-values. Modern standards require both.",
                )
            )

        if effect_sizes_found > 0 and len(ci_patterns) == 0:
            issues.append(
                HookIssue(
                    hook_id="B16",
                    severity="WARNING",
                    section="Results",
                    message=f"Found {effect_sizes_found} effect size(s) but no confidence intervals",
                    suggestion="Report 95% CI alongside all effect sizes (e.g., OR = 2.3, 95% CI 1.2-4.5)",
                )
            )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B16", passed=passed, issues=issues, stats=stats)
