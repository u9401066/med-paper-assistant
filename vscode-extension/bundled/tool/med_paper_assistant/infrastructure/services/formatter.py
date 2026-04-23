import os
from pathlib import Path, PureWindowsPath

from med_paper_assistant.infrastructure.services.exporter import WordExporter
from med_paper_assistant.shared.path_guard import PathGuardError, resolve_child_path


class Formatter:
    def __init__(self):
        self.exporter = WordExporter()
        # Define templates directory relative to the project root
        # Go up 5 levels: services -> infrastructure -> med_paper_assistant -> src -> root
        self.templates_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            ),
            "templates",
        )

    def apply_template(self, draft_path: str, template_name: str, output_path: str) -> str:
        """
        Apply a specific journal template to the draft and export to Word.

        Args:
            draft_path: Path to the markdown draft file.
            template_name: Name of the template file (e.g., "sensors-template.docx").
                           Explicit absolute .docx paths are also accepted by this
                           service API for backwards compatibility.
            output_path: Path to save the generated Word document.

        Returns:
            Path to the generated file.
        """
        # 1. Resolve Template Path
        raw_template_name = str(template_name or "").strip()
        if not raw_template_name:
            raise PathGuardError("template name is required.")

        raw_path = Path(raw_template_name)
        if raw_path.is_absolute():
            template_path_obj = raw_path.resolve()
            if template_path_obj.suffix.lower() != ".docx":
                raise PathGuardError("template name must use one of: .docx.")
        else:
            windows_path = PureWindowsPath(raw_template_name)
            if windows_path.is_absolute() or windows_path.drive:
                raise PathGuardError("template name must be relative, not absolute.")
            template_path_obj = resolve_child_path(
                self.templates_dir,
                raw_template_name,
                field_name="template name",
                default_suffix=".docx",
                allowed_suffixes={".docx"},
            )

        if not template_path_obj.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        # 2. Export using WordExporter
        return self.exporter.export_to_word(draft_path, str(template_path_obj), output_path)
