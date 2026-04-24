import os
import subprocess

import pytest

from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.infrastructure.services.drafter import (
    CitationStyle,
    Drafter,
    draft_filename_from_section,
)


@pytest.mark.integration
def test_drafter(tmp_path):
    # Setup
    test_ref_dir = str(tmp_path / "test_references_draft")
    test_draft_dir = str(tmp_path / "test_drafts")

    ref_manager = ReferenceManager(base_dir=test_ref_dir)
    drafter = Drafter(ref_manager, drafts_dir=test_draft_dir)

    # 1. Prepare a known PMID (e.g., 41285088 from previous test)
    pmid = "41285088"

    # 2. Create Content with Placeholder
    content = f"""
# Introduction

Asthma is a chronic condition (PMID:{pmid}).
Recent studies have shown significant economic burden [PMID:{pmid}].
    """

    print("Creating draft...")
    filepath = drafter.create_draft("test_intro", content)
    print(f"Draft created at: {filepath}")

    # 3. Verify Output
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            final_content = f.read()

        print("\n--- Final Content ---")
        print(final_content)
        print("---------------------")

        if "[1]" in final_content and "## References" in final_content:
            print("Test PASSED: Citations and Bibliography found.")
        else:
            print("Test FAILED: Missing citations or bibliography.")

        # Check if reference was automatically fetched/saved
        if os.path.exists(os.path.join(test_ref_dir, pmid)):
            print(f"Reference {pmid} was automatically saved.")
        else:
            print(f"Reference {pmid} was NOT saved (Unexpected).")

    else:
        print("Test FAILED: File not created.")


# ── Unit Tests (no network, no integration mark) ──────────────────────────


class TestDraftFilenameValidation:
    """Tests for cross-platform-safe draft filenames."""

    def _make_drafter(self, tmp_path):
        ref = ReferenceManager(base_dir=str(tmp_path / "refs"))
        return Drafter(ref, drafts_dir=str(tmp_path / "drafts"))

    @pytest.mark.parametrize(
        "bad_filename",
        [
            "",
            "   ",
            ".md",
            "../escape",
            r"..\escape",
            "/tmp/escape",
            r"C:\tmp\escape",
            "folder/file",
            "bad:name",
            "CON",
        ],
    )
    def test_create_draft_rejects_unsafe_filename(self, tmp_path, bad_filename):
        drafter = self._make_drafter(tmp_path)

        with pytest.raises(ValueError, match="Draft filename"):
            drafter.create_draft(bad_filename, "# Methods\n\nContent.")

        assert not (tmp_path / "drafts" / ".md").exists()

    def test_create_draft_normalizes_missing_suffix(self, tmp_path):
        drafter = self._make_drafter(tmp_path)

        path = drafter.create_draft("methods", "# Methods\n\nWe analysed data.")

        assert os.path.basename(path) == "methods.md"
        assert os.path.exists(path)

    def test_section_filename_derivation(self):
        assert draft_filename_from_section("Methods") == "methods.md"
        assert draft_filename_from_section("Title Page") == "title_page.md"
        assert draft_filename_from_section("!!!") == ""


