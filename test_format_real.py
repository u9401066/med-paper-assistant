import sys
import os
sys.path.append(os.path.join(os.getcwd(), "src"))
from med_paper_assistant.core.formatter import Formatter

def run_test():
    formatter = Formatter()
    draft_path = "/home/eric/workspace251125/drafts/introduction_draft.md"
    template_name = "Type of the Paper.docx"
    output_path = "/home/eric/workspace251125/results/introduction_draft.docx"
    
    # Ensure results dir exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Exporting {draft_path}...")
    try:
        result = formatter.apply_template(draft_path, template_name, output_path)
        print(f"Success! Saved to: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()
