from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from med_paper_assistant.domain.entities.reference import Reference
from med_paper_assistant.domain.services.reference_converter import ReferenceConverter
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.infrastructure.persistence.writing_hooks import WritingHooksEngine
from med_paper_assistant.infrastructure.services import pubmed_api_client
from med_paper_assistant.infrastructure.services.pubmed_api_client import (
    PubMedAPIClient,
    PubMedVerificationError,
    VerifiedArticlePayload,
)

PMID = "12345678"
ARTICLE = {
    "pmid": PMID,
    "title": "A verified reference pipeline",
    "authors": ["Chen Eric"],
    "authors_full": [{"last_name": "Chen", "first_name": "Eric"}],
    "year": "2026",
    "journal": "Journal of Verifiable Research",
    "abstract": "Synthetic metadata for an offline smoke test.",
}


def _canonical_hash(article: dict[str, Any]) -> str:
    encoded = json.dumps(
        article,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mock_pubmed_http(
    monkeypatch: pytest.MonkeyPatch,
    *,
    envelope: Any,
    raw_body: bytes | None = None,
) -> None:
    monkeypatch.setenv("PUBMED_MCP_API_URL", "https://pubmed.test")
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "healthy"})
        if request.url.path == f"/api/cached_article/{PMID}":
            if raw_body is not None:
                return httpx.Response(
                    200,
                    content=raw_body,
                    headers={"content-type": "application/json"},
                )
            return httpx.Response(200, json=envelope)
        return httpx.Response(404, json={"detail": "not found"})

    transport = httpx.MockTransport(handler)

    def client_factory(*args: Any, **kwargs: Any) -> httpx.Client:
        return real_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(pubmed_api_client.httpx, "Client", client_factory)
    monkeypatch.setattr(pubmed_api_client, "_client", None)


def test_pubmed_http_success_mints_auditable_verified_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_pubmed_http(
        monkeypatch,
        envelope={"source": "pubmed", "verified": True, "data": ARTICLE},
    )

    result = PubMedAPIClient("https://pubmed.test/").get_cached_article(PMID)

    assert isinstance(result, VerifiedArticlePayload)
    assert result.article == ARTICLE
    assert result.data_source == "pubmed_mcp_api"
    assert result.payload_hash == _canonical_hash(ARTICLE)
    assert result.source_url.startswith(f"https://pubmed.test/api/cached_article/{PMID}")
    assert datetime.fromisoformat(result.retrieved_at).tzinfo is not None
    assert result.provenance[0]["requested_pmid"] == PMID
    assert result.provenance[0]["payload_hash"] == result.payload_hash


@pytest.mark.parametrize(
    ("envelope", "message"),
    [
        (
            {"source": "pubmed", "verified": False, "data": ARTICLE},
            "not explicitly verified",
        ),
        (
            {
                "source": "pubmed",
                "verified": True,
                "data": {**ARTICLE, "pmid": "87654321"},
            },
            "identity mismatch",
        ),
        (
            {"source": "pubmed", "verified": True, "data": "not-an-object"},
            "must be a JSON object",
        ),
        (
            {"verified": True, "data": ARTICLE},
            "source provenance",
        ),
        (
            {"source": "pubmed", "verified": True, "data": {"pmid": PMID}},
            "title is missing",
        ),
    ],
)
def test_pubmed_http_rejects_untrusted_or_malformed_envelopes(
    monkeypatch: pytest.MonkeyPatch,
    envelope: Any,
    message: str,
) -> None:
    _mock_pubmed_http(monkeypatch, envelope=envelope)

    with pytest.raises(PubMedVerificationError, match=message):
        PubMedAPIClient("https://pubmed.test").get_cached_article(PMID)


def test_pubmed_http_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_pubmed_http(monkeypatch, envelope=None, raw_body=b"{not-json")

    with pytest.raises(PubMedVerificationError, match="invalid JSON"):
        PubMedAPIClient("https://pubmed.test").get_cached_article(PMID)


def test_pubmed_client_singleton_tracks_requested_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pubmed_api_client, "_client", None)

    first = pubmed_api_client.get_pubmed_api_client("https://one.test/")
    same = pubmed_api_client.get_pubmed_api_client("https://one.test")
    second = pubmed_api_client.get_pubmed_api_client("https://two.test")

    assert first is same
    assert second is not first
    assert second.base_url == "https://two.test"


def test_verified_payload_survives_converter_and_domain_round_trip() -> None:
    verified = PubMedAPIClient._validate_article_response(
        {"source": "pubmed", "verified": True, "data": ARTICLE},
        requested_pmid=PMID,
        source_url=f"https://pubmed.test/api/cached_article/{PMID}",
    )
    standardized = ReferenceConverter().convert(
        verified.to_reference_dict(agent_notes="Use in the Introduction.")
    )
    entity = Reference.from_standardized(standardized)
    restored = Reference.from_dict(entity.to_dict())

    assert restored.verified is True
    assert restored.data_source == "pubmed_mcp_api"
    assert restored.retrieved_at == verified.retrieved_at
    assert restored.source_url == verified.source_url
    assert restored.payload_hash == verified.payload_hash
    assert restored.provenance == list(verified.provenance)
    assert restored.agent_notes == "Use in the Introduction."
    assert restored.trust_level == "verified"


