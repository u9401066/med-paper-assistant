"""Tests for CSL Citation Formatter + Pandoc Exporter + Reference.to_csl_json()."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from med_paper_assistant.domain.entities.reference import Reference
from med_paper_assistant.domain.value_objects.citation import CitationStyle

# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

TEMPLATES_CSL = Path(__file__).parent.parent / "templates" / "csl"


@pytest.fixture
def sample_ref() -> Reference:
    """A realistic PubMed-style reference."""
    return Reference(
        unique_id="38049909",
        title="Remimazolam versus propofol for procedural sedation: a systematic review",
        source="pubmed",
        pmid="38049909",
        doi="10.1093/bja/aet378",
        authors=["Tang WC", "Chen MY", "Liu TJ", "Wang HK", "Lin CS", "Huang CJ", "Wu GJ"],
        authors_full=[
            {"last_name": "Tang", "first_name": "Wei-Chih", "initials": "WC"},
            {"last_name": "Chen", "first_name": "Ming-Yuan", "initials": "MY"},
            {"last_name": "Liu", "first_name": "Tsai-Jung", "initials": "TJ"},
            {"last_name": "Wang", "first_name": "Hao-Kuang", "initials": "HK"},
            {"last_name": "Lin", "first_name": "Chun-Sung", "initials": "CS"},
            {"last_name": "Huang", "first_name": "Cheuk-Kwan", "initials": "CJ"},
            {"last_name": "Wu", "first_name": "Guann-Jou", "initials": "GJ"},
        ],
        journal="British Journal of Anaesthesia",
        journal_abbrev="Br J Anaesth",
        year=2024,
        volume="132",
        issue="1",
        pages="45-56",
    )


@pytest.fixture
def sample_ref_minimal() -> Reference:
    """A reference with minimal data."""
    return Reference(
        unique_id="12345",
        title="Minimal reference",
        authors=["Smith J"],
        year=2023,
    )


@pytest.fixture
def two_refs(sample_ref: Reference) -> list[Reference]:
    """Two references for bibliography formatting."""
    ref2 = Reference(
        unique_id="99999999",
        title="Deep learning in anesthesiology: A review",
        source="pubmed",
        pmid="99999999",
        doi="10.1097/ALN.0000000000004567",
        authors=["Lee SH", "Park JY"],
        authors_full=[
            {"last_name": "Lee", "first_name": "Sung-Hoon", "initials": "SH"},
            {"last_name": "Park", "first_name": "Ji-Young", "initials": "JY"},
        ],
        journal="Anesthesiology",
        journal_abbrev="Anesthesiology",
        year=2023,
        volume="139",
        issue="3",
        pages="301-315",
    )
    return [sample_ref, ref2]


# ═══════════════════════════════════════════════════════════════════
# Reference.to_csl_json() Tests
# ═══════════════════════════════════════════════════════════════════


class TestReferenceToCslJson:
    """Test Reference → CSL-JSON conversion."""

    def test_basic_fields(self, sample_ref: Reference):
        csl = sample_ref.to_csl_json()
        assert csl["id"] == "38049909"
        assert csl["type"] == "article-journal"
        assert csl["title"] == sample_ref.title
        assert csl["DOI"] == "10.1093/bja/aet378"
        assert csl["PMID"] == "38049909"

    def test_authors_from_authors_full(self, sample_ref: Reference):
        csl = sample_ref.to_csl_json()
        authors = csl["author"]
        assert len(authors) == 7
        assert authors[0] == {"family": "Tang", "given": "Wei-Chih"}
        assert authors[1] == {"family": "Chen", "given": "Ming-Yuan"}

    def test_authors_fallback_to_authors_list(self, sample_ref_minimal: Reference):
        csl = sample_ref_minimal.to_csl_json()
        authors = csl["author"]
        assert len(authors) == 1
        assert authors[0] == {"family": "Smith", "given": "J"}

    def test_issued_date(self, sample_ref: Reference):
        csl = sample_ref.to_csl_json()
        assert csl["issued"] == {"date-parts": [[2024]]}

    def test_container_title_uses_abbrev(self, sample_ref: Reference):
        csl = sample_ref.to_csl_json()
        assert csl["container-title"] == "Br J Anaesth"

    def test_container_title_falls_back_to_journal(self):
        ref = Reference(
            unique_id="1",
            title="Test",
            journal="Full Journal Name",
            year=2024,
        )
        csl = ref.to_csl_json()
        assert csl["container-title"] == "Full Journal Name"

    def test_custom_ref_id(self, sample_ref: Reference):
        csl = sample_ref.to_csl_json(ref_id="custom-id")
        assert csl["id"] == "custom-id"

    def test_volume_issue_pages(self, sample_ref: Reference):
        csl = sample_ref.to_csl_json()
        assert csl["volume"] == "132"
        assert csl["issue"] == "1"
        assert csl["page"] == "45-56"

    def test_missing_optional_fields_omitted(self):
        ref = Reference(unique_id="2", title="Bare minimum")
        csl = ref.to_csl_json()
        assert "container-title" not in csl
        assert "volume" not in csl
        assert "DOI" not in csl

    def test_empty_authors_full_uses_authors(self):
        ref = Reference(
            unique_id="3",
            title="Test",
            authors=["Wang HK", "Lin CS"],
            authors_full=[],
            year=2024,
        )
        csl = ref.to_csl_json()
        assert len(csl["author"]) == 2
        assert csl["author"][0]["family"] == "Wang"


# ═══════════════════════════════════════════════════════════════════
# CSL Citation Formatter Tests
# ═══════════════════════════════════════════════════════════════════


class TestCSLCitationFormatter:
    """Test CSL-based citation formatting using citeproc-py."""

    @pytest.fixture(autouse=True)
    def _import_formatter(self):
        """Import formatter, skip if citeproc-py not available."""
        try:
            from med_paper_assistant.infrastructure.services.csl_formatter import (
                CSLCitationFormatter,
                reference_to_csl_json,
            )

            self.CSLCitationFormatter = CSLCitationFormatter
            self.reference_to_csl_json = reference_to_csl_json
        except ImportError:
            pytest.skip("citeproc-py not installed")

    def test_vancouver_csl_exists(self):
        """Vancouver CSL file should be available."""
        fmt = self.CSLCitationFormatter("vancouver")
        assert fmt.available, f"Vancouver CSL not found. Available: {fmt.list_available_styles()}"

    def test_format_bibliography_vancouver(self, sample_ref: Reference):
        fmt = self.CSLCitationFormatter("vancouver")
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        entries = fmt.format_bibliography([sample_ref])
        assert len(entries) == 1
        entry = entries[0]
        # Should contain author, title, journal, year
        assert "Tang" in entry
        assert "Remimazolam" in entry
        assert "2024" in entry

    def test_format_bibliography_multiple(self, two_refs: list[Reference]):
        fmt = self.CSLCitationFormatter("vancouver")
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        entries = fmt.format_bibliography(two_refs)
        assert len(entries) == 2
        # Each entry should be different
        assert entries[0] != entries[1]

    def test_format_in_text_citations_vancouver(self, two_refs: list[Reference]):
        fmt = self.CSLCitationFormatter("vancouver")
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        citations = fmt.format_in_text_citations(two_refs)
        assert len(citations) == 2
        # Vancouver uses numeric: "1", "1,2", etc.
        assert "1" in citations[0]

    def test_format_single(self, sample_ref: Reference):
        fmt = self.CSLCitationFormatter("vancouver")
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        entry = fmt.format_single(sample_ref)
        assert len(entry) > 10
        assert "Tang" in entry

    def test_list_available_styles(self):
        styles = self.CSLCitationFormatter.list_available_styles()
        assert isinstance(styles, list)
        # At minimum, vancouver should be there
        assert any("vancouver" in s for s in styles) or any("harvard" in s for s in styles)

    def test_unavailable_style_not_available(self):
        fmt = self.CSLCitationFormatter("nonexistent-style-xyz")
        assert not fmt.available

    def test_unavailable_style_raises_on_format(self, sample_ref: Reference):
        fmt = self.CSLCitationFormatter("nonexistent-style-xyz")
        with pytest.raises(RuntimeError, match="not available"):
            fmt.format_bibliography([sample_ref])

    def test_empty_references(self):
        fmt = self.CSLCitationFormatter("vancouver")
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        assert fmt.format_bibliography([]) == []
        assert fmt.format_in_text_citations([]) == []

    def test_reference_to_csl_json_matches_entity(self, sample_ref: Reference):
        """The standalone function and entity method should produce equivalent output."""
        from_func = self.reference_to_csl_json(sample_ref, ref_id="test1")
        from_entity = sample_ref.to_csl_json(ref_id="test1")
        assert from_func == from_entity

    def test_apa_style_if_available(self, sample_ref: Reference):
        fmt = self.CSLCitationFormatter("apa")
        if not fmt.available:
            pytest.skip("APA CSL not available")
        entries = fmt.format_bibliography([sample_ref])
        assert len(entries) == 1
        # APA should contain year in parentheses somewhere
        assert "2024" in entries[0]

    def test_html_output(self, sample_ref: Reference):
        fmt = self.CSLCitationFormatter("vancouver")
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        entries = fmt.format_bibliography([sample_ref], output_format="html")
        assert len(entries) == 1
        # HTML output should contain tags or at minimum the text
        assert "Tang" in entries[0]

    def test_citation_style_enum_input(self, sample_ref: Reference):
        """Should accept CitationStyle enum as input."""
        fmt = self.CSLCitationFormatter(CitationStyle.VANCOUVER)
        if not fmt.available:
            pytest.skip("Vancouver CSL not available")
        entries = fmt.format_bibliography([sample_ref])
        assert len(entries) == 1


# ═══════════════════════════════════════════════════════════════════
# Pandoc Exporter Tests
# ═══════════════════════════════════════════════════════════════════


class TestPandocExporter:
    """Test Pandoc-based document export."""

    @pytest.fixture(autouse=True)
    def _import_exporter(self):
        """Import exporter, skip if pypandoc not available."""
        try:
            from med_paper_assistant.infrastructure.services.pandoc_exporter import PandocExporter

            self.PandocExporter = PandocExporter
        except ImportError:
            pytest.skip("pypandoc not installed")

    def test_pandoc_available(self):
        exporter = self.PandocExporter()
        # May or may not be available depending on environment
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")
        version = exporter.get_pandoc_version()
        assert version is not None

    def test_markdown_to_docx(self):
        exporter = self.PandocExporter()
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")

        md = "# Introduction\n\nThis is a test paragraph with **bold** and *italic*.\n"

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        try:
            result = exporter.markdown_to_docx(md, output_path)
            assert os.path.isfile(result)
            assert os.path.getsize(result) > 0
        finally:
            os.unlink(output_path)

    def test_markdown_to_html(self):
        exporter = self.PandocExporter()
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")

        md = "# Title\n\nParagraph with a [link](https://example.com).\n"
        html = exporter.markdown_to_html(md)
        assert "<h1" in html or "Title" in html
        assert "Paragraph" in html

    def test_markdown_with_table(self):
        exporter = self.PandocExporter()
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")

        md = """# Results

