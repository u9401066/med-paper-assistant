"""Writing Hooks — Manuscript-level hooks mixin (C-series: C3–C13)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from ._constants import COMMON_ABBREVIATIONS
from ._models import HookIssue, HookResult

logger = structlog.get_logger()


class ManuscriptHooksMixin:
    """C-series hooks: post-manuscript quality checks."""

    # Declared by JournalConfigMixin / _engine.py
    _project_dir: Path
    _audit_dir: Path

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

        n_patterns = [
            (r"\b[Nn]\s*=\s*(\d+)\b", "N="),
            (
                r"(\d+)\s+(?:patients|subjects|participants|individuals|cases|controls|samples|enrolled)",
                "count of",
            ),
        ]

        def _extract_n_values(text: str) -> dict[str, set[str]]:
            result: dict[str, set[str]] = {}
            for pattern, label in n_patterns:
                values = set(re.findall(pattern, text, re.IGNORECASE))
                if values:
                    result[label] = values
            return result

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

        all_abbrs = re.findall(r"\b([A-Z]{2,})\b", content)
        if not all_abbrs:
            return HookResult(
                hook_id="C4",
                passed=True,
                stats={"abbreviations_found": 0},
            )

        seen: set[str] = set()
        unique_abbrs: list[str] = []
        for abbr in all_abbrs:
            if abbr not in seen and abbr not in COMMON_ABBREVIATIONS:
                seen.add(abbr)
                unique_abbrs.append(abbr)

        defined: list[str] = []
        undefined: list[str] = []

        for abbr in unique_abbrs:
            first_pos = content.find(abbr)
            if first_pos == -1:
                continue

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
            "undefined": undefined[:10],
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
            if wl in existing_refs:
                resolved += 1
            else:
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

        Per academic convention (ICMJE), counts only body sections.
        """
        issues: list[HookIssue] = []

        limit = self._get_total_word_limit()
        if limit is None:
            return HookResult(
                hook_id="C6",
                passed=True,
                stats={"note": "No total word limit configured"},
            )

        body_info = self._extract_body_word_count(content)
        total_words = body_info["body_words"]

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
            "body_words": total_words,
            "limit": limit,
            "deviation_pct": round(deviation_pct, 1),
            "body_sections": body_info["breakdown"],
            "excluded_sections": body_info["excluded_sections"],
            "counting_method": "body_only (ICMJE convention)",
        }

        logger.info("Hook C6 complete", passed=passed, body_words=total_words, limit=limit)
        return HookResult(hook_id="C6", passed=passed, issues=issues, stats=stats)

    # ── Hook C7a: Figure/Table Count Limits ────────────────────────

    def check_figure_table_counts(
        self,
        content: str,
    ) -> HookResult:
        """Hook C7a: Check figure and table counts against journal limits."""
        issues: list[HookIssue] = []

        fig_limit, tbl_limit = self._get_figure_table_limits()
        if fig_limit is None and tbl_limit is None:
            return HookResult(
                hook_id="C7a",
                passed=True,
                stats={"note": "No figure/table limits configured"},
            )

        fig_refs = set(re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE))
        tbl_refs = set(re.findall(r"Table\s+(\d+)", content, re.IGNORECASE))

        manifest_path = self._project_dir / "results" / "manifest.json"
        if manifest_path.is_file():
            try:
                with open(manifest_path, encoding="utf-8") as f:
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

        fig_refs = set(re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE))
        tbl_refs = set(re.findall(r"Table\s+(\d+)", content, re.IGNORECASE))

        manifest_path = self._project_dir / "results" / "manifest.json"
        if not manifest_path.is_file():
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
            with open(manifest_path, encoding="utf-8") as f:
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

        phantom_figs = fig_refs - manifest_figs
        phantom_tbls = tbl_refs - manifest_tbls

        for f_num in phantom_figs:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="CRITICAL",
                    section="manuscript",
                    message=f"Phantom: Figure {f_num} referenced in text but not in manifest",
                    suggestion=f"Add Figure {f_num} to manifest or remove from text",
                )
            )
        for t_num in phantom_tbls:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="CRITICAL",
                    section="manuscript",
                    message=f"Phantom: Table {t_num} referenced in text but not in manifest",
                    suggestion=f"Add Table {t_num} to manifest or remove from text",
                )
            )

        orphan_figs = manifest_figs - fig_refs
        orphan_tbls = manifest_tbls - tbl_refs

        for fig in orphan_figs:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="WARNING",
                    section="manifest",
                    message=f"Orphan: Figure {fig} in manifest but not referenced in text",
                    suggestion=f"Add Figure {fig} reference to text or remove from manifest",
                )
            )
        for t_num in orphan_tbls:
            issues.append(
                HookIssue(
                    hook_id="C7d",
                    severity="WARNING",
                    section="manifest",
                    message=f"Orphan: Table {t_num} in manifest but not referenced in text",
                    suggestion=f"Add Table {t_num} reference to text or remove from manifest",
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

    # ── Hook C9: Supplementary Material Cross-Reference ────────────

    def check_supplementary_crossref(
        self,
        content: str,
    ) -> HookResult:
        """Hook C9: Verify supplementary material cross-references."""
        issues: list[HookIssue] = []

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

        text_refs: dict[str, list[str]] = {}
        for pattern, ref_type in supp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                text_refs.setdefault(ref_type, []).extend(matches)

        supp_dir = self._project_dir / "supplementary"
        supp_files: set[str] = set()
        if supp_dir.is_dir():
            for f in supp_dir.rglob("*"):
                if f.is_file():
                    supp_files.add(f.name)

        exports_supp = self._project_dir / "exports" / "supplementary"
        if exports_supp.is_dir():
            for f in exports_supp.rglob("*"):
                if f.is_file():
                    supp_files.add(f.name)

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

        if supp_files and total_refs > 0:
            for ref_type, ids in text_refs.items():
                for ref_id in ids:
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

    # ── Hook C10: Reference Fulltext Verification ──────────────────

    def check_reference_fulltext_status(
        self,
        content: str,
    ) -> HookResult:
        """
        C10: Verify that cited references have fulltext + analysis status.
        """
        issues: list[HookIssue] = []

        wikilinks = re.findall(r"\[\[(\w+\d{4}_\d+)\]\]", content)
        unique_refs = set(wikilinks)

        if not unique_refs:
            return HookResult(
                hook_id="C10",
                passed=True,
                stats={"note": "No wikilink citations found"},
            )

        refs_dir = self._project_dir / "references"
        ingested = 0
        not_ingested = 0
        analyzed = 0
        not_analyzed = 0
        missing_metadata = 0

        for ref_key in sorted(unique_refs):
            ref_dir = refs_dir / ref_key
            meta_path = ref_dir / "metadata.json"

            if not meta_path.is_file():
                missing_metadata += 1
                continue

            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                missing_metadata += 1
                continue

            if meta.get("fulltext_ingested", False):
                ingested += 1
            else:
                not_ingested += 1
                reason = meta.get("fulltext_unavailable_reason", "not attempted")
                issues.append(
                    HookIssue(
                        hook_id="C10",
                        severity="WARNING",
                        section="References",
                        message=f"Reference [[{ref_key}]] cited without fulltext ingestion",
                        location=ref_key,
                        suggestion=f"Run asset-aware fulltext ingestion or note reason: {reason}",
                    )
                )

            if meta.get("analysis_completed", False):
                analyzed += 1
            else:
                not_analyzed += 1
                issues.append(
                    HookIssue(
                        hook_id="C10",
                        severity="WARNING",
                        section="References",
                        message=f"Reference [[{ref_key}]] cited without subagent analysis",
                        location=ref_key,
                        suggestion="Run get_reference_for_analysis → subagent → save_reference_analysis before citing",
                    )
                )

        total = ingested + not_ingested + missing_metadata
        stats = {
            "total_cited": len(unique_refs),
            "fulltext_ingested": ingested,
            "fulltext_missing": not_ingested,
            "analysis_completed": analyzed,
            "analysis_missing": not_analyzed,
            "metadata_missing": missing_metadata,
            "fulltext_pct": round(ingested / total * 100, 1) if total > 0 else 0,
            "analysis_pct": round(analyzed / total * 100, 1) if total > 0 else 0,
        }

        passed = not_ingested == 0 and missing_metadata == 0 and not_analyzed == 0
        logger.info(
            "Hook C10 (Reference Fulltext+Analysis) complete",
            passed=passed,
            ingested=ingested,
            analyzed=analyzed,
            missing_fulltext=not_ingested,
            missing_analysis=not_analyzed,
        )
        return HookResult(hook_id="C10", passed=passed, issues=issues, stats=stats)

    # ── Hook C11: Citation Distribution Across Sections ────────────

    def check_citation_distribution(
        self,
        content: str,
    ) -> HookResult:
        """
        C11: Verify citations are distributed across sections, not clustered.
        """
        issues: list[HookIssue] = []

        sections = self._parse_sections(content)
        if not sections:
            return HookResult(
                hook_id="C11",
                passed=True,
                stats={"note": "No sections parsed"},
            )

        canonical = ["Introduction", "Methods", "Results", "Discussion"]
        section_citations: dict[str, int] = {}

        for canon in canonical:
            for name, text in sections.items():
                if name.lower().startswith(canon.lower()):
                    count = len(re.findall(r"\[\[[^\]]+\]\]", text))
                    section_citations[canon] = count
                    break

        total_citations = sum(section_citations.values())

        if total_citations == 0:
            return HookResult(
                hook_id="C11",
                passed=True,
                stats={
                    "note": "No citations found in manuscript",
                    "section_citations": section_citations,
                },
            )

        disc_count = section_citations.get("Discussion", 0)
        if disc_count == 0 and "Discussion" in section_citations:
            issues.append(
                HookIssue(
                    hook_id="C11",
                    severity="CRITICAL",
                    section="Discussion",
                    message="Discussion has 0 citations — must compare findings with prior literature",
                    suggestion="Add citations comparing your results with published studies: 'Consistent with [[ref]], ...' or 'In contrast to [[ref]], ...'",
                )
            )

        methods_count = section_citations.get("Methods", 0)
        if methods_count == 0 and "Methods" in section_citations:
            issues.append(
                HookIssue(
                    hook_id="C11",
                    severity="WARNING",
                    section="Methods",
                    message="Methods has 0 citations — should cite methodology sources",
                    suggestion="Cite statistical methods, validated instruments, prior protocols, or classification systems used",
                )
            )

        for sec_name, count in section_citations.items():
            pct = (count / total_citations) * 100
            if pct > 70 and total_citations >= 5:
                issues.append(
                    HookIssue(
                        hook_id="C11",
                        severity="WARNING",
                        section=sec_name,
                        message=f"{sec_name} holds {pct:.0f}% of all citations ({count}/{total_citations}) — distribution imbalance",
                        suggestion=f"Redistribute citations: ensure other sections also cite relevant literature (current: {section_citations})",
                    )
                )

        results_count = section_citations.get("Results", 0)
        if results_count > 0 and total_citations > 0:
            results_pct = (results_count / total_citations) * 100
            if results_pct > 50:
                issues.append(
                    HookIssue(
                        hook_id="C11",
                        severity="INFO",
                        section="Results",
                        message=f"Results has {results_pct:.0f}% of citations — typically Results should focus on your data, not prior literature",
                        suggestion="Consider moving literature comparisons to Discussion",
                    )
                )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "total_citations": total_citations,
            "section_citations": section_citations,
            "distribution_pct": {
                k: round((v / total_citations) * 100, 1) if total_citations > 0 else 0
                for k, v in section_citations.items()
            },
        }

        logger.info(
            "Hook C11 (Citation Distribution) complete",
            passed=passed,
            total=total_citations,
            distribution=section_citations,
        )
        return HookResult(hook_id="C11", passed=passed, issues=issues, stats=stats)

    # ── Hook C12: Citation Relevance Audit ─────────────────────────

    def check_citation_relevance_audit(
        self,
        content: str,
    ) -> HookResult:
        """
        C12: Verify citations have recorded usage justification.
        """
        issues: list[HookIssue] = []

        sections = self._parse_sections(content)

        ref_to_sections: dict[str, set[str]] = {}
        for sec_name, sec_text in sections.items():
            wikilinks = re.findall(r"\[\[(\w+\d{4}_\d+)\]\]", sec_text)
            for ref_key in wikilinks:
                if ref_key not in ref_to_sections:
                    ref_to_sections[ref_key] = set()
                ref_to_sections[ref_key].add(sec_name)

        if not ref_to_sections:
            return HookResult(
                hook_id="C12",
                passed=True,
                stats={"note": "No wikilink citations found"},
            )

        refs_dir = self._project_dir / "references"
        decisions_path = self._project_dir / "citation_decisions.json"

        decisions: dict[str, Any] = {}
        if decisions_path.is_file():
            try:
                decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        has_justification = 0
        missing_justification = 0
        section_mismatch = 0

        for ref_key, cited_sections in sorted(ref_to_sections.items()):
            ref_dir = refs_dir / ref_key
            meta_path = ref_dir / "metadata.json"
            analysis_path = ref_dir / "analysis.json"

            has_analysis = False
            usage_sections: list[str] = []
            if analysis_path.is_file():
                try:
                    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
                    has_analysis = True
                    usage_sections = analysis.get("usage_sections", [])
                except (json.JSONDecodeError, OSError):
                    pass
            elif meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    has_analysis = meta.get("analysis_completed", False)
                    usage_sections = meta.get("usage_sections", [])
                except (json.JSONDecodeError, OSError):
                    pass

            if has_analysis and usage_sections:
                for cited_sec in cited_sections:
                    normalized_usage = [s.lower() for s in usage_sections]
                    if cited_sec.lower() not in normalized_usage:
                        section_mismatch += 1
                        issues.append(
                            HookIssue(
                                hook_id="C12",
                                severity="WARNING",
                                section=cited_sec,
                                message=f"[[{ref_key}]] cited in {cited_sec} but usage_sections={usage_sections} — section not in planned usage",
                                location=ref_key,
                                suggestion=f"Update analysis for [[{ref_key}]] to include '{cited_sec}' in usage_sections, or reconsider if this citation belongs here",
                            )
                        )

            ref_decision = decisions.get(ref_key, {})
            if ref_decision and ref_decision.get("justification"):
                has_justification += 1
            else:
                missing_justification += 1
                issues.append(
                    HookIssue(
                        hook_id="C12",
                        severity="WARNING",
                        section="References",
                        message=f"[[{ref_key}]] has no citation decision record — why was this reference chosen?",
                        location=ref_key,
                        suggestion=(
                            f"Add decision record to citation_decisions.json: "
                            f'{{"justification": "...", "cited_sections": {list(cited_sections)}, "decision_date": "..."}}'
                        ),
                    )
                )

        total = has_justification + missing_justification
        passed = missing_justification == 0 and section_mismatch == 0
        stats = {
            "total_cited_refs": len(ref_to_sections),
            "has_justification": has_justification,
            "missing_justification": missing_justification,
            "section_mismatch": section_mismatch,
            "justification_pct": round(has_justification / total * 100, 1) if total > 0 else 0,
            "decisions_file_exists": decisions_path.is_file(),
        }

        logger.info(
            "Hook C12 (Citation Relevance Audit) complete",
            passed=passed,
            justified=has_justification,
            missing=missing_justification,
            mismatched=section_mismatch,
        )
        return HookResult(hook_id="C12", passed=passed, issues=issues, stats=stats)

    # ── Hook C13: Figure/Table Quality & Ordering ──────────────────

    def check_figure_table_quality(
        self,
        content: str,
    ) -> HookResult:
        """
        C13: Verify figure/table quality, ordering, and caption completeness.
        """
        issues: list[HookIssue] = []

        sections = self._parse_sections(content)

        # Check 1: Sequential ordering
        fig_order = [int(n) for n in re.findall(r"(?:Figure|Fig\.?)\s+(\d+)", content, re.IGNORECASE)]
        tbl_order = [int(n) for n in re.findall(r"Table\s+(\d+)", content, re.IGNORECASE)]

        seen_figs: list[int] = []
        for n in fig_order:
            if n not in seen_figs:
                seen_figs.append(n)
        for i in range(1, len(seen_figs)):
            if seen_figs[i] < seen_figs[i - 1]:
                issues.append(
                    HookIssue(
                        hook_id="C13",
                        severity="WARNING",
                        section="manuscript",
                        message=f"Figure {seen_figs[i]} appears before Figure {seen_figs[i-1]} in text — should be sequential",
                        suggestion="Renumber figures so they appear in the order they are first mentioned",
                    )
                )

        seen_tbls: list[int] = []
        for n in tbl_order:
            if n not in seen_tbls:
                seen_tbls.append(n)
        for i in range(1, len(seen_tbls)):
            if seen_tbls[i] < seen_tbls[i - 1]:
                issues.append(
                    HookIssue(
                        hook_id="C13",
                        severity="WARNING",
                        section="manuscript",
                        message=f"Table {seen_tbls[i]} appears before Table {seen_tbls[i-1]} in text — should be sequential",
                        suggestion="Renumber tables so they appear in the order they are first mentioned",
                    )
                )

        # Check 2: Caption presence and quality
        fig_captions = re.findall(
            r"(?:Figure|Fig\.?)\s+(\d+)\.\s*(.+?)(?:\n\n|\n#|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        tbl_captions = re.findall(
            r"Table\s+(\d+)\.\s*(.+?)(?:\n\n|\n#|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )

        captioned_figs = {int(n) for n, _ in fig_captions}
        captioned_tbls = {int(n) for n, _ in tbl_captions}

        for n in set(seen_figs):
            if n not in captioned_figs:
                issues.append(
                    HookIssue(
                        hook_id="C13",
                        severity="WARNING",
                        section="manuscript",
                        message=f"Figure {n} referenced in text but no caption found (expected 'Figure {n}. <description>')",
                        suggestion=f"Add a descriptive caption: 'Figure {n}. <Brief description of what the figure shows>'",
                    )
                )
            else:
                for num, cap_text in fig_captions:
                    if int(num) == n:
                        cap_words = len(cap_text.split())
                        if cap_words < 10:
                            issues.append(
                                HookIssue(
                                    hook_id="C13",
                                    severity="WARNING",
                                    section="manuscript",
                                    message=f"Figure {n} caption too short ({cap_words} words) — should be descriptive (≥10 words)",
                                    suggestion="Expand caption to describe axes, key findings, statistical significance, and abbreviations",
                                )
                            )
                        break

        for n in set(seen_tbls):
            if n not in captioned_tbls:
                issues.append(
                    HookIssue(
                        hook_id="C13",
                        severity="WARNING",
                        section="manuscript",
                        message=f"Table {n} referenced in text but no caption found (expected 'Table {n}. <description>')",
                        suggestion=f"Add a descriptive caption: 'Table {n}. <Brief description of table content>'",
                    )
                )

        # Check 3: Results section should reference figures/tables if it has data claims
        results_text = ""
        for name, text in sections.items():
            if name.lower().startswith("result"):
                results_text = text
                break

        if results_text:
            has_data = bool(re.search(
                r"\b(?:p\s*[<>=]\s*0\.\d|mean|median|OR|HR|RR|CI|SD|IQR|\d+\.\d+%|\d+/\d+)\b",
                results_text,
                re.IGNORECASE,
            ))
            has_fig_ref = bool(re.search(r"(?:Figure|Fig\.?|Table)\s+\d+", results_text, re.IGNORECASE))

            if has_data and not has_fig_ref:
                issues.append(
                    HookIssue(
                        hook_id="C13",
                        severity="WARNING",
                        section="Results",
                        message="Results contains statistical data but no figure/table references — consider visual presentation",
                        suggestion="Present key data in tables (demographics, outcomes) and figures (trends, comparisons). Add: 'as shown in Table 1' or 'Figure 1 illustrates...'",
                    )
                )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "figures_referenced": sorted(set(seen_figs)),
            "tables_referenced": sorted(set(seen_tbls)),
            "figures_with_captions": sorted(captioned_figs),
            "tables_with_captions": sorted(captioned_tbls),
            "fig_order_correct": seen_figs == sorted(set(seen_figs), key=seen_figs.index),
            "tbl_order_correct": seen_tbls == sorted(set(seen_tbls), key=seen_tbls.index),
        }

        logger.info(
            "Hook C13 (Figure/Table Quality) complete",
            passed=passed,
            figs=len(set(seen_figs)),
            tbls=len(set(seen_tbls)),
        )
        return HookResult(hook_id="C13", passed=passed, issues=issues, stats=stats)
