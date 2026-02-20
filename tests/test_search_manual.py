import pytest
from pubmed_search import LiteratureSearcher

pytestmark = pytest.mark.integration


def test_search():
    print("Initializing Searcher...")
    searcher = LiteratureSearcher(email="test@example.com")

    query = "COVID-19 vaccine efficacy"
    print(f"Searching for: {query}")

    results = searcher.search(query, limit=3, strategy="recent")

    if not results:
        print("No results found.")
        return

    if "error" in results[0]:
        print(f"Error: {results[0]['error']}")
        return

    print(f"Found {len(results)} results:")
    for i, paper in enumerate(results, 1):
        print(f"--- Paper {i} ---")
        print(f"Title: {paper['title']}")
        print(f"Authors: {paper['authors']}")
        print(f"Journal: {paper['journal']} ({paper['year']})")
        print(f"PMID: {paper['pmid']}")
        print(f"Abstract length: {len(paper['abstract'])}")
        print("")


if __name__ == "__main__":
    test_search()
