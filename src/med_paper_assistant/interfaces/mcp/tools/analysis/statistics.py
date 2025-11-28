"""
Statistics Tools

analyze_dataset, run_statistical_test, generate_table_one
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.services import Analyzer
from med_paper_assistant.infrastructure.logging import setup_logger

logger = setup_logger()


def register_statistics_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register statistics analysis tools."""

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
            continuous_cols: Comma-separated continuous variable names 
                            (e.g., "age,weight,height").
            categorical_cols: Comma-separated categorical variable names 
                             (e.g., "sex,diabetes,smoking").
            output_name: Optional output filename for the table.
            
        Returns:
            Markdown formatted Table 1 with p-values.
        """
        try:
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
    def run_statistical_test(
        filename: str, 
        test_type: str, 
        col1: str, 
        col2: str = None
    ) -> str:
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
