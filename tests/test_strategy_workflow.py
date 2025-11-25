import os
import sys
import json
import pytest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.strategy_manager import StrategyManager, SearchCriteria
from med_paper_assistant.core.search import LiteratureSearcher

def test_strategy_manager(tmp_path):
    strategy_file = tmp_path / "test_strategy.json"
    manager = StrategyManager(str(strategy_file))
    
    criteria = {
        "keywords": ["anesthesia", "pain"],
        "exclusions": ["children"],
        "article_types": ["Clinical Trial"],
        "min_sample_size": 100,
        "date_range": "2020:2025"
    }
    
    # Test Save
    msg = manager.save_strategy(criteria)
    assert "saved" in msg
    assert strategy_file.exists()
    
    # Test Load
    loaded = manager.load_strategy()
    assert loaded.keywords == ["anesthesia", "pain"]
    assert loaded.min_sample_size == 100
    
    # Test Query Build
    query = manager.build_pubmed_query(loaded)
    assert "(anesthesia) AND (pain)" in query
    assert "NOT (children)" in query
    assert '"Clinical Trial"[pt]' in query
    assert "2020:2025[dp]" in query

def test_abstract_filtering():
    searcher = LiteratureSearcher()
    
    papers = [
        {"title": "Paper 1", "abstract": "This study included n=150 patients."},
        {"title": "Paper 2", "abstract": "We recruited 50 participants."},
        {"title": "Paper 3", "abstract": "A total of 200 subjects were analyzed."},
        {"title": "Paper 4", "abstract": "No sample size mentioned."}
    ]
    
    # Filter > 100
    filtered = searcher.filter_results(papers, min_sample_size=100)
    assert len(filtered) == 2
    titles = [p['title'] for p in filtered]
    assert "Paper 1" in titles
    assert "Paper 3" in titles
    assert "Paper 2" not in titles
