from med_paper_assistant.domain.entities.reference import Reference


def test_reference_to_dict_round_trip_preserves_fulltext_and_analysis_fields() -> None:
    original = Reference(
        unique_id="12345678",
        title="Round trip reference",
        source="pubmed",
        pmid="12345678",
        citation_key="chen2026_12345678",
        authors=["Chen Eric"],
        year=2026,
        fulltext_ingested=True,
        fulltext_unavailable_reason="",
        asset_aware_doc_id="doc_789",
        fulltext_sections=["Methods", "Results"],
        analysis_completed=True,
        analysis_summary="Supports the local import pipeline.",
        usage_sections=["Introduction", "Discussion"],
        verified=True,
        data_source="pubmed_mcp_api",
        retrieved_at="2026-08-17T00:00:00+00:00",
        source_url="https://pubmed.test/api/cached_article/12345678",
        payload_hash="a" * 64,
        provenance=[
            {
                "event": "pubmed_mcp_fetch",
                "source": "pubmed",
                "data_source": "pubmed_mcp_api",
                "requested_pmid": "12345678",
                "retrieved_at": "2026-08-17T00:00:00+00:00",
                "source_url": "https://pubmed.test/api/cached_article/12345678",
                "payload_hash": "a" * 64,
            }
        ],
        agent_notes="Use in the Discussion.",
        trust_level="verified",
    )

    payload = original.to_dict()
    restored = Reference.from_dict(payload)

    assert payload["fulltext_ingested"] is True
    assert payload["asset_aware_doc_id"] == "doc_789"
    assert payload["analysis_completed"] is True
    assert payload["usage_sections"] == ["Introduction", "Discussion"]
    assert payload["verified"] is True
    assert payload["payload_hash"] == "a" * 64

    assert restored.fulltext_ingested is True
    assert restored.asset_aware_doc_id == "doc_789"
    assert restored.fulltext_sections == ["Methods", "Results"]
    assert restored.analysis_completed is True
    assert restored.analysis_summary == "Supports the local import pipeline."
    assert restored.usage_sections == ["Introduction", "Discussion"]
    assert restored.verified is True
    assert restored.data_source == "pubmed_mcp_api"
    assert restored.retrieved_at == "2026-08-17T00:00:00+00:00"
    assert restored.source_url == "https://pubmed.test/api/cached_article/12345678"
    assert restored.payload_hash == "a" * 64
    assert restored.provenance == [
        {
            "event": "pubmed_mcp_fetch",
            "source": "pubmed",
            "data_source": "pubmed_mcp_api",
            "requested_pmid": "12345678",
            "retrieved_at": "2026-08-17T00:00:00+00:00",
            "source_url": "https://pubmed.test/api/cached_article/12345678",
            "payload_hash": "a" * 64,
        }
    ]
    assert restored.agent_notes == "Use in the Discussion."
    assert restored.trust_level == "verified"
