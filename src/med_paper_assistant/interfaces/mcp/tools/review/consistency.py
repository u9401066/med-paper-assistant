"""
Manuscript Consistency Checker

Helper functions for consistency checks used by check_formatting.
No MCP tools registered here — all checks are called from formatting.py.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from med_paper_assistant.infrastructure.persistence import ReferenceManager


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue found in the manuscript."""

    category: str
    severity: str  # "error", "warning", "info"
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ConsistencyReport:
    """Report of all consistency issues found."""

    issues: list[ConsistencyIssue] = field(default_factory=list)

    def add(
        self,
        category: str,
        severity: str,
        description: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        self.issues.append(
            ConsistencyIssue(
                category=category,
                severity=severity,
                description=description,
                location=location,
                suggestion=suggestion,
            )
        )

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_markdown(self) -> str:
        if not self.issues:
            return (
                "✅ **No consistency issues found!**\n\nYour manuscript looks ready for submission."
            )

        output = "## 📋 Manuscript Consistency Report\n\n"

        # Summary
        output += "### Summary\n"
        output += f"- 🔴 Errors: {self.error_count}\n"
        output += f"- 🟡 Warnings: {self.warning_count}\n"
        output += f"- ℹ️ Info: {len(self.issues) - self.error_count - self.warning_count}\n\n"

        # Group by category
        categories: dict[str, list[ConsistencyIssue]] = {}
        for issue in self.issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)

        for category, issues in categories.items():
            output += f"### {category}\n\n"
            for issue in issues:
                icon = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(issue.severity, "❓")
                output += f"{icon} **{issue.description}**\n"
                if issue.location:
                    output += f"   - Location: {issue.location}\n"
                if issue.suggestion:
                    output += f"   - Suggestion: {issue.suggestion}\n"
                output += "\n"

        return output


def _check_citations(content: str, ref_manager: ReferenceManager, report: ConsistencyReport):
    """Check citation consistency."""
    # Find all [[wikilink]] citations
    _citations = re.findall(r"\[\[([^\]]+)\]\]", content)
    # Find all (PMID:xxx) citations
    pmid_citations = re.findall(r"\(PMID[:\s]?(\d+)\)", content, re.IGNORECASE)

    # Get saved references
    try:
        saved_refs = ref_manager.list_references()
        saved_pmids = {str(r.get("pmid", "")) for r in saved_refs if r.get("pmid")}
    except Exception:
        saved_pmids = set()

    # Check PMID citations
    for pmid in pmid_citations:
        if pmid not in saved_pmids:
            report.add(
                category="Citation Issues",
                severity="warning",
                description=f"Citation PMID:{pmid} not found in saved references",
                suggestion="Use save_reference to save this reference first",
            )

    # Check for uncited references (info only)
    cited_pmids = set(pmid_citations)
    for pmid in saved_pmids:
        if pmid and pmid not in cited_pmids:
            report.add(
                category="Citation Issues",
                severity="info",
                description=f"Reference PMID:{pmid} is saved but not cited",
                suggestion="Consider citing this reference or removing it",
            )


def _check_numbers(content: str, report: ConsistencyReport):
    """Check numerical consistency (sample sizes, etc.)."""
    # Find N=xxx patterns
    n_values = re.findall(r"[Nn]\s*=\s*(\d+)", content)
    n_values_int = [int(n) for n in n_values]

    if n_values_int:
        unique_ns = set(n_values_int)
        # Check if total N is mentioned and matches subgroups
        if len(unique_ns) > 1:
            max_n = max(unique_ns)
            other_ns = [n for n in unique_ns if n != max_n]
            # Check if subgroups sum to total
            if sum(other_ns) != max_n and len(other_ns) == 2:
                report.add(
                    category="Number Consistency",
                    severity="warning",
                    description=f"Sample size mismatch: Total N={max_n} but subgroups sum to {sum(other_ns)}",
                    suggestion="Verify that subgroup sample sizes add up to total",
                )


