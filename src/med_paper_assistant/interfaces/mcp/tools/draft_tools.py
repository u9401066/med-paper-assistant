"""
Draft Tools Module

Tools for creating and editing paper drafts, section templates, and word counting.

Key Features:
- Automatic concept validation before draft processing
- Novelty scoring with 3-round LLM evaluation (75+ threshold)
- Integration with ConceptValidator service
"""

import os
import re
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator


# Global validator instance
_concept_validator = ConceptValidator()


def _get_concept_path() -> str:
    """Get the path to the current project's concept.md file."""
    from med_paper_assistant.infrastructure.persistence import get_project_manager
    pm = get_project_manager()
    current = pm.get_current_project()
    
    if current.get("project_path"):
        return os.path.join(current["project_path"], "concept.md")
    return None


def _enforce_concept_validation(require_novelty: bool = True) -> tuple:
    """
    Enforce concept validation before draft operations.
    
    This is a MANDATORY check that runs before any draft writing.
    
    Args:
        require_novelty: Whether to require novelty check (default: True)
    
    Returns:
        Tuple of (can_proceed: bool, message: str, protected_content: dict)
    """
    concept_path = _get_concept_path()
    
    if not concept_path or not os.path.exists(concept_path):
        return (
            False, 
            "❌ **VALIDATION REQUIRED**\n\n"
            "No concept.md found for current project.\n"
            "You must create and validate a concept file first:\n\n"
            "1. Use `/mdpaper.concept` to develop your research concept\n"
            "2. Fill in 🔒 NOVELTY STATEMENT\n"
            "3. Fill in 🔒 KEY SELLING POINTS (at least 3)\n"
            "4. Run `validate_concept` to verify\n\n"
            "Draft writing is blocked until concept validation passes.",
            {}
        )
    
    # Run validation
    result = _concept_validator.validate(
        concept_path,
        run_novelty_check=require_novelty,
        run_consistency_check=True,
        force_refresh=False  # Use cache if available
    )
    
    if not result.overall_passed:
        report = _concept_validator.generate_report(result)
        return (
            False,
            f"❌ **CONCEPT VALIDATION FAILED**\n\n"
            f"You must fix the following issues before writing drafts:\n\n"
            f"{report}\n\n"
            f"**Draft writing is blocked until validation passes.**",
            {}
        )
    
    # Extract protected content for reference
    novelty_section = result.sections.get("novelty_statement")
    selling_section = result.sections.get("selling_points")
    
    protected_content = {
        "novelty_statement": novelty_section.content if novelty_section else "",
        "selling_points": selling_section.content if selling_section else "",
        "novelty_score": result.novelty_average
    }
    
    return (
        True,
        f"✅ Concept validation passed (Novelty score: {result.novelty_average:.1f}/100)",
        protected_content
    )


