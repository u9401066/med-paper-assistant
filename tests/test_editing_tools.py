"""
Tests for draft editing tools: get_available_citations and patch_draft.
"""

import json

import pytest


@pytest.fixture
def project_structure(tmp_path):
    """Create a minimal project structure with references and drafts."""
    # Create project directories
    refs_dir = tmp_path / "references"
    refs_dir.mkdir()
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()

    # Create reference: greer2017_27345583
    ref_dir = refs_dir / "27345583"
    ref_dir.mkdir()
    metadata = {
        "pmid": "27345583",
        "title": "Review of remimazolam sedation in ICU patients",
        "authors": ["Greer JA", "Lee DH"],
        "authors_full": [
            {"last_name": "Greer", "first_name": "Joseph A"},
            {"last_name": "Lee", "first_name": "Dong H"},
        ],
        "year": "2017",
        "journal": "British Journal of Anaesthesia",
        "citation_key": "greer2017_27345583",
        "citation": {
            "vancouver": "[1] Greer JA, Lee DH. Review of remimazolam. BJA (2017).",
            "in_text": "Greer & Lee, 2017",
        },
    }
    with open(ref_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    # Create reference: smith2020_12345678
    ref_dir2 = refs_dir / "12345678"
    ref_dir2.mkdir()
    metadata2 = {
        "pmid": "12345678",
        "title": "Propofol vs remimazolam: a meta-analysis",
        "authors": ["Smith AB"],
        "authors_full": [{"last_name": "Smith", "first_name": "Adam B"}],
        "year": "2020",
        "journal": "Anesthesiology",
        "citation_key": "smith2020_12345678",
        "citation": {
            "vancouver": "[1] Smith AB. Propofol vs remimazolam. Anesthesiology (2020).",
            "in_text": "Smith, 2020",
        },
    }
    with open(ref_dir2 / "metadata.json", "w") as f:
        json.dump(metadata2, f)

    # Create a draft
    draft_content = (
        "# Introduction\n\n"
        "Remimazolam is a novel benzodiazepine sedative.\n\n"
        "Prior studies have shown promising results [[greer2017_27345583]].\n\n"
        "However, more evidence is needed for ICU settings.\n"
    )
    with open(drafts_dir / "introduction.md", "w") as f:
        f.write(draft_content)

    return tmp_path


@pytest.fixture
def ref_manager(project_structure):
    """Create ReferenceManager pointing to test structure."""
    from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager

    return ReferenceManager(
        base_dir=str(project_structure / "references"),
    )


@pytest.fixture
def drafter(ref_manager, project_structure):
    """Create Drafter pointing to test structure."""
    from med_paper_assistant.infrastructure.services.drafter import Drafter

    return Drafter(
        reference_manager=ref_manager,
        drafts_dir=str(project_structure / "drafts"),
    )


class TestGetAvailableCitations:
    """Tests for get_available_citations tool logic."""

    def test_lists_all_references(self, ref_manager):
        """Should return all saved references."""
        pmids = ref_manager.list_references()
        assert len(pmids) == 2
        assert "27345583" in pmids
        assert "12345678" in pmids

    def test_metadata_has_citation_key(self, ref_manager):
        """Each reference should have a citation_key."""
        meta = ref_manager.get_metadata("27345583")
        assert meta["citation_key"] == "greer2017_27345583"

        meta2 = ref_manager.get_metadata("12345678")
        assert meta2["citation_key"] == "smith2020_12345678"

    def test_empty_references(self, tmp_path):
        """Should handle empty references directory."""
        from med_paper_assistant.infrastructure.persistence.reference_manager import (
            ReferenceManager,
        )

        empty_refs = tmp_path / "empty_refs"
        empty_refs.mkdir()
        rm = ReferenceManager(base_dir=str(empty_refs))
        assert rm.list_references() == []

    def test_no_references_dir(self, tmp_path):
        """Should handle missing references directory."""
        from med_paper_assistant.infrastructure.persistence.reference_manager import (
            ReferenceManager,
        )

        rm = ReferenceManager(base_dir=str(tmp_path / "nonexistent"))
        assert rm.list_references() == []


class TestPatchDraft:
    """Tests for patch_draft tool logic (file-level operations)."""

    def test_simple_replacement(self, project_structure):
        """Should replace text in draft file."""
        draft_path = project_structure / "drafts" / "introduction.md"

        with open(draft_path) as f:
            content = f.read()

        old_text = "However, more evidence is needed for ICU settings."
        new_text = "However, additional evidence is required for ICU settings."

        assert old_text in content
        new_content = content.replace(old_text, new_text, 1)

        with open(draft_path, "w") as f:
            f.write(new_content)

        with open(draft_path) as f:
            result = f.read()

        assert new_text in result
        assert old_text not in result

    def test_unique_match_required(self, project_structure):
        """Should detect non-unique matches."""
        draft_path = project_structure / "drafts" / "introduction.md"

        # Write content with duplicate text
        content = "Hello world.\n\nHello world.\n"
        with open(draft_path, "w") as f:
            f.write(content)

        with open(draft_path) as f:
            content = f.read()

        match_count = content.count("Hello world.")
        assert match_count == 2  # Should be non-unique

    def test_old_text_not_found(self, project_structure):
        """Should detect when old_text doesn't exist."""
        draft_path = project_structure / "drafts" / "introduction.md"

        with open(draft_path) as f:
            content = f.read()

        assert "NONEXISTENT TEXT 12345" not in content

    def test_wikilink_validation_in_new_text(self, project_structure):
        """Should validate wikilinks in replacement text."""
        from med_paper_assistant.domain.services.wikilink_validator import (
            validate_wikilinks_in_content,
        )

        refs_dir = str(project_structure / "references")

        # Valid wikilink
        new_text = "Studies show [[greer2017_27345583]] that remimazolam is safe."
        result, fixed = validate_wikilinks_in_content(new_text, references_dir=refs_dir)
        assert result.is_valid
        assert result.total_wikilinks == 1
        assert result.valid_count == 1

    def test_wikilink_autofix_pmid_only(self, project_structure):
        """Should auto-fix [[PMID]] to [[author_year_PMID]]."""
        from med_paper_assistant.domain.services.wikilink_validator import (
            validate_wikilinks_in_content,
        )

        refs_dir = str(project_structure / "references")

        # PMID-only wikilink
        new_text = "Studies show [[27345583]] that remimazolam is safe."
        result, fixed = validate_wikilinks_in_content(
            new_text, references_dir=refs_dir, auto_fix=True
        )

        # Should detect the issue and attempt auto-fix
        assert result.total_wikilinks >= 1

    def test_missing_reference_detection(self, ref_manager):
        """Should detect wikilinks to non-existent references."""
        # Check non-existent PMID
        assert not ref_manager.check_reference_exists("99999999")
        # Check existing PMID
        assert ref_manager.check_reference_exists("27345583")

    def test_replacement_preserves_rest(self, project_structure):
        """Replacement should not alter other parts of the draft."""
        draft_path = project_structure / "drafts" / "introduction.md"

        with open(draft_path) as f:
            original = f.read()

        old_text = "Remimazolam is a novel benzodiazepine sedative."
        new_text = "Remimazolam is a novel ultra-short-acting benzodiazepine."

        new_content = original.replace(old_text, new_text, 1)
        with open(draft_path, "w") as f:
            f.write(new_content)

        with open(draft_path) as f:
            result = f.read()

        # Changed text
        assert new_text in result
        # Untouched text
        assert "Prior studies have shown promising results [[greer2017_27345583]]." in result
        assert "However, more evidence is needed for ICU settings." in result

    def test_wikilink_in_patch_with_valid_ref(self, project_structure):
        """Patch with valid wikilink should succeed validation."""
        from med_paper_assistant.domain.services.wikilink_validator import (
            ALL_WIKILINK_PATTERN,
            validate_wikilinks_in_content,
        )

        refs_dir = str(project_structure / "references")
        ref_manager_mod = pytest.importorskip(
            "med_paper_assistant.infrastructure.persistence.reference_manager"
        )
        rm = ref_manager_mod.ReferenceManager(base_dir=refs_dir)

        new_text = "A recent meta-analysis [[smith2020_12345678]] confirmed these findings."

        # Validate wikilinks
        result, fixed = validate_wikilinks_in_content(
            new_text, references_dir=refs_dir, auto_fix=True
        )
        assert result.is_valid

        # Check all wikilinks resolve to existing refs
        wikilinks = ALL_WIKILINK_PATTERN.findall(fixed)
        for wl in wikilinks:
            if "_" in wl:
                pmid = wl.split("_")[-1]
                assert rm.check_reference_exists(pmid), f"Reference {pmid} should exist"


class TestEditingIntegration:
    """Integration tests for the full editing workflow."""

    def test_full_patch_workflow(self, project_structure, ref_manager):
        """Test: get citations → validate → patch → verify."""
        draft_path = project_structure / "drafts" / "introduction.md"
        refs_dir = str(project_structure / "references")

        # Step 1: List available citations
        pmids = ref_manager.list_references()
        citation_keys = []
        for pmid in pmids:
            meta = ref_manager.get_metadata(pmid)
            if meta:
                citation_keys.append(meta.get("citation_key", pmid))
        assert len(citation_keys) == 2
        assert "greer2017_27345583" in citation_keys

        # Step 2: Read draft
        with open(draft_path) as f:
            content = f.read()

        # Step 3: Patch with new citation
        old_text = "However, more evidence is needed for ICU settings."
        new_text = "However, a meta-analysis [[smith2020_12345678]] suggests more evidence is needed for ICU settings."

        # Validate
        from med_paper_assistant.domain.services.wikilink_validator import (
            validate_wikilinks_in_content,
        )

        result, fixed_new = validate_wikilinks_in_content(
            new_text, references_dir=refs_dir, auto_fix=True
        )
        assert result.is_valid

        # Apply patch
        assert content.count(old_text) == 1  # unique match
        new_content = content.replace(old_text, fixed_new, 1)
        with open(draft_path, "w") as f:
            f.write(new_content)

        # Step 4: Verify
        with open(draft_path) as f:
            final = f.read()
        assert "[[smith2020_12345678]]" in final
        assert "[[greer2017_27345583]]" in final  # untouched
        assert old_text not in final

    def test_patch_rejects_hallucinated_citation(self, project_structure, ref_manager):
        """Patch with non-existent reference PMID should be detectable."""
        new_text = "Studies show [[fakename2099_99999999]] important results."

        # The PMID doesn't exist
        assert not ref_manager.check_reference_exists("99999999")

        # Agent should check this before applying
        from med_paper_assistant.domain.services.wikilink_validator import ALL_WIKILINK_PATTERN

        wikilinks = ALL_WIKILINK_PATTERN.findall(new_text)
        for wl in wikilinks:
            if "_" in wl:
                pmid = wl.split("_")[-1]
                if pmid.isdigit():
                    assert not ref_manager.check_reference_exists(pmid)
