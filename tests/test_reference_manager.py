import os

import pytest
from pubmed_search import LiteratureSearcher

from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager

pytestmark = pytest.mark.integration


async def test_reference_manager(tmp_path):
    # Setup
    searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
    test_dir = str(tmp_path / "test_references")

    manager = ReferenceManager(base_dir=test_dir)

    # 1. Search to get a PMID
    print("Searching for a PMID...")
    results = await searcher.search("asthma", limit=1)
    if not results:
        print("Search failed.")
        return

    pmid = results[0]["pmid"]
    print(f"Found PMID: {pmid}")

    # 2. Save Reference
    print(f"Saving reference {pmid}...")
    result = manager.save_reference(pmid)
    print(result)

    # 3. Verify Files
    ref_path = os.path.join(test_dir, pmid)
    if os.path.exists(ref_path):
        print(f"Directory {ref_path} created.")

        if os.path.exists(os.path.join(ref_path, "metadata.json")):
            print("metadata.json exists.")
        else:
            print("metadata.json MISSING.")

        if os.path.exists(os.path.join(ref_path, "content.md")):
            print("content.md exists.")
        else:
            print("content.md MISSING.")
    else:
        print(f"Directory {ref_path} MISSING.")

    # 4. List References
    refs = manager.list_references()
    print(f"Saved references: {refs}")

    if pmid in refs:
        print("Test PASSED.")
