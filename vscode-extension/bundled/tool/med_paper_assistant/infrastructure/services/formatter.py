import os

from med_paper_assistant.infrastructure.services.exporter import WordExporter


class Formatter:
    def __init__(self):
        self.exporter = WordExporter()
        # Define templates directory relative to the project root (assuming core is in src/med_paper_assistant/core)
        # Go up 3 levels: core -> med_paper_assistant -> src -> root
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "templates",
        )

    def apply_template(self, draft_path: str, template_name: str, output_path: str) -> str:
        """
        Apply a specific journal template to the draft and export to Word.

        Args:
            draft_path: Path to the markdown draft file.
            template_name: Name of the template file (e.g., "sensors-template.docx").
                           If not found in templates dir, treats as full path.
            output_path: Path to save the generated Word document.

        Returns:
            Path to the generated file.
        """
        # 1. Resolve Template Path
        template_path = os.path.join(self.templates_dir, template_name)

        # If not in templates dir, check if it's a full path or relative to CWD
        if not os.path.exists(template_path):
            if os.path.exists(template_name):
                template_path = template_name
            else:
                # Try adding .docx extension if missing
                if not template_name.endswith(".docx"):
                    template_path_ext = os.path.join(self.templates_dir, template_name + ".docx")
                    if os.path.exists(template_path_ext):
                        template_path = template_path_ext
                    else:
                        raise FileNotFoundError(f"Template not found: {template_name}")
                else:
                    raise FileNotFoundError(f"Template not found: {template_name}")

        # 2. Export using WordExporter
        return self.exporter.export_to_word(draft_path, template_path, output_path)
