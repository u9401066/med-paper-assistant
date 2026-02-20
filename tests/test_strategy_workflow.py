import pytest
from pubmed_search.entrez import LiteratureSearcher


@pytest.mark.skip(reason="StrategyManager removed during DDD refactor - needs reimplementation")
def test_strategy_manager(tmp_path):
    """StrategyManager was removed during DDD refactor. Test kept as spec reference."""
    pass


def test_abstract_filtering():
    searcher = LiteratureSearcher()

    papers = [
        {"title": "Paper 1", "abstract": "This study included n=150 patients."},
        {"title": "Paper 2", "abstract": "We recruited 50 participants."},
        {"title": "Paper 3", "abstract": "A total of 200 subjects were analyzed."},
        {"title": "Paper 4", "abstract": "No sample size mentioned."},
    ]

    # Filter > 100
    filtered = searcher.filter_results(papers, min_sample_size=100)
    assert len(filtered) == 2
    titles = [p["title"] for p in filtered]
    assert "Paper 1" in titles
    assert "Paper 3" in titles
    assert "Paper 2" not in titles
