import sys
import os
import shutil

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.search import LiteratureSearcher
from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.drafter import Drafter

def test_drafter():
    # Setup
    searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
    test_ref_dir = "test_references_draft"
    test_draft_dir = "test_drafts"
    
    # Clean up
    if os.path.exists(test_ref_dir):
        shutil.rmtree(test_ref_dir)
    if os.path.exists(test_draft_dir):
        shutil.rmtree(test_draft_dir)
        
    ref_manager = ReferenceManager(searcher, base_dir=test_ref_dir)
    drafter = Drafter(ref_manager, drafts_dir=test_draft_dir)
    
    # 1. Prepare a known PMID (e.g., 41285088 from previous test)
    pmid = "41285088"
    
    # 2. Create Content with Placeholder
    content = f"""
# Introduction

Asthma is a chronic condition (PMID:{pmid}). 
Recent studies have shown significant economic burden [PMID:{pmid}].
    """
    
    print("Creating draft...")
    filepath = drafter.create_draft("test_intro", content)
    print(f"Draft created at: {filepath}")
    
    # 3. Verify Output
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            final_content = f.read()
            
        print("\n--- Final Content ---")
        print(final_content)
        print("---------------------")
        
        if "[1]" in final_content and "## References" in final_content:
            print("Test PASSED: Citations and Bibliography found.")
        else:
            print("Test FAILED: Missing citations or bibliography.")
            
        # Check if reference was automatically fetched/saved
        if os.path.exists(os.path.join(test_ref_dir, pmid)):
             print(f"Reference {pmid} was automatically saved.")
        else:
             print(f"Reference {pmid} was NOT saved (Unexpected).")
             
    else:
        print("Test FAILED: File not created.")

    # Cleanup
    # shutil.rmtree(test_ref_dir)
    # shutil.rmtree(test_draft_dir)

if __name__ == "__main__":
    test_drafter()
