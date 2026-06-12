"""Tests for article-type-aware hook applicability (common vs type-specific harness).

Verifies that the always-on writing-hooks batch runners gate statistical
Methods↔Results hooks (B8/B11/B16) by paper type, so they do not misfire on
letters, narrative reviews, or case reports — while keeping the empirical-type
behaviour (and legacy default) unchanged.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    ALL_PAPER_TYPES,
    EMPIRICAL_TYPES,
    WritingHooksEngine,
    is_applicable,
    is_type_specific,
    type_specific_hook_ids,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks._applicability import (
    not_applicable_result,
)
from med_paper_assistant.shared.constants import PAPER_TYPES


def _project(tmp_path: Path, paper_type: str | None) -> Path:
    d = tmp_path / f"proj-{paper_type or 'default'}"
    d.mkdir()
    (d / ".audit").mkdir()
    (d / "drafts").mkdir()
    if paper_type is not None:
        (d / "journal-profile.yaml").write_text(
            yaml.dump({"paper": {"type": paper_type}}), encoding="utf-8"
        )
    return d


class TestApplicabilityMatrix:
    def test_all_paper_types_matches_taxonomy(self) -> None:
        assert ALL_PAPER_TYPES == frozenset(PAPER_TYPES.keys())

    def test_empirical_subset(self) -> None:
        assert EMPIRICAL_TYPES <= ALL_PAPER_TYPES
        assert "original-research" in EMPIRICAL_TYPES
        assert "letter" not in EMPIRICAL_TYPES

    def test_b8_applicable_to_empirical(self) -> None:
        for pt in EMPIRICAL_TYPES:
            assert is_applicable("B8", pt) is True

    def test_b8_not_applicable_to_non_empirical(self) -> None:
        for pt in ("letter", "review-article", "case-report", "other"):
            assert is_applicable("B8", pt) is False

    def test_common_hook_applies_to_all(self) -> None:
        # A3 (anti-AI) is common — applies to every paper type.
        for pt in ALL_PAPER_TYPES:
            assert is_applicable("A3", pt) is True

    def test_unknown_paper_type_defaults_to_original_research(self) -> None:
        assert is_applicable("B8", None) is True
        assert is_applicable("B8", "") is True

    def test_type_specific_ids(self) -> None:
        ids = type_specific_hook_ids()
        assert {"B8", "B11", "B16"} <= ids
        assert "A3" not in ids
        assert is_type_specific("B8") is True
        assert is_type_specific("A3") is False

    def test_not_applicable_result_shape(self) -> None:
        r = not_applicable_result("B8", "letter")
        assert r.hook_id == "B8"
        assert r.passed is True
        assert r.issues == []
        assert r.stats["applicable"] is False
        assert r.stats["skipped"] is True
        assert r.stats["paper_type"] == "letter"


class TestRunnerGating:
    METHODS = "We used t-test and chi-square test."
    RESULTS = "The t-test showed significance. Mann-Whitney revealed differences."
    FULL = "# Methods\nWe used t-test.\n# Results\nMann-Whitney revealed differences (p<0.05).\n"

    def test_letter_skips_statistical_hooks(self, tmp_path: Path) -> None:
        engine = WritingHooksEngine(_project(tmp_path, "letter"))
        results = engine.run_post_section_hooks(self.METHODS, self.RESULTS, self.FULL)
        # Keys preserved (backward compatible) but recorded as skipped, not failed.
        for hook_id in ("B8", "B11", "B16"):
            assert hook_id in results
            assert results[hook_id].passed is True
            assert results[hook_id].stats.get("applicable") is False

    def test_original_research_runs_b8(self, tmp_path: Path) -> None:
        engine = WritingHooksEngine(_project(tmp_path, "original-research"))
        results = engine.run_post_section_hooks(self.METHODS, self.RESULTS, self.FULL)
        assert "B8" in results
        # B8 runs for real: Mann-Whitney in Results not in Methods → fails.
        assert results["B8"].passed is False
        assert results["B8"].stats.get("applicable") is not False

    def test_default_profile_runs_b8(self, tmp_path: Path) -> None:
        # No journal-profile → default original-research → B8 runs for real.
        engine = WritingHooksEngine(_project(tmp_path, None))
        results = engine.run_post_section_hooks(self.METHODS, self.RESULTS)
        assert results["B8"].passed is False

    def test_case_report_keeps_common_hooks(self, tmp_path: Path) -> None:
        engine = WritingHooksEngine(_project(tmp_path, "case-report"))
        results = engine.run_post_section_hooks(self.METHODS, self.RESULTS, self.FULL)
        # Statistical hooks skipped, but common structural B-series still run.
        assert results["B8"].stats.get("applicable") is False
        assert "B12" in results  # intro structure stays universal
        assert "B13" in results  # discussion structure stays universal
        assert "B14" in results  # ethical statements stay universal

    def test_hook_applicability_report(self, tmp_path: Path) -> None:
        engine = WritingHooksEngine(_project(tmp_path, "letter"))
        report = engine.hook_applicability()
        assert report["B8"] is False
        assert report["B11"] is False
        assert report["B16"] is False

        engine2 = WritingHooksEngine(_project(tmp_path, "meta-analysis"))
        report2 = engine2.hook_applicability()
        assert report2["B8"] is True
        assert report2["B11"] is True
        assert report2["B16"] is True
