"""
Submission Preparation Data

Journal requirements database used by check_formatting.
Submission preparation tools have been migrated to skills:
  → .claude/skills/submission-preparation/SKILL.md
"""

from dataclasses import dataclass, field
from typing import Any, Optional

# Type alias for journal requirements
JournalReqs = dict[str, Any]

# Common journal requirements database
JOURNAL_REQUIREMENTS: dict[str, JournalReqs] = {
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