def _check_abbreviations(content: str, report: ConsistencyReport):
    """Check abbreviation consistency."""
    # Common medical abbreviations
    common_abbrevs = [
        ("BMI", "body mass index"),
        ("ASA", "American Society of Anesthesiologists"),
        ("ICU", "intensive care unit"),
        ("SD", "standard deviation"),
        ("CI", "confidence interval"),
        ("OR", "odds ratio"),
        ("HR", "hazard ratio"),
        ("RR", "relative risk"),
        ("IQR", "interquartile range"),
    ]

    for abbrev, full_form in common_abbrevs:
        # Check if abbreviation is used
        if re.search(rf"\b{abbrev}\b", content):
            # Check if it's defined on first use
            if not re.search(
                rf"{full_form}\s*\({abbrev}\)", content, re.IGNORECASE
            ) and not re.search(rf"\({full_form};\s*{abbrev}\)", content, re.IGNORECASE):
                # Only warn if used multiple times
                count = len(re.findall(rf"\b{abbrev}\b", content))
                if count > 1:
                    report.add(
                        category="Abbreviation Issues",
                        severity="info",
                        description=f"'{abbrev}' used {count} times but may not be defined on first use",
                        suggestion=f"Define as '{full_form} ({abbrev})' on first use",
                    )


def _check_table_figure_refs(content: str, report: ConsistencyReport):
    """Check table and figure reference consistency."""
    # Find table references
    table_refs = re.findall(r"Table\s+(\d+)", content, re.IGNORECASE)
    figure_refs = re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE)
    fig_refs = re.findall(r"Fig\.?\s+(\d+)", content, re.IGNORECASE)

    # Combine figure references
    all_figure_refs = set(figure_refs + fig_refs)

    # Check sequential numbering
    if table_refs:
        table_nums = sorted(set(int(t) for t in table_refs))
        expected = list(range(1, max(table_nums) + 1))
        missing = set(expected) - set(table_nums)
        if missing:
            report.add(
                category="Table/Figure Issues",
                severity="warning",
                description=f"Table numbering gap: missing Table(s) {sorted(missing)}",
                suggestion="Check if all tables are referenced in sequence",
            )

    if all_figure_refs:
        fig_nums = sorted(set(int(f) for f in all_figure_refs))
        expected = list(range(1, max(fig_nums) + 1))
        missing = set(expected) - set(fig_nums)
        if missing:
            report.add(
                category="Table/Figure Issues",
                severity="warning",
                description=f"Figure numbering gap: missing Figure(s) {sorted(missing)}",
                suggestion="Check if all figures are referenced in sequence",
            )


def _check_pvalue_format(content: str, report: ConsistencyReport):
    """Check p-value format consistency."""
    # Different p-value formats
    lowercase_p = len(re.findall(r"\bp\s*[<>=]", content))
    uppercase_p = len(re.findall(r"\bP\s*[<>=]", content))
    italic_p = len(re.findall(r"\*p\*\s*[<>=]", content))

    formats_used = []
    if lowercase_p:
        formats_used.append(f"lowercase 'p' ({lowercase_p}x)")
    if uppercase_p:
        formats_used.append(f"uppercase 'P' ({uppercase_p}x)")
    if italic_p:
        formats_used.append(f"italic '*p*' ({italic_p}x)")

    if len(formats_used) > 1:
        report.add(
            category="Formatting Issues",
            severity="warning",
            description=f"Inconsistent p-value format: {', '.join(formats_used)}",
            suggestion="Use consistent format throughout (check journal guidelines)",
        )


def _check_statistical_reporting(content: str, report: ConsistencyReport):
    """Check statistical reporting format."""
    # Check for common issues
    # Missing space in ± notation
    if re.search(r"\d±\d", content) or re.search(r"\d\s*±\s*\d", content):
        # Count proper vs improper
        proper = len(re.findall(r"\d+\.?\d*\s*±\s*\d+\.?\d*", content))
        if proper > 0:
            report.add(
                category="Statistical Reporting",
                severity="info",
                description=f"Found {proper} mean ± SD values",
            )

    # Check for confidence intervals
    ci_patterns = len(re.findall(r"95%\s*CI", content, re.IGNORECASE))
    if ci_patterns:
        report.add(
            category="Statistical Reporting",
            severity="info",
            description=f"Found {ci_patterns} confidence interval reports",
        )
