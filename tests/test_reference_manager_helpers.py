from __future__ import annotations

import json
from pathlib import Path

from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager


def test_get_reference_details_returns_metadata_and_ref_dir(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    ref_dir = refs_dir / "27345583"
    ref_dir.mkdir(parents=True)

    metadata = {
        "pmid": "27345583",
        "title": "Synthetic smoke reference",
        "authors": ["Greer JA"],
        "citation_key": "greer2017_27345583",
    }
    (ref_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    manager = ReferenceManager(base_dir=str(refs_dir))

    detail = manager.get_reference_details("27345583")

    assert detail["pmid"] == "27345583"
    assert detail["metadata"]["title"] == "Synthetic smoke reference"
    assert detail["ref_dir"] == str(ref_dir)
    assert detail["has_fulltext_pdf"] is False


def test_get_reference_details_returns_empty_dict_for_missing_reference(tmp_path) -> None:
    manager = ReferenceManager(base_dir=str(tmp_path / "references"))

    assert manager.get_reference_details("99999999") == {}


def test_import_local_file_creates_reference_note_and_scaffolding(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))
    source_file = tmp_path / "paper.pdf"
    source_file.write_bytes(b"synthetic-pdf-content")

    result = manager.import_local_file(
        str(source_file),
        metadata={
            "title": "Local PDF Reference",
            "authors": ["Chen Eric"],
            "year": "2026",
            "data_source": "asset_aware",
            "asset_aware_doc_id": "doc_123",
            "fulltext_sections": ["Methods", "Results"],
            "extracted_markdown": "# Methods\n\nSynthetic content.",
        },
    )

    assert "Successfully imported local source" in result

    saved_ids = manager.list_references()
    assert len(saved_ids) == 1
    ref_id = saved_ids[0]

    metadata = manager.get_metadata(ref_id)
    assert metadata["title"] == "Local PDF Reference"
    assert metadata["trust_level"] == "extracted"
    assert metadata["asset_aware_doc_id"] == "doc_123"
    assert metadata["fulltext_ingested"] is True
    assert metadata["content_hash"]

    ref_dir = refs_dir / ref_id
    note_path = ref_dir / f"{metadata['citation_key']}.md"
    assert note_path.exists()
    assert (ref_dir / "source" / ".").exists()
    assert (ref_dir / "artifacts" / "asset-aware" / "sections.md").exists()

    index_path = tmp_path / "notes" / "index.md"
    log_path = tmp_path / "notes" / "log.md"
    hash_registry_path = tmp_path / "registry" / "by-hash.json"

    assert index_path.exists()
    assert log_path.exists()
    assert hash_registry_path.exists()

    index_text = index_path.read_text(encoding="utf-8")
    log_text = log_path.read_text(encoding="utf-8")
    hash_registry = json.loads(hash_registry_path.read_text(encoding="utf-8"))

    assert metadata["citation_key"] in index_text
    assert "local_import" in log_text
    assert "local_import_materialized" not in log_text
    assert hash_registry[metadata["content_hash"]] == ref_id


def test_import_local_file_deduplicates_by_content_hash(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))
    source_file = tmp_path / "duplicate.pdf"
    source_file.write_bytes(b"same-content")

    first = manager.import_local_file(str(source_file), metadata={"title": "First import"})
    second = manager.import_local_file(str(source_file), metadata={"title": "Second import"})

    assert "Successfully imported local source" in first
    assert "already imported" in second
    assert len(manager.list_references()) == 1


def test_import_web_source_creates_materialized_reference(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))

    result = manager.import_web_source(
        "https://example.com/remimazolam",
        "# Remimazolam in ICU\n\nRemimazolam may support ICU sedation workflows.\n\n## Findings\n\nEarly data remain heterogeneous.",
        metadata={"title": "Remimazolam in ICU", "authors": ["Chen Eric"], "year": "2026"},
    )

    assert "Successfully imported web source" in result

    ref_id = manager.list_references()[0]
    metadata = manager.get_metadata(ref_id)
    ref_dir = refs_dir / ref_id

    assert metadata["source"] == "web"
    assert metadata["trust_level"] == "user"
    assert metadata["fulltext_ingested"] is True
    assert metadata["content_hash"]
    assert (ref_dir / "source" / "captured.md").exists()
    assert (ref_dir / "artifacts" / "asset-aware" / "sections.md").exists()


