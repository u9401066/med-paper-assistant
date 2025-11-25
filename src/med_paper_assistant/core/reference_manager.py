import os
import json
from typing import List, Dict, Any
from med_paper_assistant.core.search import LiteratureSearcher

class ReferenceManager:
    def __init__(self, searcher: LiteratureSearcher, base_dir: str = "references"):
        """
        Initialize the ReferenceManager.
        
        Args:
            searcher: Instance of LiteratureSearcher to fetch details.
            base_dir: Directory to store references.
        """
        self.searcher = searcher
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def save_reference(self, pmid: str) -> str:
        """
        Save a reference by PMID.
        
        Args:
            pmid: PubMed ID of the article.
            
        Returns:
            Status message.
        """
        # Check if already exists
        ref_dir = os.path.join(self.base_dir, pmid)
        if os.path.exists(ref_dir):
            return f"Reference {pmid} already exists."

        # Fetch details
        results = self.searcher.fetch_details([pmid])
        if not results:
            return f"Could not find article with PMID {pmid}."
        
        if "error" in results[0]:
            return f"Error fetching article: {results[0]['error']}"
            
        article = results[0]
        
        # Create directory
        os.makedirs(ref_dir)
        
        # Save metadata
        with open(os.path.join(ref_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(article, f, indent=2, ensure_ascii=False)
            
        # Save content (Markdown)
        content = f"# {article['title']}\n\n"
        content += f"**Authors**: {', '.join(article['authors'])}\n"
        content += f"**Journal**: {article['journal']} ({article['year']})\n"
        content += f"**PMID**: {article['pmid']}\n\n"
        content += "## Abstract\n\n"
        content += article['abstract']
        
        with open(os.path.join(ref_dir, "content.md"), "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Successfully saved reference {pmid} to {ref_dir}."

    def list_references(self) -> List[str]:
        """
        List all saved references.
        
        Returns:
            List of PMIDs.
        """
        if not os.path.exists(self.base_dir):
            return []
        return [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]

    def get_metadata(self, pmid: str) -> Dict[str, Any]:
        """
        Get metadata for a reference. If not saved locally, attempts to fetch and save it.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            Dictionary containing metadata, or empty dict if failed.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        metadata_path = os.path.join(ref_dir, "metadata.json")
        
        # If exists locally, read it
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading metadata for {pmid}: {e}")
                return {}
        
        # If not, try to save it first
        print(f"Reference {pmid} not found locally. Attempting to fetch...")
        result = self.save_reference(pmid)
        if "Successfully saved" in result:
            # Try reading again
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        
        return {}
