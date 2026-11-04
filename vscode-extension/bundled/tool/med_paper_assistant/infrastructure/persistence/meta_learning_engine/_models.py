"""Value objects produced by the meta-learning analyses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Threshold adjustment limits (CONSTITUTION §23)
MAX_THRESHOLD_ADJUSTMENT = 0.20  # ±20%


class ThresholdAdjustment:
    """A recommended threshold change."""

    def __init__(
        self,
        hook_id: str,
        parameter: str,
        current_value: float,
        suggested_value: float,
        reason: str,
        auto_apply: bool = True,
    ) -> None:
        self.hook_id = hook_id
        self.parameter = parameter
        self.current_value = current_value
        self.suggested_value = suggested_value
        self.reason = reason
        self.auto_apply = auto_apply

    @property
    def change_pct(self) -> float:
        """Percentage change from current to suggested."""
        if self.current_value == 0:
            return 0.0
        return (self.suggested_value - self.current_value) / self.current_value

    @property
    def within_bounds(self) -> bool:
        """Check if adjustment is within ±20% limit."""
        return abs(self.change_pct) <= MAX_THRESHOLD_ADJUSTMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "parameter": self.parameter,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "change_pct": f"{self.change_pct:+.0%}",
            "within_bounds": self.within_bounds,
            "auto_apply": self.auto_apply and self.within_bounds,
            "reason": self.reason,
        }


class LessonLearned:
    """A lesson to record in the auto-paper skill's references/lessons-learned.md."""

    def __init__(
        self,
        category: str,
        lesson: str,
        source: str,
        severity: str = "info",
    ) -> None:
        self.category = category  # e.g., "hook_tuning", "writing_pattern", "tool_usage"
        self.lesson = lesson
        self.source = source  # e.g., "D1 analysis", "D3 threshold adjustment"
        self.severity = severity  # "info", "warning", "critical"
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "lesson": self.lesson,
            "source": self.source,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}.get(self.severity, "•")
        return f"- {icon} **[{self.category}]** {self.lesson} _(source: {self.source}, {self.timestamp[:10]})_"
