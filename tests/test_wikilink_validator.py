import json

import pytest

from med_paper_assistant.domain.services.wikilink_validator import (
    find_citation_key_for_pmid,
    validate_wikilinks_in_file,
)


def test_find_citation_key_for_pmid_is_deterministic(tmp_path):
    refs_dir = tmp_path / "references"
    refs_dir.mkdir()

    (refs_dir / "zeta2024_12345678").mkdir()
    (refs_dir / "alpha2024_12345678").mkdir()

    found = find_citation_key_for_pmid("12345678", str(refs_dir))
    assert found == "alpha2024_12345678"


def test_validate_wikilinks_in_file_reports_non_utf8_file(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(ValueError, match="not valid UTF-8"):
        validate_wikilinks_in_file(str(draft))


def test_find_citation_key_from_pmid_folder_metadata(tmp_path):
    refs_dir = tmp_path / "references"
    refs_dir.mkdir()

    pmid_dir = refs_dir / "12345678"
    pmid_dir.mkdir()
    (pmid_dir / "metadata.json").write_text(
        json.dumps({"citation_key": "smith2024_12345678"}), encoding="utf-8"
    )

    found = find_citation_key_for_pmid("12345678", str(refs_dir))
    assert found == "smith2024_12345678"
