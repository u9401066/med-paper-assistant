"""
Test PDF Download Functionality

Tests that PDF download from PMC Open Access works correctly.
Uses known Open Access articles to verify functionality.
"""

import logging
import os
import tempfile

import pytest
from pubmed_search import LiteratureSearcher

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

pytestmark = pytest.mark.integration

# Known Open Access PMIDs (these should always be available)
# These are well-known open access articles from PMC
OPEN_ACCESS_PMIDS = [
    # PMID 32678530 - "A deep learning approach to antibiotic discovery" (Cell 2020)
    # This is a highly cited Open Access article
    "32678530",
    # PMID 35418249 - Recent open access article
    "35418249",
    # PMID 34128826 - COVID-19 related, usually available
    "34128826",
]


def test_pmc_id_lookup():
    """Test that we can find PMC IDs for known Open Access articles."""
    print("\n" + "=" * 60)
    print("TEST: PMC ID Lookup")
    print("=" * 60)

    searcher = LiteratureSearcher(email="test@example.com")

    for pmid in OPEN_ACCESS_PMIDS:
        pmc_id = searcher._get_pmc_id(pmid)
        if pmc_id:
            print(f"✅ PMID {pmid} -> PMC{pmc_id}")
        else:
            print(f"❌ PMID {pmid} -> No PMC ID found")

    print()


def test_pdf_download():
    """Test that we can download PDFs from PMC."""
    print("\n" + "=" * 60)
    print("TEST: PDF Download")
    print("=" * 60)

    searcher = LiteratureSearcher(email="test@example.com")

    with tempfile.TemporaryDirectory() as tmpdir:
        for pmid in OPEN_ACCESS_PMIDS:
            pdf_path = os.path.join(tmpdir, f"{pmid}.pdf")

            success = searcher.download_pmc_pdf(pmid, pdf_path)

            if success and os.path.exists(pdf_path):
                size = os.path.getsize(pdf_path)
                print(f"✅ PMID {pmid}: Downloaded {size:,} bytes")
            else:
                print(f"❌ PMID {pmid}: Download failed")

    print()


def test_non_oa_article():
    """Test behavior for non-Open Access articles."""
    print("\n" + "=" * 60)
    print("TEST: Non-Open Access Article (should fail gracefully)")
    print("=" * 60)

    # These are subscription-only PMIDs
    non_oa_pmids = [
        "26775126",  # One of the user's saved refs
        "25837741",  # Another of the user's saved refs
    ]

    searcher = LiteratureSearcher(email="test@example.com")

    with tempfile.TemporaryDirectory() as tmpdir:
        for pmid in non_oa_pmids:
            pdf_path = os.path.join(tmpdir, f"{pmid}.pdf")

            pmc_id = searcher._get_pmc_id(pmid)
            success = searcher.download_pmc_pdf(pmid, pdf_path)

            if pmc_id:
                status = "has PMC ID but download " + ("✅" if success else "❌")
            else:
                status = "no PMC ID (not in PMC)"

            print(f"PMID {pmid}: {status}")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" PDF DOWNLOAD FUNCTIONALITY TEST")
    print("=" * 60)

    try:
        test_pmc_id_lookup()
        test_pdf_download()
        test_non_oa_article()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
