"""View session search history for verification."""
import json
import os
from pathlib import Path

SESSION_DIR = Path.home() / ".pubmed-search-mcp"
SESSION_FILE = SESSION_DIR / "session_c2ff294e705e.json"

if not SESSION_FILE.exists():
    print(f"Session file not found: {SESSION_FILE}")
    exit(1)

with open(SESSION_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 70)
print("📋 SESSION AUDIT LOG (可供人工驗證的搜尋紀錄)")
print("=" * 70)
print(f"Session ID: {data['session_id']}")
print(f"Created:    {data['created_at']}")
print(f"Updated:    {data['updated_at']}")
print(f"Topic:      {data.get('topic', 'N/A')}")
print(f"Total Searches: {len(data['search_history'])}")
print(f"Cached Articles: {len(data.get('article_cache', {}))}")
print()
print("=" * 70)
print("🔍 SEARCH HISTORY (搜尋紀錄)")
print("=" * 70)

for i, search in enumerate(data['search_history']):
    print(f"\n[Search #{i}]")
    print(f"  Timestamp:    {search['timestamp']}")
    print(f"  Query:        {search['query'][:80]}{'...' if len(search['query']) > 80 else ''}")
    print(f"  Result Count: {search['result_count']}")
    pmids = search.get('pmids', [])
    if pmids:
        print(f"  PMIDs:        {', '.join(pmids[:5])}{'...' if len(pmids) > 5 else ''}")
    print(f"  Filters:      {search.get('filters', {})}")

print()
print("=" * 70)
print("✅ 此紀錄可作為 Agent 確實執行搜尋的證明")
print("   Session 檔案位置:", SESSION_FILE)
print("=" * 70)
