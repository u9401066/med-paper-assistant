"""Cross-layer contracts for formal academic output profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from med_paper_assistant.domain.paper_types import (
    PAPER_TYPES,
    WRITING_ORDER,
    get_concept_requirements,
)
from med_paper_assistant.infrastructure.services.concept_template_reader import (
    ConceptTemplateReader,
)
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator
from med_paper_assistant.interfaces.mcp.tools.project.settings import PaperTypeSchema
from med_paper_assistant.shared.constants import PAPER_TYPES as LEGACY_PAPER_TYPES

FORMAL_OUTPUT_TYPES = {
    "research-proposal",
    "project-closeout-report",
    "student-paper",
    "conference-paper",
    "thesis-dissertation",
    "arxiv-preprint",
}


def test_formal_profiles_have_domain_and_writing_order_contracts() -> None:
    assert FORMAL_OUTPUT_TYPES <= PAPER_TYPES.keys()
    assert FORMAL_OUTPUT_TYPES <= WRITING_ORDER.keys()
    for paper_type in FORMAL_OUTPUT_TYPES:
        assert PAPER_TYPES[paper_type].sections
        assert PAPER_TYPES[paper_type].typical_words > 0
        assert WRITING_ORDER[paper_type]


def test_legacy_taxonomy_matches_domain_taxonomy() -> None:
    """Guard the remaining compatibility constant from silently drifting."""
    assert set(LEGACY_PAPER_TYPES) == set(PAPER_TYPES)
    for paper_type, profile in PAPER_TYPES.items():
        assert LEGACY_PAPER_TYPES[paper_type]["name"] == profile.name
        assert LEGACY_PAPER_TYPES[paper_type]["description"] == profile.description
        assert LEGACY_PAPER_TYPES[paper_type]["sections"] == profile.sections


def test_ui_schema_is_derived_from_domain_taxonomy() -> None:
    field_schema = PaperTypeSchema.model_json_schema()["properties"]["paper_type"]
    assert field_schema["enum"] == list(PAPER_TYPES)
    assert field_schema["enumNames"] == [profile.name for profile in PAPER_TYPES.values()]


@pytest.mark.parametrize("paper_type", sorted(FORMAL_OUTPUT_TYPES))
def test_each_formal_output_has_a_complete_concept_template(paper_type: str) -> None:
    rendered = ConceptTemplateReader().get_concept_template(
        "Boundary Study",
        paper_type=paper_type,
        target_journal="Target",
        memo="Keep this note.",
    )

    assert "Boundary Study" in rendered
    assert "Target" in rendered
    assert "Keep this note." in rendered
    assert "{{" not in rendered


@pytest.mark.parametrize(
    "paper_type",
    ["research-proposal", "project-closeout-report", "student-paper", "thesis-dissertation"],
)
def test_non_novelty_profiles_do_not_inherit_journal_novelty_template(paper_type: str) -> None:
    rendered = ConceptTemplateReader().get_concept_template("Study", paper_type=paper_type)
    assert "NOVELTY STATEMENT" not in rendered
    assert "novelty_statement" not in get_concept_requirements(paper_type).core_required


def _proposal_concept(*, include_objectives: bool = True) -> str:
    objectives = (
        "## Objectives\n\n"
        "We will determine whether the planned intervention can improve the primary outcome.\n\n"
        if include_objectives
        else ""
    )
    return (
        "## Background and Rationale\n\n"
        "Current services vary substantially across settings and patient groups. "
        "Prior observational work describes inconsistent implementation, limited follow-up, "
        "and unresolved questions about feasibility, equity, cost, patient-important outcomes, "
        "long-term sustainability, and access across underserved communities.\n\n"
        "## Research Gap\n\n"
        "Existing studies do not evaluate the complete intervention prospectively or report "
        "implementation outcomes using a prespecified and reproducible framework that includes "
        "equity, resource use, stakeholder experience, and transparent decision thresholds.\n\n"
        f"{objectives}"
        "## Methods Overview\n\n"
        "We propose a prospective mixed-methods study with prespecified eligibility criteria, "
        "transparent sampling, blinded outcome assessment, reproducible analysis, and governance.\n\n"
        "## Expected Impact\n\n"
        "The project is expected to produce a reusable protocol, feasibility estimates, and "
        "evidence for a later adequately powered evaluation.\n"
    )


def test_proposal_validation_uses_its_own_contract_and_skips_novelty(tmp_path: Path) -> None:
    concept = tmp_path / "proposal.md"
    concept.write_text(_proposal_concept(), encoding="utf-8")

    result = ConceptValidator().validate(
        str(concept),
        paper_type="research-proposal",
        run_novelty_check=True,
        run_consistency_check=False,
    )

    assert result.structure_valid is True
    assert result.novelty_checked is False
    assert result.overall_passed is True
    assert result.sections["research_question"].required is True


def test_proposal_validation_blocks_missing_objectives(tmp_path: Path) -> None:
    concept = tmp_path / "proposal.md"
    concept.write_text(_proposal_concept(include_objectives=False), encoding="utf-8")

    result = ConceptValidator().validate_structure_only(
        str(concept), paper_type="research-proposal"
    )

    assert result.structure_valid is False
    assert any("Research Question" in error for error in result.errors)


def test_validation_cache_separates_novelty_modes(tmp_path: Path) -> None:
    concept = tmp_path / "concept.md"
    concept.write_text(
        "## NOVELTY STATEMENT\n\n"
        "This is the first independently verified comparison of two reproducible approaches "
        "using prespecified outcomes and an explicit analysis protocol.\n\n"
        "## KEY SELLING POINTS\n\n"
        "1. **Contribution**: Compares both approaches.\n"
        "2. **Method**: Uses prespecified outcomes.\n"
        "3. **Evidence**: Reports reproducible analyses.\n",
        encoding="utf-8",
    )
    validator = ConceptValidator()

    structural = validator.validate_structure_only(str(concept))
    with_novelty = validator.validate(
        str(concept), run_novelty_check=True, run_consistency_check=False
    )

    assert structural.novelty_checked is False
    assert with_novelty.novelty_checked is True
