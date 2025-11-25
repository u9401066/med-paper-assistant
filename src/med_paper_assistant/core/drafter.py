import os
import re
from typing import List, Dict, Any
from med_paper_assistant.core.reference_manager import ReferenceManager

from enum import Enum

class CitationStyle(Enum):
    VANCOUVER = "vancouver"      # [1]
    APA = "apa"                  # (Author, Year)
    HARVARD = "harvard"          # (Author Year)
    NATURE = "nature"            # Superscript
    AMA = "ama"                  # Superscript

class Drafter:
    def __init__(self, reference_manager: ReferenceManager, drafts_dir: str = "drafts", citation_style: str = CitationStyle.VANCOUVER.value):
        """
        Initialize the Drafter.
        
        Args:
            reference_manager: Instance of ReferenceManager to retrieve citation info.
            drafts_dir: Directory to store drafts.
            citation_style: Default citation style.
        """
        self.ref_manager = reference_manager
        self.drafts_dir = drafts_dir
        self.citation_style = citation_style
        if not os.path.exists(self.drafts_dir):
            os.makedirs(self.drafts_dir)

    def set_citation_style(self, style: str):
        """Set the citation style."""
        # Validate style
        valid_styles = [s.value for s in CitationStyle]
        if style not in valid_styles:
            raise ValueError(f"Invalid style: {style}. Valid options: {valid_styles}")
        self.citation_style = style

    def create_draft(self, filename: str, content: str) -> str:
        """
        Create a draft file with formatted citations.
        
        Args:
            filename: Name of the draft file (e.g., "introduction.md").
            content: Content with placeholders like (PMID:123456).
            
        Returns:
            Path to the created draft file.
        """
        final_content = self._compile_draft(content)
        
        # Save file
        if not filename.endswith(".md"):
            filename += ".md"
            
        filepath = os.path.join(self.drafts_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        return filepath

    def insert_citation(self, filename: str, target_text: str, pmid: str) -> str:
        """
        Insert a citation after the target text in an existing draft.
        
        Args:
            filename: Name of the draft file.
            target_text: Text segment to locate insertion point.
            pmid: PubMed ID to cite.
            
        Returns:
            Path to the updated draft file.
        """
        if not filename.endswith(".md"):
            filename += ".md"
            
        filepath = os.path.join(self.drafts_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Draft file {filename} not found.")
            
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 1. Extract and Parse Bibliography to map [n] -> PMID
        body_content = content
        existing_refs = {} 
        
        if "## References" in content:
            parts = content.split("## References")
            body_content = parts[0].strip()
            
            # Regex to parse bib: \[(\d+)\] .*? PMID:(\d+)
            # Note: This only works for numbered styles (Vancouver). 
            # For Author-Date styles, we need a different strategy or just rely on PMID presence.
            # For now, we assume if we are inserting, we might be disrupting the order.
            # But if we use Author-Date, order doesn't matter as much (alphabetical usually).
            
            bib_pattern = r"\[(\d+)\] .*? PMID:(\d+)"
            found_refs = re.findall(bib_pattern, content)
            for ref_num, ref_pmid in found_refs:
                existing_refs[ref_num] = ref_pmid
            
        # 2. Replace [n] in body with [PMID:xxx] (Only for numbered styles)
        # If style is APA/Harvard, citations are (Author, Year).
        # We need to reverse-engineer them too? Or just leave them?
        # If we leave them, `_compile_draft` won't touch them unless they match `(PMID:...)`.
        # So we only need to revert if we want to re-number.
        
        if self.citation_style in [CitationStyle.VANCOUVER.value, CitationStyle.NATURE.value, CitationStyle.AMA.value]:
            for ref_num, ref_pmid in existing_refs.items():
                # Handle brackets [1] or superscript ^1 (if we implemented that)
                # For now assuming [1] for Vancouver
                body_content = body_content.replace(f"[{ref_num}]", f"[PMID:{ref_pmid}]")
            
        # 3. Find target text and insert new placeholder
        if target_text not in body_content:
             raise ValueError(f"Target text '{target_text}' not found in draft.")
             
        insertion = f" [PMID:{pmid}]"
        new_content = body_content.replace(target_text, target_text + insertion, 1)
        
        # 4. Re-compile
        final_content = self._compile_draft(new_content)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        return filepath

    def _format_citation_in_text(self, number: int, metadata: Dict[str, Any]) -> str:
        """Format the in-text citation."""
        if self.citation_style == CitationStyle.VANCOUVER.value:
            return f"[{number}]"
        elif self.citation_style == CitationStyle.APA.value:
            # (Author, Year)
            authors = metadata.get('authors', [])
            if not authors:
                author_text = "Unknown"
            elif len(authors) == 1:
                author_text = authors[0].split()[0]
            elif len(authors) == 2:
                author1 = authors[0].split()[0]
                author2 = authors[1].split()[0]
                author_text = f"{author1} & {author2}"
            else:
                author_text = f"{authors[0].split()[0]} et al."
            
            year = metadata.get('year', 'n.d.')
            return f"({author_text}, {year})"
        elif self.citation_style == CitationStyle.HARVARD.value:
            # (Author Year)
            authors = metadata.get('authors', [])
            if not authors:
                author_text = "Unknown"
            elif len(authors) == 1:
                author_text = authors[0].split()[0]
            elif len(authors) == 2:
                author1 = authors[0].split()[0]
                author2 = authors[1].split()[0]
                author_text = f"{author1} and {author2}"
            else:
                author_text = f"{authors[0].split()[0]} et al."
            
            year = metadata.get('year', 'n.d.')
            return f"({author_text} {year})"
        elif self.citation_style in [CitationStyle.NATURE.value, CitationStyle.AMA.value]:
            # Superscript (Markdown doesn't support native superscript, usually ^1^)
            return f"^{number}^"
        return f"[{number}]"

    def _format_bibliography_entry(self, number: int, metadata: Dict[str, Any], pmid: str) -> str:
        """Format the bibliography entry."""
        authors = ", ".join(metadata.get('authors', []))
        title = metadata.get('title', 'Unknown Title')
        journal = metadata.get('journal', 'Unknown Journal')
        year = metadata.get('year', 'Unknown Year')
        
        if self.citation_style == CitationStyle.VANCOUVER.value:
            return f"[{number}] {authors}. {title}. {journal} ({year}). PMID:{pmid}.\n"
        elif self.citation_style == CitationStyle.APA.value:
            # Author (Year). Title. Journal.
            return f"{authors} ({year}). {title}. {journal}. PMID:{pmid}.\n"
        elif self.citation_style == CitationStyle.HARVARD.value:
            # Author (Year) 'Title', Journal.
            return f"{authors} ({year}) '{title}', {journal}. PMID:{pmid}.\n"
        elif self.citation_style == CitationStyle.NATURE.value:
            # Number. Author. Title. Journal Year;Volume:Page.
            return f"{number}. {authors}. {title}. {journal} ({year}). PMID:{pmid}.\n"
        elif self.citation_style == CitationStyle.AMA.value:
            # Number. Author. Title. Journal. Year.
            return f"{number}. {authors}. {title}. {journal}. {year}. PMID:{pmid}.\n"
        return f"[{number}] {authors}. {title}. {journal} ({year}). PMID:{pmid}.\n"

    def _compile_draft(self, content: str) -> str:
        """
        Compile draft content: replace placeholders and generate bibliography.
        
        Args:
            content: Raw content with [PMID:xxx] placeholders.
            
        Returns:
            Compiled content with formatted citations and bibliography.
        """
        # 1. Find all PMID placeholders
        pattern = r"[\(\[]PMID:(\d+)[\)\]]"
        matches = re.findall(pattern, content)
        
        # Deduplicate but keep order
        pmids = []
        for pmid in matches:
            if pmid not in pmids:
                pmids.append(pmid)
        
        # 2. Replace placeholders
        citation_map = {pmid: i+1 for i, pmid in enumerate(pmids)}
        
        def replace_match(match):
            pmid = match.group(1)
            number = citation_map.get(pmid)
            metadata = self.ref_manager.get_metadata(pmid) or {}
            return self._format_citation_in_text(number, metadata)
            
        formatted_content = re.sub(pattern, replace_match, content)
        
        # 3. Generate Bibliography
        bibliography = "\n\n## References\n\n"
        
        # For Author-Date styles, usually bibliography is alphabetical.
        # For Numbered styles, it's by appearance.
        # We will stick to appearance order for now unless strictly required otherwise.
        # (APA/Harvard usually alphabetical, but for simplicity we keep appearance order or we'd need to re-sort pmids)
        
        # If APA/Harvard, we should sort pmids alphabetically by author?
        # Let's keep it simple for Phase 1: Order by appearance for all, but format differently.
        
        for pmid in pmids:
            number = citation_map[pmid]
            metadata = self.ref_manager.get_metadata(pmid) or {}
            entry = self._format_bibliography_entry(number, metadata, pmid)
            bibliography += entry
            
        return formatted_content + bibliography
