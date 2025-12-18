"""Validate novelty claim with actual PubMed searches."""
import requests

API_URL = "http://127.0.0.1:8765/search"

queries = [
    '"lip injury" AND laryngoscopy AND supraglottic',
    '"oral soft tissue" AND airway device comparison',
    'lip trauma AND (direct laryngoscopy OR video laryngoscopy) AND supraglottic',
]

print("=== PubMed Search Validation (2024-12-18) ===\n")

for q in queries:
    try:
        r = requests.get(API_URL, params={"query": q, "limit": 5}, timeout=30)
        data = r.json()
        count = data.get("total_count", 0)
        print(f"Query: {q}")
        print(f"Results: {count}")
        if count > 0 and "articles" in data:
            for a in data["articles"][:3]:
                title = a.get("title", "No title")[:70]
                print(f"  - {title}...")
        print()
    except Exception as e:
        print(f"Error: {e}\n")
