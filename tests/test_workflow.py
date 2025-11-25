import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.drafter import Drafter
from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.search import LiteratureSearcher

def simulate_workflow():
    print("Simulating /mdpaper.draft workflow...")
    
    # 1. Read concept.md
    with open("concept.md", "r") as f:
        concept = f.read()
    print("Read concept.md")
    
    # 2. Read template
    with open("src/med_paper_assistant/templates/general_medical_journal.md", "r") as f:
        template = f.read()
    print("Read template")
    
    # 3. Generate Content (Mocking LLM generation)
    # In a real scenario, the Agent would do this using the LLM.
    # Here we just manually construct the string based on concept.md
    
    generated_content = """# Efficacy of Honey in Treating Cough in Children

**Authors**: Agent Smith

**Abstract**:
Background: Cough is common in children. Methods: RCT with 100 children. Results: Honey reduced cough. Conclusion: Honey is effective.

## Introduction
Cough is a major symptom in URTI. We hypothesized that honey is effective (PMID:41285088).

## Methods
We conducted a randomized controlled trial involving 100 children aged 2-5 years.

## Results
Honey significantly reduced cough frequency compared to placebo.

## Discussion
Our findings support the use of honey.
"""

    # 4. Write Draft
    searcher = LiteratureSearcher(email="u9401066@gap.kmu.edu.tw")
    ref_manager = ReferenceManager(searcher)
    drafter = Drafter(ref_manager)
    
    print("Writing draft...")
    path = drafter.create_draft("workflow_test_draft", generated_content)
    print(f"Draft created at: {path}")
    
    # Verify
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        if "[1]" in content and "## References" in content:
            print("Workflow Simulation PASSED.")
        else:
            print("Workflow Simulation FAILED: Missing citations.")
    else:
        print("Workflow Simulation FAILED: File not created.")

if __name__ == "__main__":
    simulate_workflow()
