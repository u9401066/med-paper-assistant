"""
Export Tools Module

Tools for Word document export using the 8-step workflow:
1. read_template - Get template structure
2. read_draft - Get draft content  
3. start_document_session - Begin editing session
4. insert_section - Insert content (Agent decides where)
5. verify_document - Check content placement
6. check_word_limits - Verify word limits
7. save_document - Final output

Also includes the legacy export_word tool for simple exports.
"""

import os
import json
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter


# Global state for document editing sessions
_active_documents = {}


def get_active_documents() -> dict:
    """Get the active document sessions dictionary."""
    return _active_documents


def register_export_tools(
    mcp: FastMCP, 
    formatter: Formatter,
    template_reader: TemplateReader,
    word_writer: WordWriter
):
    """Register all export-related tools with the MCP server."""
    
    # ============================================================
    # LEGACY EXPORT
    # ============================================================
    
    @mcp.tool()
    def export_word(draft_filename: str, template_name: str, output_filename: str) -> str:
        """
        [LEGACY] Simple export - use the new workflow for better control.
        
        Export a markdown draft to a Word document using a template.
        
        Args:
            draft_filename: Path to the markdown draft file (e.g., "drafts/draft.md").
            template_name: Name of the template file in templates/ or full path.
            output_filename: Path to save the output file (e.g., "results/paper.docx").
        """
        try:
            path = formatter.apply_template(draft_filename, template_name, output_filename)
            return f"Word document exported successfully to: {path}"
        except Exception as e:
            return f"Error exporting Word document: {str(e)}"

    # ============================================================
    # NEW WORKFLOW: Template-based Word Export with Agent Control
    # ============================================================

    @mcp.tool()
    def list_templates() -> str:
        """
        List all available Word templates.
        
        Returns:
            List of template files in the templates/ directory.
        """
        try:
            templates = template_reader.list_templates()
            if not templates:
                return "No templates found in templates/ directory."
            
            output = "📄 **Available Templates**\n\n"
            for t in templates:
                output += f"- {t}\n"
            return output
        except Exception as e:
            return f"Error listing templates: {str(e)}"

    @mcp.tool()
    def read_template(template_name: str) -> str:
        """
        Read a Word template and get its structure.
        Use this FIRST to understand what sections the template has and their word limits.
        
        Args:
            template_name: Name of the template file (e.g., "Type of the Paper.docx").
            
        Returns:
            Template structure including sections, styles, and word limits.
        """
        try:
            return template_reader.get_template_summary(template_name)
        except Exception as e:
            return f"Error reading template: {str(e)}"

    @mcp.tool()
    def start_document_session(template_name: str, session_id: str = "default") -> str:
        """
        Start a new document editing session by loading a template.
        This creates an in-memory document that you can modify with insert_section.
        
        Args:
            template_name: Name of the template file.
            session_id: Unique identifier for this editing session (default: "default").
            
        Returns:
            Confirmation and template structure.
        """
        try:
            template_path = os.path.join(template_reader.templates_dir, template_name)
            if not os.path.exists(template_path):
                return f"Error: Template not found: {template_name}"
            
            doc = word_writer.create_document_from_template(template_path)
            _active_documents[session_id] = {
                "doc": doc,
                "template": template_name,
                "modifications": []
            }
            
            structure = template_reader.get_template_summary(template_name)
            
            return f"✅ Document session '{session_id}' started with template: {template_name}\n\n{structure}"
        except Exception as e:
            return f"Error starting session: {str(e)}"

    @mcp.tool()
    def insert_section(
        session_id: str, 
        section_name: str, 
        content: str, 
        mode: str = "replace"
    ) -> str:
        """
        Insert content into a specific section of the active document.
        YOU (the Agent) decide which section to insert into based on your analysis.
        
        Args:
            session_id: The document session ID (from start_document_session).
            section_name: Target section name (e.g., "Introduction", "Methods").
            content: The text content to insert (can include multiple paragraphs).
            mode: "replace" (clear existing then insert) or "append" (add to existing).
            
        Returns:
            Confirmation with word count for the section.
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'. Use start_document_session first."
        
        try:
            session = _active_documents[session_id]
            doc = session["doc"]
            
            paragraphs = [p for p in content.split('\n') if p.strip()]
            clear_existing = (mode == "replace")
            
            count = word_writer.insert_content_in_section(
                doc, section_name, paragraphs, clear_existing=clear_existing
            )
            
            session["modifications"].append({
                "section": section_name,
                "paragraphs": count,
                "mode": mode
            })
            
            word_count = word_writer.count_words_in_section(doc, section_name)
            
            return f"✅ Inserted {count} paragraphs into '{section_name}' ({word_count} words)"
        except Exception as e:
            return f"Error inserting section: {str(e)}"

    @mcp.tool()
    def verify_document(session_id: str) -> str:
        """
        Get a summary of the current document state for verification.
        Use this to check that all content was inserted correctly.
        
        Args:
            session_id: The document session ID.
            
        Returns:
            Document summary with all sections and word counts.
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'."
        
        try:
            session = _active_documents[session_id]
            doc = session["doc"]
            
            counts = word_writer.get_all_word_counts(doc)
            
            output = f"📊 **Document Verification: {session['template']}**\n\n"
            output += "| Section | Word Count |\n"
            output += "|---------|------------|\n"
            
            total = 0
            for section, count in counts.items():
                output += f"| {section} | {count} |\n"
                total += count
            
            output += f"| **TOTAL** | **{total}** |\n\n"
            
            output += f"**Modifications made:** {len(session['modifications'])}\n"
            for mod in session["modifications"]:
                output += f"- {mod['section']}: {mod['paragraphs']} paragraphs ({mod['mode']})\n"
            
            return output
        except Exception as e:
            return f"Error verifying document: {str(e)}"

    @mcp.tool()
    def check_word_limits(session_id: str, limits_json: str = None) -> str:
        """
        Check if all sections meet their word limits.
        
        Args:
            session_id: The document session ID.
            limits_json: Optional JSON string with custom limits, 
                        e.g., '{"Introduction": 800, "Abstract": 250}'.
                        If not provided, uses default limits.
            
        Returns:
            Word limit compliance report.
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'."
        
        try:
            session = _active_documents[session_id]
            doc = session["doc"]
            
            counts = word_writer.get_all_word_counts(doc)
            
            # Default limits
            limits = {
                "Abstract": 250,
                "Introduction": 800,
                "Methods": 1500,
                "Materials and Methods": 1500,
                "Results": 1500,
                "Discussion": 1500,
                "Conclusions": 300,
            }
            
            if limits_json:
                custom_limits = json.loads(limits_json)
                limits.update(custom_limits)
            
            output = "📏 **Word Limit Check**\n\n"
            output += "| Section | Words | Limit | Status |\n"
            output += "|---------|-------|-------|--------|\n"
            
            all_ok = True
            for section, count in counts.items():
                limit = None
                for limit_key, limit_val in limits.items():
                    if limit_key.lower() in section.lower() or section.lower() in limit_key.lower():
                        limit = limit_val
                        break
                
                if limit:
                    if count <= limit:
                        status = "✅"
                    else:
                        status = f"⚠️ Over by {count - limit}"
                        all_ok = False
                    output += f"| {section} | {count} | {limit} | {status} |\n"
                else:
                    output += f"| {section} | {count} | - | - |\n"
            
            if all_ok:
                output += "\n✅ **All sections within word limits!**"
            else:
                output += "\n⚠️ **Some sections exceed word limits. Consider revising.**"
            
            return output
        except Exception as e:
            return f"Error checking word limits: {str(e)}"

    @mcp.tool()
    def save_document(session_id: str, output_filename: str) -> str:
        """
        Save the document to a Word file.
        This is the final step after all content has been inserted and verified.
        
        Args:
            session_id: The document session ID.
            output_filename: Path to save the output file (e.g., "results/paper.docx").
            
        Returns:
            Confirmation with file path.
        """
        if session_id not in _active_documents:
            return f"Error: No active session '{session_id}'."
        
        try:
            session = _active_documents[session_id]
            doc = session["doc"]
            
            path = word_writer.save_document(doc, output_filename)
            
            del _active_documents[session_id]
            
            return f"✅ Document saved successfully to: {path}\n\nSession '{session_id}' closed."
        except Exception as e:
            return f"Error saving document: {str(e)}"
