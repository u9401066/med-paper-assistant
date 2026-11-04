"""Regression tests for writing-hook fixes (DOM-4/5/6/7/9/11/13)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.writing_hooks import WritingHooksEngine


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    d = tmp_path / "proj"
    d.mkdir()
    (d / ".audit").mkdir()
    return d


@pytest.fixture()
def engine(project_dir: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_dir)


def _write_plan(project_dir: Path, section: str = "Results", caption: str = "Flow chart") -> None:
    plan = {
        "asset_plan": [
            {"id": "fig-1", "type": "plot", "section": section, "caption": caption},
        ]
    }
    (project_dir / "manuscript-plan.yaml").write_text(yaml.dump(plan), encoding="utf-8")


def _write_manifest(project_dir: Path, figures: list[dict[str, object]]) -> None:
    (project_dir / "results").mkdir(exist_ok=True)
    (project_dir / "results" / "manifest.json").write_text(
        json.dumps({"figures": figures}), encoding="utf-8"
    )


class TestDom4Sections:
    def test_subsection_words_count_toward_parent(self, engine: WritingHooksEngine):
        info = engine._extract_body_word_count("## Methods\n\n### Participants\n" + "word " * 100)
        assert 95 <= info["body_words"] <= 105
        assert info["breakdown"] == [{"section": "Methods", "words": info["body_words"]}]

    def test_nested_body_sections_not_double_counted(self, engine: WritingHooksEngine):
        text = "## Discussion\n" + "a " * 50 + "\n### Conclusion\n" + "b " * 50
        assert engine._extract_body_word_count(text)["body_words"] == 100

    def test_duplicate_heading_names_are_merged(self, engine: WritingHooksEngine):
        sections = engine._parse_sections("## Notes\none\n\n## Other\nx\n\n## Notes\ntwo")
        assert "one" in sections["Notes"] and "two" in sections["Notes"]

    def test_title_heading_does_not_swallow_sections(self, engine: WritingHooksEngine):
        full = engine._parse_sections_full("# Title\n\n## Methods\nmethods text")
        assert full["Title"] == ""
        assert full["Methods"] == "methods text"

    def test_a1_counts_subsection_text(self, tmp_path: Path):
        d = tmp_path / "p"
        d.mkdir()
        (d / ".audit").mkdir()
        profile = {"paper": {"sections": [{"name": "Methods", "word_limit": 100}]}}
        (d / "journal-profile.yaml").write_text(yaml.dump(profile), encoding="utf-8")
        eng = WritingHooksEngine(d)
        r = eng.check_word_count_compliance("## Methods\n\n### Participants\n" + "word " * 100)
        assert r.passed is True
        assert r.stats["sections_checked"][0]["word_count"] >= 95

    def test_b11_sees_results_subsection(self, engine: WritingHooksEngine):
        text = "## Results\n\n### Primary\nThis suggests that the drug works, indicating that it is good."
        r = engine.check_results_interpretation(text)
        assert r.stats["interpretive_count"] >= 1


class TestDom5NValues:
    def test_thousands_separator_and_subgroup_not_critical(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\nWe analysed n = 1,200 patients.\n\n"
            "## Results\n\nA total of n = 1,200 patients. 45 patients developed hypotension."
        )
        r = engine.check_n_value_consistency(text)
        assert r.passed is True
        assert not any(i.severity == "CRITICAL" for i in r.issues)
        assert "1200" in r.stats["methods_n_values"]
        info = [i for i in r.issues if i.severity == "INFO"]
        assert info and "count of 45" in info[0].message

    def test_total_mismatch_still_critical(self, engine: WritingHooksEngine):
        text = "## Methods\n\nn = 1,200 patients.\n\n## Results\n\nA total of n = 1,500 patients."
        r = engine.check_n_value_consistency(text)
        assert r.passed is False
        assert "N=1500" in r.issues[0].message

    def test_methods_subsection_values_are_source_of_truth(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\n### Participants\nN = 300 patients.\n\n"
            "## Results\n\nTotal of 300 patients were analysed."
        )
        assert engine.check_n_value_consistency(text).passed is True


class TestDom6AssetPlacement:
    def test_empty_filename_and_caption_do_not_count_as_placed(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        _write_plan(project_dir)
        _write_manifest(project_dir, [{"number": 1}])
        r = engine.check_asset_plan_coverage("## Results\n\nNothing relevant here at all.")
        assert r.passed is False
        assert any("not referenced or embedded" in i.message for i in r.issues)

    def test_bare_word_figure_is_not_a_placement(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        _write_plan(project_dir)
        _write_manifest(project_dir, [{"filename": "a.png"}])
        r = engine.check_asset_plan_coverage("## Results\n\nThe figure is discussed later.")
        assert any("not referenced or embedded" in i.message for i in r.issues)

    def test_subsection_and_case_insensitive_section_lookup(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "figures" / "a.png").write_bytes(b"png")
        _write_plan(project_dir, section="results")
        _write_manifest(project_dir, [{"number": 1, "filename": "a.png", "caption": "Flow chart"}])
        text = "## Results\n\n### Primary outcome\nSee Figure 1 for details."
        r = engine.check_asset_plan_coverage(text)
        assert r.passed is True
        assert r.stats["placed_assets"] == 1

    def test_empty_manifest_caption_does_not_match_planned_caption(
        self, engine: WritingHooksEngine
    ):
        planned = {"id": "fig-9", "kind": "figure", "section": "Results", "caption": "Flow chart"}
        entries = [
            {"kind": "figure", "number": "1", "filename": "a.png", "caption": ""},
            {"kind": "figure", "number": "2", "filename": "b.png", "caption": "Other"},
        ]
        assert engine._match_planned_asset_to_manifest(planned, entries) is None


class TestDom7ParseErrors:
    def test_corrupt_manifest_reported_by_c7b(self, engine: WritingHooksEngine, project_dir: Path):
        _write_plan(project_dir)
        (project_dir / "results").mkdir()
        (project_dir / "results" / "manifest.json").write_text("{not json", encoding="utf-8")
        r = engine.check_asset_plan_coverage("## Results\n\nSee Figure 1.")
        assert r.passed is False
        assert any("Cannot parse results/manifest.json" in i.message for i in r.issues)

    def test_corrupt_manifest_reported_by_c7d(self, engine: WritingHooksEngine, project_dir: Path):
        (project_dir / "results").mkdir()
        (project_dir / "results" / "manifest.json").write_text("{not json", encoding="utf-8")
        r = engine.check_cross_references("See Figure 1.")
        assert r.passed is False
        assert r.issues[0].hook_id == "C7d"

    def test_corrupt_manifest_reported_by_c7a(self, tmp_path: Path):
        d = tmp_path / "p"
        d.mkdir()
        (d / ".audit").mkdir()
        (d / "journal-profile.yaml").write_text(
            yaml.dump({"assets": {"figures_max": 6, "tables_max": 5}}), encoding="utf-8"
        )
        (d / "results").mkdir()
        (d / "results" / "manifest.json").write_text("[", encoding="utf-8")
        r = WritingHooksEngine(d).check_figure_table_counts("Figure 1")
        assert r.passed is False
        assert any("Cannot parse" in i.message for i in r.issues)

    def test_corrupt_plan_reported_by_c7b(self, engine: WritingHooksEngine, project_dir: Path):
        (project_dir / "manuscript-plan.yaml").write_text("asset_plan: [unclosed", encoding="utf-8")
        r = engine.check_asset_plan_coverage("## Results\n\ntext")
        assert r.passed is False
        assert any("manuscript-plan.yaml" in i.message for i in r.issues)

    def test_missing_files_still_pass(self, engine: WritingHooksEngine):
        assert engine.check_cross_references("See Figure 1.").passed is True
        assert engine.check_asset_plan_coverage("## Results\n\ntext").passed is True


class TestDom9CitationKeys:
    @pytest.mark.parametrize(
        "key",
        [
            "garcia-lopez2020_12345678",
            "smith2024_zot_ABC",
            "smith2024_1234",
            "smith2024_12345678",
        ],
    )
    def test_a4_accepts_valid_keys(self, engine: WritingHooksEngine, key: str):
        r = engine.check_wikilink_format(f"Prior work [[{key}]] shows this.")
        assert r.passed is True
        assert r.stats["valid_count"] == 1

    def test_a4_still_flags_bare_pmid_and_prefix_forms(self, engine: WritingHooksEngine):
        r = engine.check_wikilink_format("See [[12345678]] and [[PMID: 87654321]].")
        assert r.stats["issue_count"] == 2

    def test_c12_audits_hyphenated_and_zotero_keys(self, engine: WritingHooksEngine):
        text = "## Introduction\n\nSee [[garcia-lopez2020_12345678]] and [[smith2024_zot_ABC]]."
        r = engine.check_citation_relevance_audit(text)
        assert r.stats["total_cited_refs"] == 2


class TestDom11Appendix:
    def test_prose_appendix_is_not_a_reference(self, engine: WritingHooksEngine):
        r = engine.check_supplementary_crossref("The appendix was removed in surgery.")
        assert r.passed is True
        assert r.stats["text_references"] == 0

    def test_labelled_appendix_is_a_reference(self, engine: WritingHooksEngine):
        r = engine.check_supplementary_crossref("Details are in Appendix A and Appendix S2.")
        assert r.stats["text_references"] == 2


class TestDom13WordCount:
    def test_cjk_characters_counted_individually(self, engine: WritingHooksEngine):
        assert engine._count_words("患者年齡為六十歲") == 8

    def test_numbers_with_separators_are_single_tokens(self, engine: WritingHooksEngine):
        assert engine._count_words("n = 1,200 and p = 0.05") == 5

    def test_mixed_text(self, engine: WritingHooksEngine):
        assert engine._count_words("Patients 患者 were enrolled") == 5
