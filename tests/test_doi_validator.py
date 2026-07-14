"""Unit tests for the offline DOI validator (med_paper_assistant.shared.doi)."""

from __future__ import annotations

import pytest

from med_paper_assistant.shared.doi import is_valid_doi, normalize_doi, validate_doi


class TestNormalizeDoi:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("10.1001/jama.2020.1585", "10.1001/jama.2020.1585"),
            ("  10.1001/jama.2020.1585  ", "10.1001/jama.2020.1585"),
            ("https://doi.org/10.1001/jama.2020.1585", "10.1001/jama.2020.1585"),
            ("http://dx.doi.org/10.1038/nature12373", "10.1038/nature12373"),
            ("doi:10.1016/j.cell.2019.05.031", "10.1016/j.cell.2019.05.031"),
            ("DOI: 10.1016/j.cell.2019.05.031", "10.1016/j.cell.2019.05.031"),
            ("10.1001/jama.2020.1585.", "10.1001/jama.2020.1585"),
            ("(10.1001/jama.2020.1585)", "(10.1001/jama.2020.1585"),
        ],
    )
    def test_normalize(self, raw: str, expected: str) -> None:
        assert normalize_doi(raw) == expected

    def test_empty(self) -> None:
        assert normalize_doi("") == ""
        assert normalize_doi("   ") == ""


class TestIsValidDoi:
    @pytest.mark.parametrize(
        "doi",
        [
            "10.1001/jama.2020.1585",
            "10.1038/nature12373",
            "10.1016/j.cell.2019.05.031",
            "https://doi.org/10.1097/ALN.0000000000003456",
            "doi:10.1213/ANE.0000000000004002",
            "10.1234/foo(bar):baz_qux",
        ],
    )
    def test_valid(self, doi: str) -> None:
        assert is_valid_doi(doi) is True

    @pytest.mark.parametrize(
        "doi",
        [
            "",
            "   ",
            "not-a-doi",
            "10.123/x",  # registrant too short (needs 4-9 digits)
            "11.1001/jama.2020.1585",  # must start with 10.
            "10.1001",  # missing slash + suffix
            "10.1001/",  # empty suffix
            "abc10.1001/jama",  # junk prefix
            "10.1001/jama 2020",  # space in suffix
        ],
    )
    def test_invalid(self, doi: str) -> None:
        assert is_valid_doi(doi) is False


class TestValidateDoi:
    def test_valid_returns_normalized(self) -> None:
        ok, normalized, reason = validate_doi("https://doi.org/10.1001/jama.2020.1585")
        assert ok is True
        assert normalized == "10.1001/jama.2020.1585"
        assert reason == ""

    def test_empty_reason(self) -> None:
        ok, normalized, reason = validate_doi("")
        assert ok is False
        assert normalized == ""
        assert reason == "empty DOI"

    def test_missing_prefix_reason(self) -> None:
        ok, _normalized, reason = validate_doi("11.1001/jama.2020.1585")
        assert ok is False
        assert "10." in reason

    def test_missing_slash_reason(self) -> None:
        ok, _normalized, reason = validate_doi("10.1001")
        assert ok is False
        assert "/" in reason

    def test_pattern_mismatch_reason(self) -> None:
        ok, _normalized, reason = validate_doi("10.12/short")
        assert ok is False
        assert "pattern" in reason
