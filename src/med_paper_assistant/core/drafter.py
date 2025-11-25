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
        existing_refs = {} # Map "1" -> "12345"
        
        if "## References" in content:
            parts = content.split("## References")
            body_content = parts[0].strip()
            bib_section = parts[1].strip()
            
            # Regex to find [n] ... PMID:12345 ... or we need to look up metadata?
            # Actually, simpler: We can just look for the PMID in the bib entry if we stored it?
            # Our format: [1] Authors. Title. Journal (Year).
            # It DOES NOT contain the PMID explicitly in the visible text usually, unless we added it.
            # Wait, in `_compile_draft` I didn't add PMID to the bibliography entry unless metadata failed.
            # This is a problem for reconstruction.
            # FIX: We should include PMID in the bibliography entry for machine readability, 
            # or at least in a hidden comment? Or just visible is fine for this tool.
            # Let's update `_compile_draft` to include PMID in the entry.
            pass

        # TEMPORARY FIX: For now, `insert_citation` will fail to re-order correctly if we can't map [1] back to PMID.
        # But if we just append the new [PMID:xxx] and re-compile, `_compile_draft` will see [1] as just text?
        # No, `_compile_draft` regex looks for `[PMID:...]`. It ignores `[1]`.
        # So if we leave `[1]` as is, it will remain `[1]`.
        # But if we insert a new reference before it, `[1]` should become `[2]`.
        # So we MUST convert `[1]` back to `[PMID:old_id]`.
        
        # To fix this properly, I need to modify `_compile_draft` to output PMID in the bibliography
        # so I can parse it back.
        
        # Let's assume I will update `_compile_draft` below to include PMID.
        # Regex to parse bib: \[(\d+)\] .*? PMID:(\d+)
        
        bib_pattern = r"\[(\d+)\] .*? PMID:(\d+)"
        found_refs = re.findall(bib_pattern, content)
        for ref_num, ref_pmid in found_refs:
            existing_refs[ref_num] = ref_pmid
            
        # 2. Replace [n] in body with [PMID:xxx]
        for ref_num, ref_pmid in existing_refs.items():
            body_content = body_content.replace(f"[{ref_num}]", f"[PMID:{ref_pmid}]")
            
        # 3. Find target text and insert new placeholder
        if target_text not in body_content:
             # Try to be lenient? No, strict for safety.
             raise ValueError(f"Target text '{target_text}' not found in draft.")
             
        insertion = f" [PMID:{pmid}]"
        new_content = body_content.replace(target_text, target_text + insertion, 1)
        
        # 4. Re-compile
        final_content = self._compile_draft(new_content)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        return filepath

    def _compile_draft(self, content: str) -> str:
        """
        Compile draft content: replace placeholders and generate bibliography.
        
        Args:
            content: Raw content with [PMID:xxx] placeholders.
            
        Returns:
            Compiled content with [1] style citations and bibliography.
        """
        # 1. Find all PMID placeholders
        # Pattern: (PMID:12345) or [PMID:12345] or just PMID:12345 if we want to be loose
        # Let's stick to brackets/parens for safety, but also handle the case where we just inserted [PMID:xxx]
        # Note: The previous regex was r"[\(\[]PMID:(\d+)[\)\]]"
        # We need to handle potential existing [1] if we re-read a compiled file?
        # Actually, insert_citation strips the bibliography, but the text still has [1].
        # This is tricky. If we re-compile a compiled file, we need to revert [1] back to placeholders OR
        # we need to store the raw draft separately. 
        # FOR SIMPLICITY in this iteration: We assume the user/agent is working on the "source" text 
        # OR we reverse-engineer [1] -> PMID? No, that's hard without state.
        # STRATEGY: We will assume the file on disk is the "compiled" version. 
        # But to insert, we really want to insert into the "source". 
        # Since we don't have a database of drafts, we have to parse the compiled file.
        # BUT, the compiled file has [1], [2]. We don't know what PMID [1] is unless we parse the bibliography.
        
        # Let's implement a "De-compiler" first?
        # Or simpler: We parse the existing bibliography to map [1] -> PMID.
        # Then replace [1] -> [PMID:xxx] in the text.
        # Then insert the new [PMID:yyy].
        # Then re-compile.
        
        # Extract existing bibliography if present (handled in insert_citation splitting)
        # Wait, insert_citation splits content. So `content` passed here is just body text.
        # If `content` has [1], [2], we need to know what they are.
        
        # REVISED STRATEGY for insert_citation:
        # 1. Read full file.
        # 2. Extract Bibliography to build a map: "1" -> "12345", "2" -> "67890".
        # 3. Replace all `[\d+]` in text with `[PMID:...]` using the map.
        # 4. Perform insertion of new `[PMID:new]`.
        # 5. Call `_compile_draft`.
        
        # However, `_compile_draft` is also used by `create_draft` which starts from scratch.
        # So `_compile_draft` should just take text with `[PMID:...]` and do the job.
        # The "De-compilation" logic should be in `insert_citation` or a helper.
        
        # Let's put the regex logic here.
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
                # Format: [1] Authors. Title. Journal (Year). PMID:xxxx.
                authors = ", ".join(metadata.get('authors', []))
                title = metadata.get('title', 'Unknown Title')
                journal = metadata.get('journal', 'Unknown Journal')
                year = metadata.get('year', 'Unknown Year')
                
                entry = f"[{number}] {authors}. {title}. {journal} ({year}). PMID:{pmid}.\n"
            else:
                entry = f"[{number}] PMID:{pmid} (Metadata not found).\n"
            
            bibliography += entry
            
        return formatted_content + bibliography
