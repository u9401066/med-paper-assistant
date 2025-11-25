from mcp.server.fastmcp import FastMCP
from med_paper_assistant.core.search import LiteratureSearcher, SearchStrategy
from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.drafter import Drafter, CitationStyle
from med_paper_assistant.core.analyzer import Analyzer
from med_paper_assistant.core.formatter import Formatter
from med_paper_assistant.core.template_reader import TemplateReader
from med_paper_assistant.core.word_writer import WordWriter, InsertInstruction
from med_paper_assistant.core.logger import setup_logger
from med_paper_assistant.core.strategy_manager import StrategyManager
import json
import os

# Setup Logger
logger = setup_logger()

# Initialize Core Modules
searcher = LiteratureSearcher(email="your.email@example.com")
analyzer = Analyzer()
ref_manager = ReferenceManager(searcher)
drafter = Drafter(ref_manager)
formatter = Formatter()
template_reader = TemplateReader()
word_writer = WordWriter()
strategy_manager = StrategyManager()

# Server Instructions (sent to agent, not shown to user)
SERVER_INSTRUCTIONS = """
You are MedPaper Assistant, helping researchers write medical papers.

WORKFLOW FOR EXPORTING TO WORD:
1. read_template - Get template structure (sections, word limits)
2. read_draft - Get draft content 
3. YOU (Agent) decide: Which draft sections map to which template sections
4. insert_section - Insert content into specific sections (Agent specifies where)
5. verify_document - Compare result with original draft
6. YOU (Agent) review: Check for missing content, logic, flow
7. check_word_limits - Verify all sections meet word limits
8. save_document - Final output

AVAILABLE PROMPTS:
- concept: Develop research concept
- strategy: Configure literature search strategy
- draft: Write paper draft
- analysis: Analyze data
- clarify: Refine content
- format: Export draft to Word (uses the 8-step workflow above)

KEY TOOLS: 
- search_literature, save_reference, write_draft
- read_template, insert_section, verify_document, check_word_limits, save_document
- analyze_dataset, generate_table_one, create_plot
- count_words (for drafts)
"""

mcp = FastMCP("MedPaperAssistant", instructions=SERVER_INSTRUCTIONS)

def format_results(results):
    if not results:
        return "No results found."
        
    if "error" in results[0]:
        return f"Error searching PubMed: {results[0]['error']}"
        
    formatted_output = f"Found {len(results)} results:\n\n"
    for i, paper in enumerate(results, 1):
        formatted_output += f"{i}. {paper['title']}\n"
        formatted_output += f"   Authors: {', '.join(paper['authors'][:3])}{' et al.' if len(paper['authors']) > 3 else ''}\n"
        formatted_output += f"   Journal: {paper['journal']} ({paper['year']})\n"
        formatted_output += f"   PMID: {paper['pmid']}\n"
        formatted_output += f"   Abstract: {paper['abstract'][:200]}...\n\n"
        
    return formatted_output

@mcp.tool()
def configure_search_strategy(criteria_json: str) -> str:
    """
    Save a structured search strategy.
    
    Args:
        criteria_json: JSON string with keys: keywords (list), exclusions (list), article_types (list), min_sample_size (int), date_range (str).
    """
    try:
        criteria = json.loads(criteria_json)
        return strategy_manager.save_strategy(criteria)
    except Exception as e:
        return f"Error configuring strategy: {str(e)}"

@mcp.tool()
def get_search_strategy() -> str:
    """Get the currently saved search strategy."""
    strategy = strategy_manager.load_strategy()
    if not strategy:
        return "No strategy saved."
    return json.dumps(strategy.dict(), indent=2)

