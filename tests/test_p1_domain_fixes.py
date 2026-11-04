"""Regression tests for P1 domain/service audit findings (DOM-1/2/3/8/10/12/15)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pandas as pd

from med_paper_assistant.domain.services.citation_converter import (
    restore_reversible_citations_to_wikilinks,
    wikilinks_to_pandoc,
)
from med_paper_assistant.domain.services.reference_key_resolution import (
    extract_pmid_from_key,
    resolve_reference_metadata,
)
from med_paper_assistant.domain.services.references_section import split_references_section
from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.domain.value_objects.reference_id import ReferenceId
from med_paper_assistant.infrastructure.services.analyzer import Analyzer
from med_paper_assistant.infrastructure.services.drafter import Drafter

METADATA = {
    "11111111": {
        "title": "First study",
        "authors": ["Smith J"],
        "journal": "J Test",
        "year": "2024",
    },
    "zot_ABC123XY": {
        "title": "Zotero study",
        "authors": ["Jones K"],
        "journal": "J Zot",
        "year": "2023",
        "citation_key": "jones2023_zot_ABC123XY",
    },
}


def _make_drafter(tmp_path) -> Drafter:
    ref = MagicMock()
    ref.get_metadata.side_effect = lambda ref_id: METADATA.get(ref_id, {})
    ref.list_references.return_value = list(METADATA)
    drafter = Drafter(ref, drafts_dir=str(tmp_path / "drafts"))
    drafter._git_committer = MagicMock()
    drafter._git_committer_root = os.path.dirname(drafter.drafts_dir)
    os.makedirs(drafter.drafts_dir, exist_ok=True)
    return drafter


# ── DOM-1 ────────────────────────────────────────────────────────────────────


class TestDom1ReversibleRegex:
    def test_statistics_parenthetical_is_not_removed(self):
        text = "Enrolled (n = 1500) [[a2020_12345678]] ok"
        assert restore_reversible_citations_to_wikilinks(text) == text

    def test_statistics_parenthetical_not_converted_to_pandoc(self):
        result = wikilinks_to_pandoc("Enrolled (n = 1500) [[a2020_12345678]] ok")
        assert "(n = 1500)" in result.content
        assert "[@a2020_12345678]" in result.content

    def test_generated_author_date_markers_still_restore(self):
        for marker in ("(Smith et al., 2024)", "(Smith et al. 2024)", "(Smith & Lee, 2024)"):
            restored = restore_reversible_citations_to_wikilinks(
                f"Text {marker} [[s2024_1234567]]."
            )
            assert restored == "Text [[s2024_1234567]]."


# ── DOM-2 / DOM-15 ───────────────────────────────────────────────────────────


class TestReferencesSplit:
    def test_tail_sections_are_separated(self):
        split = split_references_section(
            "Body\n\n---\n\n## References\n\n[1] x\n\n## Figure Legends\n\nFig 1.\n"
        )
        assert split.body == "Body"
        assert "[1] x" in split.references
        assert split.tail.startswith("## Figure Legends")

    def test_no_references(self):
        split = split_references_section("Body only\n")
        assert not split.has_references
        assert split.body == "Body only"


class TestDom2TailPreserved:
    def test_sync_references_keeps_sections_after_references(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = os.path.join(drafter.drafts_dir, "results.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "Text [[smith2024_11111111]].\n\n## References\n\nold\n\n"
                "## Figure Legends\n\nFigure 1. Legend text.\n"
            )

        result = drafter.sync_references_from_wikilinks("results.md")

        assert result["citations_found"] == 1
        content = open(path, encoding="utf-8").read()
        assert "## Figure Legends" in content
        assert "Figure 1. Legend text." in content
        assert content.count("## References") == 1
        assert content.index("## References") < content.index("## Figure Legends")

    def test_resync_does_not_accumulate_rules_or_tail(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = os.path.join(drafter.drafts_dir, "results.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Text [[smith2024_11111111]].\n\n## Tables\n\nTable 1.\n")
        drafter.sync_references_from_wikilinks("results.md")
        drafter.sync_references_from_wikilinks("results.md")
        content = open(path, encoding="utf-8").read()
        assert content.count("## Tables") == 1
        assert content.count("Table 1.") == 1


class TestDom15CompileDraft:
    def test_create_draft_with_existing_references_has_single_heading(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = drafter.create_draft(
            "intro.md", "Claim [PMID:11111111].\n\n## References\n\nmanual entry\n"
        )
        content = open(path, encoding="utf-8").read()
        assert content.count("## References") == 1
        assert "manual entry" not in content

    def test_create_draft_without_citations_adds_no_references_heading(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = drafter.create_draft("intro.md", "No citations here.\n")
        content = open(path, encoding="utf-8").read()
        assert "## References" not in content

    def test_unresolved_pmid_is_flagged_not_unknown_title(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = drafter.create_draft("intro.md", "Claim [PMID:99999999].\n")
        content = open(path, encoding="utf-8").read()
        assert "metadata unavailable" in content
        assert "Unknown Title" not in content
        assert "Unknown Journal" not in content

    def test_insert_citation_preserves_tail(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = drafter.create_draft("intro.md", "Claim one [PMID:11111111]. Another sentence.\n")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n## Figure Legends\n\nFigure 1. Legend.\n")

        drafter.insert_citation("intro.md", "Another sentence.", "11111111")

        content = open(path, encoding="utf-8").read()
        assert content.count("## References") == 1
        assert "Figure 1. Legend." in content
        assert content.index("## References") < content.index("## Figure Legends")


# ── DOM-3 ────────────────────────────────────────────────────────────────────


class TestDom3NonPmidKeys:
    def test_zotero_key_is_not_a_pmid(self):
        assert extract_pmid_from_key("smith2024_zot_12345678") is None
        assert extract_pmid_from_key("jones2023_doi_10.1000") is None
        assert extract_pmid_from_key("tang2023_38049909") == "38049909"
        assert extract_pmid_from_key("PMID:38049909") == "38049909"

    def test_resolve_zotero_key_via_storage_id(self):
        resolved = resolve_reference_metadata(
            "jones2023_zot_ABC123XY", lambda ref_id: METADATA.get(ref_id, {})
        )
        assert resolved is not None
        assert resolved[0] == "zot_ABC123XY"

    def test_resolve_falls_back_to_citation_key_scan(self):
        metadata = {"custom_id": {"citation_key": "jones2023_zot_ABC123XY", "title": "t"}}
        resolved = resolve_reference_metadata(
            "jones2023_zot_ABC123XY",
            lambda ref_id: metadata.get(ref_id, {}),
            lambda: list(metadata),
        )
        assert resolved is not None
        assert resolved[0] == "custom_id"

    def test_export_pipeline_resolves_zotero_key(self):
        from med_paper_assistant.application.export_pipeline import ExportPipeline

        ref = MagicMock()
        ref.get_metadata.side_effect = lambda ref_id: METADATA.get(ref_id, {})
        pipeline = ExportPipeline(ref, MagicMock())
        entry = pipeline._resolve_citation_key("jones2023_zot_ABC123XY")
        assert entry is not None
        assert entry["id"] == "jones2023_zot_ABC123XY"

    def test_sync_references_handles_zotero_key(self, tmp_path):
        drafter = _make_drafter(tmp_path)
        path = os.path.join(drafter.drafts_dir, "intro.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Text [[jones2023_zot_ABC123XY]].\n")
        result = drafter.sync_references_from_wikilinks("intro.md")
        assert result["citations_found"] == 1
        assert result["not_found"] == []


# ── DOM-8 ────────────────────────────────────────────────────────────────────


class TestDom8Analyzer:
    def _analyzer(self, tmp_path, df: pd.DataFrame) -> Analyzer:
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        df.to_csv(data_dir / "d.csv", index=False)
        return Analyzer(data_dir=str(data_dir), results_dir=str(tmp_path / "results"))

    def test_paired_ttest_with_nan_in_different_rows(self, tmp_path):
        df = pd.DataFrame(
            {
                "pre": [1.0, 2.0, None, 4.0, 5.0, 6.0],
                "post": [2.0, None, 3.5, 5.5, 6.0, 8.0],
            }
        )
        result = self._analyzer(tmp_path, df).run_statistical_test(
            "d.csv", "paired_ttest", variables=["pre", "post"]
        )
        assert "Paired T-Test Results" in result
        assert "nan" not in result.lower()

    def test_paired_ttest_too_few_pairs_returns_error(self, tmp_path):
        df = pd.DataFrame({"pre": [1.0, None], "post": [None, 2.0]})
        result = self._analyzer(tmp_path, df).run_statistical_test(
            "d.csv", "paired_ttest", variables=["pre", "post"]
        )
        assert result.startswith("Error")

    def test_table_one_ignores_nan_group(self, tmp_path):
        df = pd.DataFrame(
            {
                "group": ["A", "A", "A", "B", "B", "B", None],
                "age": [50.0, 52.0, 55.0, 60.0, 61.0, 63.0, 70.0],
                "sex": ["M", "F", "M", "F", "F", "M", "M"],
            }
        )
        table = self._analyzer(tmp_path, df).generate_table_one("d.csv", "group", ["age"], ["sex"])
        header = table.splitlines()[2]
        assert "nan" not in table.lower()
        assert header.count("(N=") == 3  # Overall + 2 groups

    def test_format_pvalue_non_finite(self, tmp_path):
        analyzer = Analyzer(data_dir=str(tmp_path), results_dir=str(tmp_path))
        assert analyzer._format_pvalue(float("nan")) == "N/A"


# ── DOM-10 ───────────────────────────────────────────────────────────────────


class TestDom10WikilinkValidator:
    def test_repeated_wikilink_on_two_lines_reported_twice(self):
        result, _ = validate_wikilinks_in_content("see [[12345678]]\nand [[12345678]] again")
        assert result.total_wikilinks == 2
        assert len(result.issues) == 2
        assert {issue.line_number for issue in result.issues} == {1, 2}

    def test_messy_format_not_double_counted(self):
        result, _ = validate_wikilinks_in_content("see Smith 2024 [[12345678]] here")
        assert result.total_wikilinks == 1
        assert len(result.issues) == 1


# ── DOM-12 ───────────────────────────────────────────────────────────────────


class TestDom12ReferenceId:
    def test_none_year_does_not_leak_into_key(self):
        ref = ReferenceId.from_article({"pmid": "1", "year": None, "authors": ["Smith J"]})
        assert "None" not in ref.citation_key
        assert ref.citation_key == "smithnd_1"

    def test_non_ascii_author_is_folded(self):
        ref = ReferenceId.from_article(
            {"pmid": "123", "year": 2020, "authors_full": [{"last_name": "Müller"}]}
        )
        assert ref.citation_key == "muller2020_123"

    def test_cjk_author_falls_back_to_anon(self):
        ref = ReferenceId.from_article(
            {"pmid": "123", "year": 2020, "authors_full": [{"last_name": "王"}]}
        )
        assert ref.citation_key == "anon2020_123"

    def test_none_last_name_is_safe(self):
        ref = ReferenceId.from_article(
            {"pmid": "123", "year": 2020, "authors_full": [{"last_name": None}]}
        )
        assert ref.citation_key == "anon2020_123"
