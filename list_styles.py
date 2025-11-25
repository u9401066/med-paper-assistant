import sys
import os
from docx import Document

def list_styles():
    template_path = "src/med_paper_assistant/templates/Type of the Paper.docx"
    try:
        doc = Document(template_path)
        styles = [s.name for s in doc.styles]
        print("Available styles:")
        for s in styles:
            print(f"- {s}")
    except Exception as e:
        print(f"Error reading template: {e}")

if __name__ == "__main__":
    list_styles()
