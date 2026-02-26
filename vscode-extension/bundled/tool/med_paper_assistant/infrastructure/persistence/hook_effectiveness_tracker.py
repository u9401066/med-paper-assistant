"""
Hook Effectiveness Tracker — Track and analyze Copilot Hook performance.

Records hook trigger/pass/fix/false-positive events across pipeline runs.
Persists to `.audit/hook-effectiveness.yaml` and generates `.md` reports.

Architecture:
  Infrastructure layer service. Called after each hook evaluation.
  Provides data for Hook D meta-learning analysis.

Design rationale (CONSTITUTION §23):
  - Hook self-improvement requires objective effectiveness metrics
  - Metrics survive across pipeline runs via persistent YAML storage
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

EventType = Literal["trigger", "pass", "fix", "false_positive"]

HOOK_CATEGORIES = {
    "A": "post-write",
    "B": "post-section",
    "C": "post-manuscript",
    "D": "meta-learning",
}


class HookEffectivenessTracker:
    """
    Track hook trigger/pass/fix/false-positive events.

    Usage:
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")
        tracker.record_event("A3", "trigger")
        tracker.record_event("A3", "fix")
        report = tracker.generate_report()
    """

    DATA_FILE = "hook-effectiveness.yaml"
    REPORT_FILE = "hook-effectiveness.md"

    def __init__(self, audit_dir: str | Path) -> None:
        self._audit_dir = Path(audit_dir)
        self._data_path = self._audit_dir / self.DATA_FILE
        self._report_path = self._audit_dir / self.REPORT_FILE
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        """Load or initialize tracking data."""
        if self._data is not None:
            return self._data

        if self._data_path.is_file():
            try:
                loaded = yaml.safe_load(self._data_path.read_text(encoding="utf-8"))
                if loaded is None:
                    loaded = {}
                self._data = loaded
                return loaded
            except (yaml.YAMLError, OSError) as e:
                logger.warning("Failed to load hook effectiveness data: %s", e)

        self._data = {
            "version": 1,
            "hooks": {},
            "runs": [],
            "created_at": datetime.now().isoformat(),
        }
        return self._data

    def _save(self) -> None:
        """Persist tracking data to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["updated_at"] = datetime.now().isoformat()
        self._data_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def record_event(self, hook_id: str, event_type: EventType) -> None:
        """
        Record a hook event.

        Args:
            hook_id: Hook identifier (e.g., "A1", "B5", "C3")
            event_type: One of "trigger", "pass", "fix", "false_positive"
        """
        data = self._load()
        if hook_id not in data["hooks"]:
            data["hooks"][hook_id] = {
                "trigger": 0,
                "pass": 0,
                "fix": 0,
                "false_positive": 0,
            }
        data["hooks"][hook_id][event_type] += 1
        self._save()

    def record_run(self, run_id: str, hook_results: dict[str, dict[str, int]]) -> None:
        """
        Record a complete pipeline run's hook results.

        Args:
            run_id: Pipeline run identifier (e.g., "20260223-1430")
            hook_results: {hook_id: {trigger: N, pass: N, fix: N, false_positive: N}}
        """
        data = self._load()
        data["runs"].append(
            {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "results": hook_results,
            }
        )

        # Also accumulate into aggregate stats
        for hook_id, counts in hook_results.items():
            if hook_id not in data["hooks"]:
                data["hooks"][hook_id] = {"trigger": 0, "pass": 0, "fix": 0, "false_positive": 0}
            for event_type, count in counts.items():
                if event_type in data["hooks"][hook_id]:
                    data["hooks"][hook_id][event_type] += count

        self._save()

    def get_stats(self, hook_id: str | None = None) -> dict[str, Any]:
        """
        Get effectiveness statistics for one or all hooks.

        Returns dict with trigger_rate, pass_rate, fix_rate, false_positive_rate.
        """
        data = self._load()

        if hook_id:
            raw = data["hooks"].get(hook_id, {})
            return self._compute_rates(hook_id, raw)

        result = {}
        for hid, raw in data["hooks"].items():
            result[hid] = self._compute_rates(hid, raw)
        return result

    def _compute_rates(self, hook_id: str, raw: dict[str, int]) -> dict[str, Any]:
        """Compute rates from raw counts."""
        trigger = raw.get("trigger", 0)
        passed = raw.get("pass", 0)
        fix = raw.get("fix", 0)
        false_pos = raw.get("false_positive", 0)

        total_evaluations = trigger + passed  # triggered + clean passes
        return {
            "hook_id": hook_id,
            "trigger": trigger,
            "pass": passed,
            "fix": fix,
            "false_positive": false_pos,
            "trigger_rate": trigger / total_evaluations if total_evaluations > 0 else 0.0,
            "fix_rate": fix / trigger if trigger > 0 else 0.0,
            "false_positive_rate": false_pos / trigger if trigger > 0 else 0.0,
        }

    def get_recommendations(self) -> list[dict[str, Any]]:
        """
        Analyze stats and generate recommendations per CONSTITUTION §23.

        Returns list of recommendation dicts with:
            hook_id, type ("loosen"|"tighten"|"remove"|"fix_logic"), reason, confidence
        """
        recommendations = []
        all_stats = self.get_stats()

        for hook_id, stats in all_stats.items():
            total_evals = stats["trigger"] + stats["pass"]

            # §23: trigger_rate > 80% → too strict
            if total_evals >= 5 and stats["trigger_rate"] > 0.80:
                recommendations.append(
                    {
                        "hook_id": hook_id,
                        "type": "loosen",
                        "reason": f"Trigger rate {stats['trigger_rate']:.0%} > 80% — threshold too strict",
                        "confidence": "high" if total_evals >= 10 else "medium",
                    }
                )

            # §23: trigger_rate < 5% over 5+ evaluations → too loose or redundant
            if total_evals >= 5 and stats["trigger_rate"] < 0.05:
                recommendations.append(
                    {
                        "hook_id": hook_id,
                        "type": "tighten",
                        "reason": f"Trigger rate {stats['trigger_rate']:.0%} < 5% over {total_evals} evaluations — may be too loose or redundant",
                        "confidence": "medium",
                    }
                )

            # §23: false_positive_rate > 30% → needs logic fix
            if stats["trigger"] >= 3 and stats["false_positive_rate"] > 0.30:
                recommendations.append(
                    {
                        "hook_id": hook_id,
                        "type": "fix_logic",
                        "reason": f"False positive rate {stats['false_positive_rate']:.0%} > 30% — judgment criteria need correction",
                        "confidence": "high",
                    }
                )

            # Fix rate 0% with multiple triggers → fix logic isn't working
            if stats["trigger"] >= 3 and stats["fix_rate"] == 0.0:
                recommendations.append(
                    {
                        "hook_id": hook_id,
                        "type": "fix_logic",
                        "reason": f"0% fix rate after {stats['trigger']} triggers — auto-fix mechanism may be broken",
                        "confidence": "medium",
                    }
                )

        return recommendations

    def generate_report(self) -> str:
        """
        Generate a Markdown report of hook effectiveness.
        Also writes the report to .audit/hook-effectiveness.md.
        """
        all_stats = self.get_stats()
        recommendations = self.get_recommendations()

        lines = [
            "# Hook Effectiveness Report",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
            "| Hook | Category | Triggers | Passes | Fixes | False+ | Trigger Rate | Fix Rate | FP Rate |",
            "|------|----------|----------|--------|-------|--------|-------------|----------|---------|",
        ]

        for hook_id in sorted(all_stats.keys()):
            s = all_stats[hook_id]
            cat_key = hook_id[0] if hook_id else "?"
            cat = HOOK_CATEGORIES.get(cat_key, "unknown")
            lines.append(
                f"| {hook_id} | {cat} | {s['trigger']} | {s['pass']} | "
                f"{s['fix']} | {s['false_positive']} | "
                f"{s['trigger_rate']:.0%} | {s['fix_rate']:.0%} | "
                f"{s['false_positive_rate']:.0%} |"
            )

        if recommendations:
            lines.extend(
                [
                    "",
                    "## Recommendations (CONSTITUTION §23)",
                    "",
                ]
            )
            for rec in recommendations:
                icon = {"loosen": "⬇️", "tighten": "⬆️", "fix_logic": "🔧", "remove": "🗑️"}.get(
                    rec["type"], "❓"
                )
                lines.append(
                    f"- {icon} **{rec['hook_id']}** [{rec['type']}] "
                    f"({rec['confidence']}): {rec['reason']}"
                )

        report = "\n".join(lines) + "\n"

        # Write report file
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report, encoding="utf-8")

        return report

    def get_run_count(self) -> int:
        """Number of recorded pipeline runs."""
        return len(self._load().get("runs", []))

    def reset(self) -> None:
        """Clear all tracking data (for testing)."""
        self._data = None
        for path in (self._data_path, self._report_path):
            if path.is_file():
                path.unlink()
