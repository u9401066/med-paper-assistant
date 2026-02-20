import os

import pytest

from med_paper_assistant.infrastructure.services.formatter import Formatter


def test_formatter_real_template(tmp_path):
    """
    Integration test using the actual 'Type of the Paper.docx' template.
    This test verifies that the template exists and can be applied to a draft.
    """
    # Setup paths — use project root for template, tmp_path for outputs
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    draft_path = str(tmp_path / "draft.md")
    template_name = "Type of the Paper.docx"
    output_path = str(tmp_path / "test_integration_output.docx")

    # Create a test draft
    with open(draft_path, "w") as f:
        f.write("# Introduction\nThis is a test introduction.\n")

    # Check if template exists
    template_path = os.path.join(project_root, "templates", template_name)
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
