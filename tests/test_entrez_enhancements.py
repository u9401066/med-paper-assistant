"""
Test suite for Bio.Entrez enhancements in LiteratureSearcher.
Tests new features: ESummary, ESpell, EGQuery, ECitMatch, ELink variants, EInfo, History Server.
"""

import time

import pytest
from pubmed_search import LiteratureSearcher

pytestmark = pytest.mark.integration


@pytest.fixture
def searcher():
    """Create a LiteratureSearcher instance for testing."""
    return LiteratureSearcher(email="test@example.com")


class TestExistingFeatures:
    """Test that existing features still work."""

    async def test_basic_search(self, searcher):
        """Test basic search functionality."""
        results = await searcher.search("diabetes mellitus type 2", limit=3)
        assert len(results) > 0
        assert "pmid" in results[0]
        assert "title" in results[0]
        print(f"\n✓ Basic search returned {len(results)} results")
        time.sleep(1)

    async def test_fetch_details(self, searcher):
        """Test fetching article details."""
        # PMID for a well-known paper
        results = await searcher.fetch_details(["33892063"])  # COVID-19 vaccine paper
        assert len(results) == 1
        assert results[0]["pmid"] == "33892063"
        print(f"\n✓ Fetch details: {results[0]['title'][:60]}...")
        time.sleep(1)


class TestRelatedArticles:
    """Test ELink features for finding related articles."""

    async def test_get_related_articles(self, searcher):
        """Test finding related articles."""
        pmid = "33892063"
        related = await searcher.get_related_articles(pmid, limit=3)
        assert isinstance(related, list)
        if related and "error" not in related[0]:
            assert len(related) <= 3
            print(f"\n✓ Found {len(related)} related articles")
        time.sleep(1)

    async def test_get_citing_articles(self, searcher):
        """Test finding citing articles."""
        pmid = "33892063"
        citing = await searcher.get_citing_articles(pmid, limit=3)
        assert isinstance(citing, list)
        if citing and "error" not in citing[0]:
            print(f"\n✓ Found {len(citing)} citing articles")
        time.sleep(1)

    async def test_get_article_references(self, searcher):
        """Test getting article references."""
        pmid = "33892063"
        refs = await searcher.get_article_references(pmid, limit=5)
        assert isinstance(refs, list)
        if refs and "error" not in refs[0]:
            print(f"\n✓ Found {len(refs)} references")
        time.sleep(1)


class TestQuickSummary:
    """Test ESummary for faster metadata retrieval."""

    async def test_quick_fetch_summary(self, searcher):
        """Test ESummary for quick metadata."""
        pmids = ["33892063", "34043894"]
        summaries = await searcher.quick_fetch_summary(pmids)
        assert len(summaries) == 2
        assert "pmid" in summaries[0]
        assert "title" in summaries[0]
        print(f"\n✓ Quick summary retrieved {len(summaries)} articles")
        print(f"  Title: {summaries[0]['title'][:60]}...")
        time.sleep(1)


class TestSpellCheck:
    """Test ESpell for query spell checking."""

    async def test_spell_check_query_correct(self, searcher):
        """Test spell check with correct spelling."""
        query = "diabetes mellitus"
        corrected = await searcher.spell_check_query(query)
        assert isinstance(corrected, str)
        print(f"\n✓ Spell check: '{query}' -> '{corrected}'")
        time.sleep(1)

    async def test_spell_check_query_typo(self, searcher):
        """Test spell check with typo."""
        query = "diabetis melitus"
        corrected = await searcher.spell_check_query(query)
        assert isinstance(corrected, str)
        print(f"\n✓ Spell check: '{query}' -> '{corrected}'")
        time.sleep(1)


class TestDatabaseCounts:
    """Test EGQuery for multi-database counts."""

    async def test_get_database_counts(self, searcher):
        """Test getting counts across databases."""
        query = "diabetes type 2"
        counts = await searcher.get_database_counts(query)
        assert isinstance(counts, dict)
        if "error" not in counts:
            assert "pubmed" in counts
            print(f"\n✓ Database counts for '{query}':")
            for db, count in list(counts.items())[:5]:
                print(f"  {db}: {count}")
        time.sleep(1)


class TestMeSHValidation:
    """Test MeSH term validation."""

    async def test_validate_mesh_terms(self, searcher):
        """Test MeSH term validation."""
        terms = ["Diabetes Mellitus", "Insulin"]
        result = await searcher.validate_mesh_terms(terms)
        assert isinstance(result, dict)
        if "error" not in result:
            print(f"\n✓ MeSH validation: {result['valid_count']} valid terms")
            for term in result.get("terms", [])[:3]:
                print(f"  {term['term']} (ID: {term['mesh_id']})")
        time.sleep(1)


