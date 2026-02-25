"""Tests for CitationConverter — bidirectional wikilink ↔ Pandoc conversion."""

from med_paper_assistant.domain.services.citation_converter import (
    _looks_like_citation_key,
    _strip_references_section,
    extract_citation_keys,
    pandoc_to_wikilinks,
    wikilinks_to_pandoc,
)

# ──────────────────────────────────────────────────────────────────────────────
# wikilinks_to_pandoc
# ──────────────────────────────────────────────────────────────────────────────


class TestWikilinksToPandoc:
    """Test wikilink → [@key] conversion."""

    def test_basic_wikilink(self):
        content = "Some text [[tang2023_38049909]] here."
        result = wikilinks_to_pandoc(content)
        assert "[@tang2023_38049909]" in result.content
        assert "[[tang2023_38049909]]" not in result.content
        assert result.citations_converted == 1
        assert "tang2023_38049909" in result.citation_keys

    def test_multiple_wikilinks(self):
        content = "First [[tang2023_38049909]] and second [[lee2024_12345678]]."
        result = wikilinks_to_pandoc(content)
        assert "[@tang2023_38049909]" in result.content
        assert "[@lee2024_12345678]" in result.content
        assert result.citations_converted == 2
        assert len(result.citation_keys) == 2

    def test_reversible_format_numbered(self):
        content = "Some text [1]<!-- [[tang2023_38049909]] --> here."
        result = wikilinks_to_pandoc(content)
        assert "[@tang2023_38049909]" in result.content
        assert "[1]<!-- [[tang2023_38049909]] -->" not in result.content
        assert result.citations_converted == 1

    def test_reversible_format_apa(self):
        content = "Some text (Tang et al., 2023)<!-- [[tang2023_38049909]] --> here."
        result = wikilinks_to_pandoc(content)
        assert "[@tang2023_38049909]" in result.content
        assert result.citations_converted == 1

    def test_mixed_formats(self):
        """Both reversible and raw wikilinks should be converted."""
        content = "[1]<!-- [[tang2023_38049909]] --> and [[lee2024_12345678]]."
        result = wikilinks_to_pandoc(content)
        assert "[@tang2023_38049909]" in result.content
        assert "[@lee2024_12345678]" in result.content
        assert result.citations_converted == 2

    def test_duplicate_key_counted_once_in_keys(self):
        content = "First [[tang2023_38049909]] and again [[tang2023_38049909]]."
        result = wikilinks_to_pandoc(content)
        # Both should be converted but key appears once in keys list
        assert result.citations_converted == 2
        assert result.citation_keys.count("tang2023_38049909") == 1

    def test_non_citation_wikilink_preserved(self):
        """Internal links like [[introduction]] should not be converted."""
        content = "See [[introduction]] for details [[tang2023_38049909]]."
        result = wikilinks_to_pandoc(content)
        assert "[[introduction]]" in result.content
        assert "[@tang2023_38049909]" in result.content
        assert result.citations_converted == 1

    def test_strips_references_section(self):
        content = "Body text.\n\n## References\n\n[1] Tang et al. Title. PMID:38049909.\n"
        result = wikilinks_to_pandoc(content)
        assert "## References" not in result.content
        assert "Tang et al." not in result.content

    def test_strips_references_with_hr(self):
        content = "Body text.\n\n---\n\n## References\n\n[1] Tang et al.\n"
        result = wikilinks_to_pandoc(content)
        assert "## References" not in result.content

    def test_no_citations_returns_empty_result(self):
        content = "No citations here, just plain text."
        result = wikilinks_to_pandoc(content)
        assert result.citations_converted == 0
        assert result.citation_keys == []

    def test_pmid_only_wikilink(self):
        content = "Some [[PMID:38049909]] here."
        result = wikilinks_to_pandoc(content)
        assert "[@PMID:38049909]" in result.content
        assert result.citations_converted == 1

    def test_bare_pmid_wikilink(self):
        content = "Some [[38049909]] here."
        result = wikilinks_to_pandoc(content)
        assert "[@38049909]" in result.content
        assert result.citations_converted == 1

    def test_output_ends_with_newline(self):
        result = wikilinks_to_pandoc("text [[tang2023_38049909]]")
        assert result.content.endswith("\n")


# ──────────────────────────────────────────────────────────────────────────────
# pandoc_to_wikilinks
# ──────────────────────────────────────────────────────────────────────────────


class TestPandocToWikilinks:
    """Test [@key] → [[wikilink]] conversion."""

    def test_basic_pandoc(self):
        content = "Some text [@tang2023_38049909] here."
        result = pandoc_to_wikilinks(content)
        assert "[[tang2023_38049909]]" in result.content
        assert "[@tang2023_38049909]" not in result.content
        assert result.citations_converted == 1

    def test_multi_citation(self):
        content = "Some text [@tang2023_38049909; @lee2024_12345678] here."
        result = pandoc_to_wikilinks(content)
        assert "[[tang2023_38049909]]" in result.content
        assert "[[lee2024_12345678]]" in result.content
        assert result.citations_converted == 2

    def test_single_citation_in_brackets(self):
        content = "Text [@key1] more."
        result = pandoc_to_wikilinks(content)
        assert "[[key1]]" in result.content
        assert result.citations_converted == 1

    def test_multiple_separate_citations(self):
        content = "First [@a] and second [@b]."
        result = pandoc_to_wikilinks(content)
        assert "[[a]]" in result.content
        assert "[[b]]" in result.content
        assert result.citations_converted == 2

    def test_no_citations(self):
        content = "No citations here."
        result = pandoc_to_wikilinks(content)
        assert result.citations_converted == 0