class TestFormatAuthorsVancouver:
    """Tests for _format_authors_vancouver."""

    def _make_drafter(self, tmp_path):
        ref = ReferenceManager(base_dir=str(tmp_path / "refs"))
        return Drafter(ref, drafts_dir=str(tmp_path / "drafts"))

    def test_uses_authors_full_with_initials(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {
            "authors_full": [
                {"last_name": "Collins", "initials": "GS"},
                {"last_name": "Moons", "initials": "KGM"},
            ]
        }
        result = drafter._format_authors_vancouver(metadata)
        assert result == "Collins GS, Moons KGM"

    def test_truncates_with_et_al(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {
            "authors_full": [{"last_name": f"Author{i}", "initials": "A"} for i in range(10)]
        }
        result = drafter._format_authors_vancouver(metadata, max_authors=3)
        assert result == "Author0 A, Author1 A, Author2 A, et al."

    def test_fallback_to_flat_authors(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {"authors": ["Smith John", "Doe Jane"]}
        result = drafter._format_authors_vancouver(metadata)
        assert result == "Smith John, Doe Jane"

    def test_fallback_flat_truncation(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {"authors": [f"Author{i}" for i in range(8)]}
        result = drafter._format_authors_vancouver(metadata, max_authors=6)
        assert "et al." in result
        assert result.count(",") == 6  # 6 commas: 6 names + "et al."

    def test_no_authors_returns_unknown(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        result = drafter._format_authors_vancouver({})
        assert result == "Unknown"

    def test_missing_initials_uses_last_name_only(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {"authors_full": [{"last_name": "Solo"}]}
        result = drafter._format_authors_vancouver(metadata)
        assert result == "Solo"


class TestFormatBibliographyEntry:
    """Tests for _format_bibliography_entry."""

    def _make_drafter(self, tmp_path, style="vancouver"):
        ref = ReferenceManager(base_dir=str(tmp_path / "refs"))
        return Drafter(ref, drafts_dir=str(tmp_path / "drafts"), citation_style=style)

    def test_uses_preformatted_vancouver(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {
            "citation": {
                "vancouver": "Smith J. A Great Paper. Nature. 2024;600:1-5. doi:10.1234/test"
            }
        }
        entry = drafter._format_bibliography_entry(1, metadata, "12345678")
        assert entry == "[1] Smith J. A Great Paper. Nature. 2024;600:1-5. doi:10.1234/test\n"

    def test_uses_preformatted_apa(self, tmp_path):
        drafter = self._make_drafter(tmp_path, style="apa")
        metadata = {"citation": {"apa": "Smith, J. (2024). A Great Paper. *Nature*, *600*, 1-5."}}
        entry = drafter._format_bibliography_entry(1, metadata, "12345678")
        assert entry == "Smith, J. (2024). A Great Paper. *Nature*, *600*, 1-5.\n"

    def test_manual_vancouver_with_volume_issue_pages_doi(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {
            "authors_full": [
                {"last_name": "Alkaissi", "initials": "H"},
                {"last_name": "McFarlane", "initials": "SI"},
            ],
            "title": "AI Hallucinations.",
            "journal": "Cureus",
            "year": "2023",
            "volume": "15",
            "issue": "2",
            "pages": "e35179",
            "doi": "10.7759/cureus.35179",
        }
        entry = drafter._format_bibliography_entry(5, metadata, "36811129")
        assert "[5]" in entry
        assert "Alkaissi H, McFarlane SI" in entry
        assert ";15(2):e35179" in entry
        assert "doi:10.7759/cureus.35179" in entry
        assert "PMID:" not in entry  # No more raw PMID in output

    def test_manual_fallback_no_volume(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {
            "authors": ["Smith John"],
            "title": "A Paper.",
            "journal": "Science",
            "year": "2025",
        }
        entry = drafter._format_bibliography_entry(1, metadata, "99999999")
        assert "Science. 2025." in entry
        assert ";" not in entry  # No volume segment

    def test_vancouver_with_doi_only(self, tmp_path):
        drafter = self._make_drafter(tmp_path)
        metadata = {
            "authors_full": [{"last_name": "Doe", "initials": "J"}],
            "title": "Test.",
            "journal": "BMJ",
            "year": "2024",
            "doi": "10.1136/test",
        }
        entry = drafter._format_bibliography_entry(1, metadata, "11111111")
        assert "doi:10.1136/test" in entry

    def test_nature_style_preformatted(self, tmp_path):
        drafter = self._make_drafter(tmp_path, style="nature")
        metadata = {"citation": {"nature": "Smith J. Great Paper. *Nature* **600**, 1-5 (2024)."}}
        entry = drafter._format_bibliography_entry(3, metadata, "12345678")
        assert entry.startswith("3. ")

    def test_ama_style_manual(self, tmp_path):
        drafter = self._make_drafter(tmp_path, style="ama")
        metadata = {
            "authors_full": [{"last_name": "Lee", "initials": "K"}],
            "title": "Research.",
            "journal": "JAMA",
            "year": "2025",
            "volume": "330",
            "pages": "100-105",
        }
        entry = drafter._format_bibliography_entry(2, metadata, "22222222")
        assert entry.startswith("2. ")
        assert ";330" in entry
        assert ":100-105" in entry


class TestSyncReferencesBlankLines:
    """Test that sync_references_from_wikilinks produces blank lines between entries."""

    @staticmethod
    def _write_reference(refs_dir, pmid, key, title, authors=None, year="2024"):
        import json

        ref_dir = refs_dir / pmid
        ref_dir.mkdir(parents=True)
        meta = {
            "title": title,
            "authors": authors or ["Author A"],
            "journal": "J Test",
            "year": year,
            "citation_key": key,
        }
        (ref_dir / "metadata.json").write_text(json.dumps(meta))

    def test_references_separated_by_blank_lines(self, tmp_path):
        """References section should have blank lines between entries."""
        # Setup minimal references
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        for pmid, key, title in [
            ("11111111", "smith2024_11111111", "Paper One"),
            ("22222222", "doe2024_22222222", "Paper Two"),
        ]:
            self._write_reference(refs_dir, pmid, key, title)

        # Create draft with wikilinks
        draft = "# Test\n\nSome text [[smith2024_11111111]] and [[doe2024_22222222]].\n"
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(ref, drafts_dir=str(drafts_dir))

        result = drafter.sync_references_from_wikilinks("test.md")
        assert result["success"]
        assert result["citations_found"] == 2

        # Read output and check blank lines
        content = (drafts_dir / "test.md").read_text()
        # Between [1] entry end and [2] entry start, there should be a blank line
        ref_section = content.split("## References")[1]
        lines = ref_section.strip().split("\n")
        # Should have: entry1, blank, entry2, blank (or trailing)
        non_empty = [ln for ln in lines if ln.strip()]
        assert len(non_empty) == 2  # Two reference entries
        # Check there's at least one blank line between them
        found_blank_between = False
        saw_first = False
        for ln in lines:
            if ln.strip().startswith("[1]"):
                saw_first = True
            elif saw_first and not ln.strip():
                found_blank_between = True
                break
        assert found_blank_between, "No blank line between reference entries"

    def test_resync_visible_reversible_citations_does_not_duplicate_prefixes(self, tmp_path):
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        self._write_reference(refs_dir, "11111111", "smith2024_11111111", "Paper One")

        draft = "# Test\n\nSome text [1] [[smith2024_11111111]].\n"
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(ref, drafts_dir=str(drafts_dir))

        result = drafter.sync_references_from_wikilinks("test.md")
        assert result["success"]

        content = (drafts_dir / "test.md").read_text()
        body_content = content.split("## References")[0]
        assert "[1] [1] [[smith2024_11111111]]" not in body_content
        assert body_content.count("[1] [[smith2024_11111111]]") == 1

        references_content = content.split("## References")[1]
        assert "[[smith2024_11111111]]" in references_content

    def test_resync_legacy_reversible_citations_upgrades_to_visible_format(self, tmp_path):
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        self._write_reference(refs_dir, "11111111", "smith2024_11111111", "Paper One")

        draft = "# Test\n\nSome text [1]<!-- [[smith2024_11111111]] -->.\n"
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(ref, drafts_dir=str(drafts_dir))

        result = drafter.sync_references_from_wikilinks("test.md")
        assert result["success"]

        content = (drafts_dir / "test.md").read_text()
        body_content = content.split("## References")[0]
        assert "<!-- [[smith2024_11111111]] -->" not in body_content
        assert body_content.count("[1] [[smith2024_11111111]]") == 1

    def test_resync_visible_apa_reversible_citations_does_not_duplicate_prefixes(self, tmp_path):
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        self._write_reference(
            refs_dir,
            "11111111",
            "smith2024_11111111",
            "Paper One",
            authors=["Smith John", "Doe Jane", "Lee Kay"],
        )

        draft = "# Test\n\nSome text (Smith et al., 2024) [[smith2024_11111111]].\n"
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(
            ref,
            drafts_dir=str(drafts_dir),
            citation_style=CitationStyle.APA.value,
        )

        result = drafter.sync_references_from_wikilinks("test.md")
        assert result["success"]

        content = (drafts_dir / "test.md").read_text()
        body_content = content.split("## References")[0]
        assert (
            "(Smith et al., 2024) (Smith et al., 2024) [[smith2024_11111111]]" not in body_content
        )
        assert body_content.count("(Smith et al., 2024) [[smith2024_11111111]]") == 1

    def test_resync_visible_harvard_reversible_citations_does_not_duplicate_prefixes(
        self, tmp_path
    ):
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        self._write_reference(
            refs_dir,
            "11111111",
            "smith2024_11111111",
            "Paper One",
            authors=["Smith John", "Doe Jane", "Lee Kay"],
        )

        draft = "# Test\n\nSome text (Smith et al. 2024) [[smith2024_11111111]].\n"
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(
            ref,
            drafts_dir=str(drafts_dir),
            citation_style=CitationStyle.HARVARD.value,
        )

        result = drafter.sync_references_from_wikilinks("test.md")
        assert result["success"]

        content = (drafts_dir / "test.md").read_text()
        body_content = content.split("## References")[0]
        assert "(Smith et al. 2024) (Smith et al. 2024) [[smith2024_11111111]]" not in body_content
        assert body_content.count("(Smith et al. 2024) [[smith2024_11111111]]") == 1

    def test_resync_visible_nature_reversible_citations_does_not_duplicate_prefixes(self, tmp_path):
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        self._write_reference(refs_dir, "11111111", "smith2024_11111111", "Paper One")

        draft = "# Test\n\nSome text ^1^ [[smith2024_11111111]].\n"
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(
            ref,
            drafts_dir=str(drafts_dir),
            citation_style=CitationStyle.NATURE.value,
        )

        result = drafter.sync_references_from_wikilinks("test.md")
        assert result["success"]

        content = (drafts_dir / "test.md").read_text()
        body_content = content.split("## References")[0]
        assert "^1^ ^1^ [[smith2024_11111111]]" not in body_content
        assert body_content.count("^1^ [[smith2024_11111111]]") == 1

    def test_insert_citation_rejects_wikilink_synced_draft(self, tmp_path):
        refs_dir = tmp_path / "refs"
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        draft = (
            "# Test\n\nBody sentence.\n\n## References\n\n[1] Example ref. [[smith2024_11111111]]\n"
        )
        (drafts_dir / "test.md").write_text(draft)

        ref = ReferenceManager(base_dir=str(refs_dir))
        drafter = Drafter(ref, drafts_dir=str(drafts_dir))

        with pytest.raises(ValueError) as exc_info:
            drafter.insert_citation("test", "Body sentence", "11111111")

        message = str(exc_info.value)
        assert "wikilink-synced references" in message
        assert "sync_references_from_wikilinks()" in message
        assert "sync_references tool" in message


def test_create_draft_refreshes_draft_section_graph_notes(tmp_path):
    refs_dir = tmp_path / "refs"
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()

    ref = ReferenceManager(base_dir=str(refs_dir))
    drafter = Drafter(ref, drafts_dir=str(drafts_dir))

    drafter.create_draft(
        "results.md",
        "# Results\n\nThis section mentions [[figure-1]] and reports the main outcome.",
    )

    graph_note = tmp_path / "notes" / "draft-sections" / "results-results.md"
    assert graph_note.exists()
    graph_text = graph_note.read_text(encoding="utf-8")
    assert 'type: "draft-section"' in graph_text
    assert 'section_kind: "results"' in graph_text
    assert "[[figure-1]]" in graph_text


def test_git_committer_refreshes_when_project_switches(tmp_path):
    def init_git_repo(repo_path):
        subprocess.run(["git", "init"], cwd=str(repo_path), capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(repo_path),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(repo_path),
            capture_output=True,
            check=True,
        )

    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Alpha")
    alpha_repo = tmp_path / "projects" / "alpha"
    init_git_repo(alpha_repo)

    ref = ReferenceManager(base_dir=str(tmp_path / "projects" / "alpha" / "references"))
    drafter = Drafter(ref, project_manager=pm)

    first_committer = drafter.git_committer
    first_repo = first_committer._repo_dir

    pm.create_project(name="Beta")
    beta_repo = tmp_path / "projects" / "beta"
    init_git_repo(beta_repo)
    second_committer = drafter.git_committer
    second_repo = second_committer._repo_dir

    assert first_repo == tmp_path / "projects" / "alpha"
    assert second_repo == tmp_path / "projects" / "beta"
    assert first_committer.enabled is True
    assert second_committer.enabled is True
