"""Tests for ExportPipeline — citation conversion + bibliography + Pandoc export."""

import json
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ── Mock broken modules in the application.__init__ import chain ──
# save_reference.py → pubmed (missing), use_cases.__init__ → search_literature (missing)
for _mod_name in [
    "med_paper_assistant.infrastructure.external.pubmed",
    "med_paper_assistant.infrastructure.external.pubmed.parser",
    "med_paper_assistant.application.use_cases.search_literature",
]:
    sys.modules.setdefault(_mod_name, types.ModuleType(_mod_name))
# Provide expected attributes for save_reference.py imports
sys.modules["med_paper_assistant.infrastructure.external.pubmed"].PubMedClient = MagicMock  # type: ignore[attr-defined]
sys.modules["med_paper_assistant.infrastructure.external.pubmed.parser"].PubMedParser = MagicMock  # type: ignore[attr-defined]
# Provide expected attribute for use_cases.__init__ import
sys.modules["med_paper_assistant.application.use_cases.search_literature"].SearchLiteratureUseCase = MagicMock  # type: ignore[attr-defined]

from med_paper_assistant.application.export_pipeline import ExportPipeline
from med_paper_assistant.domain.entities.reference import Reference


@pytest.fixture
def mock_ref_manager():
    """Mock ReferenceManager that returns metadata for known PMIDs."""
    manager = MagicMock()
    manager.get_metadata.side_effect = lambda pmid: {
        "38049909": {
            "title": "Remimazolam sedation in ICU patients",
            "authors": ["Tang J", "Lee K"],
            "authors_full": [
                {"last_name": "Tang", "first_name": "J", "initials": "J"},
                {"last_name": "Lee", "first_name": "K", "initials": "K"},
            ],
            "journal": "British Journal of Anaesthesia",
            "journal_abbrev": "Br J Anaesth",
            "year": "2023",
            "volume": "131",
            "issue": "3",
            "pages": "456-463",
            "doi": "10.1016/j.bja.2023.06.001",
        },
        "12345678": {
            "title": "AI in anesthesiology: A review",
            "authors": ["Lee K"],
            "authors_full": [
                {"last_name": "Lee", "first_name": "K", "initials": "K"},
            ],
            "journal": "Anesthesiology",
            "journal_abbrev": "Anesthesiology",
            "year": "2024",
            "volume": "140",
            "issue": "1",
            "pages": "100-120",
            "doi": "10.1097/ALN.0000000001",
        },
    }.get(pmid)
    return manager


@pytest.fixture
def mock_pandoc():
    """Mock PandocExporter."""
    pandoc = MagicMock()
    pandoc.available = True
    pandoc.markdown_to_docx.return_value = "/output/test.docx"
    pandoc.convert.return_value = "<p>HTML content</p>"
    return pandoc


@pytest.fixture
def pipeline(mock_ref_manager, mock_pandoc):
    return ExportPipeline(mock_ref_manager, mock_pandoc)


# ──────────────────────────────────────────────────────────────────────────────
# prepare_for_pandoc
# ──────────────────────────────────────────────────────────────────────────────


class TestPrepareForPandoc:
    def test_converts_wikilinks(self, pipeline):
        content = "Text [[tang2023_38049909]] here."
        result = pipeline.prepare_for_pandoc(content)
        assert "[@tang2023_38049909]" in result["content"]
        assert result["citation_keys"] == ["tang2023_38049909"]

    def test_builds_bibliography(self, pipeline):
        content = "Text [[tang2023_38049909]]."
        result = pipeline.prepare_for_pandoc(content)
        assert len(result["bibliography"]) == 1
        bib = result["bibliography"][0]
        assert bib["id"] == "tang2023_38049909"
        assert "Remimazolam" in bib["title"]

    def test_multiple_citations(self, pipeline):
        content = "First [[tang2023_38049909]] second [[lee2024_12345678]]."
        result = pipeline.prepare_for_pandoc(content)
        assert len(result["bibliography"]) == 2
        assert len(result["citation_keys"]) == 2

    def test_missing_reference_warns(self, pipeline):
        content = "Text [[unknown2099_99999999]]."
        result = pipeline.prepare_for_pandoc(content)
        assert len(result["warnings"]) == 1
        assert "not found" in result["warnings"][0]
        assert len(result["bibliography"]) == 0

    def test_no_citations(self, pipeline):
        content = "No citations here."
        result = pipeline.prepare_for_pandoc(content)
        assert result["citation_keys"] == []
        assert result["bibliography"] == []

    def test_reversible_format(self, pipeline):
        content = "Text [1]<!-- [[tang2023_38049909]] -->."
        result = pipeline.prepare_for_pandoc(content)
        assert "[@tang2023_38049909]" in result["content"]
        assert len(result["bibliography"]) == 1