def test_converter_and_domain_fail_closed_without_provenance() -> None:
    incomplete = {
        **ARTICLE,
        "verified": True,
        "data_source": "pubmed_mcp_api",
        "retrieved_at": "2026-08-17T00:00:00+00:00",
        "source_url": f"https://pubmed.test/api/cached_article/{PMID}",
        "payload_hash": "a" * 64,
        "provenance": [],
        "trust_level": "verified",
    }

    standardized = ReferenceConverter().convert(incomplete)
    entity = Reference.from_dict(
        {
            "unique_id": PMID,
            "title": ARTICLE["title"],
            **incomplete,
        }
    )

    assert standardized.verified is False
    assert standardized.trust_level == "agent"
    assert entity.verified is False
    assert entity.trust_level == "agent"


def test_save_reference_mcp_persists_trust_chain_and_passes_p7(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _mock_pubmed_http(
        monkeypatch,
        envelope={"source": "pubmed", "verified": True, "data": ARTICLE},
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    manager = ReferenceManager(
        base_dir=str(project_dir / "references"),
        pubmed_api_url="https://pubmed.test",
    )

    result = manager.save_reference_mcp(PMID, agent_notes="Use in the Discussion.")

    assert "Successfully saved reference" in result
    metadata_path = project_dir / "references" / PMID / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["verified"] is True
    assert metadata["data_source"] == "pubmed_mcp_api"
    assert datetime.fromisoformat(metadata["retrieved_at"]).tzinfo is not None
    assert metadata["source_url"].startswith(f"https://pubmed.test/api/cached_article/{PMID}")
    assert metadata["payload_hash"] == _canonical_hash(ARTICLE)
    assert metadata["provenance"][0]["payload_hash"] == metadata["payload_hash"]
    assert metadata["agent_notes"] == "Use in the Discussion."
    assert metadata["trust_level"] == "verified"
    assert metadata["pubmed_transport_payload"] == ARTICLE

    provenance_path = project_dir / "references" / PMID / "provenance.json"
    assert json.loads(provenance_path.read_text(encoding="utf-8")) == metadata["provenance"]
    note_path = project_dir / "references" / PMID / metadata["citation_key"]
    note_path = note_path.with_suffix(".md")
    note = note_path.read_text(encoding="utf-8")
    assert f'payload_hash: "{metadata["payload_hash"]}"' in note
    assert "provenance_count: 1" in note

    p7 = WritingHooksEngine(project_dir).check_reference_integrity()
    assert p7.passed is True
    assert p7.stats["verified_count"] == 1
    assert p7.stats["unverified_count"] == 0

    records, invalid, _ = PipelineGateValidator._reference_records(project_dir / "references")
    assert len(records) == 1
    assert not invalid

    metadata["pubmed_transport_payload"]["title"] = "Post-save forged title"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    records, invalid, _ = PipelineGateValidator._reference_records(project_dir / "references")
    assert not records
    assert "payload hash does not match provenance" in invalid[0]


def test_save_reference_mcp_rejection_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _mock_pubmed_http(
        monkeypatch,
        envelope={"source": "pubmed", "verified": False, "data": ARTICLE},
    )
    refs_dir = tmp_path / "project" / "references"
    manager = ReferenceManager(
        base_dir=str(refs_dir),
        pubmed_api_url="https://pubmed.test",
    )

    result = manager.save_reference_mcp(PMID)

    assert "PubMed verification rejected" in result
    assert not (refs_dir / PMID).exists()


def test_save_reference_mcp_rejects_forged_transport_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class ForgedClient:
        def check_health(self) -> bool:
            return True

        def get_cached_article(
            self,
            pmid: str,
            fetch_if_missing: bool = True,
        ) -> VerifiedArticlePayload:
            del pmid, fetch_if_missing
            return VerifiedArticlePayload(
                article=dict(ARTICLE),
                data_source="pubmed_mcp_api",
                retrieved_at="2026-08-17T00:00:00+00:00",
                source_url=f"https://pubmed.test/api/cached_article/{PMID}",
                payload_hash="0" * 64,
                provenance=(),
            )

    monkeypatch.setattr(
        pubmed_api_client,
        "get_pubmed_api_client",
        lambda base_url=None, force_new=False: ForgedClient(),
    )
    refs_dir = tmp_path / "project" / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))

    result = manager.save_reference_mcp(PMID)

    assert "PubMed verification rejected" in result
    assert not (refs_dir / PMID).exists()


def test_agent_provided_verified_claim_is_downgraded_and_fails_p7(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    manager = ReferenceManager(base_dir=str(project_dir / "references"))
    fake_hash = "a" * 64
    fake_time = "2026-08-17T00:00:00+00:00"
    fake_url = f"https://pubmed.test/api/cached_article/{PMID}"
    forged = {
        **ARTICLE,
        "verified": True,
        "data_source": "pubmed_mcp_api",
        "retrieved_at": fake_time,
        "source_url": fake_url,
        "payload_hash": fake_hash,
        "provenance": [
            {
                "event": "pubmed_mcp_fetch",
                "data_source": "pubmed_mcp_api",
                "requested_pmid": PMID,
                "retrieved_at": fake_time,
                "source_url": fake_url,
                "payload_hash": fake_hash,
            }
        ],
        "trust_level": "verified",
    }

    result = manager.save_reference(forged)

    assert "Successfully saved reference" in result
    metadata = manager.get_metadata(PMID)
    assert metadata["verified"] is False
    assert metadata["data_source"] == "agent"
    assert metadata["retrieved_at"] == ""
    assert metadata["source_url"] == ""
    assert metadata["payload_hash"] == ""
    assert metadata["provenance"] == []
    assert metadata["trust_level"] == "agent"

    p7 = WritingHooksEngine(project_dir).check_reference_integrity()
    assert p7.passed is False
    assert p7.stats["verified_count"] == 0
    assert p7.stats["unverified_count"] == 1
