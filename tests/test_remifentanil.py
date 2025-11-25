import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.search import LiteratureSearcher

def test_remifentanil_search():
    searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
    
    # Translating "remifentanyl的術後止痛使用" to English for better results
    query = "remifentanil postoperative analgesia"
    print(f"Searching PubMed for: '{query}'")
    
    results = searcher.search(query, limit=3)
    
    if not results:
        print("No results found.")
        return

    if "error" in results[0]:
        print(f"Error: {results[0]['error']}")
        return

    print(f"\nFound {len(results)} results:\n")
    for i, paper in enumerate(results, 1):
        print(f"--- Article {i} ---")
        print(f"Title: {paper['title']}")
        print(f"Journal: {paper['journal']} ({paper['year']})")
        print(f"Authors: {', '.join(paper['authors'][:3])}...")
        print(f"Abstract Snippet: {paper['abstract'][:300]}...")
        print("-" * 20 + "\n")

if __name__ == "__main__":
    test_remifentanil_search()
