"""Test save_reference directly."""
import json
from med_paper_assistant.infrastructure.persistence import ReferenceManager, get_project_manager

pm = get_project_manager()
ref_manager = ReferenceManager(project_manager=pm)

# 模擬 MCP 傳入的資料
article = {
    "pmid": "27345583",
    "title": "Review of videolaryngoscopy pharyngeal wall injuries.",
    "year": "2017",
    "authors": ["Greer Devon", "Marshall Kathryn E"],
    "authors_full": [
        {"last_name": "Greer", "fore_name": "Devon", "initials": "D"},
        {"last_name": "Marshall", "fore_name": "Kathryn E", "initials": "KE"}
    ],
    "journal": "The Laryngoscope",
    "journal_abbrev": "Laryngoscope",
    "doi": "10.1002/lary.26134",
    "volume": "127",
    "issue": "2",
    "pages": "349-353",
    "abstract": "Reports of patient injuries associated with videolaryngoscopy are increasing."
}

print(f"Article type: {type(article)}")
print(f"PMID: {article.get('pmid')}")
print(f"Base dir: {ref_manager.base_dir}")

try:
    result = ref_manager.save_reference(article)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
