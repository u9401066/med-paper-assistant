from __future__ import annotations

import json

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