@mcp.tool()
def search_literature(query: str = "", limit: int = 5, min_year: int = None, max_year: int = None, article_type: str = None, strategy: str = "relevance", use_saved_strategy: bool = False) -> str:
    """
    Search for medical literature based on a query using PubMed.
    
    Args:
        query: The search query (e.g., "diabetes treatment guidelines"). Required if use_saved_strategy is False.
        limit: The maximum number of results to return.
        min_year: Optional minimum publication year (e.g., 2020).
        max_year: Optional maximum publication year.
        article_type: Optional article type (e.g., "Review", "Clinical Trial", "Meta-Analysis").
        strategy: Search strategy ("recent", "most_cited", "relevance", "impact", "agent_decided"). Default is "relevance".
        use_saved_strategy: If True, uses the criteria from configure_search_strategy.
    """
    logger.info(f"Searching literature: query='{query}', limit={limit}, strategy='{strategy}', use_saved_strategy={use_saved_strategy}")
    try:
        min_sample_size = None
        
        if use_saved_strategy:
            saved_criteria = strategy_manager.load_strategy()
            if saved_criteria:
                # Build query from saved criteria
                query = strategy_manager.build_pubmed_query(saved_criteria)
                min_sample_size = saved_criteria.min_sample_size
                logger.info(f"Using saved strategy. Generated query: {query}")
            else:
                return "Error: No saved strategy found. Please use configure_search_strategy first."
        
        if not query:
            return "Error: Query is required unless use_saved_strategy is True and a strategy is saved."

        # Perform search
        # Note: We pass limit*2 to searcher to allow for post-filtering, but searcher.search logic handles retmax.
        # We might need to adjust searcher.search to return more if we are filtering.
        # For now, let's rely on searcher.search returning what it finds.
        results = searcher.search(query, limit, min_year, max_year, article_type, strategy)
        
        # Apply sample size filter if needed
        if min_sample_size:
            results = searcher.filter_results(results, min_sample_size)
            
        return format_results(results[:limit])
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Error: {e}"

@mcp.tool()
def save_reference(pmid: str) -> str:
    """
    Save a reference to the local library.
    
    Args:
        pmid: The PubMed ID of the article to save.
    """
    return ref_manager.save_reference(pmid)

@mcp.tool()
def list_saved_references() -> str:
    """
    List all saved references in the local library.
    """
    refs = ref_manager.list_references()
    if not refs:
        return "No references saved."
    return f"Saved references (PMIDs): {', '.join(refs)}"

@mcp.tool()
def draft_section(topic: str, notes: str) -> str:
    """
    Draft a section of a medical paper based on notes.
    
    Args:
        topic: The topic of the section (e.g., "Introduction").
        notes: Raw notes or bullet points to convert into text.
    """
    # Placeholder for drafting logic
    return f"Drafting section '{topic}' based on notes..."

@mcp.tool()
def set_citation_style(style: str) -> str:
    """
    Set the citation style for the current session.
    
    Args:
        style: Citation style ("vancouver", "apa", "harvard", "nature", "ama").
    """
    try:
        drafter.set_citation_style(style)
        return f"Citation style set to: {style}"
    except ValueError as e:
        return str(e)

