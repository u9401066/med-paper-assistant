"""Data models for medRxiv pre-submission screening."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScreeningIssue:
    """A single medRxiv screening issue."""

    category: str
    severity: str  # "error", "warning", "info"
    description: str
    suggestion: Optional[str] = None


@dataclass
class ScreeningReport:
    """Aggregated medRxiv screening report."""

    issues: list[ScreeningIssue] = field(default_factory=list)

    def add(
        self,
        category: str,
        severity: str,
        description: str,
        suggestion: Optional[str] = None,
    ):
        self.issues.append(
            ScreeningIssue(
                category=category,
                severity=severity,
                description=description,
                suggestion=suggestion,
            )
        )

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_summary(self) -> str:
        """One-line summary for embedding in check_formatting report."""
        total = len(self.issues)
        if total == 0:
            return "✅ All medRxiv screening checks passed"
        return (
            f"❌ {self.error_count} errors, ⚠️ {self.warning_count} warnings, "
            f"ℹ️ {total - self.error_count - self.warning_count} info"
        )