class TestCitationMatch:
    """Test ECitMatch for finding articles by citation."""

    async def test_find_by_citation(self, searcher):
        """Test finding article by citation."""
        # Example: Find a known paper
        pmid = await searcher.find_by_citation(
            journal="Science", year="2020", volume="370", first_page="1110"
        )
        assert pmid is None or pmid.isdigit()
        if pmid:
            print(f"\n✓ Found article by citation: PMID {pmid}")
        else:
            print("\n✓ Citation match tested (no match found)")
        time.sleep(1)


class TestHistoryServer:
    """Test History Server for large result sets."""

    async def test_search_with_history(self, searcher):
        """Test initiating search with history server."""
        query = "cancer treatment"
        history = await searcher.search_with_history(query, batch_size=100)
        assert isinstance(history, dict)
        if "error" not in history:
            assert "webenv" in history
            assert "query_key" in history
            assert "count" in history
            print(f"\n✓ History search: {history['count']} total results")
            print(f"  WebEnv: {history['webenv'][:20]}...")
        time.sleep(1)

    async def test_fetch_batch_from_history(self, searcher):
        """Test fetching batch using history server."""
        query = "diabetes"
        history = await searcher.search_with_history(query, batch_size=5)

        if "error" not in history and history.get("count", 0) > 0:
            batch = await searcher.fetch_batch_from_history(
                webenv=history["webenv"], query_key=history["query_key"], start=0, batch_size=3
            )
            assert isinstance(batch, list)
            if batch and "error" not in batch[0]:
                assert len(batch) <= 3
                print(f"\n✓ Fetched batch of {len(batch)} from history server")
        time.sleep(1)


class TestExportCitations:
    """Test citation export in various formats."""

    async def test_export_medline(self, searcher):
        """Test exporting in MEDLINE format."""
        pmids = ["33892063"]
        result = await searcher.export_citations(pmids, format="medline")
        assert isinstance(result, str)
        assert len(result) > 0
        print(f"\n✓ MEDLINE export: {len(result)} characters")
        print(f"  Preview: {result[:100]}...")
        time.sleep(1)

    async def test_export_abstract(self, searcher):
        """Test exporting abstract format."""
        pmids = ["33892063"]
        result = await searcher.export_citations(pmids, format="abstract")
        assert isinstance(result, str)
        print(f"\n✓ Abstract export: {len(result)} characters")
        time.sleep(1)


class TestDatabaseInfo:
    """Test EInfo for database information."""

    async def test_get_database_info(self, searcher):
        """Test getting PubMed database info."""
        info = await searcher.get_database_info("pubmed")
        assert isinstance(info, dict)
        if "error" not in info:
            assert "name" in info
            print(f"\n✓ Database info for {info['name']}:")
            print(f"  Description: {info.get('description', '')[:60]}...")
            print(f"  Record count: {info.get('count', 'N/A')}")
            print(f"  Available fields: {len(info.get('fields', []))}")
        time.sleep(1)


class TestPMCFeatures:
    """Test PMC-related features."""

    async def test_get_pmc_fulltext_url(self, searcher):
        """Test getting PMC full text URL."""
        # Use a PMID known to have PMC full text
        pmid = "33892063"
        url = await searcher.get_pmc_fulltext_url(pmid)
        if url:
            assert "pmc" in url.lower()
            print(f"\n✓ PMC URL found: {url}")
        else:
            print("\n✓ PMC URL tested (not available for this article)")
        time.sleep(1)


async def test_integration_workflow(searcher):
    """Test a complete workflow using multiple features."""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST: Complete workflow")
    print("=" * 60)

    # Step 1: Spell check query
    original_query = "diabetis treatmnt"
    corrected_query = await searcher.spell_check_query(original_query)
    print(f"\n1. Spell check: '{original_query}' -> '{corrected_query}'")
    time.sleep(1)

    # Step 2: Get database counts
    counts = await searcher.get_database_counts("diabetes treatment")
    if "error" not in counts:
        print(f"\n2. Database counts: PubMed has {counts.get('pubmed', 0)} results")
    time.sleep(1)

    # Step 3: Search for articles
    results = await searcher.search("diabetes treatment guidelines", limit=2)
    if results and "error" not in results[0]:
        print(f"\n3. Search found {len(results)} articles")
        pmid = results[0]["pmid"]
        print(f"   First article PMID: {pmid}")
        time.sleep(1)

        # Step 4: Get related articles
        related = await searcher.get_related_articles(pmid, limit=2)
        if related and "error" not in related[0]:
            print(f"\n4. Found {len(related)} related articles")
        time.sleep(1)

        # Step 5: Export citation
        citation = await searcher.export_citations([pmid], format="medline")
        print(f"\n5. Exported citation ({len(citation)} chars)")
        time.sleep(1)

    print("\n" + "=" * 60)
    print("✓ Integration test complete!")
    print("=" * 60)