@mcp.tool()
def format_references(pmids: str, style: str = "vancouver", journal: str = None) -> str:
    """
    Format a list of references according to a specific citation style or journal format.
    Use this to get properly formatted references for the References section.
    
    Args:
        pmids: Comma-separated list of PMIDs (e.g., "31645286,28924371,33160604").
        style: Citation style ("vancouver", "apa", "harvard", "nature", "ama", "mdpi", "nlm").
               Default is "vancouver".
        journal: Optional journal name for journal-specific formatting 
                (e.g., "sensors", "lancet", "bja", "anesthesiology").
                If provided, overrides the style parameter.
    
    Returns:
        Formatted reference list ready for insertion into the References section.
    """
    from med_paper_assistant.core.drafter import JOURNAL_CITATION_CONFIGS
    
    pmid_list = [p.strip() for p in pmids.split(",") if p.strip()]
    
    if not pmid_list:
        return "Error: No PMIDs provided."
    
    # Style-specific configurations
    STYLE_CONFIGS = {
        "vancouver": {"author_format": "last_initials", "max_authors": 6, "et_al_threshold": 3},
        "apa": {"author_format": "last_comma_initials", "max_authors": 7, "et_al_threshold": 6},
        "harvard": {"author_format": "last_comma_initials", "max_authors": 3, "et_al_threshold": 3},
        "nature": {"author_format": "last_initials", "max_authors": 5, "et_al_threshold": 5},
        "ama": {"author_format": "last_initials", "max_authors": 6, "et_al_threshold": 6},
        "mdpi": {"author_format": "last_comma_initials", "max_authors": 6, "et_al_threshold": 6},
        "nlm": {"author_format": "last_initials", "max_authors": 6, "et_al_threshold": 6},
    }
    
    # Get configuration
    if journal and journal.lower() in JOURNAL_CITATION_CONFIGS:
        config = JOURNAL_CITATION_CONFIGS[journal.lower()]
        style_name = f"{journal.upper()} format"
    else:
        config = STYLE_CONFIGS.get(style.lower(), STYLE_CONFIGS["vancouver"])
        style_name = style.upper()
    
    output = f"📚 **Formatted References ({style_name})**\n\n"
    
    for i, pmid in enumerate(pmid_list, 1):
        metadata = ref_manager.get_metadata(pmid)
        
        if not metadata:
            output += f"[{i}] PMID:{pmid} - Reference not found in local library. Use save_reference first.\n"
            continue
        
        # Format authors based on config
        authors = metadata.get('authors', [])
        author_format = config.get('author_format', 'full')
        max_authors = config.get('max_authors', 6)
        et_al_threshold = config.get('et_al_threshold', 3)
        
        formatted_authors = _format_authors(authors, author_format, max_authors, et_al_threshold)
        
        # Build reference string
        title = metadata.get('title', 'Unknown Title').rstrip('.')  # Remove trailing period
        journal_name = metadata.get('journal', 'Unknown Journal')
        year = metadata.get('year', 'Unknown')
        volume = metadata.get('volume', '')
        pages = metadata.get('pages', '')
        
        # Helper function to add separator after authors
        def author_separator(authors_text):
            """Add appropriate separator after author list."""
            # Check if already ends with punctuation
            if authors_text.endswith('.') or authors_text.endswith(','):
                return authors_text + " "  # already has punctuation
            else:
                return authors_text + ". "  # add period and space
        
        # Build reference string with proper punctuation
        author_block = author_separator(formatted_authors)
        
        # Use template format or style-specific format
        if style.lower() == "vancouver" or (journal and config.get('style') == 'vancouver'):
            ref_str = f"[{i}] {author_block}{title}. {journal_name} ({year})."
            if volume:
                ref_str = f"[{i}] {author_block}{title}. {journal_name} {year}; {volume}"
                if pages:
                    ref_str += f": {pages}"
                ref_str += "."
        elif style.lower() == "apa":
            ref_str = f"{formatted_authors} ({year}). {title}. *{journal_name}*"
            if volume:
                ref_str += f", {volume}"
                if pages:
                    ref_str += f", {pages}"
            ref_str += "."
        elif style.lower() == "harvard":
            ref_str = f"{formatted_authors} ({year}) '{title}', *{journal_name}*"
            if volume:
                ref_str += f", vol. {volume}"
                if pages:
                    ref_str += f", pp. {pages}"
            ref_str += "."
        elif style.lower() == "nature" or style.lower() == "ama":
            ref_str = f"{i}. {author_block}{title}. {journal_name}"
            if volume:
                ref_str += f" {volume}"
                if pages:
                    ref_str += f", {pages}"
            ref_str += f" ({year})."
        elif style.lower() == "mdpi":
            ref_str = f"{i}. {author_block}{title}. *{journal_name}* **{year}**"
            if volume:
                ref_str += f", *{volume}*"
                if pages:
                    ref_str += f", {pages}"
            ref_str += "."
        else:
            ref_str = f"[{i}] {author_block}{title}. {journal_name} ({year}). PMID:{pmid}."
        
        output += ref_str + "\n"
    
    output += f"\n*Total: {len(pmid_list)} references*"
    return output


