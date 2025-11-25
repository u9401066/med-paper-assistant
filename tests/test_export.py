import sys
import os
import shutil
from docx import Document

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from med_paper_assistant.core.exporter import WordExporter

def test_export():
    # Setup
    test_dir = "test_export"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Create Dummy Template
    template_path = os.path.join(test_dir, "template.docx")
    doc = Document()
    doc.add_heading('Template Header', 0)
    doc.save(template_path)
    print(f"Created template at {template_path}")
    
    # 2. Create Dummy Image
    # We need a real image file for python-docx to work. 
    # Let's create a simple plot using matplotlib
    import matplotlib.pyplot as plt
    img_path = os.path.join(test_dir, "test_plot.png")
    plt.plot([1, 2, 3], [1, 4, 9])
    plt.savefig(img_path)
    print(f"Created image at {img_path}")
    
    # 3. Create Dummy Draft
    draft_path = os.path.join(test_dir, "draft.md")
    with open(draft_path, "w") as f:
        f.write("# Test Paper\n\n")
        f.write("This is a paragraph.\n\n")
        f.write(f"![Test Figure]({img_path})\n\n")
        f.write("## Conclusion\nEnd of paper.")
    print(f"Created draft at {draft_path}")
    
    # 4. Run Export
    exporter = WordExporter()
    output_path = os.path.join(test_dir, "output.docx")
    
    print("Exporting...")
    try:
        exporter.export_to_word(draft_path, template_path, output_path)
        print(f"Exported to {output_path}")
        
        if os.path.exists(output_path):
            print("Test PASSED: Output file created.")
        else:
            print("Test FAILED: Output file missing.")
            
    except Exception as e:
        print(f"Test FAILED: Exception {e}")

if __name__ == "__main__":
    test_export()
