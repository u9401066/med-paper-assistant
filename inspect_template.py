import sys
import os
from docx import Document

def inspect_template():
    template_path = "src/med_paper_assistant/templates/Type of the Paper.docx"
    try:
        doc = Document(template_path)
        print(f"--- Inspecting {template_path} ---")
        for i, p in enumerate(doc.paragraphs[:50]): # Check first 50 paragraphs
            text = p.text.strip()
            if text:
                print(f"[{i}] Style='{p.style.name}': {text[:50]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_template()
