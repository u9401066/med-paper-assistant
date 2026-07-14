"""Boundary tests for safe, auditable exemplar use."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.exemplar_usage_store import (
    ALLOWED_EXEMPLAR_ROLES,
    ExemplarPolicyError,
    ExemplarUsageStore,
)


@pytest.fixture
def store(tmp_path: Path) -> ExemplarUsageStore:
    return ExemplarUsageStore(tmp_path / "project")


def test_record_persists_non_evidentiary_policy(store: ExemplarUsageStore) -> None:
    record = store.record(
        source_id="doi:10.1000/example",
        roles=["structure", "methodology", "structure"],
        target_sections=["Methods", "Discussion"],
        purpose="Compare reporting order; independently verify all claims.",
        source_sha256="a" * 64,
    )

    assert record["id"] == "EX-0001"
    assert record["roles"] == ["structure", "methodology"]
    assert record["evidence_eligible"] is False
    assert record["citation_credit"] is False
    assert record["verbatim_copy"] is False
    assert record["requires_independent_verification"] is True
    data = yaml.safe_load(store.path.read_text(encoding="utf-8"))
    assert data["schema"] == "mdpaper.exemplar_usage.v1"
    assert data["policy"]["allowed_roles"] == sorted(ALLOWED_EXEMPLAR_ROLES)
    assert data["records"][0]["source_sha256"] == "a" * 64


def test_record_ids_increment_across_store_instances(tmp_path: Path) -> None:
    project = tmp_path / "project"
    first = ExemplarUsageStore(project).record(source_id="one", roles=["reporting"])
    second = ExemplarUsageStore(project).record(source_id="two", roles=["argument-map"])
    assert first["id"] == "EX-0001"
    assert second["id"] == "EX-0002"


@pytest.mark.parametrize(
    "roles",
    [
        ["verbatim-copy"],
        ["evidence-substitute"],
        ["citation-substitute"],
        ["fabricated-data"],
    ],
)
def test_prohibited_roles_are_rejected(store: ExemplarUsageStore, roles: list[str]) -> None:
    with pytest.raises(ExemplarPolicyError, match="prohibited exemplar role"):
        store.record(source_id="unsafe", roles=roles)
    assert not store.path.exists()


def test_unknown_roles_and_invalid_hash_are_rejected(store: ExemplarUsageStore) -> None:
    with pytest.raises(ExemplarPolicyError, match="unsupported exemplar role"):
        store.record(source_id="source", roles=["evidence"])
    with pytest.raises(ExemplarPolicyError, match="64 hexadecimal"):
        store.record(source_id="source", roles=["structure"], source_sha256="bad")


def test_tampered_policy_blocks_new_records(store: ExemplarUsageStore) -> None:
    store.record(source_id="safe", roles=["style-calibration"])
    data = yaml.safe_load(store.path.read_text(encoding="utf-8"))
    data["records"][0]["evidence_eligible"] = True
    store.path.write_text(yaml.safe_dump(data), encoding="utf-8")

    assert any("evidence_eligible" in issue for issue in store.validate_integrity())
    with pytest.raises(ExemplarPolicyError, match="violates policy"):
        store.record(source_id="next", roles=["structure"])


def test_tampered_role_allowlist_is_detected(store: ExemplarUsageStore) -> None:
    store.record(source_id="safe", roles=["structure"])
    data = yaml.safe_load(store.path.read_text(encoding="utf-8"))
    data["policy"]["allowed_roles"].append("evidence")
    store.path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert any("allowed_roles" in issue for issue in store.validate_integrity())


def test_summary_for_new_store_is_valid(store: ExemplarUsageStore) -> None:
    assert store.summary() == {
        "total": 0,
        "integrity_passed": True,
        "issues": [],
        "path": str(store.path),
    }
