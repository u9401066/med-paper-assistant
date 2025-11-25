import os
import pytest
from med_paper_assistant.core.formatter import Formatter

def test_formatter_real_template():
    """
    Integration test using the actual 'Type of the Paper.docx' template.
    This test verifies that the template exists and can be applied to a draft.
    """
    # Setup paths
    base_dir = os.getcwd()
    draft_path = os.path.join(base_dir, "drafts", "introduction_draft.md")
    template_name = "Type of the Paper.docx"
    output_path = os.path.join(base_dir, "results", "test_integration_output.docx")
    
    # Ensure draft exists (create if not)
    if not os.path.exists(draft_path):
        os.makedirs(os.path.dirname(draft_path), exist_ok=True)
        with open(draft_path, "w") as f:
            f.write("# Introduction\nThis is a test introduction.\n")
            
    # Check if template exists
    template_path = os.path.join(base_dir, "src", "med_paper_assistant", "templates", template_name)
    if not os.path.exists(template_path):
        pytest.skip(f"Template not found at {template_path}")

    # Run Formatter
    formatter = Formatter()
    try:
        result_path = formatter.apply_template(draft_path, template_name, output_path)
        assert os.path.exists(result_path)
        assert result_path == output_path
    except Exception as e:
        pytest.fail(f"Formatter failed: {e}")

if __name__ == "__main__":
    test_formatter_real_template()
