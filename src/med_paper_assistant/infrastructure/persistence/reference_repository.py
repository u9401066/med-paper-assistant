"""
Reference Repository - Persistence for Reference entities.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from med_paper_assistant.domain.entities.reference import Reference
from med_paper_assistant.shared.exceptions import ReferenceNotFoundError


class ReferenceRepository:
    """
    Repository for Reference persistence.
    
    Handles saving, loading, and managing references on disk.
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def save(self, reference: Reference) -> Reference:
        """
        Save a reference to disk.
        
        Args:
            reference: Reference entity to save.
            
        Returns:
            Saved reference.
        """
        ref_dir = self.base_dir / reference.pmid
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_path = ref_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(reference.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Save content (abstract as markdown)
        content_path = ref_dir / "content.md"
        content = f"""# {reference.title}

## Citation
**{reference.first_author} et al.** ({reference.year}). {reference.journal}.

## Abstract
{reference.abstract}

## Keywords
{', '.join(reference.keywords) if reference.keywords else 'N/A'}

## MeSH Terms
{', '.join(reference.mesh_terms) if reference.mesh_terms else 'N/A'}
"""
        content_path.write_text(content, encoding='utf-8')
        
        return reference
    
    def get(self, pmid: str) -> Reference:
        """
        Get a reference by PMID.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            Reference entity.
            
        Raises:
            ReferenceNotFoundError: If reference not found.
        """
        ref_dir = self.base_dir / pmid
        metadata_path = ref_dir / "metadata.json"
        
        if not metadata_path.exists():
            raise ReferenceNotFoundError(f"Reference {pmid} not found.")
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        reference = Reference.from_dict(data)
        reference.has_pdf = (ref_dir / "fulltext.pdf").exists()
        
        return reference
    
    def exists(self, pmid: str) -> bool:
        """Check if a reference exists."""
        return (self.base_dir / pmid / "metadata.json").exists()
    
    def list_all(self) -> List[Reference]:
        """List all saved references."""
        references = []
        if not self.base_dir.exists():
            return references
        
        for ref_dir in self.base_dir.iterdir():
            if ref_dir.is_dir():
                try:
                    references.append(self.get(ref_dir.name))
                except Exception:
                    pass
        
        return references
    
    def search(self, query: str) -> List[Reference]:
        """
        Search references by keyword.
        
        Args:
            query: Search query.
            
        Returns:
            List of matching references.
        """
        query_lower = query.lower()
        results = []
        
        for ref in self.list_all():
            if (query_lower in ref.title.lower() or 
                query_lower in ref.abstract.lower() or
                any(query_lower in kw.lower() for kw in ref.keywords)):
                results.append(ref)
        
        return results
    
    def delete(self, pmid: str):
        """Delete a reference."""
        import shutil
        ref_dir = self.base_dir / pmid
        if ref_dir.exists():
            shutil.rmtree(ref_dir)
    
    def get_pdf_path(self, pmid: str) -> Optional[Path]:
        """Get the PDF path for a reference."""
        pdf_path = self.base_dir / pmid / "fulltext.pdf"
        return pdf_path if pdf_path.exists() else None
    
    def save_pdf(self, pmid: str, pdf_content: bytes) -> Path:
        """Save PDF content for a reference."""
        ref_dir = self.base_dir / pmid
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = ref_dir / "fulltext.pdf"
        pdf_path.write_bytes(pdf_content)
        
        # Update metadata
        try:
            reference = self.get(pmid)
            reference.has_pdf = True
            self.save(reference)
        except ReferenceNotFoundError:
            pass
        
        return pdf_path
    
    def get_fulltext(self, pmid: str, max_chars: int = 10000) -> Optional[str]:
        """
        Extract text from PDF.
        
        Args:
            pmid: PubMed ID.
            max_chars: Maximum characters to return.
            
        Returns:
            Extracted text or None if no PDF.
        """
        pdf_path = self.get_pdf_path(pmid)
        if not pdf_path:
            return None
        
        try:
            import PyPDF2
            text = []
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text())
            
            full_text = '\n'.join(text)
            return full_text[:max_chars] if len(full_text) > max_chars else full_text
        except Exception:
            return None
