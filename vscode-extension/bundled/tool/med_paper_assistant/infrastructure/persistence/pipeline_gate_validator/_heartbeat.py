"""Lightweight pipeline heartbeat: per-phase status without running the hard gates."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ._constants import _PIPELINE_PHASE_NAMES, _PIPELINE_PHASES
from ._heartbeat_early import HeartbeatEarlyMixin
from ._heartbeat_late import HeartbeatLateMixin
from ._types import GateCheck, GateResult


class HeartbeatMixin(HeartbeatEarlyMixin, HeartbeatLateMixin):
    """Pipeline status snapshot built from cheap artifact checks."""

    def get_pipeline_status(self) -> dict[str, Any]:
        """
        Get lightweight pipeline status — heartbeat check.

        Returns current state across ALL phases:
        - Which phases appear complete from cheap artifact snapshots
        - What key artifacts exist
        - What's missing at a glance
        - Completion percentage

        This is intentionally not a full gate validation. Heartbeat must be
        fast and non-blocking, so it must not call validate_phase(), run Git,
        execute hooks, or append gate validation audit logs. Use
        validate_phase() for the authoritative hard gate.
        """
        results = []
        total_critical = 0
        total_passed = 0

        for phase in _PIPELINE_PHASES:
            result = self._heartbeat_phase_snapshot(phase)
            critical_count = len(result.critical_failures)
            total_critical += critical_count
            if result.passed:
                total_passed += 1
            results.append(
                {
                    "phase": phase,
                    "name": _PIPELINE_PHASE_NAMES.get(phase, "Unknown"),
                    "passed": result.passed,
                    "critical_failures": critical_count,
                    "warnings": len(result.warnings),
                    "details": [
                        {"check": c.name, "passed": c.passed, "details": c.details}
                        for c in result.checks
                        if not c.passed
                    ],
                }
            )

        completion_pct = (total_passed / len(_PIPELINE_PHASES)) * 100

        return {
            "completion_pct": round(completion_pct, 1),
            "phases_passed": total_passed,
            "phases_total": len(_PIPELINE_PHASES),
            "total_critical_failures": total_critical,
            "phases": results,
            "timestamp": datetime.now().isoformat(),
        }

    def _heartbeat_phase_snapshot(self, phase: int) -> GateResult:
        """Build a cheap, side-effect-free phase status snapshot."""
        checks = []
        if phase > 1:
            checks.extend(self._check_prerequisites(phase))
        checks.extend(self._heartbeat_phase_checks(phase))
        result = GateResult(
            phase=phase,
            phase_name=_PIPELINE_PHASE_NAMES.get(phase, "Unknown"),
            checks=checks,
            passed=False,
            timestamp=datetime.now().isoformat(),
        )
        result.passed = len(result.critical_failures) == 0
        return result

    def _heartbeat_phase_checks(self, phase: int) -> list[GateCheck]:
        """Cheap artifact checks used by heartbeat only.

        These checks deliberately avoid Git, hook execution, manifest/data
        provenance validation, and audit-log writes. They are a navigation aid,
        not the final source of truth.
        """
        handlers = {
            0: self._heartbeat_phase_0,
            1: self._heartbeat_phase_1,
            2: self._heartbeat_phase_2,
            21: self._heartbeat_phase_21,
            3: self._heartbeat_phase_3,
            4: self._heartbeat_phase_4,
            5: self._heartbeat_phase_5,
            6: self._heartbeat_phase_6,
            65: self._heartbeat_phase_65,
            7: self._heartbeat_phase_7,
            8: self._heartbeat_phase_8,
            9: self._heartbeat_phase_9,
            10: self._heartbeat_phase_10,
            11: self._heartbeat_phase_11,
        }
        handler = handlers.get(phase)
        return handler() if handler is not None else []
