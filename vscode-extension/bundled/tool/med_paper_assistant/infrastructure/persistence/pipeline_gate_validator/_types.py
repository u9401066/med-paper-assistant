"""Result types returned by the pipeline gate validator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GateCheck:
    """A single gate check item."""

    name: str
    description: str
    passed: bool
    details: str = ""
    severity: str = "CRITICAL"  # CRITICAL = blocks, WARNING = advisory
    expected_pattern: str = ""
    search_path: str = ""
    actual_found: list[str] = field(default_factory=list)
    fix_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize check with agent-actionable repair metadata."""
        data: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "passed": self.passed,
            "severity": self.severity,
            "details": self.details,
        }
        if self.expected_pattern:
            data["expected_pattern"] = self.expected_pattern
        if self.search_path:
            data["search_path"] = self.search_path
        if self.actual_found:
            data["actual_found"] = self.actual_found
        if self.fix_hint:
            data["fix_hint"] = self.fix_hint
        return data


@dataclass
class GateResult:
    """Result of a phase gate validation."""

    phase: int
    phase_name: str
    passed: bool
    checks: list[GateCheck] = field(default_factory=list)
    timestamp: str = ""

    @property
    def critical_failures(self) -> list[GateCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "CRITICAL"]

    @property
    def warnings(self) -> list[GateCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "WARNING"]

    @property
    def missing(self) -> list[str]:
        """Return names of failed critical checks for agent-friendly repair loops."""
        return [c.name for c in self.critical_failures]

    def to_dict(self, compact: bool = False) -> dict[str, Any]:
        """Serialize gate result for agent consumption."""
        checks = self.checks
        if compact:
            checks = [c for c in checks if not c.passed]
        return {
            "schema": "mdpaper.gate_result.v1",
            "phase": self.phase,
            "phase_name": self.phase_name,
            "passed": self.passed,
            "critical_failures": len(self.critical_failures),
            "warnings": len(self.warnings),
            "timestamp": self.timestamp,
            "checks": [c.to_dict() for c in checks],
        }

    def to_json(self, compact: bool = False) -> str:
        """Generate a JSON report of the gate result."""
        return json.dumps(self.to_dict(compact=compact), indent=2, ensure_ascii=False)

    def to_markdown(self, compact: bool = False) -> str:
        """Generate a markdown report of the gate result."""
        lines = [
            f"# Phase {self.phase} Gate Validation: {'✅ PASSED' if self.passed else '❌ FAILED'}",
            f"**Phase**: {self.phase_name}",
            f"**Timestamp**: {self.timestamp}",
            "",
            "| # | Check | Status | Severity | Details |",
            "|---|-------|--------|----------|---------|",
        ]
        checks = self.checks if not compact else [c for c in self.checks if not c.passed]
        for i, c in enumerate(checks, 1):
            status = "✅" if c.passed else "❌"
            detail_bits = [c.details]
            if c.expected_pattern:
                detail_bits.append(f"expected_pattern: `{c.expected_pattern}`")
            if c.search_path:
                detail_bits.append(f"search_path: `{c.search_path}`")
            if c.actual_found:
                detail_bits.append(f"actual_found: {', '.join(c.actual_found)}")
            if c.fix_hint:
                detail_bits.append(f"fix_hint: {c.fix_hint}")
            details = "<br>".join(bit for bit in detail_bits if bit)
            lines.append(f"| {i} | {c.name} | {status} | {c.severity} | {details} |")

        if self.critical_failures:
            lines.extend(
                [
                    "",
                    "## ❌ BLOCKING: Cannot proceed to next phase",
                    "",
                ]
            )
            for f in self.critical_failures:
                lines.append(f"- **{f.name}**: {f.description}")

        return "\n".join(lines)
