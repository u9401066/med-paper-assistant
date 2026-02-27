"""
Quality Scorecard — Quantitative quality assessment for manuscripts.

Tracks quality scores across multiple dimensions (0-10 scale).
Persists to `.audit/quality-scorecard.json` and generates `.md` reports.

Architecture:
  Infrastructure layer service. Called after Phase 6 (Hook C) and Phase 7 (Review).
  Consumed by Hook D for meta-learning and by Review for quality threshold checks.

Dimensions (from auto-paper SKILL.md):
  - citation_quality: Citation relevance, recency, coverage
  - methodology_reproducibility: Can another researcher replicate?
  - text_quality: Clarity, flow, specificity (vs generic AI filler)
  - concept_consistency: Alignment with concept.md and 🔒 protected content
  - format_compliance: Journal-profile conformance
  - figure_table_quality: Informative, correctly labeled, referenced in text
  - equator_compliance: CONSORT/STROBE/PRISMA/CARE checklist adherence
  - reproducibility_data_availability: Data/code sharing, protocol registration
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

DIMENSIONS = [
    "citation_quality",
    "methodology_reproducibility",
    "text_quality",
    "concept_consistency",
    "format_compliance",
    "figure_table_quality",
    "equator_compliance",
    "reproducibility_data_availability",
]


class QualityScorecard:
    """
    Track and persist quality scores for a manuscript.

    Usage:
        sc = QualityScorecard(audit_dir)
        sc.set_score("text_quality", 7, "Clear writing, minimal AI filler")
        sc.set_score("citation_quality", 8, "15 refs, all recent and relevant")
        report = sc.generate_report()
        ok = sc.meets_threshold(7)
    """

    DATA_FILE = "quality-scorecard.yaml"
    REPORT_FILE = "quality-scorecard.md"

    def __init__(self, audit_dir: str | Path) -> None:
        self._audit_dir = Path(audit_dir)
        self._data_path = self._audit_dir / self.DATA_FILE
        self._report_path = self._audit_dir / self.REPORT_FILE
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
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
                logger.warning("Failed to load quality scorecard: %s", e)

        self._data = {
            "version": 1,
            "scores": {},
            "history": [],
            "created_at": datetime.now().isoformat(),
        }
        return self._data

    def _save(self) -> None:
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["updated_at"] = datetime.now().isoformat()
        self._data_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def set_score(self, dimension: str, score: int | float, explanation: str = "") -> None:
        """
        Set a quality score for a dimension.

        Args:
            dimension: One of DIMENSIONS (or custom)
            score: 0-10 scale
            explanation: Why this score was given
        """
        if not 0 <= score <= 10:
            raise ValueError(f"Score must be 0-10, got {score}")

        data = self._load()
        old_score = data["scores"].get(dimension, {}).get("score")

        data["scores"][dimension] = {
            "score": score,
            "explanation": explanation,
            "updated_at": datetime.now().isoformat(),
        }

        # Track score changes in history
        data["history"].append(
            {
                "dimension": dimension,
                "old_score": old_score,
                "new_score": score,
                "explanation": explanation,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._save()

    def get_score(self, dimension: str) -> float | None:
        """Get the current score for a dimension, or None if not set."""
        data = self._load()
        entry = data["scores"].get(dimension)
        return entry["score"] if entry else None

    def get_scorecard(self) -> dict[str, Any]:
        """Get the full scorecard with all dimensions and computed total."""
        data = self._load()
        scores = data["scores"]

        scored_dims = {k: v["score"] for k, v in scores.items() if "score" in v}
        total = sum(scored_dims.values()) / len(scored_dims) if scored_dims else 0.0

        return {
            "dimensions": scores,
            "scored_count": len(scored_dims),
            "total_dimensions": len(DIMENSIONS),
            "average_score": round(total, 1),
            "min_score": min(scored_dims.values()) if scored_dims else None,
            "max_score": max(scored_dims.values()) if scored_dims else None,
            "missing_dimensions": [d for d in DIMENSIONS if d not in scores],
        }

    def meets_threshold(self, threshold: float) -> bool:
        """Check if the average score meets or exceeds the threshold."""
        sc = self.get_scorecard()
        return sc["average_score"] >= threshold

    def get_weak_dimensions(self, min_score: float = 6.0) -> list[dict[str, Any]]:
        """Get dimensions scoring below min_score."""
        data = self._load()
        weak = []
        for dim, entry in data["scores"].items():
            if entry["score"] < min_score:
                weak.append(
                    {
                        "dimension": dim,
                        "score": entry["score"],
                        "explanation": entry.get("explanation", ""),
                    }
                )
        return sorted(weak, key=lambda x: x["score"])

    def generate_report(self) -> str:
        """Generate a Markdown report. Also writes to .audit/quality-scorecard.md."""
        sc = self.get_scorecard()
        data = self._load()

        lines = [
            "# Quality Scorecard",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Scores",
            "",
            "| Dimension | Score (0-10) | Explanation |",
            "|-----------|:------------:|-------------|",
        ]

        for dim in DIMENSIONS:
            entry = data["scores"].get(dim)
            if entry:
                score_str = f"{entry['score']}"
                expl = entry.get("explanation", "")
                # Visual indicator
                if entry["score"] >= 8:
                    icon = "🟢"
                elif entry["score"] >= 6:
                    icon = "🟡"
                else:
                    icon = "🔴"
                lines.append(f"| {dim} | {icon} {score_str} | {expl} |")
            else:
                lines.append(f"| {dim} | ⬜ — | Not yet evaluated |")

        # Custom dimensions (not in standard list)
        for dim, entry in data["scores"].items():
            if dim not in DIMENSIONS:
                score_str = f"{entry['score']}"
                lines.append(f"| {dim} (custom) | {score_str} | {entry.get('explanation', '')} |")

        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"- **Average Score**: {sc['average_score']}",
                f"- **Min / Max**: {sc['min_score']} / {sc['max_score']}",
                f"- **Scored**: {sc['scored_count']} / {sc['total_dimensions']} dimensions",
            ]
        )

        if sc["missing_dimensions"]:
            lines.append(f"- **Missing**: {', '.join(sc['missing_dimensions'])}")

        weak = self.get_weak_dimensions()
        if weak:
            lines.extend(["", "## ⚠️ Weak Dimensions (< 6.0)", ""])
            for w in weak:
                lines.append(f"- **{w['dimension']}**: {w['score']} — {w['explanation']}")

        # Score history (last 10)
        history = data.get("history", [])[-10:]
        if history:
            lines.extend(["", "## Recent Changes", ""])
            for h in history:
                old = h.get("old_score")
                new = h["new_score"]
                change = f"{old} → {new}" if old is not None else f"→ {new}"
                lines.append(f"- **{h['dimension']}**: {change}")

        report = "\n".join(lines) + "\n"

        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report, encoding="utf-8")

        return report

    def reset(self) -> None:
        """Clear all data (for testing)."""
        self._data = None
        for path in (self._data_path, self._report_path):
            if path.is_file():
                path.unlink()
