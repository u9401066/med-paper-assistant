"""Phase 10 gate: retrospective artifacts (D1-D9) with data validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from ._base import GateBase
from ._constants import _META_LEARNING_STEPS
from ._types import GateCheck, GateResult

_AUDIT_FLAG_LABELS = (
    "schema mdpaper.meta_learning_audit.v2",
    "source_tool run_meta_learning",
    "analysis counts",
    "analysis_steps D1-D9",
    "count/list consistency",
    "matching evolution-log provenance",
)


def _read_meta_events(elog: Path) -> tuple[bool, list[dict[str, Any]]]:
    has_meta = False
    meta_events: list[dict[str, Any]] = []
    if elog.is_file():
        try:
            for line in elog.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    entry = json.loads(line)
                    if isinstance(entry, dict) and entry.get("event") == "meta_learning":
                        meta_events.append(entry)
                        if entry.get("source_tool") == "run_meta_learning":
                            has_meta = True
        except (json.JSONDecodeError, OSError):
            pass
    return has_meta, meta_events


def _audit_entry_flags(
    latest_entry: Any, meta_events: list[dict[str, Any]]
) -> tuple[bool, bool, bool, bool, bool, bool]:
    has_counts = all(
        k in latest_entry for k in ("adjustments_count", "lessons_count", "suggestions_count")
    )
    has_schema = latest_entry.get("schema") == "mdpaper.meta_learning_audit.v2"
    has_source = latest_entry.get("source_tool") == "run_meta_learning"
    steps = latest_entry.get("analysis_steps", {})
    has_steps = isinstance(steps, dict) and all(step in steps for step in _META_LEARNING_STEPS)
    counts_match = (
        latest_entry.get("adjustments_count", 0) == len(latest_entry.get("adjustments", []) or [])
        and latest_entry.get("lessons_count", 0) == len(latest_entry.get("lessons", []) or [])
        and latest_entry.get("suggestions_count", 0)
        == len(latest_entry.get("suggestions", []) or [])
    )
    matching_event = any(
        event.get("source_tool") == "run_meta_learning"
        and event.get("audit_timestamp") == latest_entry.get("timestamp")
        and event.get("adjustments_count") == latest_entry.get("adjustments_count")
        and event.get("lessons_count") == latest_entry.get("lessons_count")
        and event.get("suggestions_count") == latest_entry.get("suggestions_count")
        for event in meta_events
    )
    return has_schema, has_source, has_counts, has_steps, counts_match, matching_event


def _evaluate_audit_data(data: Any, meta_events: list[dict[str, Any]]) -> tuple[bool, str]:
    if not (isinstance(data, list) and len(data) > 0):
        return False, "meta-learning-audit.yaml exists but empty or invalid format"

    latest_entry = data[-1]
    flags = _audit_entry_flags(latest_entry, meta_events)
    if all(flags):
        return True, (
            f"{len(data)} analysis entries, latest: "
            f"adj={latest_entry.get('adjustments_count', 0)}, "
            f"lessons={latest_entry.get('lessons_count', 0)}, "
            f"suggestions={latest_entry.get('suggestions_count', 0)}"
        )

    missing = [label for label, ok in zip(_AUDIT_FLAG_LABELS, flags, strict=True) if not ok]
    return False, "meta-learning-audit.yaml exists but entry missing " + ", ".join(missing)


def _meta_learning_audit_check(mla_yaml: Path, meta_events: list[dict[str, Any]]) -> GateCheck:
    mla_has_data = False
    mla_details = "MISSING meta-learning-audit.yaml — call run_meta_learning()"

    if mla_yaml.is_file():
        try:
            data = yaml.safe_load(mla_yaml.read_text(encoding="utf-8"))
            mla_has_data, mla_details = _evaluate_audit_data(data, meta_events)
        except (yaml.YAMLError, OSError, TypeError):
            mla_details = "meta-learning-audit.yaml exists but cannot be parsed"

    return GateCheck(
        name="meta-learning-audit:data",
        description="Meta-learning audit has ≥1 analysis entry (run_meta_learning required)",
        passed=mla_has_data,
        details=mla_details,
    )


class RetrospectivePhaseMixin(GateBase):
    """Validation of Phase 10 (retrospective).

    Required: pipeline-run-{ts}.md (with D7+D8 sections), hook-effectiveness.md (D1),
    meta-learning-audit.yaml with actual analysis data, an evolution-log.jsonl
    meta_learning event, and updated .memory/ files.
    """

    def _validate_phase_10(self) -> GateResult:
        """Phase 10: Retrospective — D1-D9 artifacts with DATA validation."""
        checks = []

        checks.extend(self._pipeline_run_checks())

        # 2. hook-effectiveness.md
        he = self._audit_dir / "hook-effectiveness.md"
        checks.append(
            GateCheck(
                name="hook-effectiveness.md",
                description="Hook effectiveness report (D1)",
                passed=he.is_file(),
                details="exists" if he.is_file() else "MISSING",
            )
        )

        # 3. evolution-log.jsonl with meta_learning event
        has_meta, meta_events = _read_meta_events(self._audit_dir / "evolution-log.jsonl")
        checks.append(
            GateCheck(
                name="evolution-log:meta_learning",
                description="evolution-log.jsonl contains run_meta_learning event (D6)",
                passed=has_meta,
                details="found" if has_meta else "MISSING source_tool=run_meta_learning event",
            )
        )

        # 4. meta-learning-audit.yaml DATA validation
        checks.append(
            _meta_learning_audit_check(self._audit_dir / "meta-learning-audit.yaml", meta_events)
        )

        # 5. .memory/ files
        for mem_file in ["activeContext.md", "progress.md"]:
            p = self._memory_dir / mem_file
            checks.append(
                GateCheck(
                    name=f"memory:{mem_file}",
                    description=f"Project memory file {mem_file}",
                    passed=p.is_file(),
                    details="exists" if p.is_file() else "MISSING",
                    severity="WARNING",
                )
            )

        return GateResult(phase=10, phase_name="Retrospective", checks=checks, passed=False)

    def _pipeline_run_checks(self) -> list[GateCheck]:
        pipeline_runs = list(self._audit_dir.glob("pipeline-run-*.md"))
        found_candidates = self._find_pipeline_run_candidates()
        checks = [
            GateCheck(
                name="pipeline-run.md",
                description="Pipeline run retrospective document",
                passed=len(pipeline_runs) > 0,
                details=f"{len(pipeline_runs)} run(s)"
                if pipeline_runs
                else (
                    "MISSING — need `.audit/pipeline-run-*.md`"
                    if not found_candidates
                    else "MISSING — found pipeline-run-like file(s) with wrong name/location"
                ),
                expected_pattern="pipeline-run-*.md",
                search_path=".audit/pipeline-run-*.md",
                actual_found=found_candidates,
                fix_hint="Create or rename to `.audit/pipeline-run-YYYYMMDD-HHmm.md`.",
            )
        ]

        # Check latest pipeline-run has D7 and D8 sections
        if pipeline_runs:
            latest = sorted(pipeline_runs)[-1]
            content = latest.read_text(encoding="utf-8")
            for section in ["D7", "D8"]:
                checks.append(self._retrospective_section_check(latest, content, section))
        return checks

    def _retrospective_section_check(self, latest: Path, content: str, section: str) -> GateCheck:
        expected = rf"^##\s+{section}\s+retrospective\s*:"
        found = bool(re.search(expected, content, re.IGNORECASE | re.MULTILINE))
        actual_headings = self._extract_matching_headings(content, section)
        return GateCheck(
            name=f"pipeline-run:{section}",
            description=f"{section} retrospective section in pipeline run",
            passed=found,
            details="found"
            if found
            else f"MISSING — latest file `{latest.name}` lacks required heading",
            expected_pattern=expected,
            search_path=f".audit/{latest.name}",
            actual_found=actual_headings,
            fix_hint=(
                f"Add heading `## {section} retrospective: "
                f"{section} Retrospective` to `.audit/{latest.name}`."
            ),
        )

    def _find_pipeline_run_candidates(self) -> list[str]:
        """Find pipeline-run-like files that almost satisfy Phase 10 naming."""
        candidates: list[str] = []
        for base in (self._audit_dir, self._project_dir):
            if not base.is_dir():
                continue
            for path in sorted(base.glob("pipeline-run*.md")):
                try:
                    candidates.append(path.relative_to(self._project_dir).as_posix())
                except ValueError:
                    candidates.append(path.as_posix())
        return candidates

    def _extract_matching_headings(self, content: str, marker: str) -> list[str]:
        """Extract markdown headings that mention a marker such as D7 or D8."""
        pattern = re.compile(rf"^#+\s+.*\b{re.escape(marker)}\b.*$", re.MULTILINE)
        return [match.group(0).strip() for match in pattern.finditer(content)]