| Drug | Dose | Effect |
|------|------|--------|
| Remimazolam | 0.2 mg/kg | Sedation |
| Propofol | 1.5 mg/kg | Anesthesia |

Table 1: Comparison of sedation agents.
"""

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        try:
            result = exporter.markdown_to_docx(md, output_path)
            assert os.path.isfile(result)
            # Docx with table should be larger than minimal
            assert os.path.getsize(result) > 1000
        finally:
            os.unlink(output_path)

    def test_markdown_to_docx_creates_output_dir(self):
        exporter = self.PandocExporter()
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "subdir", "output.docx")
            result = exporter.markdown_to_docx("# Test\n\nContent.\n", output_path)
            assert os.path.isfile(result)

    def test_convert_with_csl_json_refs(self, sample_ref: Reference):
        exporter = self.PandocExporter()
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")

        csl_json = [sample_ref.to_csl_json(ref_id="tang2024")]

        # Markdown with Pandoc citation syntax
        md = """---
nocite: "@*"
---

# Introduction

Remimazolam is a novel benzodiazepine [@tang2024].

# References
"""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        try:
            result = exporter.convert_with_csl_json_refs(
                md,
                output_path,
                csl_json,
                csl="vancouver",
            )
            assert os.path.isfile(result)
        finally:
            os.unlink(output_path)

    def test_markdown_file_to_docx(self):
        exporter = self.PandocExporter()
        if not exporter.available:
            pytest.skip("Pandoc binary not installed")

        md_content = "# Test\n\nThis is from a file.\n"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as md_file:
            md_file.write(md_content)
            md_path = md_file.name

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as out:
            output_path = out.name

        try:
            result = exporter.markdown_file_to_docx(md_path, output_path)
            assert os.path.isfile(result)
        finally:
            os.unlink(md_path)
            os.unlink(output_path)

    def test_unavailable_pandoc_raises(self):
        """If Pandoc is not available, convert should raise."""
        exporter = self.PandocExporter()
        if exporter.available:
            # Can't easily test this when Pandoc IS available
            # Just verify the property works
            assert exporter.available is True
            return
        with pytest.raises(RuntimeError, match="not available"):
            exporter.convert("# Test", "docx")
