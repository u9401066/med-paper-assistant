"""
Submission Preparation Tools

Tools for preparing manuscript submission materials.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_result,
)


# Common journal requirements database
JOURNAL_REQUIREMENTS = {
    "bja": {
        "name": "British Journal of Anaesthesia",
        "word_limit": {"original": 3500, "review": 5000, "case": 1500},
        "abstract_limit": 300,
        "references_limit": 50,
        "figures_limit": 6,
        "tables_limit": 5,
        "keywords": "3-6",
        "cover_letter": True,
        "highlights": False,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "corresponding author required",
    },
    "anesthesiology": {
        "name": "Anesthesiology",
        "word_limit": {"original": 4500, "review": 6000, "case": 2000},
        "abstract_limit": 300,
        "references_limit": 60,
        "figures_limit": 8,
        "tables_limit": 6,
        "keywords": "3-5",
        "cover_letter": True,
        "highlights": True,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "all authors",
    },
    "anesth_analg": {
        "name": "Anesthesia & Analgesia",
        "word_limit": {"original": 3000, "review": 5000, "case": 1500},
        "abstract_limit": 250,
        "references_limit": 40,
        "figures_limit": 6,
        "tables_limit": 4,
        "keywords": "3-6",
        "cover_letter": True,
        "highlights": False,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "optional",
    },
    "jama": {
        "name": "JAMA",
        "word_limit": {"original": 3000, "review": 4000, "case": 1200},
        "abstract_limit": 350,
        "references_limit": 40,
        "figures_limit": 4,
        "tables_limit": 4,
        "keywords": "3-10",
        "cover_letter": True,
        "highlights": True,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "all authors",
    },
    "nejm": {
        "name": "New England Journal of Medicine",
        "word_limit": {"original": 2700, "review": 4000, "case": 1200},
        "abstract_limit": 250,
        "references_limit": 40,
        "figures_limit": 4,
        "tables_limit": 4,
        "keywords": None,
        "cover_letter": True,
        "highlights": False,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "all authors",
    },
    "lancet": {
        "name": "The Lancet",
        "word_limit": {"original": 3500, "review": 4000, "case": 1500},
        "abstract_limit": 300,
        "references_limit": 30,
        "figures_limit": 5,
        "tables_limit": 5,
        "keywords": None,
        "cover_letter": True,
        "highlights": False,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "corresponding author required",
    },
    "ccm": {
        "name": "Critical Care Medicine",
        "word_limit": {"original": 3000, "review": 4000, "case": 1500},
        "abstract_limit": 250,
        "references_limit": 50,
        "figures_limit": 6,
        "tables_limit": 5,
        "keywords": "3-5",
        "cover_letter": True,
        "highlights": False,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "optional",
    },
    "generic": {
        "name": "Generic Journal",
        "word_limit": {"original": 4000, "review": 5000, "case": 2000},
        "abstract_limit": 300,
        "references_limit": 50,
        "figures_limit": 6,
        "tables_limit": 5,
        "keywords": "3-6",
        "cover_letter": True,
        "highlights": False,
        "graphical_abstract": False,
        "author_contributions": True,
        "conflict_of_interest": True,
        "ethics_statement": True,
        "data_availability": True,
        "orcid": "optional",
    },
}


@dataclass
class ChecklistItem:
    """Represents a submission checklist item."""

    category: str
    item: str
    status: str  # "pass", "fail", "warning", "info"
    details: Optional[str] = None


@dataclass
class SubmissionChecklist:
    """Submission checklist report."""

    items: list[ChecklistItem] = field(default_factory=list)

    def add(
        self,
        category: str,
        item: str,
        status: str,
        details: Optional[str] = None,
    ):
        self.items.append(
            ChecklistItem(category=category, item=item, status=status, details=details)
        )

    @property
    def pass_count(self) -> int:
        return sum(1 for i in self.items if i.status == "pass")

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if i.status == "fail")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.items if i.status == "warning")

    def to_markdown(self, journal_name: str) -> str:
        output = f"# 📋 Submission Checklist for {journal_name}\n\n"

        # Summary
        total = len(self.items)
        output += "## Summary\n"
        output += f"- ✅ Pass: {self.pass_count}/{total}\n"
        output += f"- ❌ Fail: {self.fail_count}\n"
        output += f"- ⚠️ Warning: {self.warning_count}\n\n"

        if self.fail_count == 0:
            output += "🎉 **Ready for submission!**\n\n"
        else:
            output += "⚠️ **Please fix the issues before submission.**\n\n"

        # Group by category
        categories: dict[str, list[ChecklistItem]] = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)

        for category, items in categories.items():
            output += f"## {category}\n\n"
            for item in items:
                icon = {
                    "pass": "✅",
                    "fail": "❌",
                    "warning": "⚠️",
                    "info": "ℹ️",
                }.get(item.status, "❓")
                output += f"- {icon} {item.item}"
                if item.details:
                    output += f" — {item.details}"
                output += "\n"
            output += "\n"

        return output


def register_submission_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register submission preparation tools."""

    @mcp.tool()
    def generate_cover_letter(
        title: str,
        authors: str,
        journal: str = "generic",
        novelty_points: Optional[str] = None,
        suggested_reviewers: Optional[str] = None,
        excluded_reviewers: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Generate a professional cover letter for journal submission.

        Args:
            title: Manuscript title.
            authors: Comma-separated author names (corresponding author first).
            journal: Target journal code (bja, anesthesiology, anesth_analg,
                    jama, nejm, lancet, ccm, or generic).
            novelty_points: Key novelty points (comma-separated or newline-separated).
                           Will be highlighted in the cover letter.
            suggested_reviewers: Optional suggested reviewers (name, affiliation, email).
            excluded_reviewers: Optional reviewers to exclude (with reasons).
            project: Project slug. If not specified, uses current project.

        Returns:
            Formatted cover letter ready for submission.

        Example:
            generate_cover_letter(
                title="Remimazolam vs Propofol in Elderly Patients",
                authors="John Smith, Jane Doe, Bob Wilson",
                journal="bja",
                novelty_points="First RCT in elderly population; Novel safety profile"
            )
        """
        log_tool_call(
            "generate_cover_letter",
            {"title": title, "journal": journal, "project": project},
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Get journal info
        journal_key = journal.lower().replace(" ", "_").replace("-", "_")
        journal_info = JOURNAL_REQUIREMENTS.get(journal_key, JOURNAL_REQUIREMENTS["generic"])
        journal_name = journal_info["name"]

        # Parse authors
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
        corresponding_author = author_list[0] if author_list else "[Corresponding Author]"

        # Parse novelty points
        novelty_list = []
        if novelty_points:
            # Split by comma or newline
            for point in re.split(r"[,\n]", novelty_points):
                point = point.strip()
                if point:
                    novelty_list.append(point)

        # Generate cover letter
        letter = f"""Dear Editor,

We are pleased to submit our manuscript entitled **"{title}"** for consideration for publication in *{journal_name}*.

"""

        # Add novelty paragraph
        if novelty_list:
            letter += "**Key Highlights of This Study:**\n\n"
            for i, point in enumerate(novelty_list, 1):
                letter += f"{i}. {point}\n"
            letter += "\n"

        letter += """This manuscript has not been published elsewhere and is not under consideration by another journal. All authors have approved the manuscript and agree with its submission to *{journal_name}*.

""".format(journal_name=journal_name)

        # Add required statements based on journal
        if journal_info.get("author_contributions"):
            letter += "All authors have made substantial contributions to the conception, design, acquisition of data, analysis, and interpretation of the work. All authors have revised the manuscript critically for important intellectual content and approved the final version to be published.\n\n"

        if journal_info.get("conflict_of_interest"):
            letter += "**Conflicts of Interest:** The authors declare no conflicts of interest relevant to this work.\n\n"

        if journal_info.get("ethics_statement"):
            letter += "**Ethics Statement:** This study was approved by the Institutional Review Board/Ethics Committee [IRB/Ethics Committee Name] (Approval No. [NUMBER]). Written informed consent was obtained from all participants.\n\n"

        if journal_info.get("data_availability"):
            letter += "**Data Availability:** The data that support the findings of this study are available from the corresponding author upon reasonable request.\n\n"

        # Add suggested reviewers
        if suggested_reviewers:
            letter += "**Suggested Reviewers:**\n"
            for reviewer in suggested_reviewers.split(";"):
                reviewer = reviewer.strip()
                if reviewer:
                    letter += f"- {reviewer}\n"
            letter += "\n"

        # Add excluded reviewers
        if excluded_reviewers:
            letter += "**Reviewers to Exclude:**\n"
            for reviewer in excluded_reviewers.split(";"):
                reviewer = reviewer.strip()
                if reviewer:
                    letter += f"- {reviewer}\n"
            letter += "\n"

        letter += f"""We believe this manuscript is well suited for *{journal_name}* and will be of interest to your readers. Thank you for considering our submission.

Sincerely,

{corresponding_author}
(On behalf of all authors)

---

**Corresponding Author:**
{corresponding_author}
[Institution]
[Address]
[Email]
[Phone]
[ORCID: https://orcid.org/0000-0000-0000-0000]
"""

        log_tool_result("generate_cover_letter", "success", success=True)
        return letter

    @mcp.tool()
    def check_submission_checklist(
        journal: str = "generic",
        word_count: Optional[int] = None,
        abstract_count: Optional[int] = None,
        reference_count: Optional[int] = None,
        figure_count: Optional[int] = None,
        table_count: Optional[int] = None,
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
        Check manuscript against journal submission requirements.

        Verifies word counts, required sections, and formatting requirements
        for the target journal.

        Args:
            journal: Target journal code (bja, anesthesiology, anesth_analg,
                    jama, nejm, lancet, ccm, or generic).
            word_count: Main text word count (excluding abstract, references).
            abstract_count: Abstract word count.
            reference_count: Number of references.
            figure_count: Number of figures.
            table_count: Number of tables.
            has_cover_letter: Cover letter prepared?
            has_ethics: Ethics approval statement included?
            has_consent: Informed consent statement included?
            has_coi: Conflict of interest statement included?
            has_author_contributions: Author contributions statement included?
            has_data_availability: Data availability statement included?
            has_keywords: Keywords included?
            has_highlights: Highlights/key points included?
            project: Project slug. If not specified, uses current project.

        Returns:
            Detailed submission checklist with pass/fail status.

        Example:
            check_submission_checklist(
                journal="bja",
                word_count=3200,
                abstract_count=280,
                reference_count=45,
                figure_count=4,
                table_count=3,
                has_cover_letter=True,
                has_ethics=True
            )
        """
        log_tool_call(
            "check_submission_checklist",
            {"journal": journal, "word_count": word_count, "project": project},
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Get journal requirements
        journal_key = journal.lower().replace(" ", "_").replace("-", "_")
        reqs = JOURNAL_REQUIREMENTS.get(journal_key, JOURNAL_REQUIREMENTS["generic"])
        journal_name = reqs["name"]

        checklist = SubmissionChecklist()

        # Word count checks
        if word_count is not None:
            limit = reqs["word_limit"].get("original", 4000)
            if word_count <= limit:
                checklist.add(
                    "Word Counts",
                    f"Main text: {word_count} words",
                    "pass",
                    f"Limit: {limit}",
                )
            else:
                checklist.add(
                    "Word Counts",
                    f"Main text: {word_count} words",
                    "fail",
                    f"Exceeds limit by {word_count - limit} words (max: {limit})",
                )
        else:
            checklist.add(
                "Word Counts",
                "Main text word count",
                "warning",
                "Not provided — please verify",
            )

        # Abstract count
        if abstract_count is not None:
            limit = reqs.get("abstract_limit", 300)
            if abstract_count <= limit:
                checklist.add(
                    "Word Counts",
                    f"Abstract: {abstract_count} words",
                    "pass",
                    f"Limit: {limit}",
                )
            else:
                checklist.add(
                    "Word Counts",
                    f"Abstract: {abstract_count} words",
                    "fail",
                    f"Exceeds limit by {abstract_count - limit} words (max: {limit})",
                )
        else:
            checklist.add(
                "Word Counts",
                "Abstract word count",
                "warning",
                "Not provided — please verify",
            )

        # Reference count
        if reference_count is not None:
            limit = reqs.get("references_limit", 50)
            if reference_count <= limit:
                checklist.add(
                    "References",
                    f"References: {reference_count}",
                    "pass",
                    f"Limit: {limit}",
                )
            else:
                checklist.add(
                    "References",
                    f"References: {reference_count}",
                    "fail",
                    f"Exceeds limit by {reference_count - limit} (max: {limit})",
                )
        else:
            checklist.add(
                "References",
                "Reference count",
                "warning",
                "Not provided — please verify",
            )

        # Figures
        if figure_count is not None:
            limit = reqs.get("figures_limit", 6)
            if figure_count <= limit:
                checklist.add(
                    "Figures & Tables",
                    f"Figures: {figure_count}",
                    "pass",
                    f"Limit: {limit}",
                )
            else:
                checklist.add(
                    "Figures & Tables",
                    f"Figures: {figure_count}",
                    "fail",
                    f"Exceeds limit (max: {limit})",
                )

        # Tables
        if table_count is not None:
            limit = reqs.get("tables_limit", 5)
            if table_count <= limit:
                checklist.add(
                    "Figures & Tables",
                    f"Tables: {table_count}",
                    "pass",
                    f"Limit: {limit}",
                )
            else:
                checklist.add(
                    "Figures & Tables",
                    f"Tables: {table_count}",
                    "fail",
                    f"Exceeds limit (max: {limit})",
                )

        # Required documents
        if reqs.get("cover_letter"):
            if has_cover_letter:
                checklist.add("Required Documents", "Cover letter", "pass")
            else:
                checklist.add(
                    "Required Documents",
                    "Cover letter",
                    "fail",
                    "Required — use generate_cover_letter",
                )

        if reqs.get("highlights"):
            if has_highlights:
                checklist.add("Required Documents", "Highlights/Key Points", "pass")
            else:
                checklist.add(
                    "Required Documents",
                    "Highlights/Key Points",
                    "fail",
                    "Required for this journal",
                )

        # Required statements
        if reqs.get("ethics_statement"):
            if has_ethics:
                checklist.add("Required Statements", "Ethics approval", "pass")
            else:
                checklist.add(
                    "Required Statements",
                    "Ethics approval",
                    "fail",
                    "Include IRB/Ethics approval number",
                )

        if has_consent:
            checklist.add("Required Statements", "Informed consent", "pass")
        else:
            checklist.add(
                "Required Statements",
                "Informed consent",
                "warning",
                "Verify consent statement is included",
            )

        if reqs.get("conflict_of_interest"):
            if has_coi:
                checklist.add("Required Statements", "Conflict of interest", "pass")
            else:
                checklist.add(
                    "Required Statements",
                    "Conflict of interest",
                    "fail",
                    "Required — even if 'None'",
                )

        if reqs.get("author_contributions"):
            if has_author_contributions:
                checklist.add("Required Statements", "Author contributions", "pass")
            else:
                checklist.add(
                    "Required Statements",
                    "Author contributions",
                    "fail",
                    "Use CRediT taxonomy if applicable",
                )

        if reqs.get("data_availability"):
            if has_data_availability:
                checklist.add("Required Statements", "Data availability", "pass")
            else:
                checklist.add(
                    "Required Statements",
                    "Data availability",
                    "fail",
                    "Required — state if data is available on request",
                )

        # Keywords
        if reqs.get("keywords"):
            if has_keywords:
                checklist.add(
                    "Formatting",
                    "Keywords",
                    "pass",
                    f"Required: {reqs['keywords']}",
                )
            else:
                checklist.add(
                    "Formatting",
                    "Keywords",
                    "warning",
                    f"Include {reqs['keywords']} keywords",
                )

        # ORCID
        orcid_req = reqs.get("orcid", "optional")
        checklist.add(
            "Author Information",
            "ORCID",
            "info",
            f"Requirement: {orcid_req}",
        )

        result = checklist.to_markdown(journal_name)
        log_tool_result(
            "check_submission_checklist",
            f"pass={checklist.pass_count}, fail={checklist.fail_count}",
            success=True,
        )
        return result

    @mcp.tool()
    def list_supported_journals() -> str:
        """
        List all supported journals and their submission requirements.

        Returns:
            Table of supported journals with key requirements.
        """
        log_tool_call("list_supported_journals", {})

        output = "# 📚 Supported Journals\n\n"
        output += "| Code | Journal | Word Limit | Abstract | References | Figures | Tables |\n"
        output += "|------|---------|------------|----------|------------|---------|--------|\n"

        for code, info in JOURNAL_REQUIREMENTS.items():
            if code == "generic":
                continue
            word_limit = info["word_limit"].get("original", "-")
            output += f"| `{code}` | {info['name']} | {word_limit} | {info.get('abstract_limit', '-')} | {info.get('references_limit', '-')} | {info.get('figures_limit', '-')} | {info.get('tables_limit', '-')} |\n"

        output += f"| `generic` | Generic (fallback) | 4000 | 300 | 50 | 6 | 5 |\n"

        output += "\n---\n"
        output += "💡 Use the journal code in `generate_cover_letter` and `check_submission_checklist`.\n"
        output += "📝 Don't see your journal? Use `generic` or request it to be added.\n"

        log_tool_result("list_supported_journals", "success", success=True)
        return output

    @mcp.tool()
    def generate_highlights(
        novelty_statement: str,
        key_findings: str,
        clinical_impact: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Generate bullet-point highlights for journal submission.

        Many journals require 3-5 bullet points highlighting the key findings.
        This tool helps format them properly.

        Args:
            novelty_statement: Main novelty/innovation of the study.
            key_findings: Key findings (comma or newline separated).
            clinical_impact: Clinical implications (optional).
            project: Project slug. If not specified, uses current project.

        Returns:
            Formatted highlights ready for submission.

        Example:
            generate_highlights(
                novelty_statement="First RCT comparing remimazolam to propofol in elderly",
                key_findings="Lower hypotension rate; Faster recovery; Similar efficacy",
                clinical_impact="May reduce perioperative complications in elderly patients"
            )
        """
        log_tool_call(
            "generate_highlights",
            {"project": project},
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        highlights = []

        # Add novelty as first highlight
        if novelty_statement:
            highlights.append(novelty_statement.strip())

        # Parse key findings
        for finding in re.split(r"[,\n;]", key_findings):
            finding = finding.strip()
            if finding and len(highlights) < 5:
                highlights.append(finding)

        # Add clinical impact as last highlight
        if clinical_impact and len(highlights) < 5:
            highlights.append(clinical_impact.strip())

        # Format output
        output = "# Highlights\n\n"

        if len(highlights) < 3:
            output += "⚠️ **Warning**: Most journals require 3-5 highlights.\n\n"

        for i, highlight in enumerate(highlights, 1):
            # Ensure bullet format
            if not highlight.startswith("•"):
                output += f"• {highlight}\n"
            else:
                output += f"{highlight}\n"

        output += "\n---\n"
        output += f"**Total highlights**: {len(highlights)}\n"
        output += "**Recommended**: 3-5 bullet points\n"
        output += "\n💡 Keep each highlight under 125 characters for best readability.\n"

        log_tool_result("generate_highlights", f"{len(highlights)} highlights", success=True)
        return output