def _format_authors(authors: list, format_type: str, max_authors: int, et_al_threshold: int) -> str:
    """Helper function to format author names according to style.
    
    PubMed returns author names as "Lastname Firstname" (e.g., "Cho Sang-Hyeon").
    """
    if not authors:
        return "Unknown Author"
    
    # Truncate if too many authors
    use_et_al = len(authors) > et_al_threshold
    display_authors = authors[:max_authors] if not use_et_al else authors[:et_al_threshold]
    
    formatted = []
    for author in display_authors:
        # PubMed format: "Lastname Firstname" or "Lastname First-Middle" or "Lastname F"
        parts = author.split()
        if len(parts) >= 2:
            # First part is last name, rest are first/middle names
            last_name = parts[0]
            first_parts = parts[1:]
            
            if format_type == "last_initials":
                # "Cho SH" - Last name + initials without space
                initials = "".join([p[0].upper() for p in first_parts if p])
                formatted.append(f"{last_name} {initials}")
            elif format_type == "last_initials_space":
                # "Cho S H" - Last name + initials with space
                initials = " ".join([p[0].upper() for p in first_parts if p])
                formatted.append(f"{last_name} {initials}")
            elif format_type == "last_comma_initials":
                # "Cho, S.H." - Last name, comma, initials with dots
                initials = ".".join([p[0].upper() for p in first_parts if p]) + "."
                formatted.append(f"{last_name}, {initials}")
            elif format_type == "initials_last":
                # "S.H. Cho" - Initials first, then last name
                initials = ".".join([p[0].upper() for p in first_parts if p]) + "."
                formatted.append(f"{initials} {last_name}")
            else:
                # "full" - use as-is
                formatted.append(author)
        else:
            formatted.append(author)
    
    # Join authors
    if len(formatted) == 1:
        result = formatted[0]
    elif len(formatted) == 2:
        result = f"{formatted[0]}, {formatted[1]}"
    else:
        result = ", ".join(formatted)
    
    if use_et_al:
        result += ", et al."
    
    return result

@mcp.tool()
def search_local_references(query: str) -> str:
    """
    Search within saved local references by keyword.
    
    Args:
        query: Keyword to search in titles and abstracts.
    """
    results = ref_manager.search_local(query)
    
    if not results:
        return f"No local references found matching '{query}'"
    
    output = f"Found {len(results)} matching references:\n"
    for meta in results:
        output += f"- PMID:{meta.get('pmid')} | {meta.get('title', 'Unknown')}\n"
        
    return output

@mcp.tool()
def get_section_template(section: str) -> str:
    """
    Get writing guidelines for a specific paper section.
    
    Args:
        section: "introduction", "methods", "results", "discussion", "abstract"
    """
    from med_paper_assistant.core.prompts import SECTION_PROMPTS
    return SECTION_PROMPTS.get(section.lower(), "Section not found. Available: " + ", ".join(SECTION_PROMPTS.keys()))

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
def analyze_dataset(filename: str) -> str:
    """
    Analyze a dataset and return descriptive statistics.
    
    Args:
        filename: Name of the CSV file in the data/ directory.
    """
    try:
        return analyzer.describe_data(filename)
    except Exception as e:
        return f"Error analyzing data: {str(e)}"

@mcp.tool()
def generate_table_one(
    filename: str,
    group_col: str,
    continuous_cols: str,
    categorical_cols: str,
    output_name: str = None
) -> str:
    """
    Generate Table 1 (baseline characteristics) for medical papers.
    
    This creates a standard baseline characteristics table showing patient
    demographics stratified by treatment/study groups with statistical tests.
    
    Args:
        filename: Name of the CSV file in the data/ directory.
        group_col: Column name for grouping (e.g., "treatment", "group").
        continuous_cols: Comma-separated continuous variable names (e.g., "age,weight,height").
        categorical_cols: Comma-separated categorical variable names (e.g., "sex,diabetes,smoking").
        output_name: Optional output filename for the table.
        
    Returns:
        Markdown formatted Table 1 with p-values.
    """
    try:
        # Parse comma-separated column names
        cont_cols = [c.strip() for c in continuous_cols.split(",") if c.strip()]
        cat_cols = [c.strip() for c in categorical_cols.split(",") if c.strip()]
        
        return analyzer.generate_table_one(
            filename=filename,
            group_col=group_col,
            continuous_cols=cont_cols,
            categorical_cols=cat_cols,
            output_name=output_name
        )
    except Exception as e:
        logger.error(f"Error generating Table 1: {e}")
        return f"Error generating Table 1: {str(e)}"

@mcp.tool()
def run_statistical_test(filename: str, test_type: str, col1: str, col2: str = None) -> str:
    """
    Run a statistical test on the dataset.
    
    Args:
        filename: Name of the CSV file.
        test_type: Type of test ("t-test", "correlation").
        col1: First column name.
        col2: Second column name (optional depending on test).
    """
    try:
        return analyzer.run_statistical_test(filename, test_type, col1, col2)
    except Exception as e:
        return f"Error running test: {str(e)}"

