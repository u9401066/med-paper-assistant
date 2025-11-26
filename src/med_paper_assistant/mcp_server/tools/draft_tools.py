"""
Draft Tools Module

Tools for creating and editing paper drafts, section templates, and word counting.
"""

import os
import re
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.core.drafter import Drafter


def register_draft_tools(mcp: FastMCP, drafter: Drafter):
    """Register all draft-related tools with the MCP server."""
    
    @mcp.tool()
    def draft_section(topic: str, notes: str) -> str:
        """
        Draft a section of a medical paper based on notes.
        
        Args:
            topic: The topic of the section (e.g., "Introduction").
            notes: Raw notes or bullet points to convert into text.
        """
        return f"Drafting section '{topic}' based on notes..."

    @mcp.tool()
    def get_section_template(section: str) -> str:
        """
        Get writing guidelines for a specific paper section.
        
        Args:
            section: "introduction", "methods", "results", "discussion", "abstract"
        """
        from med_paper_assistant.core.prompts import SECTION_PROMPTS
        return SECTION_PROMPTS.get(
            section.lower(), 
            "Section not found. Available: " + ", ".join(SECTION_PROMPTS.keys())
        )

    @mcp.tool()
    def write_draft(filename: str, content: str) -> str:
        """
        Create a draft file with automatic citation formatting.
        Use (PMID:123456) or [PMID:123456] in content to insert citations.
        
        Args:
            filename: Name of the file (e.g., "draft.md").
            content: The text content with citation placeholders.
        """
        try:
            path = drafter.create_draft(filename, content)
            return f"Draft created successfully at: {path}"
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
    def validate_concept(filename: str) -> str:
        """
        Validate a concept file before proceeding to draft writing.
        Checks that all required sections are complete and protected content is defined.
        
        Args:
            filename: Path to the concept file (e.g., "concept_study.md").
        
        Returns:
            Validation report with checklist status and any warnings.
        """
        if not os.path.isabs(filename):
            filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"❌ Error: Concept file not found: {filename}\n\n" \
                   f"Use `/mdpaper.concept` to create a concept file first."
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validation checklist
            checks = {
                "novelty_statement": {
                    "name": "🔒 NOVELTY STATEMENT",
                    "required": True,
                    "patterns": [r"🔒\s*NOVELTY STATEMENT", r"What is new\?", r"novelty"],
                    "found": False,
                    "has_content": False
                },
                "selling_points": {
                    "name": "🔒 KEY SELLING POINTS",
                    "required": True,
                    "patterns": [r"🔒\s*KEY SELLING POINTS", r"Selling Point \d"],
                    "found": False,
                    "has_content": False,
                    "count": 0
                },
                "background": {
                    "name": "📝 Background",
                    "required": False,
                    "patterns": [r"📝\s*Background", r"##\s*Background"],
                    "found": False,
                    "has_content": False
                },
                "research_gap": {
                    "name": "📝 Research Gap",
                    "required": False,
                    "patterns": [r"📝\s*Research Gap", r"##\s*Research Gap"],
                    "found": False,
                    "has_content": False
                },
                "research_question": {
                    "name": "📝 Research Question/Hypothesis",
                    "required": False,
                    "patterns": [r"Research Question", r"Hypothesis"],
                    "found": False,
                    "has_content": False
                },
                "methods": {
                    "name": "📝 Methods Overview",
                    "required": False,
                    "patterns": [r"📝\s*Methods", r"##\s*Methods", r"Study Design"],
                    "found": False,
                    "has_content": False
                },
                "expected_outcomes": {
                    "name": "📝 Expected Outcomes",
                    "required": False,
                    "patterns": [r"📝\s*Expected", r"##\s*Expected Outcomes"],
                    "found": False,
                    "has_content": False
                }
            }
            
            # Check each section
            lines = content.split('\n')
            current_section = None
            section_content = []
            
            for i, line in enumerate(lines):
                # Check for section headers
                for key, check in checks.items():
                    for pattern in check["patterns"]:
                        if re.search(pattern, line, re.IGNORECASE):
                            check["found"] = True
                            current_section = key
                            section_content = []
                            break
                
                # Collect content for current section
                if current_section and not line.startswith('#') and not line.startswith('🔒') and not line.startswith('📝'):
                    stripped = line.strip()
                    if stripped and not stripped.startswith('<!--') and not stripped.startswith('>'):
                        if not stripped.startswith('[') or ']' not in stripped:  # Not a placeholder
                            section_content.append(stripped)
                            checks[current_section]["has_content"] = True
            
            # Count selling points
            selling_points_matches = re.findall(r'Selling Point \d+.*?:.*?\S', content, re.IGNORECASE)
            checks["selling_points"]["count"] = len(selling_points_matches)
            if checks["selling_points"]["count"] >= 3:
                checks["selling_points"]["has_content"] = True
            
            # Generate report
            output = f"📋 **Concept Validation Report**\n"
            output += f"📄 File: `{os.path.basename(filename)}`\n\n"
            
            output += "## 🔒 Protected Sections (Required)\n\n"
            output += "| Section | Found | Has Content | Status |\n"
            output += "|---------|-------|-------------|--------|\n"
            
            required_pass = True
            for key in ["novelty_statement", "selling_points"]:
                check = checks[key]
                found = "✅" if check["found"] else "❌"
                has_content = "✅" if check["has_content"] else "❌"
                
                if check["found"] and check["has_content"]:
                    status = "✅ PASS"
                else:
                    status = "❌ MISSING"
                    required_pass = False
                
                extra = ""
                if key == "selling_points":
                    extra = f" ({check['count']} points)"
                
                output += f"| {check['name']}{extra} | {found} | {has_content} | {status} |\n"
            
            output += "\n## 📝 Editable Sections (Optional)\n\n"
            output += "| Section | Found | Has Content |\n"
            output += "|---------|-------|-------------|\n"
            
            for key in ["background", "research_gap", "research_question", "methods", "expected_outcomes"]:
                check = checks[key]
                found = "✅" if check["found"] else "⚪"
                has_content = "✅" if check["has_content"] else "⚪"
                output += f"| {check['name']} | {found} | {has_content} |\n"
            
            # Final verdict
            output += "\n---\n\n"
            
            if required_pass:
                output += "## ✅ VALIDATION PASSED\n\n"
                output += "The concept file has all required protected sections.\n"
                output += "You may proceed with `/mdpaper.draft` to write the paper.\n\n"
                output += "**Remember:**\n"
                output += "- 🔒 Protected content must be preserved in the final paper\n"
                output += "- Ask user before modifying any 🔒 sections\n"
            else:
                output += "## ❌ VALIDATION FAILED\n\n"
                output += "**Missing required sections:**\n"
                
                if not checks["novelty_statement"]["found"] or not checks["novelty_statement"]["has_content"]:
                    output += "- 🔒 NOVELTY STATEMENT is missing or empty\n"
                    output += "  → What makes this research unique?\n"
                
                if checks["selling_points"]["count"] < 3:
                    output += f"- 🔒 KEY SELLING POINTS has only {checks['selling_points']['count']} points (need at least 3)\n"
                    output += "  → What are the main contributions?\n"
                
                output += "\n**Action Required:**\n"
                output += "Please complete the missing sections before proceeding to draft writing.\n"
                output += "Use `write_draft` to update the concept file.\n"
            
            return output
            
        except Exception as e:
            return f"❌ Error validating concept: {str(e)}"
