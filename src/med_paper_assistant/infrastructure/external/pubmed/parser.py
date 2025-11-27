"""
PubMed Parser - Parse PubMed responses into domain entities.
"""

from typing import Dict, Any, List
from med_paper_assistant.domain.entities.reference import Reference


class PubMedParser:
    """
    Parser for converting PubMed API responses to domain entities.
    """
    
    @staticmethod
    def to_reference(data: Dict[str, Any]) -> Reference:
        """
        Convert PubMed search result to Reference entity.
        
        Args:
            data: Raw PubMed article data.
            
        Returns:
            Reference entity.
        """
        # Parse authors
        authors = []
        for author_data in data.get("authors_full", []):
            if "collective_name" in author_data:
                authors.append(author_data["collective_name"])
            else:
                last = author_data.get("last_name", "")
                fore = author_data.get("fore_name", "")
                initials = author_data.get("initials", "")
                authors.append({
                    "last_name": last,
                    "fore_name": fore,
                    "initials": initials,
                })
        
        return Reference(
            pmid=data.get("pmid", ""),
            title=data.get("title", ""),
            authors=authors,
            journal=data.get("journal", ""),
            journal_abbrev=data.get("journal_abbrev", ""),
            year=data.get("year", ""),
            month=data.get("month", ""),
            day=data.get("day", ""),
            volume=data.get("volume", ""),
            issue=data.get("issue", ""),
            pages=data.get("pages", ""),
            doi=data.get("doi", ""),
            pmc_id=data.get("pmc_id", ""),
            abstract=data.get("abstract", ""),
            keywords=data.get("keywords", []),
            mesh_terms=data.get("mesh_terms", []),
        )
    
    @staticmethod
    def to_references(data_list: List[Dict[str, Any]]) -> List[Reference]:
        """
        Convert multiple PubMed results to Reference entities.
        
        Args:
            data_list: List of raw PubMed article data.
            
        Returns:
            List of Reference entities.
        """
        return [
            PubMedParser.to_reference(data) 
            for data in data_list 
            if "error" not in data
        ]
