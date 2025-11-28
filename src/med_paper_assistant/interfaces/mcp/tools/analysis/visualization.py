"""
Visualization Tools

create_plot and future chart types
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.services import Analyzer


def register_visualization_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register visualization tools."""

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

    # Future tools:
    # - create_kaplan_meier: Survival curves
    # - create_forest_plot: Meta-analysis forest plots
    # - create_consort_diagram: CONSORT flowchart (via Draw.io)
    # - create_roc_curve: ROC analysis
