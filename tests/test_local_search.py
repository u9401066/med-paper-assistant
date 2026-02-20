import json
from unittest.mock import MagicMock

import pytest
from pubmed_search.entrez import LiteratureSearcher

from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager


@pytest.fixture
def mock_searcher():
    return MagicMock(spec=LiteratureSearcher)


def test_local_search(mock_searcher, tmp_path):
    # Setup: Create dummy references
    ref_dir = tmp_path / "references"
    ref_dir.mkdir()

    # Ref 1: Matches "cancer"
    pmid1 = "11111"
    dir1 = ref_dir / pmid1
    dir1.mkdir()
    with open(dir1 / "metadata.json", "w") as f:
        json.dump(
            {
                "pmid": pmid1,
                "title": "Cancer Research",
                "abstract": "Study on lung cancer.",
                "authors": ["A"],
                "journal": "J",
                "year": "2020",
            },
            f,
        )

    # Ref 2: Matches "diabetes"
    pmid2 = "22222"
    dir2 = ref_dir / pmid2
    dir2.mkdir()
    with open(dir2 / "metadata.json", "w") as f:
        json.dump(
            {
                "pmid": pmid2,
                "title": "Diabetes Study",
                "abstract": "Insulin resistance.",
                "authors": ["B"],
                "journal": "J",
                "year": "2021",
            },
            f,
        )

    rm = ReferenceManager(base_dir=str(ref_dir))

    # Test 1: Search "cancer" -> Should find Ref 1
    results = rm.search_local("cancer")
    assert len(results) == 1
    assert results[0]["pmid"] == pmid1

    # Test 2: Search "insulin" -> Should find Ref 2
    results = rm.search_local("insulin")
    assert len(results) == 1
    assert results[0]["pmid"] == pmid2

    # Test 3: Search "study" -> Should find both
    results = rm.search_local("study")
    assert len(results) == 2

    # Test 4: Search "heart" -> Should find none
    results = rm.search_local("heart")
    assert len(results) == 0