@mcp.tool()
def create_plot(filename: str, plot_type: str, x_col: str, y_col: str) -> str:
    """
    Create a plot from the dataset.
    
    Args:
        filename: Name of the CSV file.
        plot_type: Type of plot ("scatter", "bar", "box", "histogram").
        x_col: Column for X-axis.
        y_col: Column for Y-axis.
    """
    try:
        path = analyzer.create_plot(filename, plot_type, x_col, y_col)
        return f"Plot created successfully at: {path}"
    except Exception as e:
        return f"Error creating plot: {str(e)}"

@mcp.tool()
def export_word(draft_filename: str, template_name: str, output_filename: str) -> str:
    """
    [LEGACY] Simple export - use the new workflow (read_template → insert_section → save_document) for better control.
    
    Export a markdown draft to a Word document using a template.
    
    Args:
        draft_filename: Path to the markdown draft file (e.g., "drafts/draft.md").
        template_name: Name of the template file in templates/ (e.g., "sensors.docx") or full path.
        output_filename: Path to save the output file (e.g., "results/paper.docx").
    """
    try:
        # Use Formatter to handle template lookup and export
        path = formatter.apply_template(draft_filename, template_name, output_filename)
        return f"Word document exported successfully to: {path}"
    except Exception as e:
        return f"Error exporting Word document: {str(e)}"

# ============================================================
# NEW WORKFLOW: Template-based Word Export with Agent Control
# ============================================================

# Global state for document editing session
_active_documents = {}

@mcp.tool()
def list_drafts() -> str:
    """
    List all available draft files in the drafts/ directory.
    Use this to see what drafts are available for export.
    
    Returns:
        List of draft files with their word counts.
    """
    import re
    
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
            
            # Count sections (headers)
            sections = len(re.findall(r'^#+\s+', content, re.MULTILINE))
            
            # Count words (rough estimate)
            words = len([w for w in content.split() if w.strip()])
            
            output += f"| {i} | {draft_file} | {sections} | {words} |\n"
        except Exception as e:
            output += f"| {i} | {draft_file} | Error | - |\n"
    
    return output

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
def read_draft(filename: str) -> str:
    """
    Read a draft file and return its structure and content.
    Use this to understand what content needs to be placed into the template.
    
    Args:
        filename: Path to the markdown draft file.
        
    Returns:
        Draft content organized by sections with word counts.
    """
    import re
    
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
        # Resolve template path
        template_path = os.path.join(template_reader.templates_dir, template_name)
        if not os.path.exists(template_path):
            return f"Error: Template not found: {template_name}"
        
        # Load template into memory
        doc = word_writer.create_document_from_template(template_path)
        _active_documents[session_id] = {
            "doc": doc,
            "template": template_name,
            "modifications": []
        }
        
        # Get structure
        structure = template_reader.get_template_summary(template_name)
        
        return f"✅ Document session '{session_id}' started with template: {template_name}\n\n{structure}"
    except Exception as e:
        return f"Error starting session: {str(e)}"

@mcp.tool()
def insert_section(session_id: str, section_name: str, content: str, mode: str = "replace") -> str:
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
        
        # Count words in section
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
        limits_json: Optional JSON string with custom limits, e.g., '{"Introduction": 800, "Abstract": 250}'.
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
        
        # Override with custom limits if provided
        if limits_json:
            custom_limits = json.loads(limits_json)
            limits.update(custom_limits)
        
        output = "📏 **Word Limit Check**\n\n"
        output += "| Section | Words | Limit | Status |\n"
        output += "|---------|-------|-------|--------|\n"
        
        all_ok = True
        for section, count in counts.items():
            # Find matching limit (case-insensitive partial match)
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
        
        # Clean up session
        del _active_documents[session_id]
        
        return f"✅ Document saved successfully to: {path}\n\nSession '{session_id}' closed."
    except Exception as e:
        return f"Error saving document: {str(e)}"

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
    import os
    import re
    
    # Handle relative paths
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
                # Extract section name (remove # and numbers)
                section_name = re.sub(r'^#+\s*\d*\.?\s*', '', line).strip()
                current_section = section_name if section_name else "Untitled"
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        def count_text_words(text: str) -> int:
            # Remove markdown formatting
            text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove links
            text = re.sub(r'[*_`#\[\]()]', '', text)    # Remove markdown chars
            text = re.sub(r'\s+', ' ', text)            # Normalize whitespace
            words = [w for w in text.split() if w.strip()]
            return len(words)
        
        # Count specific section or all
        if section:
            # Find matching section (case-insensitive partial match)
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
            # Count all sections
            output = "📊 **Word Count Summary**\n\n"
            output += "| Section | Words | Characters |\n"
            output += "|---------|-------|------------|\n"
            
            total_words = 0
            total_chars = 0
            
            for sec_name, sec_content in sections.items():
                if sec_name == "References":
                    continue  # Skip references section
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

