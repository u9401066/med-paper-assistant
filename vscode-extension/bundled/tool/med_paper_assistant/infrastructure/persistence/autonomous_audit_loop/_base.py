"""Typed instance-state declarations shared by the audit-loop mixins."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._models import AuditFix, AuditIssue, AuditLoopConfig, RoundRecord


class LoopState:
    """Declares the instance attributes that ``AutonomousAuditLoop.__init__`` creates."""

    if TYPE_CHECKING:
        _audit_dir: Path
        _config: AuditLoopConfig
        _data_path: Path
        _report_path: Path
        _rounds: list[RoundRecord]
        _current_issues: list[AuditIssue]
        _current_fixes: list[AuditFix]
        _current_round: int
        _in_round: bool
        _round_start_time: str
        _completed: bool
        _rewrite_sections: list[str]
        _rewrite_reason: str
