import os
import re
from typing import List, Dict, Any
from med_paper_assistant.core.reference_manager import ReferenceManager

class Drafter:
    def __init__(self, reference_manager: ReferenceManager, drafts_dir: str = "drafts"):
        """
        Initialize the Drafter.
        
        Args:
            reference_manager: Instance of ReferenceManager to retrieve citation info.
            drafts_dir: Directory to store drafts.
        """
        self.ref_manager = reference_manager
        self.drafts_dir = drafts_dir
        if not os.path.exists(self.drafts_dir):
            os.makedirs(self.drafts_dir)

    def create_draft(self, filename: str, content: str) -> str:
        """
        Create a draft file with formatted citations.
        
        Args:
            filename: Name of the draft file (e.g., "introduction.md").
            content: Content with placeholders like (PMID:123456).
            
        Returns:
            Path to the created draft file.
        """
        # 1. Find all PMID placeholders
        # Pattern: (PMID:12345) or [PMID:12345]
        pattern = r"[\(\[]PMID:(\d+)[\)\]]"
        matches = re.findall(pattern, content)
        
        # Deduplicate but keep order
        pmids = []
        for pmid in matches:
            if pmid not in pmids:
                pmids.append(pmid)
        
        # 2. Replace placeholders with citation numbers
        citation_map = {pmid: i+1 for i, pmid in enumerate(pmids)}
        
        def replace_match(match):
            pmid = match.group(1)
            number = citation_map.get(pmid)
            return f"[{number}]"
            
        formatted_content = re.sub(pattern, replace_match, content)
        
        # 3. Generate Bibliography
        bibliography = "\n\n## References\n\n"
        for pmid in pmids:
            number = citation_map[pmid]
            metadata = self.ref_manager.get_metadata(pmid)
            
            if metadata:
                # Format: [1] Authors. Title. Journal (Year).
                authors = ", ".join(metadata.get('authors', []))
                title = metadata.get('title', 'Unknown Title')
                journal = metadata.get('journal', 'Unknown Journal')
                year = metadata.get('year', 'Unknown Year')
                
                entry = f"[{number}] {authors}. {title}. {journal} ({year}).\n"
            else:
                entry = f"[{number}] PMID:{pmid} (Metadata not found).\n"
            
            bibliography += entry
            
        final_content = formatted_content + bibliography
        
        # 4. Save file
        if not filename.endswith(".md"):
            filename += ".md"
            
        filepath = os.path.join(self.drafts_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        return filepath
