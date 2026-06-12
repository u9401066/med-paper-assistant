"""Tests for ConstraintLedger — the monotonic convergence ratchet.

Covers both normal behavior and ADVERSARIAL attempts to game the ratchet:
- silently dropping a constraint must be impossible (no delete API),
- waiving without a reason must be rejected,
- re-opening without a reason must be rejected,
- re-adding the same issue must be idempotent (no churn),
- convergence is defined strictly as zero OPEN constraints.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.constraint_ledger import (
    STATUS_OPEN,
    STATUS_SATISFIED,
    ConstraintLedger,
)


@pytest.fixture()
def audit_dir(tmp_path: Path) -> Path:
    d = tmp_path / "proj" / ".audit"
    d.mkdir(parents=True)
    return d


class TestBasics:
    def test_add_creates_open_constraint(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("P7", "Malformed DOI on smith2024", severity="CRITICAL")
        assert c.status == STATUS_OPEN
        assert led.summary()["open"] == 1
        assert not led.is_converged()

    def test_satisfy_resolves(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("B13", "Missing limitations paragraph", severity="CRITICAL")
        assert led.satisfy(c.key, reason="added limitations section") is True
        assert led.get(c.key).status == STATUS_SATISFIED
        assert led.is_converged()

    def test_converged_only_when_zero_open(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        a = led.add("A3", "AI filler phrase", severity="WARNING")
        b = led.add("C3", "N mismatch", severity="CRITICAL")
        assert not led.is_converged()
        led.satisfy(a.key)
        assert not led.is_converged()  # b still open
        led.waive(b.key, reason="accepted: N differs because of dropout, explained in text")
        assert led.is_converged()  # satisfied + waived => no open


class TestRatchet:
    """The ledger must only move forward; resolutions cannot vanish silently."""

    def test_no_delete_api(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        # A silent "remove" must not exist — the ratchet forbids it.
        assert not hasattr(led, "delete")
        assert not hasattr(led, "remove")

    def test_add_is_idempotent(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c1 = led.add("P7", "Malformed DOI on smith2024", severity="CRITICAL")
        c2 = led.add("P7", "Malformed DOI on smith2024", severity="CRITICAL")
        assert c1.key == c2.key
        assert led.summary()["total"] == 1

    def test_readding_does_not_reset_resolution(self, audit_dir: Path) -> None:
        """Re-running a hook must NOT silently reopen a satisfied constraint."""
        led = ConstraintLedger(audit_dir)
        c = led.add("B14", "No ethics statement", severity="CRITICAL")
        led.satisfy(c.key, reason="added IRB statement")
        # Hook fires again and tries to add the same issue:
        led.add("B14", "No ethics statement", severity="CRITICAL")
        assert led.get(c.key).status == STATUS_SATISFIED  # unchanged
        assert led.is_converged()

    def test_waive_requires_reason(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("B9", "Present tense in Methods", severity="CRITICAL")
        with pytest.raises(ValueError, match="reason"):
            led.waive(c.key, reason="")

    def test_reopen_requires_reason(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("B12", "Results preview in intro", severity="CRITICAL")
        led.satisfy(c.key, reason="removed preview")
        with pytest.raises(ValueError, match="reason"):
            led.reopen(c.key, reason="")

    def test_reopen_with_reason_breaks_convergence(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("A6", "Duplicated paragraph", severity="WARNING")
        led.satisfy(c.key, reason="de-duplicated")
        assert led.is_converged()
        # A later edit regressed it — must be re-openable WITH a reason.
        assert led.reopen(c.key, reason="edit reintroduced the duplicate") is True
        assert not led.is_converged()

    def test_history_is_recorded(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("P7", "Malformed DOI", severity="CRITICAL")
        led.satisfy(c.key, reason="fixed")
        hist = led.get(c.key).history
        actions = [h["action"] for h in hist]
        assert "opened" in actions
        assert "open->satisfied" in actions


class TestPersistence:
    def test_survives_reload(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        c = led.add("C4", "Undefined abbreviation PONV", severity="WARNING")
        led.satisfy(c.key, reason="defined PONV")

        led2 = ConstraintLedger(audit_dir)
        loaded = led2.get(c.key)
        assert loaded is not None
        assert loaded.status == STATUS_SATISFIED
        assert led2.is_converged()

    def test_corrupt_ledger_degrades_gracefully(self, audit_dir: Path) -> None:
        (audit_dir / ConstraintLedger.LEDGER_FILE).write_text("{not: valid: yaml: [", encoding="utf-8")
        led = ConstraintLedger(audit_dir)
        # Should not raise; just starts empty.
        assert led.all_constraints() == []
        assert led.is_converged()


class TestIngestHookIssues:
    def test_ingest_from_dicts(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        issues = [
            {"hook_id": "P7", "severity": "CRITICAL", "section": "references", "message": "Malformed DOI"},
            {"hook_id": "B13", "severity": "CRITICAL", "section": "Discussion", "message": "No limitations"},
        ]
        added = led.ingest_hook_issues(issues)
        assert added == 2
        assert led.summary()["open"] == 2

    def test_ingest_is_idempotent(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        issues = [{"hook_id": "A3", "severity": "WARNING", "section": "", "message": "AI filler"}]
        assert led.ingest_hook_issues(issues) == 1
        assert led.ingest_hook_issues(issues) == 0  # no duplicate
        assert led.summary()["total"] == 1

    def test_ingest_from_hookissue_objects(self, audit_dir: Path) -> None:
        from med_paper_assistant.infrastructure.persistence.writing_hooks import HookIssue

        led = ConstraintLedger(audit_dir)
        issues = [
            HookIssue(hook_id="C3", severity="CRITICAL", section="Results", message="N mismatch"),
        ]
        added = led.ingest_hook_issues(issues)
        assert added == 1
        assert led.open_critical()[0].source == "C3"


class TestMarkdown:
    def test_markdown_renders(self, audit_dir: Path) -> None:
        led = ConstraintLedger(audit_dir)
        led.add("P7", "Malformed DOI", severity="CRITICAL", section="references")
        md = led.to_markdown()
        assert "Constraint Ledger" in md
        assert "Open" in md
        assert "❌ no" in md  # not converged
