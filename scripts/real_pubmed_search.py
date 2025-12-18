"""Real PubMed search using NCBI E-utilities API directly."""
import urllib.request
import urllib.parse
import json
from datetime import datetime

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

queries = [
    '"lip injury" AND laryngoscopy AND supraglottic',
    '"oral soft tissue" AND airway device comparison',
    "lip trauma AND (direct laryngoscopy OR video laryngoscopy) AND supraglottic",
]

print("=== REAL PubMed Search (NCBI E-utilities API) ===")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

for q in queries:
    try:
        url = f"{BASE}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(q)}&retmode=json"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
            count = data["esearchresult"]["count"]
            ids = data["esearchresult"].get("idlist", [])[:5]
            print(f"Query: {q}")
            print(f"Results: {count}")
            if ids:
                print(f"PMIDs: {', '.join(ids)}")
            print()
    except Exception as e:
        print(f"Error for query '{q}': {e}")
        print()