# ──────────────────────────────────────────────────────────────────────────────
# _extract_pmid
# ──────────────────────────────────────────────────────────────────────────────


class TestExtractPmid:
    def test_standard_key(self, pipeline):
        assert pipeline._extract_pmid("tang2023_38049909") == "38049909"

    def test_pmid_prefix(self, pipeline):
        assert pipeline._extract_pmid("PMID:38049909") == "38049909"

    def test_bare_pmid(self, pipeline):
        assert pipeline._extract_pmid("38049909") == "38049909"

    def test_no_pmid(self, pipeline):
        assert pipeline._extract_pmid("introduction") is None


# ──────────────────────────────────────────────────────────────────────────────
# _resolve_citation_key
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveCitationKey:
    def test_known_key(self, pipeline):
        entry = pipeline._resolve_citation_key("tang2023_38049909")
        assert entry is not None
        assert entry["id"] == "tang2023_38049909"
        assert entry["type"] == "article-journal"

    def test_unknown_key(self, pipeline):
        entry = pipeline._resolve_citation_key("unknown_99999999")
        assert entry is None

    def test_non_citation_key(self, pipeline):
        entry = pipeline._resolve_citation_key("introduction")
        assert entry is None


# ──────────────────────────────────────────────────────────────────────────────
# export_docx
# ──────────────────────────────────────────────────────────────────────────────


class TestExportDocx:
    def test_export_calls_pandoc(self, pipeline, mock_pandoc, tmp_path):
        # Create a draft file
        draft = tmp_path / "introduction.md"
        draft.write_text("Text [[tang2023_38049909]].", encoding="utf-8")
        output = tmp_path / "introduction.docx"

        result = pipeline.export_docx(str(draft), str(output), csl_style="vancouver")

        assert result["success"] is True
        assert mock_pandoc.markdown_to_docx.called
        # Check Pandoc was called with a bibliography file
        call_kwargs = mock_pandoc.markdown_to_docx.call_args
        assert call_kwargs.kwargs.get("bibliography") is not None
        assert call_kwargs.kwargs.get("csl") == "vancouver"

    def test_export_without_pandoc(self, mock_ref_manager, tmp_path):
        pandoc = MagicMock()
        pandoc.available = False
        pipe = ExportPipeline(mock_ref_manager, pandoc)
        draft = tmp_path / "test.md"
        draft.write_text("Text.", encoding="utf-8")

        with pytest.raises(RuntimeError, match="Pandoc"):
            pipe.export_docx(str(draft), str(tmp_path / "test.docx"))


# ──────────────────────────────────────────────────────────────────────────────
# build_bibliography_json
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildBibliographyJson:
    def test_build_and_write(self, pipeline, tmp_path):
        content = "Text [[tang2023_38049909]] and [[lee2024_12345678]]."
        bib_path = str(tmp_path / "bib.json")
        entries = pipeline.build_bibliography_json(content, bib_path)

        assert len(entries) == 2
        assert os.path.exists(bib_path)

        with open(bib_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2

    def test_build_without_writing(self, pipeline):
        content = "Text [[tang2023_38049909]]."
        entries = pipeline.build_bibliography_json(content)
        assert len(entries) == 1
        assert entries[0]["id"] == "tang2023_38049909"
