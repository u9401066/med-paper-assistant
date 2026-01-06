"""
Statistical Analysis Tools

Expose statistical analysis capabilities for medical papers.
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services.analyzer import Analyzer

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)


def register_stats_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register statistical analysis tools."""

    @mcp.tool()
    def analyze_dataset(filename: str, project: Optional[str] = None) -> str:
        """
        Get descriptive statistics for a dataset.

        Provides summary statistics including:
        - Count, mean, std, min, max for numeric columns
        - Value counts for categorical columns
        - Missing value analysis

        Args:
            filename: Name of the CSV file in data/ directory.
            project: Project slug. If not specified, uses current project.

        Returns:
            Descriptive statistics in markdown format.
        """
        log_tool_call("analyze_dataset", {"filename": filename, "project": project})

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        try:
            result = analyzer.describe_data(filename)
            log_tool_result("analyze_dataset", "success", success=True)
            return result
        except FileNotFoundError:
            error_msg = f"❌ Data file '{filename}' not found in data/ directory."
            log_tool_error("analyze_dataset", Exception(error_msg), {"filename": filename})
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error analyzing dataset: {str(e)}"
            log_tool_error("analyze_dataset", e, {"filename": filename})
            return error_msg

    @mcp.tool()
    def run_statistical_test(
        filename: str,
        test_type: str,
        variables: str,
        group_var: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Run a statistical test on the data.

        Supported tests:
        - "ttest": Independent samples t-test (requires group_var)
        - "paired_ttest": Paired samples t-test (two variables)
        - "anova": One-way ANOVA (requires group_var)
        - "chi2": Chi-square test of independence (two categorical variables)
        - "correlation": Pearson correlation (two numeric variables)
        - "mann_whitney": Mann-Whitney U test (non-parametric, requires group_var)
        - "kruskal": Kruskal-Wallis test (non-parametric ANOVA, requires group_var)

        Args:
            filename: Name of the CSV file in data/ directory.
            test_type: Type of statistical test to run.
            variables: Comma-separated variable names to analyze.
            group_var: Grouping variable (required for ttest, anova, mann_whitney, kruskal).
            project: Project slug. If not specified, uses current project.

        Returns:
            Test results with statistics and p-value.

        Example:
            # Compare age between treatment groups
            run_statistical_test(
                filename="patients.csv",
                test_type="ttest",
                variables="age",
                group_var="treatment"
            )
        """
        log_tool_call(
            "run_statistical_test",
            {
                "filename": filename,
                "test_type": test_type,
                "variables": variables,
                "group_var": group_var,
                "project": project,
            },
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Validate test type
        valid_tests = ["ttest", "paired_ttest", "anova", "chi2", "correlation", "mann_whitney", "kruskal"]
        if test_type not in valid_tests:
            return f"❌ Unknown test type: {test_type}\n\nSupported tests: {', '.join(valid_tests)}"

        # Parse variables
        var_list = [v.strip() for v in variables.split(",") if v.strip()]
        if not var_list:
            return "❌ Please specify at least one variable."

        try:
            result = analyzer.run_statistical_test(
                filename=filename,
                test_type=test_type,
                variables=var_list,
                group_var=group_var,
            )
            log_tool_result("run_statistical_test", "success", success=True)
            return result
        except FileNotFoundError:
            error_msg = f"❌ Data file '{filename}' not found in data/ directory."
            log_tool_error("run_statistical_test", Exception(error_msg), {"filename": filename})
            return error_msg
        except ValueError as e:
            error_msg = f"❌ Invalid input: {str(e)}"
            log_tool_error("run_statistical_test", e, {"test_type": test_type})
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error running statistical test: {str(e)}"
            log_tool_error("run_statistical_test", e, {"test_type": test_type})
            return error_msg

    @mcp.tool()
    def create_plot(
        filename: str,
        plot_type: str,
        x_var: str,
        y_var: Optional[str] = None,
        hue_var: Optional[str] = None,
        title: Optional[str] = None,
        output_name: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Create a statistical plot for the paper.

        Supported plot types:
        - "histogram": Distribution of a single variable
        - "boxplot": Compare distributions across groups
        - "scatter": Relationship between two variables
        - "bar": Bar chart for categorical data
        - "violin": Violin plot (boxplot + density)
        - "kaplan_meier": Survival curve (requires time and event columns)

        Args:
            filename: Name of the CSV file in data/ directory.
            plot_type: Type of plot to create.
            x_var: Variable for x-axis.
            y_var: Variable for y-axis (optional for histogram).
            hue_var: Variable for color grouping (optional).
            title: Plot title (optional).
            output_name: Output filename (saved to results/figures/).
            project: Project slug. If not specified, uses current project.

        Returns:
            Path to the saved plot file.

        Example:
            create_plot(
                filename="patients.csv",
                plot_type="boxplot",
                x_var="treatment",
                y_var="pain_score",
                title="Pain Score by Treatment Group"
            )
        """
        log_tool_call(
            "create_plot",
            {
                "filename": filename,
                "plot_type": plot_type,
                "x_var": x_var,
                "y_var": y_var,
                "hue_var": hue_var,
                "title": title,
                "project": project,
            },
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Validate plot type
        valid_plots = ["histogram", "boxplot", "scatter", "bar", "violin", "kaplan_meier"]
        if plot_type not in valid_plots:
            return f"❌ Unknown plot type: {plot_type}\n\nSupported plots: {', '.join(valid_plots)}"

        try:
            result = analyzer.create_plot(
                filename=filename,
                plot_type=plot_type,
                x_col=x_var,
                y_col=y_var,
                hue_col=hue_var,
                title=title,
                output_name=output_name,
            )
            log_tool_result("create_plot", "success", success=True)
            return result
        except FileNotFoundError:
            error_msg = f"❌ Data file '{filename}' not found in data/ directory."
            log_tool_error("create_plot", Exception(error_msg), {"filename": filename})
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error creating plot: {str(e)}"
            log_tool_error("create_plot", e, {"plot_type": plot_type})
            return error_msg
