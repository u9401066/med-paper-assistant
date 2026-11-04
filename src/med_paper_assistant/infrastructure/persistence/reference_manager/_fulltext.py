"""Fulltext and PDF access for saved references."""

import os
from typing import Optional

from med_paper_assistant.shared.path_guard import (
    PathGuardError,
)


class FulltextMixin:
    """Fulltext and PDF access for saved references."""

    def has_fulltext(self, pmid: str) -> bool:
        """
        Check if a reference has a downloaded PDF fulltext.

        Args:
            pmid: PubMed ID.

        Returns:
            True if fulltext PDF exists.
        """
        metadata = self.get_metadata(pmid)
        if metadata.get("fulltext_ingested"):
            return True

        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError):
            return False
        pdf_path = os.path.join(ref_dir, "fulltext.pdf")
        return os.path.exists(pdf_path)

    def get_fulltext_path(self, pmid: str) -> Optional[str]:
        """
        Get the path to the fulltext PDF if it exists.

        Args:
            pmid: PubMed ID.

        Returns:
            Path to PDF file, or None if not available.
        """
        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError):
            return None
        pdf_path = os.path.join(ref_dir, "fulltext.pdf")
        if os.path.exists(pdf_path):
            return pdf_path
        return None

    def read_fulltext(self, pmid: str) -> Optional[str]:
        """
        Read and extract text from fulltext PDF.

        Args:
            pmid: PubMed ID.

        Returns:
            Extracted text from PDF, or None if not available.
        """
        pdf_path = self.get_fulltext_path(pmid)
        if not pdf_path:
            return None

        try:
            import pypdf

            reader = pypdf.PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text())

            return "\n\n".join(text_parts)
        except ImportError:
            return "Error: pypdf library not installed. Install with: uv add pypdf"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

    def save_pdf(self, pmid: str, pdf_content: bytes) -> str:
        """
        Save PDF content for a reference.

        Args:
            pmid: PubMed ID.
            pdf_content: PDF file content as bytes.

        Returns:
            Status message.
        """
        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError) as exc:
            return f"Invalid reference id: {exc}"
        if not os.path.exists(ref_dir):
            return f"Reference {pmid} not found. Save metadata first."

        pdf_path = os.path.join(ref_dir, "fulltext.pdf")
        if os.path.exists(pdf_path):
            return f"PDF already exists for {pmid}."

        try:
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
            self._update_reference_metadata(pmid, {"has_pdf": True}, log_event="save_pdf")
            return f"Successfully saved PDF for {pmid}."
        except Exception as e:
            return f"Error saving PDF for {pmid}: {str(e)}"
