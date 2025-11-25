from mcp.server.fastmcp import FastMCP
from med_paper_assistant.core.search import LiteratureSearcher, SearchStrategy
from med_paper_assistant.core.reference_manager import ReferenceManager
from med_paper_assistant.core.drafter import Drafter, CitationStyle
from med_paper_assistant.core.analyzer import Analyzer
from med_paper_assistant.core.formatter import Formatter
from med_paper_assistant.core.logger import setup_logger
from med_paper_assistant.core.strategy_manager import StrategyManager
import json

# Setup Logger
logger = setup_logger()

# Initialize Core Modules
searcher = LiteratureSearcher(email="your.email@example.com")
analyzer = Analyzer()
ref_manager = ReferenceManager(searcher)
drafter = Drafter(ref_manager)
formatter = Formatter()
strategy_manager = StrategyManager()

mcp = FastMCP("MedPaperAssistant")

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

@mcp.prompt(name="mdpaper.concept", description="Develop research concept")
def mdpaper_concept() -> str:
    with open(".agent/workflows/mdpaper_concept.md", "r") as f:
        return f.read()

@mcp.prompt(name="mdpaper.strategy", description="Configure search strategy")
def mdpaper_strategy() -> str:
    with open(".agent/workflows/mdpaper_strategy.md", "r") as f:
        return f.read()

@mcp.prompt(name="mdpaper.draft", description="Write paper draft")
def mdpaper_draft() -> str:
    with open(".agent/workflows/mdpaper_draft.md", "r") as f:
        return f.read()

@mcp.prompt(name="mdpaper.analysis", description="Analyze data")
def mdpaper_data_analysis() -> str:
    with open(".agent/workflows/mdpaper_data_analysis.md", "r") as f:
        return f.read()

@mcp.prompt(name="mdpaper.clarify", description="Refine content")
def mdpaper_clarify() -> str:
    with open(".agent/workflows/mdpaper_clarify.md", "r") as f:
        return f.read()

@mcp.prompt(name="mdpaper.format", description="Export to Word")
def mdpaper_format() -> str:
    with open(".agent/workflows/mdpaper_apply_format.md", "r") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run()
