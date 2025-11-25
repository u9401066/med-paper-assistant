import os
import re
from docx import Document
from docx.shared import Inches

class WordExporter:
    def __init__(self):
        pass

    def export_to_word(self, draft_path: str, template_path: str, output_path: str) -> str:
        """
        Export a markdown draft to a Word document using a template.
        
        Args:
            draft_path: Path to the markdown draft file.
            template_path: Path to the Word template file (.docx).
            output_path: Path to save the generated Word document.
            
        Returns:
            Path to the generated file.
        """
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"Draft file not found: {draft_path}")
        
        # If template doesn't exist, create a new blank document
        if template_path and os.path.exists(template_path):
            doc = Document(template_path)
        else:
            doc = Document()
            
        with open(draft_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Headers
            if line.startswith("#"):
                level = len(line.split()[0])
                text = line.lstrip("#").strip()
                # Word supports headings 1-9
                level = min(level, 9)
                doc.add_heading(text, level=level)
                
            # Images: ![Caption](path)
            elif line.startswith("![") and "](" in line and line.endswith(")"):
                match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
                if match:
                    caption = match.group(1)
                    img_path = match.group(2)
                    
                    # Handle relative paths
                    if not os.path.isabs(img_path):
                        # Assuming image is relative to CWD or draft location?
                        # Let's try CWD first, then relative to draft
                        if not os.path.exists(img_path):
                            draft_dir = os.path.dirname(draft_path)
                            alt_path = os.path.join(draft_dir, img_path)
                            if os.path.exists(alt_path):
                                img_path = alt_path
                    
                    if os.path.exists(img_path):
                        try:
                            doc.add_picture(img_path, width=Inches(6))
                            if caption:
                                doc.add_paragraph(caption, style="Caption")
                        except Exception as e:
                            doc.add_paragraph(f"[Error inserting image: {img_path} - {str(e)}]")
                    else:
                        doc.add_paragraph(f"[Image not found: {img_path}]")
            
            # Normal Paragraph
            else:
                doc.add_paragraph(line)
                
        doc.save(output_path)
        return output_path
