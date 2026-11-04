"""Regression tests for persistence-layer audit findings PERS-1..PERS-15 (P1 batch)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence import state_io
from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
)
from med_paper_assistant.infrastructure.persistence.checkpoint_manager import CheckpointManager
from med_paper_assistant.infrastructure.persistence.constraint_ledger import (
    ConstraintLedger,
    LedgerCorruptError,
)
from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
    PendingEvolutionStore,
)
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)
from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.infrastructure.persistence.tool_invocation_store import (
    ToolInvocationStore,
)


@pytest.fixture
def project_dir(tmp_path):
    p = tmp_path / "proj"
    for d in ["drafts", "references", "data", "results", ".audit", ".memory", "exports"]:
        (p / d).mkdir(parents=True)
    return p


# ── PERS-1: library-wiki must still gate Phase 2.1 ───────────────────


def test_pers1_library_wiki_phase_21_is_not_auto_passed(project_dir):
    (project_dir / "project.json").write_text(
        json.dumps({"workflow_mode": "library-wiki"}), encoding="utf-8"
    )
    v = PipelineGateValidator(project_dir)

    phase_21 = v.validate_phase(21)
    phase_3 = v.validate_phase(3)

    assert all(c.name != "workflow_mode:library-wiki" for c in phase_21.checks)
    assert any(c.name == "workflow_mode:library-wiki" for c in phase_3.checks)


# ── PERS-2 / PERS-13: constraint ledger ──────────────────────────────


def test_pers2_corrupt_ledger_is_not_converged_and_rejects_writes(tmp_path):
    (tmp_path / "constraint-ledger.yaml").write_text("constraints: [unclosed", encoding="utf-8")
    led = ConstraintLedger(tmp_path)

    assert led.is_corrupt()
    assert not led.is_converged()
    with pytest.raises(LedgerCorruptError):
        led.add("P7", "bad doi", severity="CRITICAL")
    assert (tmp_path / "constraint-ledger.yaml").exists()  # not silently wiped

    quarantined = led.quarantine_and_reset()
    assert quarantined is not None and ".corrupt-" in quarantined.name
    assert led.is_converged()


def test_pers13_severity_escalates_and_never_downgrades(tmp_path):
    led = ConstraintLedger(tmp_path)
    c = led.add("A3", "AI filler", severity="WARNING")
    led.add("A3", "AI filler", severity="CRITICAL")
    assert led.get(c.key).severity == "CRITICAL"
    led.add("A3", "AI filler", severity="INFO")
    assert led.get(c.key).severity == "CRITICAL"


def test_pers13_invalid_transitions_rejected(tmp_path):
    led = ConstraintLedger(tmp_path)
    c = led.add("B13", "no limitations", severity="CRITICAL")
    led.satisfy(c.key)
    with pytest.raises(ValueError):
        led.satisfy(c.key)
    with pytest.raises(ValueError):
        led.waive(c.key, "because")
    assert led.reopen(c.key, "regressed")


# ── PERS-3: atomic writes ────────────────────────────────────────────


def test_pers3_atomic_write_keeps_old_content_when_replace_fails(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    target.write_text("old", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("disk gone")

    monkeypatch.setattr(state_io.os, "replace", boom)
    with pytest.raises(OSError):
        state_io.atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_pers3_atomic_write_roundtrip_utf8(tmp_path):
    target = tmp_path / "state.txt"
    state_io.atomic_write_text(target, "héllo 論文")
    assert target.read_text(encoding="utf-8") == "héllo 論文"


# ── PERS-4: corrupt state is quarantined, not silently reset ─────────


def test_pers4_corrupt_checkpoint_is_quarantined(project_dir):
    audit = project_dir / ".audit"
    (audit / "checkpoint.json").write_text("{bad", encoding="utf-8")

    assert CheckpointManager(audit).load() is None

    assert not (audit / "checkpoint.json").exists()
    assert len(list(audit.glob("checkpoint.json.corrupt-*"))) == 1


def test_pers4_non_object_checkpoint_is_quarantined(project_dir):
    audit = project_dir / ".audit"
    (audit / "checkpoint.json").write_text("[1, 2]", encoding="utf-8")
    assert CheckpointManager(audit).load() is None
    assert len(list(audit.glob("checkpoint.json.corrupt-*"))) == 1


@pytest.mark.parametrize("store_cls", [ToolInvocationStore, PendingEvolutionStore])
def test_pers4_yaml_stores_quarantine_corrupt_files(tmp_path, store_cls):
    audit = tmp_path / ".audit"
    audit.mkdir()
    store = store_cls(tmp_path)
    path = store._path
    path.write_text("a: [unclosed", encoding="utf-8")

    store._load()

    assert len(list(audit.glob(path.name + ".corrupt-*"))) == 1


# ── PERS-6: empty manifest caption must not match everything ─────────


def test_pers6_empty_manifest_caption_does_not_match(project_dir):
    v = PipelineGateValidator(project_dir)
    planned = {"type": "figure", "id": "fig-2", "caption": "Survival curves"}
    entries = [
        {"kind": "figure", "number": "1", "filename": "a.png", "caption": ""},
        {"kind": "figure", "number": "2", "filename": "b.png", "caption": "Other"},
    ]

    match = v._match_manifest_asset(planned, entries)

    assert match is not None and match["filename"] == "b.png"  # by number, not by "" in caption


# ── PERS-7: null / non-dict YAML or JSON must not crash ──────────────


@pytest.mark.parametrize(
    "content", ["references:\n", "- a\n- b\n", "", "references:\n  minimum_reference_limits:\n"]
)
def test_pers7_journal_profile_shapes_do_not_crash(project_dir, content):
    (project_dir / "journal-profile.yaml").write_text(content, encoding="utf-8")
    v = PipelineGateValidator(project_dir)
    assert isinstance(v._resolve_min_references("original-research"), int)


@pytest.mark.parametrize("content", ["[]", "null", '{"figures": null, "tables": null}', "{bad"])
def test_pers7_manifest_shapes_do_not_crash(project_dir, content):
    (project_dir / "results" / "manifest.json").write_text(content, encoding="utf-8")
    assert PipelineGateValidator(project_dir)._load_manifest_entries() == []


# ── PERS-8: complete_round validates scores ──────────────────────────


def test_pers8_complete_round_rejects_invalid_scores(project_dir):
    cfg = AuditLoopConfig(max_rounds=3, min_rounds=1, context="review")
    loop = AutonomousAuditLoop(str(project_dir / ".audit"), config=cfg)
    dims = list(cfg.dimension_weights)
    loop.start_round()

    bad_inputs = [
        {dims[0]: 10.0},  # missing dimensions
        {**dict.fromkeys(dims, 5.0), "bogus": 5.0},  # unknown dimension
        {**dict.fromkeys(dims, 5.0), dims[0]: 99.0},  # out of range
        {**dict.fromkeys(dims, 5.0), dims[0]: float("nan")},
        {**dict.fromkeys(dims, 5.0), dims[0]: True},
    ]
    for scores in bad_inputs:
        with pytest.raises(ValueError):
            loop.complete_round(scores)
    assert loop._rounds == []

    loop.complete_round(dict.fromkeys(dims, 8.0))
    assert len(loop._rounds) == 1


# ── PERS-9: pause / resume ───────────────────────────────────────────


def test_pers9_repause_keeps_original_hashes(project_dir):
    draft = project_dir / "drafts" / "manuscript.md"
    draft.write_text("v1", encoding="utf-8")
    ckpt = CheckpointManager(project_dir / ".audit")
    ckpt.save_pause("first")
    original = ckpt.load()["pause_state"]["draft_hashes"]

    draft.write_text("v2 edited while paused", encoding="utf-8")
    ckpt.save_pause("again")

    state = ckpt.load()
    assert state["pause_state"]["draft_hashes"] == original
    assert state["pause_state"]["reason"] == "first"
    assert ckpt.resume_from_pause()["changed"] is True


def test_pers9_resume_without_pause_state_does_not_raise(project_dir):
    audit = project_dir / ".audit"
    ckpt = CheckpointManager(audit)
    state = ckpt._empty_state()
    state["status"] = "paused"
    (audit / "checkpoint.json").write_text(json.dumps(state), encoding="utf-8")

    result = ckpt.resume_from_pause()

    assert "auto_resume" in result
    assert ckpt.load()["status"] == "in_progress"


# ── PERS-12: exploration conversion is guarded and transactional ─────


def test_pers12_conversion_rejects_unsafe_slug(tmp_path, monkeypatch):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.get_or_create_temp_project()
    monkeypatch.setattr(pm, "_slugify", lambda _name: "../escape")

    result = pm.convert_temp_to_project(name="x", workflow_mode="library-wiki")

    assert result["success"] is False
    assert not (tmp_path / "escape").exists()
    assert (pm.projects_dir / pm.TEMP_PROJECT_SLUG).exists()


def test_pers12_failed_copy_leaves_no_partial_target(tmp_path, monkeypatch):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.get_or_create_temp_project()
    real_copytree = shutil.copytree

    def partial_copytree(src, dst, *args, **kwargs):
        Path(dst).mkdir(parents=True)
        (Path(dst) / "half.txt").write_text("x", encoding="utf-8")
        raise OSError("copy interrupted")

    monkeypatch.setattr(shutil, "copytree", partial_copytree)
    result = pm.convert_temp_to_project(
        name="Retry Me", workflow_mode="library-wiki", keep_temp=True
    )

    assert result["success"] is False
    assert not (pm.projects_dir / "retry-me").exists()
    assert not list(pm.projects_dir.glob(".*.converting"))
    assert (pm.projects_dir / pm.TEMP_PROJECT_SLUG).exists()

    monkeypatch.setattr(shutil, "copytree", real_copytree)
    retry = pm.convert_temp_to_project(
        name="Retry Me", workflow_mode="library-wiki", keep_temp=True
    )
    assert retry["success"] is True


# ── PERS-15: no stdout noise, list_references skips non-reference dirs ─


def test_pers15_corrupt_metadata_logs_instead_of_printing(tmp_path, monkeypatch):
    from structlog.testing import capture_logs

    refs = tmp_path / "references"
    (refs / "12345").mkdir(parents=True)
    (refs / "12345" / "metadata.json").write_text("{bad", encoding="utf-8")

    def no_print(*_a, **_k):
        raise AssertionError("print() writes to the MCP stdio channel")

    monkeypatch.setattr("builtins.print", no_print)
    with capture_logs() as logs:
        assert ReferenceManager(base_dir=str(refs)).get_metadata("12345") == {}

    assert any(e["event"] == "reference_metadata_unreadable" for e in logs)


def test_pers15_list_references_skips_non_reference_dirs(tmp_path):
    refs = tmp_path / "references"
    (refs / "111").mkdir(parents=True)
    (refs / "111" / "metadata.json").write_text("{}", encoding="utf-8")
    (refs / ".cache").mkdir()
    (refs / ".cache" / "metadata.json").write_text("{}", encoding="utf-8")
    (refs / "stray").mkdir()

    assert ReferenceManager(base_dir=str(refs)).list_references() == ["111"]