def test_materialize_agent_wiki_builds_indexed_pages_from_markdown_intake(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))

    import_result = manager.import_markdown_content(
        "# ICU Sedation Notes\n\nRemimazolam is emerging as an ICU sedation option.\n\n## Gaps\n\nDelirium effects remain unclear.",
        source_name="icu-sedation.md",
        metadata={"title": "ICU Sedation Notes", "authors": ["Chen Eric"], "year": "2026"},
    )

    assert "Successfully imported markdown source" in import_result

    ref_id = manager.list_references()[0]
    metadata = manager.get_metadata(ref_id)
    result = manager.materialize_agent_wiki(
        knowledge_map_title="ICU Sedation Map",
        reference_ids=[ref_id],
        focus="Delirium implications",
    )

    knowledge_map_path = tmp_path / "notes" / "knowledge-maps" / "icu-sedation-map.md"
    synthesis_path = tmp_path / "notes" / "synthesis-pages" / "icu-sedation-map-synthesis.md"
    index_text = (tmp_path / "notes" / "index.md").read_text(encoding="utf-8")
    log_text = (tmp_path / "notes" / "log.md").read_text(encoding="utf-8")
    knowledge_map_text = knowledge_map_path.read_text(encoding="utf-8")
    synthesis_text = synthesis_path.read_text(encoding="utf-8")

    assert "Agent wiki materialized" in result
    assert knowledge_map_path.exists()
    assert synthesis_path.exists()
    assert f"[[{metadata['citation_key']}]]" in knowledge_map_text
    assert f"[[{metadata['citation_key']}]]" in synthesis_text
    assert "[[knowledge-map-icu-sedation-map]]" in index_text
    assert "[[synthesis-icu-sedation-map-synthesis]]" in index_text
    assert "markdown_intake" in log_text
    assert "knowledge_map_materialized" in log_text
    assert "synthesis_page_materialized" in log_text


def test_update_fulltext_and_analysis_status_rewrites_metadata_and_note(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))
    source_file = tmp_path / "analysis.pdf"
    source_file.write_bytes(b"analysis-content")
    manager.import_local_file(str(source_file), metadata={"title": "Analysis ready"})

    ref_id = manager.list_references()[0]
    metadata_before = manager.get_metadata(ref_id)
    note_path = refs_dir / ref_id / f"{metadata_before['citation_key']}.md"

    fulltext_result = manager.update_fulltext_ingestion_status(
        ref_id,
        True,
        asset_aware_doc_id="doc_456",
        fulltext_sections=["Introduction"],
    )
    analysis_result = manager.update_reference_analysis_status(
        ref_id,
        "Strong background evidence",
        usage_sections=["Introduction", "Discussion"],
    )

    metadata_after = manager.get_metadata(ref_id)
    note_text = note_path.read_text(encoding="utf-8")

    assert fulltext_result == f"Updated {ref_id}."
    assert analysis_result == f"Updated {ref_id}."
    assert metadata_after["asset_aware_doc_id"] == "doc_456"
    assert metadata_after["analysis_completed"] is True
    assert metadata_after["usage_sections"] == ["Introduction", "Discussion"]
    assert "asset_aware_doc_id: \"doc_456\"" in note_text
    assert "analysis_completed: true" in note_text
    assert "Strong background evidence" in note_text


def test_resolve_reference_identity_updates_registry_and_preserves_aliases(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))
    source_file = tmp_path / "resolved.pdf"
    source_file.write_bytes(b"resolved-content")

    manager.import_local_file(
        str(source_file),
        metadata={
            "title": "Needs canonical identity",
            "authors": ["Chen Eric"],
            "year": "2026",
        },
    )

    source_ref_id = manager.list_references()[0]
    source_metadata = manager.get_metadata(source_ref_id)

    result = manager.resolve_reference_identity(
        source_ref_id,
        verified_article={
            "pmid": "12345678",
            "title": "Resolved verified reference",
            "authors": ["Chen Eric"],
            "authors_full": [{"last_name": "Chen", "first_name": "Eric", "initials": "E"}],
            "year": "2026",
            "journal": "Journal of Testing",
            "doi": "10.1000/test.2026.1",
            "abstract": "Verified abstract content.",
        },
    )

    assert "Resolved" in result
    assert source_ref_id not in manager.list_references()

    canonical_metadata = manager.get_metadata("12345678")
    hash_registry = json.loads((tmp_path / "registry" / "by-hash.json").read_text(encoding="utf-8"))
    index_text = (tmp_path / "notes" / "index.md").read_text(encoding="utf-8")
    note_text = (
        refs_dir / "12345678" / f"{canonical_metadata['citation_key']}.md"
    ).read_text(encoding="utf-8")

    assert hash_registry[source_metadata["content_hash"]] == "12345678"
    assert source_metadata["citation_key"] in canonical_metadata["legacy_aliases"]
    assert source_ref_id in canonical_metadata["legacy_aliases"]
    assert source_metadata["citation_key"] in note_text
    assert f'  - "{source_ref_id}"' in note_text
    assert f"[[{canonical_metadata['citation_key']}]]" in index_text
    assert f"[[{source_metadata['citation_key']}]]" not in index_text


