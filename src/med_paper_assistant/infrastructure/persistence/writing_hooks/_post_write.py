"""Writing Hooks — Post-write hooks mixin (A-series: A1–A6, A3b)."""

from __future__ import annotations

import re
from typing import Any

import structlog

from ._constants import (
    AI_TRANSITION_WORDS,
    AMER_VS_BRIT,
    ANTI_AI_PARAGRAPH_START_ONLY,
    ANTI_AI_PHRASES,
    BRIT_VS_AMER,
)
from ._models import HookIssue, HookResult

logger = structlog.get_logger()


class PostWriteHooksMixin:
    """A-series hooks: post-write quality checks on individual sections."""

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

    # ── Hook A3b: Structural AI Writing Signals ────────────────────

    def check_ai_writing_signals(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook A3b: Detect structural signals of AI-generated text.

        Goes beyond phrase matching (A3) to detect patterns that AI detectors
        like Gemini 3.1 flag: overly uniform sentence length, excessive
        transition words, low sentence-starter diversity, and formulaic
        list-of-three patterns.

        Args:
            content: Text to scan (full manuscript or section).
            section: Section name for reporting.
        """
        issues: list[HookIssue] = []

        # Strip markdown headings and reference wikilinks for prose analysis
        prose = re.sub(r"^#+\s.*$", "", content, flags=re.MULTILINE)
        prose = re.sub(r"\[\[[^\]]*\]\]", "", prose)
        prose = prose.strip()

        if len(prose) < 200:
            return HookResult(
                hook_id="A3b", passed=True, issues=[], stats={"skipped": True}
            )

        # ── 1. Sentence length uniformity (CV) ──
        sentences = [
            s.strip()
            for s in re.split(r"[.!?]+", prose)
            if len(s.strip().split()) >= 3
        ]
        sentence_lengths = [len(s.split()) for s in sentences]
        sent_cv = 0.0
        if len(sentence_lengths) >= 5:
            mean_len = sum(sentence_lengths) / len(sentence_lengths)
            if mean_len > 0:
                variance = sum((x - mean_len) ** 2 for x in sentence_lengths) / len(
                    sentence_lengths
                )
                std_dev = variance**0.5
                sent_cv = std_dev / mean_len

            if sent_cv < 0.25:
                issues.append(
                    HookIssue(
                        hook_id="A3b",
                        severity="WARNING",
                        section=section,
                        message=f"Sentence lengths too uniform (CV={sent_cv:.2f}, threshold <0.25). "
                        "AI text tends to produce sentences of similar length.",
                        suggestion="Vary sentence structure: mix short punchy sentences with longer complex ones.",
                    )
                )

        # ── 2. Transition word density at sentence start ──
        transition_starts = 0
        total_sentences = len(sentences)
        transition_used: dict[str, int] = {}
        if total_sentences >= 5:
            for s in sentences:
                first_word = s.split()[0].lower().rstrip(",") if s.split() else ""
                if first_word in AI_TRANSITION_WORDS:
                    transition_starts += 1
                    transition_used[first_word] = transition_used.get(first_word, 0) + 1

            transition_pct = transition_starts / total_sentences * 100
            if transition_pct > 20:
                issues.append(
                    HookIssue(
                        hook_id="A3b",
                        severity="CRITICAL" if transition_pct > 35 else "WARNING",
                        section=section,
                        message=f"Excessive transition words at sentence start ({transition_pct:.0f}%, "
                        f"{transition_starts}/{total_sentences} sentences). AI-generated text "
                        "overuses connectors like 'Moreover', 'Furthermore', 'Additionally'.",
                        suggestion="Remove unnecessary transition words. Let ideas flow naturally "
                        "without signposting every connection.",
                    )
                )

        # ── 3. Sentence starter diversity ──
        starters: list[str] = []
        if total_sentences >= 8:
            starters = [s.split()[0].lower() for s in sentences if s.split()]
            unique_ratio = len(set(starters)) / len(starters) if starters else 1.0
            if unique_ratio < 0.5:
                issues.append(
                    HookIssue(
                        hook_id="A3b",
                        severity="WARNING",
                        section=section,
                        message=f"Low sentence-starter diversity ({unique_ratio:.2f}, threshold <0.50). "
                        "Repetitive sentence openings suggest AI generation.",
                        suggestion="Vary how you begin sentences: use subjects, prepositional "
                        "phrases, subordinate clauses, or inverted structures.",
                    )
                )

        # ── 4. List-of-three pattern overuse ──
        list_of_three = re.findall(
            r"\b\w+(?:\s+\w+)?,\s+\w+(?:\s+\w+)?,\s+and\s+\w+", prose, re.IGNORECASE
        )
        if len(list_of_three) > 3:
            issues.append(
                HookIssue(
                    hook_id="A3b",
                    severity="WARNING",
                    section=section,
                    message=f"Overuse of 'X, Y, and Z' listing pattern ({len(list_of_three)} instances). "
                    "AI text frequently uses comma-separated triples.",
                    suggestion="Vary enumeration: use 'such as X and Y', inline descriptions, "
                    "or restructure to avoid formulaic lists.",
                )
            )

        # ── 5. Paragraph length uniformity ──
        paragraphs = [
            p.strip()
            for p in re.split(r"\n\s*\n", prose)
            if len(p.strip().split()) >= 10
        ]
        if len(paragraphs) >= 4:
            para_lengths = [len(p.split()) for p in paragraphs]
            mean_para = sum(para_lengths) / len(para_lengths)
            if mean_para > 0:
                para_variance = sum(
                    (x - mean_para) ** 2 for x in para_lengths
                ) / len(para_lengths)
                para_cv = (para_variance**0.5) / mean_para
                if para_cv < 0.20:
                    issues.append(
                        HookIssue(
                            hook_id="A3b",
                            severity="WARNING",
                            section=section,
                            message=f"Paragraph lengths too uniform (CV={para_cv:.2f}, threshold <0.20). "
                            "Human writing naturally has varied paragraph lengths.",
                            suggestion="Break up long paragraphs, merge short ones, or let paragraph "
                            "length follow content needs rather than a template.",
                        )
                    )

        # ── Composite score ──
        ai_signal_count = len(issues)
        passed = ai_signal_count == 0
        stats = {
            "ai_signal_count": ai_signal_count,
            "sentence_cv": round(sent_cv, 3),
            "transition_pct": round(
                transition_starts / total_sentences * 100, 1
            ) if total_sentences > 0 else 0,
            "starter_diversity": round(
                len(set(starters)) / len(starters), 3
            ) if total_sentences >= 8 and starters else 1.0,
            "list_of_three_count": len(list_of_three),
            "paragraph_count": len(paragraphs),
            "sentence_count": total_sentences,
            "transition_word_counts": dict(
                sorted(transition_used.items(), key=lambda x: -x[1])[:10]
            ),
        }
        logger.info(
            "Hook A3b complete",
            passed=passed,
            signal_count=ai_signal_count,
            sent_cv=sent_cv,
        )
        return HookResult(hook_id="A3b", passed=passed, issues=issues, stats=stats)

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
        """
        issues: list[HookIssue] = []

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
            target_dict = BRIT_VS_AMER
            variant_found = "British"
            variant_preferred = "American"
        elif prefer == "british":
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
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or stripped.startswith("#") or stripped.startswith("[["):
                continue
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
        n-grams that appear in multiple paragraphs.

        Args:
            content: Full manuscript text.
            min_ngram: Minimum n-gram size (words). Default 6.
            threshold: Minimum shared n-grams between two paragraphs
                       to flag as WARNING. Default 3.
        """
        issues: list[HookIssue] = []

        paragraphs: list[tuple[str, str]] = []
        current_section = "Unknown"
        for block in re.split(r"\n{2,}", content):
            block = block.strip()
            if not block:
                continue
            heading_match = re.match(r"^#{1,3}\s+(.+)", block)
            if heading_match:
                current_section = heading_match.group(1).strip()
                continue
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

        para_ngrams: list[set[str]] = [_extract_ngrams(text, min_ngram) for _, text in paragraphs]

        flagged_pairs: list[tuple[int, int, int]] = []

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
