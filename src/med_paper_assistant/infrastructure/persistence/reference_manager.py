import os
import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager

from med_paper_assistant.domain.services.reference_converter import (
    ReferenceConverter,
    StandardizedReference,
)


class ReferenceManager:
    """
    管理本地文獻參考資料的儲存、檢索和組織。
    
    重構說明 (2025-12):
    - 使用 ReferenceConverter Domain Service 處理格式轉換
    - 支援多來源：PubMed, Zotero, DOI
    - 唯一識別符：unique_id + citation_key (for Foam)
    - 文獻搜尋由外部 MCP 負責，Agent 協調資料傳遞
    """
    
    def __init__(
        self, 
        base_dir: str = "references",
        project_manager: Optional["ProjectManager"] = None
    ):
        """
        Initialize the ReferenceManager.
        
        Args:
            base_dir: Default directory to store references (used if no project active).
            project_manager: Optional ProjectManager for multi-project support.
        """
        self._default_base_dir = base_dir
        self._project_manager = project_manager
        self._converter = ReferenceConverter()
        # Note: Directory is created on-demand when saving references,
        # not at initialization to avoid polluting root directory
    
    @property
    def base_dir(self) -> str:
        """
        Get the current references directory.
        Uses project directory if a project is active, otherwise default.
        """
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("references", self._default_base_dir)
            except (ValueError, KeyError):
                pass
        return self._default_base_dir

    def save_reference(self, article: Dict[str, Any], download_pdf: bool = False) -> str:
        """
        Save a reference with provided article metadata.
        
        支援來源：
        - PubMed (需要 pmid 欄位)
        - Zotero (需要 key 或 zotero_key 欄位)
        - DOI (需要 doi 或 DOI 欄位)
        
        Args:
            article: Article metadata dictionary from any source.
                     Must contain at least one identifier: pmid, zotero_key/key, or doi/DOI.
            download_pdf: Deprecated - PDF download handled externally.
            
        Returns:
            Status message with Foam citation key.
        """
        # Use domain converter to standardize format
        try:
            ref = self._converter.convert(article)
        except ValueError as e:
            return f"Error: {str(e)}"
        
        # Check if already exists
        ref_dir = os.path.join(self.base_dir, ref.unique_id)
        if os.path.exists(ref_dir):
            return f"Reference {ref.unique_id} already exists."
        
        # Create directory
        os.makedirs(ref_dir, exist_ok=True)
        
        # Add pre-formatted citation strings to metadata
        ref_dict = ref.to_dict()
        ref_dict['citation'] = self._format_citation(ref_dict)
        
        # Save metadata
        with open(os.path.join(ref_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(ref_dict, f, indent=2, ensure_ascii=False)
            
        # Save content (Markdown) - main file for Foam preview
        content = self._generate_content_md(ref_dict)
        with open(os.path.join(ref_dir, "content.md"), "w", encoding="utf-8") as f:
            f.write(content)
        
        # Create Foam-friendly alias file
        self._create_foam_alias(ref.unique_id, ref.citation_key)
        
        foam_tip = f"\n💡 Foam: Use [[{ref.citation_key}]] to link this reference."
        source_info = f" (source: {ref.source})"
        return f"Successfully saved reference {ref.unique_id} to {ref_dir}.{source_info}{foam_tip}"
    
    def save_reference_by_pmid(self, pmid: str) -> str:
        """
        [DEPRECATED] 舊版接口，保留向後相容。
        
        新的工作流程應該是:
        1. Agent 呼叫 pubmed-search MCP 的 fetch_article_details(pmid)
        2. Agent 呼叫 mdpaper MCP 的 save_reference(article_metadata)
        
        Returns:
            提示訊息，指引使用者使用新的工作流程。
        """
        return (
            f"❌ save_reference_by_pmid is deprecated.\n\n"
            f"New workflow:\n"
            f"1. Use pubmed-search MCP: fetch_article_details(pmid='{pmid}')\n"
            f"2. Use mdpaper MCP: save_reference(article=<metadata from step 1>)\n\n"
            f"This separation allows MCP-to-MCP communication through the Agent."
        )
    
    def _generate_citation_key(self, article: Dict[str, Any]) -> str:
        """
        Generate a human-friendly citation key with PMID for verification.
        Format: 'smith2023_41285088' (author + year + underscore + PMID)
        
        Args:
            article: Article metadata dictionary.
            
        Returns:
            Citation key string like 'smith2023_41285088'.
        """
        authors_full = article.get('authors_full', [])
        authors = article.get('authors', [])
        year = article.get('year', '')
        pmid = article.get('pmid', '')
        
        # Get first author last name
        first_author = ""
        if authors_full and isinstance(authors_full[0], dict):
            first_author = authors_full[0].get('last_name', '').lower()
        elif authors:
            # Fallback: extract from string format "Last First"
            first_author = authors[0].split()[0].lower() if authors[0] else ""
        
        if not first_author:
            first_author = "unknown"
        
        # Clean up special characters
        import re
        first_author = re.sub(r'[^a-z]', '', first_author)
        
        # Format: author + year + underscore + PMID for easy verification
        return f"{first_author}{year}_{pmid}"
    
    def _create_foam_alias(self, pmid: str, citation_key: str):
        """
        Create a Foam-friendly alias file that redirects to the main content.
        This allows users to use [[smith2023_41285088]] for easy linking and verification.
        
        Args:
            pmid: PubMed ID.
            citation_key: Human-friendly citation key with PMID (e.g., 'smith2023_41285088').
        """
        alias_path = os.path.join(self.base_dir, f"{citation_key}.md")
        
        # Since citation_key now includes PMID, collisions are impossible
        # But still check just in case
        if os.path.exists(alias_path):
            return  # Already exists, no need to create
        
        # Create a redirect file that includes the content
        # This way Foam can preview it directly
        ref_dir = os.path.join(self.base_dir, pmid)
        content_path = os.path.join(ref_dir, "content.md")
        
        if os.path.exists(content_path):
            with open(content_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add alias info to the top
            alias_content = f"<!-- Alias for PMID:{pmid} -->\n"
            alias_content += f"<!-- Verify: https://pubmed.ncbi.nlm.nih.gov/{pmid}/ -->\n\n"
            alias_content += content
            
            with open(alias_path, 'w', encoding='utf-8') as f:
                f.write(alias_content)

    def _get_preferred_citation_style(self) -> Optional[str]:
        """
        Get the preferred citation style from project settings.
        
        Returns:
            Citation style string (e.g., 'apa', 'vancouver') or None if not set.
        """
        if self._project_manager:
            try:
                current_slug = self._project_manager.get_current_project()
                if current_slug:
                    project_info = self._project_manager.get_project_info(current_slug)
                    if project_info.get('success'):
                        settings = project_info.get('settings', {})
                        return settings.get('citation_style')
            except (ValueError, KeyError):
                pass
        return None

    def _format_citation(self, article: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate pre-formatted citation strings in multiple formats.
        
        Args:
            article: Article metadata dictionary.
            
        Returns:
            Dictionary with citation strings in different formats.
        """
        authors = article.get('authors', [])
        authors_full = article.get('authors_full', [])
        title = article.get('title', 'Unknown Title').rstrip('.')
        journal = article.get('journal', 'Unknown Journal')
        journal_abbrev = article.get('journal_abbrev', journal)
        year = article.get('year', '')
        volume = article.get('volume', '')
        issue = article.get('issue', '')
        pages = article.get('pages', '')
        doi = article.get('doi', '')
        pmid = article.get('pmid', '')
        
        # Format authors for different styles
        def format_vancouver_authors(auth_list, max_authors=6):
            if not auth_list:
                return "Unknown Author"
            
            formatted = []
            for i, author in enumerate(auth_list[:max_authors]):
                if isinstance(author, dict):
                    if 'collective_name' in author:
                        formatted.append(author['collective_name'])
                    else:
                        last = author.get('last_name', '')
                        initials = author.get('initials', '')
                        formatted.append(f"{last} {initials}")
                else:
                    # Fallback for simple string format
                    parts = author.split()
                    if len(parts) >= 2:
                        formatted.append(f"{parts[0]} {''.join([p[0] for p in parts[1:]])}")
                    else:
                        formatted.append(author)
            
            result = ", ".join(formatted)
            if len(auth_list) > max_authors:
                result += ", et al"
            return result
        
        def format_apa_authors(auth_list, max_authors=7):
            if not auth_list:
                return "Unknown Author"
            
            formatted = []
            for author in auth_list[:max_authors]:
                if isinstance(author, dict):
                    if 'collective_name' in author:
                        formatted.append(author['collective_name'])
                    else:
                        last = author.get('last_name', '')
                        initials = author.get('initials', '')
                        # APA: Last, F. M.
                        init_formatted = ". ".join(list(initials)) + "." if initials else ""
                        formatted.append(f"{last}, {init_formatted}")
                else:
                    parts = author.split()
                    if len(parts) >= 2:
                        init = ". ".join([p[0] for p in parts[1:]]) + "."
                        formatted.append(f"{parts[0]}, {init}")
                    else:
                        formatted.append(author)
            
            if len(formatted) == 1:
                result = formatted[0]
            elif len(formatted) == 2:
                result = f"{formatted[0]} & {formatted[1]}"
            else:
                result = ", ".join(formatted[:-1]) + f", & {formatted[-1]}"
            
            if len(auth_list) > max_authors:
                result = ", ".join(formatted[:6]) + ", ... " + formatted[-1]
            
            return result
        
        # Vancouver format
        vancouver_auth = format_vancouver_authors(authors_full or authors)
        vancouver = f"{vancouver_auth}. {title}. {journal_abbrev or journal}. {year}"
        if volume:
            vancouver += f";{volume}"
            if issue:
                vancouver += f"({issue})"
            if pages:
                vancouver += f":{pages}"
        vancouver += "."
        if doi:
            vancouver += f" doi:{doi}"
        
        # APA format
        apa_auth = format_apa_authors(authors_full or authors)
        apa = f"{apa_auth} ({year}). {title}. *{journal}*"
        if volume:
            apa += f", *{volume}*"
            if issue:
                apa += f"({issue})"
            if pages:
                apa += f", {pages}"
        apa += "."
        if doi:
            apa += f" https://doi.org/{doi}"
        
        # Nature/Science format
        nature_auth = format_vancouver_authors(authors_full or authors, max_authors=5)
        nature = f"{nature_auth} {title}. *{journal_abbrev or journal}* **{volume}**, {pages} ({year})."
        if doi:
            nature += f" https://doi.org/{doi}"
        
        # Simple format for in-text
        first_author = ""
        if authors_full:
            first_author = authors_full[0].get('last_name', '') if isinstance(authors_full[0], dict) else authors[0].split()[0] if authors else ""
        elif authors:
            first_author = authors[0].split()[0] if authors else ""
        
        if len(authors) == 1:
            in_text = f"{first_author}, {year}"
        elif len(authors) == 2:
            second_author = ""
            if authors_full and len(authors_full) > 1:
                second_author = authors_full[1].get('last_name', '') if isinstance(authors_full[1], dict) else authors[1].split()[0]
            elif len(authors) > 1:
                second_author = authors[1].split()[0]
            in_text = f"{first_author} & {second_author}, {year}"
        else:
            in_text = f"{first_author} et al., {year}"
        
        return {
            "vancouver": vancouver,
            "apa": apa,
            "nature": nature,
            "in_text": in_text,
            "pmid": f"PMID: {pmid}",
            "doi": f"doi:{doi}" if doi else ""
        }
    
    def _generate_content_md(self, article: Dict[str, Any]) -> str:
        """
        Generate markdown content for the reference.
        Optimized for Foam hover preview - shows citation formats at the top.
        
        Args:
            article: Article metadata dictionary.
            
        Returns:
            Markdown formatted content string.
        """
        pmid = article.get('pmid', '')
        title = article.get('title', 'Unknown Title')
        
        # YAML frontmatter for Foam (enables better linking)
        content = "---\n"
        content += f"pmid: \"{pmid}\"\n"
        content += f"type: reference\n"
        content += f"year: {article.get('year', '')}\n"
        if article.get('doi'):
            content += f"doi: \"{article['doi']}\"\n"
        # First author last name for easy referencing
        authors_full = article.get('authors_full', [])
        if authors_full and isinstance(authors_full[0], dict):
            first_author = authors_full[0].get('last_name', '')
            content += f"first_author: \"{first_author}\"\n"
        content += "---\n\n"
        
        content += f"# {title}\n\n"
        
        # Authors
        authors = article.get('authors', [])
        content += f"**Authors**: {', '.join(authors)}\n\n"
        
        # Journal info
        journal = article.get('journal', 'Unknown Journal')
        year = article.get('year', '')
        volume = article.get('volume', '')
        issue = article.get('issue', '')
        pages = article.get('pages', '')
        
        journal_info = f"{journal}"
        if year:
            journal_info += f" ({year})"
        if volume:
            journal_info += f"; {volume}"
            if issue:
                journal_info += f"({issue})"
            if pages:
                journal_info += f": {pages}"
        content += f"**Journal**: {journal_info}\n\n"
        
        # IDs
        content += f"**PMID**: {pmid}\n"
        if article.get('doi'):
            content += f"**DOI**: [{article['doi']}](https://doi.org/{article['doi']})\n"
        if article.get('pmc_id'):
            content += f"**PMC**: {article['pmc_id']}\n"
        content += "\n"
        
        # Citation formats (visible in Foam hover preview!)
        # Show the project's preferred style first with ⭐
        citation = article.get('citation', {})
        if citation:
            preferred_style = self._get_preferred_citation_style()
            content += "## 📋 Citation Formats\n\n"
            
            # Style order: preferred first, then others
            style_order = ['vancouver', 'apa', 'nature']
            if preferred_style and preferred_style in style_order:
                style_order.remove(preferred_style)
                style_order.insert(0, preferred_style)
            
            style_labels = {
                'vancouver': 'Vancouver',
                'apa': 'APA', 
                'nature': 'Nature',
                'harvard': 'Harvard',
                'ama': 'AMA'
            }
            
            for style in style_order:
                if citation.get(style):
                    label = style_labels.get(style, style.title())
                    if style == preferred_style:
                        content += f"**⭐ {label}**: {citation[style]}\n\n"
                    else:
                        content += f"**{label}**: {citation[style]}\n\n"
            
            if citation.get('in_text'):
                content += f"**In-text**: ({citation['in_text']})\n\n"
        
        # Keywords
        keywords = article.get('keywords', [])
        if keywords:
            content += f"**Keywords**: {', '.join(keywords)}\n\n"
        
        # MeSH terms
        mesh_terms = article.get('mesh_terms', [])
        if mesh_terms:
            content += f"**MeSH Terms**: {', '.join(mesh_terms[:10])}"
            if len(mesh_terms) > 10:
                content += f" (+{len(mesh_terms) - 10} more)"
            content += "\n\n"
        
        # Abstract
        content += "## Abstract\n\n"
        content += article.get('abstract', 'No abstract available.')
        content += "\n"
        
        return content

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
        Get metadata for a locally saved reference.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            Dictionary containing metadata, or empty dict if not found locally.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        metadata_path = os.path.join(ref_dir, "metadata.json")
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading metadata for {pmid}: {e}")
                return {}
        
        # Reference not found locally
        return {}

    def search_local(self, query: str) -> List[Dict[str, Any]]:
        """
        Search within saved local references by keyword.
        
        Args:
            query: Keyword to search in titles and abstracts.
            
        Returns:
            List of matching metadata dictionaries.
        """
        results = []
        query = query.lower()
        
        for pmid in self.list_references():
            meta = self.get_metadata(pmid)
            if not meta:
                continue
                
            title = meta.get('title', '').lower()
            abstract = meta.get('abstract', '').lower()
            
            if query in title or query in abstract:
                results.append(meta)
                
        return results
    
    def check_reference_exists(self, pmid: str) -> bool:
        """
        Check if a reference is already saved locally.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            True if reference exists locally.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        return os.path.exists(ref_dir)
                
        return results

    def has_fulltext(self, pmid: str) -> bool:
        """
        Check if a reference has a downloaded PDF fulltext.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            True if fulltext PDF exists.
        """
        pdf_path = os.path.join(self.base_dir, pmid, "fulltext.pdf")
        return os.path.exists(pdf_path)

    def get_fulltext_path(self, pmid: str) -> Optional[str]:
        """
        Get the path to the fulltext PDF if it exists.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            Path to PDF file, or None if not available.
        """
        pdf_path = os.path.join(self.base_dir, pmid, "fulltext.pdf")
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
            return "Error: pypdf library not installed. Install with: pip install pypdf"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

    def get_reference_summary(self, pmid: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a reference including availability info.
        
        Args:
            pmid: PubMed ID.
            
        Returns:
            Dictionary with metadata and availability information.
        """
        meta = self.get_metadata(pmid)
        if not meta:
            return {"error": f"Reference {pmid} not found"}
        
        summary = {
            "pmid": pmid,
            "title": meta.get('title', ''),
            "authors": meta.get('authors', []),
            "journal": meta.get('journal', ''),
            "year": meta.get('year', ''),
            "doi": meta.get('doi', ''),
            "has_abstract": bool(meta.get('abstract')),
            "has_fulltext_pdf": self.has_fulltext(pmid),
            "citation": meta.get('citation', {})
        }
        
        return summary

    def save_pdf(self, pmid: str, pdf_content: bytes) -> str:
        """
        Save PDF content for a reference.
        
        Args:
            pmid: PubMed ID.
            pdf_content: PDF file content as bytes.
            
        Returns:
            Status message.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        if not os.path.exists(ref_dir):
            return f"Reference {pmid} not found. Save metadata first."
        
        pdf_path = os.path.join(ref_dir, "fulltext.pdf")
        if os.path.exists(pdf_path):
            return f"PDF already exists for {pmid}."
        
        try:
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            return f"Successfully saved PDF for {pmid}."
        except Exception as e:
            return f"Error saving PDF for {pmid}: {str(e)}"
