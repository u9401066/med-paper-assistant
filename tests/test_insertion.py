import os
import shutil

import pytest
from pubmed_search import LiteratureSearcher

from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.infrastructure.services.drafter import Drafter

pytestmark = pytest.mark.integration


def test_insertion():
    # Setup
    searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
    test_ref_dir = "test_references_insert"
    test_draft_dir = "test_drafts_insert"

    # Clean up
    if os.path.exists(test_ref_dir):
        shutil.rmtree(test_ref_dir)
    if os.path.exists(test_draft_dir):
        shutil.rmtree(test_draft_dir)

    ref_manager = ReferenceManager(base_dir=test_ref_dir)
    drafter = Drafter(ref_manager, drafts_dir=test_draft_dir)

    # 1. Create Initial Draft with one citation
    pmid1 = "41285088"  # Asthma paper
    content = f"""
# Test Draft

This is the first statement (PMID:{pmid1}).
This is the second statement.
    """

    print("Creating initial draft...")
    filepath = drafter.create_draft("test_insert", content)

    with open(filepath, "r") as f:
        print("--- Initial Content ---")
        print(f.read())

    # 2. Insert a new citation BEFORE the first one (to test renumbering)
    # Actually, let's insert AFTER first statement but BEFORE the end.
    # "This is the second statement." -> "This is the second statement [PMID:new]."

    # Let's find another PMID.
    print("\nSearching for second PMID...")
    results = searcher.search("diabetes", limit=1)
    pmid2 = results[0]["pmid"]
    print(f"Found PMID2: {pmid2}")

    print(f"\nInserting citation {pmid2} after 'second statement'...")
    drafter.insert_citation("test_insert", "second statement", pmid2)

    with open(filepath, "r") as f:
        final_content = f.read()
        print("\n--- Content After Insertion ---")
        print(final_content)

    # 3. Verify
    # We expect:
    # ... first statement [1].
    # ... second statement [2].
    # References:
    # [1] ... PMID:41285088.
    # [2] ... PMID:{pmid2}.

    if "[1]" in final_content and "[2]" in final_content:
        print("\nTest PASSED: Both citations present.")
    else:
        print("\nTest FAILED: Missing citations.")

    if f"PMID:{pmid1}" in final_content and f"PMID:{pmid2}" in final_content:
        print("Test PASSED: Bibliography contains both PMIDs.")
    else:
        print("Test FAILED: Bibliography missing PMIDs.")

    # 4. Test Insertion BEFORE (Renumbering)
    # Insert a 3rd citation at the very beginning.
    print("\nSearching for third PMID...")
    results = searcher.search("cancer", limit=1)
    pmid3 = results[0]["pmid"]

    print(f"\nInserting citation {pmid3} after 'Test Draft'...")
    drafter.insert_citation("test_insert", "Test Draft", pmid3)

    with open(filepath, "r") as f:
        final_content_2 = f.read()
        print("\n--- Content After Second Insertion (Renumbering) ---")
        print(final_content_2)

    # Expect:
    # Test Draft [1]
    # ... first statement [2]
    # ... second statement [3]

    if "Test Draft [1]" in final_content_2:
        print("Test PASSED: Renumbering successful (New [1]).")
    else:
        print("Test FAILED: Renumbering failed.")


if __name__ == "__main__":
    test_insertion()
