import os

from docx import Document

from med_paper_assistant.infrastructure.services.formatter import Formatter


def test_formatter(tmp_path):
    # Setup
    test_dir = str(tmp_path)

    # 1. Create Dummy Template in test dir (to test full path)
    template_path = os.path.join(test_dir, "custom_template.docx")
    doc = Document()
    doc.add_heading("Custom Template", 0)
    doc.save(template_path)

    # 2. Create Dummy Draft
    draft_path = os.path.join(test_dir, "draft.md")
    with open(draft_path, "w") as f:
        f.write("# Title\nContent.")

    # 3. Initialize Formatter
    formatter = Formatter()

    # 4. Test with Full Path
    output_path_1 = os.path.join(test_dir, "output_1.docx")
    print("Testing full path template...")
    formatter.apply_template(draft_path, template_path, output_path_1)
    if os.path.exists(output_path_1):
        print("PASS: Full path template.")
    else:
        print("FAIL: Full path template.")

    # 5. Test with Template Name (Mocking templates dir)
    # We need to put a template in the actual templates dir or mock it.
    # Let's mock the templates_dir attribute for this test
    formatter.templates_dir = test_dir
    output_path_2 = os.path.join(test_dir, "output_2.docx")
    print("Testing template name lookup...")
    formatter.apply_template(draft_path, "custom_template.docx", output_path_2)
    if os.path.exists(output_path_2):
        print("PASS: Template name lookup.")
    else:
        print("FAIL: Template name lookup.")


if __name__ == "__main__":
    test_formatter()