@mcp.prompt(name="concept", description="Develop research concept")
def mdpaper_concept(topic: str) -> str:
    """Develop a research concept.
    
    Args:
        topic: Your research topic or hypothesis
    """
    return f"Help me develop a research concept about: {topic}"

@mcp.prompt(name="strategy", description="Configure search strategy")
def mdpaper_strategy(keywords: str) -> str:
    """Configure literature search strategy.
    
    Args:
        keywords: Main keywords for searching (e.g., anesthesia, pain management)
    """
    return f"Configure a literature search strategy for: {keywords}"

@mcp.prompt(name="draft", description="Write paper draft")
def mdpaper_draft(section: str) -> str:
    """Write a paper draft section.
    
    Args:
        section: Which section to write (Introduction, Methods, Results, Discussion, or all)
    """
    return f"Help me write the {section} section of my paper."

@mcp.prompt(name="analysis", description="Analyze data")
def mdpaper_data_analysis() -> str:
    """Analyze research data.
    
    This prompt automatically lists available data files for analysis.
    """
    # Get available data files
    data_dir = "data"
    data_files = []
    if os.path.exists(data_dir):
        data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    message = "Analyze research data.\n\n"
    
    message += "📊 **Available Data Files:**\n"
    if data_files:
        for i, f in enumerate(data_files, 1):
            message += f"  {i}. {f}\n"
    else:
        message += "  (No CSV files found in data/ folder)\n"
    
    message += "\n**Available Analysis Tools:**\n"
    message += "- `analyze_dataset` - Get descriptive statistics\n"
    message += "- `generate_table_one` - Create Table 1 (baseline characteristics)\n"
    message += "- `run_statistical_test` - Run t-test, correlation, etc.\n"
    message += "- `create_plot` - Create scatter, bar, box, histogram plots\n"
    
    message += "\nPlease help me analyze my data."
    
    return message

@mcp.prompt(name="clarify", description="Refine content")
def mdpaper_clarify() -> str:
    """Refine paper content.
    
    This prompt lists available drafts for refinement.
    """
    # Get available drafts
    drafts_dir = "drafts"
    drafts = []
    if os.path.exists(drafts_dir):
        drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
    
    message = "Refine paper content.\n\n"
    
    message += "📄 **Available Drafts:**\n"
    if drafts:
        for i, d in enumerate(drafts, 1):
            message += f"  {i}. {d}\n"
    else:
        message += "  (No drafts found)\n"
    
    message += "\n**Refinement Options:**\n"
    message += "- Make language more formal/academic\n"
    message += "- Shorten to meet word limits\n"
    message += "- Add more citations\n"
    message += "- Improve clarity and flow\n"
    message += "- Check grammar and style\n"
    
    message += "\nWhich draft would you like to refine, and what changes do you need?"
    
    return message

@mcp.prompt(name="format", description="Export to Word")
def mdpaper_format() -> str:
    """Export draft to Word document.
    
    This prompt automatically lists available drafts and templates for the user to choose from.
    """
    # Get available drafts
    drafts_dir = "drafts"
    drafts = []
    if os.path.exists(drafts_dir):
        drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
    
    # Get available templates
    templates = template_reader.list_templates()
    
    # Build the prompt message
    message = "Export a draft to Word format.\n\n"
    
    message += "📄 **Available Drafts:**\n"
    if drafts:
        for i, d in enumerate(drafts, 1):
            message += f"  {i}. {d}\n"
    else:
        message += "  (No drafts found in drafts/ folder)\n"
    
    message += "\n📋 **Available Templates:**\n"
    if templates:
        for i, t in enumerate(templates, 1):
            message += f"  {i}. {t}\n"
    else:
        message += "  (No templates found)\n"
    
    message += "\nPlease help me export a draft to Word. "
    message += "Use the 8-step workflow: read_template → read_draft → start_document_session → "
    message += "insert_section (for each section) → verify_document → check_word_limits → save_document"
    
    return message

if __name__ == "__main__":
    mcp.run()
