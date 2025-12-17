"""Temporary script to search PubMed."""
from pubmed_search.core.searcher import PubMedSearcher

searcher = PubMedSearcher()
results = searcher.search('dental injury anesthesia intubation', max_results=15)

print(f"\n🔍 Found {len(results)} articles:\n")
for i, r in enumerate(results, 1):
    pmid = r.get('pmid', 'N/A')
    title = r.get('title', 'No title')[:80]
    year = r.get('year', 'N/A')
    print(f"{i:2}. PMID: {pmid} ({year})")
    print(f"    {title}...")
    print()
