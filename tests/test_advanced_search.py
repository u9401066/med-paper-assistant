import pytest
from pubmed_search import LiteratureSearcher

pytestmark = pytest.mark.integration


def test_advanced_search():
    searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")

    print("--- Test 1: Recent Reviews on Asthma (2024-2025) ---")
    results = searcher.search(
        "asthma", limit=3, min_year=2023, article_type="Review", strategy="recent"
    )

    if not results:
        print("No results found.")
    elif "error" in results[0]:
        print(f"Error: {results[0]['error']}")
    else:
        for p in results:
            print(f"[{p['year']}] {p['title']} ({p['journal']})")
            # Verify year
            if int(p["year"]) < 2024:
                print("FAIL: Year < 2024")
            else:
                print("PASS: Year check")

    print("\n--- Test 2: Clinical Trials on Diabetes (Sort by Date) ---")
    results = searcher.search("diabetes", limit=3, article_type="Clinical Trial", strategy="recent")

    if not results:
        print("No results found.")
    else:
        for p in results:
            print(f"[{p['year']}] {p['title']}")


if __name__ == "__main__":
    test_advanced_search()