def test_persist_reference_payload_replaces_stale_doi_registry_entries(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))

    result = manager.save_reference(
        {
            "pmid": "12345678",
            "title": "Registry update reference",
            "authors": ["Chen Eric"],
            "authors_full": [{"last_name": "Chen", "first_name": "Eric", "initials": "E"}],
            "year": "2026",
            "journal": "Journal of Testing",
            "doi": "10.1000/original-doi",
            "abstract": "Original abstract.",
        }
    )

    assert "Successfully saved reference" in result

    metadata = manager.get_metadata("12345678")
    metadata["doi"] = "10.1000/updated-doi"
    manager._persist_reference_payload(metadata, log_event="metadata_update")

    doi_registry = json.loads((tmp_path / "registry" / "by-doi.json").read_text(encoding="utf-8"))

    assert doi_registry["10.1000/updated-doi"] == "12345678"
    assert "10.1000/original-doi" not in doi_registry


def test_resolve_reference_identity_preserves_conflicting_artifacts_without_overwrite(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))
    source_file = tmp_path / "conflict.pdf"
    source_file.write_bytes(b"conflict-content")

    manager.import_local_file(
        str(source_file),
        metadata={
            "title": "Conflict source",
            "authors": ["Chen Eric"],
            "year": "2026",
            "extracted_markdown": "# Local\n\nLocal parsed content.",
        },
    )

    source_ref_id = manager.list_references()[0]
    verified_article = {
        "pmid": "12345678",
        "title": "Canonical target",
        "authors": ["Chen Eric"],
        "authors_full": [{"last_name": "Chen", "first_name": "Eric", "initials": "E"}],
        "year": "2026",
        "journal": "Journal of Testing",
        "doi": "10.1000/test.2026.1",
        "abstract": "Verified abstract content.",
    }
    manager.save_reference(verified_article)

    target_artifact_dir = refs_dir / "12345678" / "artifacts" / "asset-aware"
    target_artifact_dir.mkdir(parents=True, exist_ok=True)
    primary_sections = target_artifact_dir / "sections.md"
    primary_sections.write_text("# Canonical\n\nCanonical parsed content.", encoding="utf-8")

    result = manager.resolve_reference_identity(source_ref_id, verified_article=verified_article)

    canonical_metadata = manager.get_metadata("12345678")
    conflict_files = sorted(target_artifact_dir.glob(f"sections.from-{source_ref_id}*.md"))
    resolution_events = [
        event for event in canonical_metadata.get("provenance", []) if event.get("event") == "identity_resolved"
    ]

    assert "Resolved" in result
    assert primary_sections.read_text(encoding="utf-8") == "# Canonical\n\nCanonical parsed content."
    assert len(conflict_files) == 1
    assert conflict_files[0].read_text(encoding="utf-8") == "# Local\n\nLocal parsed content."
    assert resolution_events[-1]["artifact_conflicts"] == [
        str(Path("artifacts") / "asset-aware" / conflict_files[0].name)
    ]


def test_delete_reference_cleans_registry_and_index(tmp_path) -> None:
    refs_dir = tmp_path / "references"
    manager = ReferenceManager(base_dir=str(refs_dir))
    source_file = tmp_path / "delete-me.pdf"
    source_file.write_bytes(b"delete-me")

    manager.import_local_file(str(source_file), metadata={"title": "Delete me"})
    ref_id = manager.list_references()[0]
    metadata = manager.get_metadata(ref_id)

    result = manager.delete_reference(ref_id, confirm=True)

    hash_registry = json.loads((tmp_path / "registry" / "by-hash.json").read_text(encoding="utf-8"))
    index_text = (tmp_path / "notes" / "index.md").read_text(encoding="utf-8")
    log_text = (tmp_path / "notes" / "log.md").read_text(encoding="utf-8")

    assert result["success"] is True
    assert not (refs_dir / ref_id).exists()
    assert metadata["content_hash"] not in hash_registry
    assert metadata["citation_key"] not in index_text
    assert "delete_reference" in log_text