# ──────────────────────────────────────────────────────────────────────────────
# _looks_like_citation_key
# ──────────────────────────────────────────────────────────────────────────────


class TestLooksLikeCitationKey:
    """Test heuristic for distinguishing citation keys from internal links."""

    def test_standard_key(self):
        assert _looks_like_citation_key("tang2023_38049909") is True

    def test_pmid_format(self):
        assert _looks_like_citation_key("PMID:38049909") is True

    def test_bare_pmid(self):
        assert _looks_like_citation_key("38049909") is True

    def test_zotero_key(self):
        assert _looks_like_citation_key("tang2023_zot_ABC123") is True

    def test_doi_key(self):
        assert _looks_like_citation_key("tang2023_doi_10") is True

    def test_internal_link(self):
        assert _looks_like_citation_key("introduction") is False

    def test_methods_link(self):
        assert _looks_like_citation_key("methods") is False

    def test_short_number(self):
        assert _looks_like_citation_key("123") is False

    def test_no_underscore_digits(self):
        assert _looks_like_citation_key("someword") is False


# ──────────────────────────────────────────────────────────────────────────────
# _strip_references_section
# ──────────────────────────────────────────────────────────────────────────────


class TestStripReferencesSection:
    """Test removal of References section."""

    def test_strip_basic(self):
        content = "Body text.\n\n## References\n\n[1] Author. Title."
        result = _strip_references_section(content)
        assert "## References" not in result
        assert "Body text." in result

    def test_no_references(self):
        content = "Body text only."
        result = _strip_references_section(content)
        assert result == content

    def test_strip_with_hr(self):
        content = "Body.\n\n---\n\n## References\n\n[1] Author."
        result = _strip_references_section(content)
        assert "## References" not in result

    def test_preserves_content_before_references(self):
        content = "## Introduction\n\nBody.\n\n## References\n\nRef list."
        result = _strip_references_section(content)
        assert "## Introduction" in result
        assert "Body." in result


# ──────────────────────────────────────────────────────────────────────────────
# extract_citation_keys
# ──────────────────────────────────────────────────────────────────────────────


class TestExtractCitationKeys:
    """Test extracting citation keys from any format."""

    def test_wikilinks(self):
        keys = extract_citation_keys("[[tang2023_38049909]] and [[lee2024_12345678]]")
        assert "tang2023_38049909" in keys
        assert "lee2024_12345678" in keys

    def test_pandoc_format(self):
        keys = extract_citation_keys("[@tang2023_38049909; @lee2024_12345678]")
        assert "tang2023_38049909" in keys
        assert "lee2024_12345678" in keys

    def test_reversible_format(self):
        keys = extract_citation_keys("[1]<!-- [[tang2023_38049909]] -->")
        assert "tang2023_38049909" in keys

    def test_mixed_formats(self):
        content = "[[a2023_111]] and [@b2024_222] and [1]<!-- [[c2025_333]] -->"
        keys = extract_citation_keys(content)
        assert "a2023_111" in keys
        assert "b2024_222" in keys
        assert "c2025_333" in keys

    def test_deduplication(self):
        keys = extract_citation_keys("[[tang2023_38049909]] and [[tang2023_38049909]]")
        assert keys.count("tang2023_38049909") == 1

    def test_skips_internal_links(self):
        keys = extract_citation_keys("[[introduction]] and [[tang2023_38049909]]")
        assert "introduction" not in keys
        assert "tang2023_38049909" in keys

    def test_empty_content(self):
        keys = extract_citation_keys("")
        assert keys == []


# ──────────────────────────────────────────────────────────────────────────────
# Roundtrip
# ──────────────────────────────────────────────────────────────────────────────


class TestRoundtrip:
    """Test bidirectional conversion consistency."""

    def test_wikilink_roundtrip(self):
        """wikilink → pandoc → wikilink should preserve keys."""
        original = "Text [[tang2023_38049909]] and [[lee2024_12345678]] end."
        to_pandoc = wikilinks_to_pandoc(original)
        back = pandoc_to_wikilinks(to_pandoc.content)
        assert "[[tang2023_38049909]]" in back.content
        assert "[[lee2024_12345678]]" in back.content

    def test_pandoc_roundtrip(self):
        """pandoc → wikilink → pandoc should preserve keys."""
        original = "Text [@tang2023_38049909] end."
        to_wiki = pandoc_to_wikilinks(original)
        back = wikilinks_to_pandoc(to_wiki.content)
        assert "[@tang2023_38049909]" in back.content
