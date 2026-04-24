import json

import pytest

from med_paper_assistant.domain.services.wikilink_validator import (
    find_citation_key_for_pmid,
    validate_wikilinks_in_content,
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


def test_validate_wikilinks_accepts_foam_compatible_reference_links():
    content = (
        "Plain [[smith2024_12345678]], "
        "anchored [[smith2024_12345678#^finding]], "
        "aliased [[smith2024_12345678|Smith 2024]], "
        "embedded ![[smith2024_12345678#^quote]], "
        "internal [[methods]], and figure [[figure-1]]."
    )

    result, fixed = validate_wikilinks_in_content(content)

    assert result.is_valid is True
    assert result.issues == []
    assert fixed == content


def test_validate_wikilinks_still_flags_pmid_only_citations():
    result, _ = validate_wikilinks_in_content("Old citation [[12345678]].")

    assert result.is_valid is False
    assert result.issues[0].issue_type == "missing_prefix"
