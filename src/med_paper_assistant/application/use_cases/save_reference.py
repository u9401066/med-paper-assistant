"""
Save Reference Use Case.

Handles saving a reference to the local library.
"""

from dataclasses import dataclass

from med_paper_assistant.infrastructure.external.pubmed import PubMedClient
from med_paper_assistant.infrastructure.external.pubmed.parser import PubMedParser
from med_paper_assistant.infrastructure.persistence import ReferenceRepository
from med_paper_assistant.shared.exceptions import ReferenceNotFoundError


@dataclass
class SaveReferenceInput:
    """Input data for saving a reference."""

    pmid: str
    download_pdf: bool = True


@dataclass
class SaveReferenceOutput:
    """Output data after saving a reference."""

    pmid: str
    title: str
    has_pdf: bool
    path: str
    message: str


class SaveReferenceUseCase:
    """
    Use case for saving a reference to the local library.

    This use case:
    1. Fetches reference details from PubMed
    2. Saves metadata and abstract to disk
    3. Optionally downloads PDF from PMC
    """

    def __init__(self, repository: ReferenceRepository, pubmed_client: PubMedClient):
        self.repository = repository
        self.client = pubmed_client

    def execute(self, input_data: SaveReferenceInput) -> SaveReferenceOutput:
        """
        Execute the save reference use case.

        Args:
            input_data: Input containing PMID and options.

        Returns:
            SaveReferenceOutput with details.

        Raises:
            ReferenceNotFoundError: If PMID not found on PubMed.
        """
        # Fetch from PubMed
        result = self.client.fetch_by_pmid(input_data.pmid)
        if result is None:
            raise ReferenceNotFoundError(f"PMID {input_data.pmid} not found on PubMed.")

        # Convert to Reference entity
        reference = PubMedParser.to_reference(result.to_dict())

        # Save to repository
        saved = self.repository.save(reference)

        # Download PDF if requested
        pdf_downloaded = False
        if input_data.download_pdf and result.pmc_id:
            pdf_content = self.client.download_pdf(input_data.pmid)
            if pdf_content:
                self.repository.save_pdf(input_data.pmid, pdf_content)
                pdf_downloaded = True

        return SaveReferenceOutput(
            pmid=saved.pmid or saved.unique_id,
            title=saved.title,
            has_pdf=pdf_downloaded,
            path=str(self.repository.base_dir / saved.unique_id),
            message=f"Reference {saved.unique_id} saved successfully."
            + (" PDF downloaded." if pdf_downloaded else ""),
        )
