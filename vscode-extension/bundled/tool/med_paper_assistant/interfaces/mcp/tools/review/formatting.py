"""
Formatting Tools

Comprehensive manuscript checking tool combining:
- Journal formatting checks (word limits, abstract, references, tables, figures)
- Consistency checks (citations, numbers, abbreviations, p-value, table/figure refs)
- Submission checklist (required documents and statements)
"""

import os
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    ensure_project_context,
    get_drafts_dir,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)

# Import consistency check helpers
from .consistency import (
    ConsistencyReport,
    _check_abbreviations,
    _check_citations,
    _check_figure_table_archive,
    _check_numbers,
    _check_pvalue_format,
    _check_statistical_reporting,
    _check_table_figure_refs,
)

# Import medRxiv screening checks
from .medrxiv_screening import run_medrxiv_screening

# Import journal requirements from submission module
from .submission import JOURNAL_REQUIREMENTS


def register_formatting_tools(mcp: FastMCP, drafter: Drafter, ref_manager: ReferenceManager):
    """Register formatting check tools."""

    @mcp.tool()
    def check_formatting(
        draft_filename: str,
        journal: str = "generic",
        check_submission: bool = False,
        has_cover_letter: bool = False,
        has_ethics: bool = False,
        has_consent: bool = False,
        has_coi: bool = False,
        has_author_contributions: bool = False,
        has_data_availability: bool = False,
        has_keywords: bool = False,
        has_highlights: bool = False,
        project: Optional[str] = None,
    ) -> str:
        """
        Check manuscript formatting, consistency, and submission readiness.

        Combines formatting checks (word limits, abstract, references), consistency
        checks (citations, numbers, abbreviations, p-values), and optionally
        submission checklist verification.

        Args:
            draft_filename: Draft file to check (or comma-separated for multiple)
            journal: Journal code (bja, anesthesiology, jama, nejm, lancet, ccm, medrxiv, jamia, jbi, generic)
            check_submission: Also check submission readiness (required documents/statements)
            has_cover_letter: Cover letter prepared? (used when check_submission=True)
            has_ethics: Ethics approval included?
            has_consent: Informed consent included?
            has_coi: Conflict of interest included?
            has_author_contributions: Author contributions included?
            has_data_availability: Data availability included?
            has_keywords: Keywords included?
            has_highlights: Highlights included?
            project: Project slug (uses current if omitted)
        """
        log_tool_call(
            "check_formatting",
            {
                "draft_filename": draft_filename,
                "journal": journal,
                "check_submission": check_submission,
            },
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Get journal requirements
        journal_key = journal.lower().replace(" ", "_").replace("-", "_")
        reqs = JOURNAL_REQUIREMENTS.get(journal_key, JOURNAL_REQUIREMENTS["generic"])
        journal_name = str(reqs["name"])

        # Read draft(s)
        filenames = [f.strip() for f in draft_filename.split(",") if f.strip()]
        all_content = ""
        file_contents: dict[str, str] = {}

        for fname in filenames:
            try:
                if not fname.endswith(".md"):
                    fname += ".md"
                drafts_dir = get_drafts_dir() or drafter.drafts_dir
                fpath = os.path.join(drafts_dir, fname) if not os.path.isabs(fname) else fname
                if not os.path.exists(fpath):
                    raise FileNotFoundError(f"Draft file {fname} not found in {drafts_dir}.")
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                all_content += content + "\n\n"
                file_contents[fname] = content
            except FileNotFoundError:
                return f"❌ Draft not found: {fname}. Use `list_drafts` to see available files."
            except Exception as e:
                log_tool_error("check_formatting", e, {"draft_filename": fname})
                return f"❌ Error reading draft: {e}"

        # ── Part 1: Formatting checks ────────────────────────────────────
        issues: list[dict[str, str]] = []
        passes: list[str] = []

        # 1. Word count
        word_count = len(all_content.split())
        word_limit = int(reqs["word_limit"].get("original", 4000))
        if word_count > word_limit:
            issues.append(
                {
                    "severity": "error",
                    "item": "Word count",
                    "detail": f"{word_count} words (limit: {word_limit}, excess: {word_count - word_limit})",
                }
            )
        else:
            passes.append(f"Word count: {word_count}/{word_limit}")

        # 2. Abstract check
        abstract_match = re.search(
            r"(?:^#{1,3}\s*abstract\s*\n)(.*?)(?=\n#{1,3}\s|\Z)",
            all_content,
            re.IGNORECASE | re.DOTALL | re.MULTILINE,
        )
        if abstract_match:
            abstract_text = abstract_match.group(1)
            abstract_words = len(abstract_text.split())
            abstract_limit = int(reqs.get("abstract_limit", 300))
            if abstract_words > abstract_limit:
                issues.append(
                    {
                        "severity": "error",
                        "item": "Abstract word count",
                        "detail": f"{abstract_words} words (limit: {abstract_limit})",
                    }
                )
            else:
                passes.append(f"Abstract: {abstract_words}/{abstract_limit} words")
        else:
            issues.append(
                {
                    "severity": "info",
                    "item": "Abstract",
                    "detail": "No abstract section detected (may be in a separate file)",
                }
            )

        # 3. Reference count
        wikilink_refs = set(re.findall(r"\[\[([^\]]+)\]\]", all_content))
        ref_limit = int(reqs.get("references_limit", 50))
        if len(wikilink_refs) > ref_limit:
            issues.append(
                {
                    "severity": "warning",
                    "item": "Reference count",
                    "detail": f"{len(wikilink_refs)} citations (limit: {ref_limit})",
                }
            )
        else:
            passes.append(f"References: {len(wikilink_refs)}/{ref_limit}")

        # 4. Table count
        table_refs = set(re.findall(r"Table\s+(\d+)", all_content, re.IGNORECASE))
        table_limit = int(reqs.get("tables_limit", 5))
        if len(table_refs) > table_limit:
            issues.append(
                {
                    "severity": "warning",
                    "item": "Table count",
                    "detail": f"{len(table_refs)} tables (limit: {table_limit})",
                }
            )
        else:
            passes.append(f"Tables: {len(table_refs)}/{table_limit}")

        # 5. Figure count
        fig_refs = set(re.findall(r"(?:Figure|Fig\.?)\s+(\d+)", all_content, re.IGNORECASE))
        fig_limit = int(reqs.get("figures_limit", 6))
        if len(fig_refs) > fig_limit:
            issues.append(
                {
                    "severity": "warning",
                    "item": "Figure count",
                    "detail": f"{len(fig_refs)} figures (limit: {fig_limit})",
                }
            )
        else:
            passes.append(f"Figures: {len(fig_refs)}/{fig_limit}")

        # 6. Keywords
        if reqs.get("keywords"):
            has_kw = bool(re.search(r"(?:keywords?|key\s+words)\s*:", all_content, re.IGNORECASE))
            if not has_kw:
                issues.append(
                    {
                        "severity": "warning",
                        "item": "Keywords",
                        "detail": f"Not found (required: {reqs['keywords']})",
                    }
                )
            else:
                passes.append("Keywords section present")

        # 7. Heading hierarchy
        headings = re.findall(r"^(#{1,6})\s+(.+)", all_content, re.MULTILINE)
        if headings:
            levels = [len(h[0]) for h in headings]
            for i in range(1, len(levels)):
                if levels[i] - levels[i - 1] > 1:
                    issues.append(
                        {
                            "severity": "info",
                            "item": "Heading hierarchy",
                            "detail": f"Skipped heading level: {'#' * levels[i - 1]} → {'#' * levels[i]} ('{headings[i][1]}')",
                        }
                    )
                    break
            else:
                passes.append("Heading hierarchy consistent")

        # 8. Required sections check
        content_lower = all_content.lower()
        required_sections = ["introduction", "methods", "results", "discussion"]
        missing_sections = [
            s
            for s in required_sections
            if not re.search(rf"^#{{1,3}}\s+{s}", content_lower, re.MULTILINE)  # fmt: skip
        ]
        if missing_sections:
            issues.append(
                {
                    "severity": "info",
                    "item": "Standard sections",
                    "detail": f"Not detected: {', '.join(s.title() for s in missing_sections)} (may be in separate files)",
                }
            )

        # 9. Special characters / encoding
        non_ascii = re.findall(r"[^\x00-\x7F]", all_content)
        unusual = [c for c in non_ascii if ord(c) > 0x2000 and c not in "–—''…±×÷≤≥≠αβγδ"]
        if unusual:
            issues.append(
                {
                    "severity": "info",
                    "item": "Special characters",
                    "detail": f"Found {len(unusual)} unusual Unicode characters — verify they display correctly",
                }
            )

        # ── Part 2: Consistency checks ───────────────────────────────────
        consistency_report = ConsistencyReport()
        _check_citations(all_content, ref_manager, consistency_report)
        _check_numbers(all_content, consistency_report)
        _check_abbreviations(all_content, consistency_report)
        _check_table_figure_refs(all_content, consistency_report)
        _check_pvalue_format(all_content, consistency_report)
        _check_statistical_reporting(all_content, consistency_report)

        # Figure/table archive cross-validation
        from med_paper_assistant.infrastructure.persistence import get_project_manager

        pm = get_project_manager()
        project_info = pm.get_project_info()
        project_path = (
            str(project_info["project_path"]) if project_info.get("project_path") else None
        )
        _check_figure_table_archive(all_content, project_path, consistency_report)

        # Convert consistency issues to formatting issues format
        for ci in consistency_report.issues:
            issues.append(
                {
                    "severity": ci.severity,
                    "item": f"[Consistency] {ci.category}",
                    "detail": ci.description + (f" — {ci.suggestion}" if ci.suggestion else ""),
                }
            )

        # ── Part 2.5: medRxiv screening (when journal is medRxiv) ────────
        medrxiv_report = None
        if journal_key == "medrxiv":
            medrxiv_report = run_medrxiv_screening(all_content)
            for si in medrxiv_report.issues:
                issues.append(
                    {
                        "severity": si.severity,
                        "item": f"[medRxiv] {si.category}",
                        "detail": si.description + (f" — {si.suggestion}" if si.suggestion else ""),
                    }
                )

        # ── Part 3: Submission checklist (optional) ──────────────────────
        submission_items: list[dict[str, str]] = []
        if check_submission:
            if reqs.get("cover_letter"):
                submission_items.append(
                    {
                        "item": "Cover letter",
                        "status": "pass" if has_cover_letter else "fail",
                        "detail": "" if has_cover_letter else "Required for this journal",
                    }
                )
            if reqs.get("highlights"):
                submission_items.append(
                    {
                        "item": "Highlights/Key Points",
                        "status": "pass" if has_highlights else "fail",
                        "detail": "" if has_highlights else "Required for this journal",
                    }
                )
            if reqs.get("ethics_statement"):
                submission_items.append(
                    {
                        "item": "Ethics approval",
                        "status": "pass" if has_ethics else "fail",
                        "detail": "" if has_ethics else "Include IRB/Ethics approval number",
                    }
                )
            submission_items.append(
                {
                    "item": "Informed consent",
                    "status": "pass" if has_consent else "warning",
                    "detail": "" if has_consent else "Verify consent statement",
                }
            )
            if reqs.get("conflict_of_interest"):
                submission_items.append(
                    {
                        "item": "Conflict of interest",
                        "status": "pass" if has_coi else "fail",
                        "detail": "" if has_coi else "Required — even if 'None'",
                    }
                )
            if reqs.get("author_contributions"):
                submission_items.append(
                    {
                        "item": "Author contributions",
                        "status": "pass" if has_author_contributions else "fail",
                        "detail": "" if has_author_contributions else "Use CRediT taxonomy",
                    }
                )
            if reqs.get("data_availability"):
                submission_items.append(
                    {
                        "item": "Data availability",
                        "status": "pass" if has_data_availability else "fail",
                        "detail": ""
                        if has_data_availability
                        else "State if data available on request",
                    }
                )
            if reqs.get("keywords"):
                submission_items.append(
                    {
                        "item": "Keywords",
                        "status": "pass" if has_keywords else "warning",
                        "detail": f"Required: {reqs['keywords']}" if not has_keywords else "",
                    }
                )

        # ── Generate report ──────────────────────────────────────────────
        output = f"# 📐 Manuscript Check: {journal_name}\n\n"
        output += f"**Files:** {', '.join(filenames)}\n"
        output += f"**Journal:** {journal_name} (`{journal_key}`)\n\n"

        error_count = sum(1 for i in issues if i["severity"] == "error")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        info_count = sum(1 for i in issues if i["severity"] == "info")

        output += "## Summary\n\n"
        output += f"- ✅ Passed: {len(passes)}\n"
        output += f"- ❌ Errors: {error_count}\n"
        output += f"- ⚠️ Warnings: {warning_count}\n"
        output += f"- ℹ️ Info: {info_count}\n\n"

        if passes:
            output += "## ✅ Passed\n\n"
            for p in passes:
                output += f"- {p}\n"
            output += "\n"

        if issues:
            output += "## Issues\n\n"
            output += "| Severity | Item | Detail |\n"
            output += "|----------|------|--------|\n"

            icons = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
            for issue in sorted(
                issues, key=lambda x: {"error": 0, "warning": 1, "info": 2}[x["severity"]]
            ):
                icon = icons[issue["severity"]]
                output += f"| {icon} | {issue['item']} | {issue['detail']} |\n"

            output += "\n"

        # Submission checklist section
        if submission_items:
            output += "## 📋 Submission Checklist\n\n"
            sub_icons = {"pass": "✅", "fail": "❌", "warning": "⚠️"}
            for item in submission_items:
                icon = sub_icons.get(item["status"], "❓")
                detail = f" — {item['detail']}" if item["detail"] else ""
                output += f"- {icon} {item['item']}{detail}\n"
            output += "\n"

        # medRxiv screening summary
        if medrxiv_report is not None:
            output += "## 🏥 medRxiv Pre-Submission Screening\n\n"
            output += (
                "Automated checks mirroring medRxiv's two-stage screening process "
                "(in-house + affiliate review).\n\n"
            )
            screening_errors = medrxiv_report.error_count
            screening_warnings = medrxiv_report.warning_count
            screening_total = len(medrxiv_report.issues)
            if screening_total == 0:
                output += "✅ **All medRxiv screening checks passed.**\n\n"
            else:
                output += (
                    f"- ❌ Errors: {screening_errors}\n"
                    f"- ⚠️ Warnings: {screening_warnings}\n"
                    f"- ℹ️ Info: {screening_total - screening_errors - screening_warnings}\n\n"
                )
                if screening_errors > 0:
                    output += (
                        "⚠️ **Fix errors before submitting to medRxiv — "
                        "these will likely cause rejection during screening.**\n\n"
                    )

        # Journal-specific notes
        output += "## Journal Requirements Overview\n\n"
        output += "| Requirement | Value |\n"
        output += "|-------------|-------|\n"
        output += f"| Word limit (original) | {reqs['word_limit'].get('original', 'N/A')} |\n"
        output += f"| Abstract limit | {reqs.get('abstract_limit', 'N/A')} |\n"
        output += f"| Max references | {reqs.get('references_limit', 'N/A')} |\n"
        output += f"| Max figures | {reqs.get('figures_limit', 'N/A')} |\n"
        output += f"| Max tables | {reqs.get('tables_limit', 'N/A')} |\n"
        output += f"| Keywords | {reqs.get('keywords', 'N/A')} |\n"
        output += f"| Cover letter | {'Required' if reqs.get('cover_letter') else 'Optional'} |\n"
        output += f"| Highlights | {'Required' if reqs.get('highlights') else 'Not required'} |\n"
        output += f"| ORCID | {reqs.get('orcid', 'N/A')} |\n\n"

        if error_count == 0:
            output += "🟢 **No critical formatting errors detected.**\n"
        else:
            output += "🔴 **Fix errors before submission.**\n"

        log_tool_result(
            "check_formatting",
            f"errors={error_count}, warnings={warning_count}",
            success=error_count == 0,
        )
        return output