def register_draft_tools(mcp: FastMCP, drafter: Drafter):
    """Register all draft-related tools with the MCP server."""
    
    @mcp.tool()
    def draft_section(topic: str, notes: str, skip_validation: bool = False) -> str:
        """
        Draft a section of a medical paper based on notes.
        
        ⚠️ REQUIRES: Valid concept.md with novelty check passed.
        
        This tool enforces concept validation before drafting. The draft must:
        - Preserve 🔒 NOVELTY STATEMENT in Introduction
        - Preserve 🔒 KEY SELLING POINTS in Discussion
        - Not weaken or remove protected content
        
        Args:
            topic: The topic of the section (e.g., "Introduction").
            notes: Raw notes or bullet points to convert into text.
            skip_validation: For internal use only. Do not set to True.
        """
        # Enforce validation
        if not skip_validation:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                return message
        
        # Remind about protected content
        reminder = ""
        if topic.lower() == "introduction":
            reminder = "\n\n⚠️ **REMINDER**: Introduction must reflect the 🔒 NOVELTY STATEMENT."
        elif topic.lower() == "discussion":
            reminder = "\n\n⚠️ **REMINDER**: Discussion must emphasize 🔒 KEY SELLING POINTS."
        
        return f"Drafting section '{topic}' based on notes...{reminder}"

    @mcp.tool()
    def get_section_template(section: str) -> str:
        """
        Get writing guidelines for a specific paper section.
        
        Args:
            section: "introduction", "methods", "results", "discussion", "abstract"
        """
        from med_paper_assistant.infrastructure.services import SECTION_PROMPTS
        return SECTION_PROMPTS.get(
            section.lower(), 
            "Section not found. Available: " + ", ".join(SECTION_PROMPTS.keys())
        )

    @mcp.tool()
    def write_draft(filename: str, content: str, skip_validation: bool = False) -> str:
        """
        Create a draft file with automatic citation formatting.
        Use (PMID:123456) or [PMID:123456] in content to insert citations.
        
        ⚠️ REQUIRES: Valid concept.md with novelty check passed.
        
        This tool enforces concept validation before creating paper drafts.
        The validation ensures:
        - 🔒 NOVELTY STATEMENT is defined and scored 75+
        - 🔒 KEY SELLING POINTS has at least 3 points
        
        Exception: Writing to concept.md itself does not require validation.
        
        Args:
            filename: Name of the file (e.g., "draft.md").
            content: The text content with citation placeholders.
            skip_validation: For internal use only. Do not set to True.
        """
        # Skip validation for concept.md files (they're being created/edited)
        is_concept_file = "concept" in filename.lower()
        
        if not skip_validation and not is_concept_file:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                return message
        
        try:
            path = drafter.create_draft(filename, content)
            
            # Add reminder about protected content
            reminder = ""
            if not is_concept_file:
                reminder = (
                    "\n\n📝 **Protected Content Reminder:**\n"
                    "- 🔒 NOVELTY STATEMENT must be reflected in Introduction\n"
                    "- 🔒 KEY SELLING POINTS must be emphasized in Discussion\n"
                    "- Ask user before modifying any protected content"
                )
            
            return f"Draft created successfully at: {path}{reminder}"
        except Exception as e:
            return f"Error creating draft: {str(e)}"

    @mcp.tool()
    def insert_citation(filename: str, target_text: str, pmid: str) -> str:
        """
        Insert a citation into an existing draft.
        
        Args:
            filename: The draft file name.
            target_text: The text segment after which the citation should be inserted.
            pmid: The PubMed ID to cite.
        """
        try:
            path = drafter.insert_citation(filename, target_text, pmid)
            return f"Citation inserted successfully in: {path}"
        except Exception as e:
            return f"Error inserting citation: {str(e)}"

    @mcp.tool()
    def list_drafts() -> str:
        """
        List all available draft files in the drafts/ directory.
        Use this to see what drafts are available for export.
        
        Returns:
            List of draft files with their word counts.
        """
        drafts_dir = "drafts"
        if not os.path.exists(drafts_dir):
            return "📁 No drafts/ directory found. Create drafts using write_draft tool first."
        
        drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
        
        if not drafts:
            return "📁 No draft files found in drafts/ directory."
        
        output = "📄 **Available Drafts**\n\n"
        output += "| # | Filename | Sections | Total Words |\n"
        output += "|---|----------|----------|-------------|\n"
        
        for i, draft_file in enumerate(sorted(drafts), 1):
            draft_path = os.path.join(drafts_dir, draft_file)
            try:
                with open(draft_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                sections = len(re.findall(r'^#+\s+', content, re.MULTILINE))
                words = len([w for w in content.split() if w.strip()])
                
                output += f"| {i} | {draft_file} | {sections} | {words} |\n"
            except Exception:
                output += f"| {i} | {draft_file} | Error | - |\n"
        
        return output

    @mcp.tool()
    def read_draft(filename: str) -> str:
        """
        Read a draft file and return its structure and content.
        Use this to understand what content needs to be placed into the template.
        
        Args:
            filename: Path to the markdown draft file.
            
        Returns:
            Draft content organized by sections with word counts.
        """
        if not os.path.isabs(filename):
            filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"Error: Draft file not found: {filename}"
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sections = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('#'):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content)
                    section_name = re.sub(r'^#+\s*\d*\.?\s*', '', line).strip()
                    current_section = section_name if section_name else "Untitled"
                    current_content = []
                elif current_section:
                    current_content.append(line)
            
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            
            # Format output
            output = f"📝 **Draft: {os.path.basename(filename)}**\n\n"
            output += "| Section | Word Count | Preview |\n"
            output += "|---------|------------|----------|\n"
            
            for sec_name, sec_content in sections.items():
                words = len([w for w in sec_content.split() if w.strip()])
                preview = sec_content[:50].replace('\n', ' ').strip() + "..."
                output += f"| {sec_name} | {words} | {preview} |\n"
            
            output += "\n---\n\n"
            output += "**Full Content by Section:**\n\n"
            
            for sec_name, sec_content in sections.items():
                output += f"### {sec_name}\n\n"
                output += sec_content.strip()[:500]
                if len(sec_content) > 500:
                    output += f"\n\n*... ({len(sec_content)} characters total)*"
                output += "\n\n"
            
            return output
        except Exception as e:
            return f"Error reading draft: {str(e)}"

    @mcp.tool()
    def count_words(filename: str, section: str = None) -> str:
        """
        Count words in a draft file. Essential for meeting journal word limits.
        
        Args:
            filename: Path to the markdown draft file (e.g., "drafts/draft.md").
            section: Optional specific section to count (e.g., "Introduction", "Abstract").
                    If not specified, counts all sections.
        
        Returns:
            Word count statistics including total words, words per section, and character count.
        """
        if not os.path.isabs(filename):
            filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"Error: File not found: {filename}"
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse sections
            sections = {}
            current_section = "Header"
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('#'):
                    if current_content:
                        sections[current_section] = '\n'.join(current_content)
                    section_name = re.sub(r'^#+\s*\d*\.?\s*', '', line).strip()
                    current_section = section_name if section_name else "Untitled"
                    current_content = []
                else:
                    current_content.append(line)
            
            if current_content:
                sections[current_section] = '\n'.join(current_content)
            
            def count_text_words(text: str) -> int:
                text = re.sub(r'\[.*?\]\(.*?\)', '', text)
                text = re.sub(r'[*_`#\[\]()]', '', text)
                text = re.sub(r'\s+', ' ', text)
                words = [w for w in text.split() if w.strip()]
                return len(words)
            
            if section:
                matched = None
                for sec_name in sections:
                    if section.lower() in sec_name.lower():
                        matched = sec_name
                        break
                
                if matched:
                    word_count = count_text_words(sections[matched])
                    char_count = len(sections[matched].replace('\n', '').replace(' ', ''))
                    return f"📊 Word Count for '{matched}':\n" \
                           f"  Words: {word_count}\n" \
                           f"  Characters (no spaces): {char_count}"
                else:
                    return f"Section '{section}' not found. Available sections: {', '.join(sections.keys())}"
            else:
                output = "📊 **Word Count Summary**\n\n"
                output += "| Section | Words | Characters |\n"
                output += "|---------|-------|------------|\n"
                
                total_words = 0
                total_chars = 0
                
                for sec_name, sec_content in sections.items():
                    if sec_name == "References":
                        continue
                    words = count_text_words(sec_content)
                    chars = len(sec_content.replace('\n', '').replace(' ', ''))
                    total_words += words
                    total_chars += chars
                    output += f"| {sec_name[:30]} | {words} | {chars} |\n"
                
                output += f"| **Total** | **{total_words}** | **{total_chars}** |\n\n"
                output += f"📝 Total word count (excluding References): **{total_words}** words"
                
                return output
                
        except Exception as e:
            return f"Error counting words: {str(e)}"

    @mcp.tool()
    def validate_concept(filename: str, run_novelty_check: bool = True) -> str:
        """
        Validate a concept file before proceeding to draft writing.
        
        This tool performs comprehensive validation including:
        1. Structural validation - Required sections present
        2. Novelty evaluation - LLM-based scoring (3 rounds, 75+ threshold)
        3. Consistency check - Alignment between sections
        
        The novelty check uses 3 evaluation rounds. All rounds must score
        75+ out of 100 for the concept to pass. This ensures the NOVELTY
        STATEMENT truly describes novel contributions.
        
        Args:
            filename: Path to the concept file (e.g., "concept.md").
            run_novelty_check: Whether to run LLM-based novelty scoring (default: True).
        
        Returns:
            Validation report with checklist status, novelty scores, and suggestions.
        """
        # Resolve path
        if not os.path.isabs(filename):
            # Try project concept.md first, then drafts/
            from med_paper_assistant.infrastructure.persistence import get_project_manager
            pm = get_project_manager()
            current = pm.get_current_project()
            
            if current.get("project_path"):
                project_concept = os.path.join(current["project_path"], "concept.md")
                if os.path.exists(project_concept) and filename in ["concept.md", project_concept]:
                    filename = project_concept
                else:
                    filename = os.path.join("drafts", filename)
            else:
                filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"❌ Error: Concept file not found: {filename}\n\n" \
                   f"Use `/mdpaper.concept` to create a concept file first."
        
        try:
            # Use the ConceptValidator service
            result = _concept_validator.validate(
                filename,
                run_novelty_check=run_novelty_check,
                run_consistency_check=True,
                run_citation_check=False,
                force_refresh=True
            )
            
            # Generate report
            return _concept_validator.generate_report(result)
            
        except Exception as e:
            return f"❌ Error validating concept: {str(e)}"

    @mcp.tool()
    def validate_concept_quick(filename: str) -> str:
        """
        Quick structural validation without LLM calls.
        
        Use this for fast checks when you just need to verify sections exist.
        For full validation with novelty scoring, use validate_concept.
        
        Args:
            filename: Path to the concept file.
        
        Returns:
            Quick validation report (structure only).
        """
        if not os.path.isabs(filename):
            from med_paper_assistant.infrastructure.persistence import get_project_manager
            pm = get_project_manager()
            current = pm.get_current_project()
            
            if current.get("project_path"):
                project_concept = os.path.join(current["project_path"], "concept.md")
                if os.path.exists(project_concept) and filename in ["concept.md", project_concept]:
                    filename = project_concept
                else:
                    filename = os.path.join("drafts", filename)
            else:
                filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"❌ Error: Concept file not found: {filename}"
        
        try:
            result = _concept_validator.validate_structure_only(filename)
            return _concept_validator.generate_report(result)
        except Exception as e:
            return f"❌ Error: {str(e)}"
