from med_paper_assistant.domain.entities.reference import Reference


def test_reference_to_dict_round_trip_preserves_fulltext_and_analysis_fields() -> None:
    original = Reference(
        unique_id="local_abc123",
        title="Round trip reference",
        source="manual",
        citation_key="chen2026_local_abc123",
        authors=["Chen Eric"],
        year=2026,
        fulltext_ingested=True,
        fulltext_unavailable_reason="",
        asset_aware_doc_id="doc_789",
        fulltext_sections=["Methods", "Results"],
        analysis_completed=True,
        analysis_summary="Supports the local import pipeline.",
        usage_sections=["Introduction", "Discussion"],
    )

    payload = original.to_dict()
    restored = Reference.from_dict(payload)

    assert payload["fulltext_ingested"] is True
    assert payload["asset_aware_doc_id"] == "doc_789"
    assert payload["analysis_completed"] is True
    assert payload["usage_sections"] == ["Introduction", "Discussion"]

    assert restored.fulltext_ingested is True
    assert restored.asset_aware_doc_id == "doc_789"
    assert restored.fulltext_sections == ["Methods", "Results"]
    assert restored.analysis_completed is True
    assert restored.analysis_summary == "Supports the local import pipeline."
    assert restored.usage_sections == ["Introduction", "Discussion"]