"""Writing Hooks — Shared data models (HookIssue, HookResult)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
