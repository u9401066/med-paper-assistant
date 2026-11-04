"""
Statistical Analysis Tools

Expose statistical analysis capabilities for medical papers.
Every tool call records provenance to data-artifacts.yaml for reproducibility.
"""

from collections.abc import Callable
from typing import Any, Optional

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.services.analyzer import Analyzer

from .._shared import (
    ensure_project_context,
    get_optional_tool_decorator,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    resolve_project_context,
)
from .provenance import (
    _get_tracker,
    _record_plot_provenance,
    _record_test_provenance,
    _scoped_analyzer,
)


def _resolve_project_info(project: Optional[str]) -> tuple[dict | None, str | None]:
    """Apply the manuscript workflow guard; return (project_info, error message)."""
    _, workflow_error = resolve_project_context(
        project,
        required_mode="manuscript",
    )
    if workflow_error:
        return None, workflow_error

    project_info = None
    if project:
        is_valid, msg, project_info = ensure_project_context(project)
        if not is_valid:
            return None, f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    else:
        is_valid, _, project_info = ensure_project_context()
    return project_info, None


def _analyze_dataset(analyzer: Analyzer, filename: str, project: Optional[str]) -> str:
    log_tool_call("analyze_dataset", {"filename": filename, "project": project})

    project_info, guard_error = _resolve_project_info(project)
    if guard_error:
        return guard_error

    try:
        active_analyzer = _scoped_analyzer(analyzer, project_info)
        result = active_analyzer.describe_data(filename)

        # Record provenance
        tracker = _get_tracker(project_info) if project_info else None
        if tracker:
            tracker.record_artifact(
                tool_name="analyze_dataset",
                artifact_type="descriptive",
                parameters={"filename": filename},
                data_source=filename,
                result_summary=result[:200] if result else None,
                provenance_code=(
                    f"from med_paper_assistant.infrastructure.services.analyzer import Analyzer\n"
                    f"analyzer = Analyzer()\n"
                    f"result = analyzer.describe_data('{filename}')\n"
                    f"print(result)"
                ),
            )

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


def _parse_test_request(test_type: str, variables: str) -> tuple[list[str], str | None]:
    """Validate the test type and parse variables; return (variable list, error message)."""
    valid_tests = [
        "ttest",
        "paired_ttest",
        "anova",
        "chi2",
        "correlation",
        "mann_whitney",
        "kruskal",
    ]
    if test_type not in valid_tests:
        return [], f"❌ Unknown test type: {test_type}\n\nSupported tests: {', '.join(valid_tests)}"

    var_list = [v.strip() for v in variables.split(",") if v.strip()]
    if not var_list:
        return [], "❌ Please specify at least one variable."
    return var_list, None


def _execute_test(
    analyzer: Analyzer,
    project_info: dict | None,
    filename: str,
    test_type: str,
    var_list: list[str],
    group_var: Optional[str],
) -> str:
    active_analyzer = _scoped_analyzer(analyzer, project_info)
    result = active_analyzer.run_statistical_test(
        filename=filename,
        test_type=test_type,
        variables=var_list,
        group_var=group_var,
    )

    _record_test_provenance(filename, test_type, group_var, project_info, result, var_list)
    return result


def _execute_plot(
    analyzer: Analyzer,
    project_info: dict | None,
    filename: str,
    plot_type: str,
    x_var: str,
    y_var: Optional[str],
    hue_var: Optional[str],
    title: Optional[str],
    output_name: Optional[str],
) -> str:
    active_analyzer = _scoped_analyzer(analyzer, project_info)
    result = active_analyzer.create_plot(
        filename=filename,
        plot_type=plot_type,
        x_col=x_var,
        y_col=y_var,
        hue_col=hue_var,
        title=title,
        output_name=output_name,
    )

    _record_plot_provenance(
        filename, plot_type, x_var, y_var, hue_var, title, output_name, project_info, result
    )
    return result


def _run_statistical_test(
    analyzer: Analyzer,
    filename: str,
    test_type: str,
    variables: str,
    group_var: Optional[str],
    project: Optional[str],
) -> str:
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

    project_info, guard_error = _resolve_project_info(project)
    if guard_error:
        return guard_error

    var_list, request_error = _parse_test_request(test_type, variables)
    if request_error:
        return request_error

    try:
        result = _execute_test(analyzer, project_info, filename, test_type, var_list, group_var)

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


def _create_plot(
    analyzer: Analyzer,
    filename: str,
    plot_type: str,
    x_var: str,
    y_var: Optional[str],
    hue_var: Optional[str],
    title: Optional[str],
    output_name: Optional[str],
    project: Optional[str],
) -> str:
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

    project_info, guard_error = _resolve_project_info(project)
    if guard_error:
        return guard_error

    # Validate plot type
    valid_plots = ["histogram", "boxplot", "scatter", "bar", "violin", "kaplan_meier"]
    if plot_type not in valid_plots:
        return f"❌ Unknown plot type: {plot_type}\n\nSupported plots: {', '.join(valid_plots)}"

    try:
        result = _execute_plot(
            analyzer, project_info, filename, plot_type, x_var, y_var, hue_var, title, output_name
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


def register_stats_tools(
    mcp: MCPServer,
    analyzer: Analyzer,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register statistical analysis tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return {
        **_register_dataset_tools(tool, analyzer),
        **_register_plot_tools(tool, analyzer),
    }


def _register_dataset_tools(
    tool: Callable[..., Any], analyzer: Analyzer
) -> dict[str, Callable[..., Any]]:
    @tool()
    def analyze_dataset(filename: str, project: Optional[str] = None) -> str:
        """
        Get descriptive statistics for a CSV dataset (count, mean, std, missing values).

        Args:
            filename: CSV filename in data/ directory
            project: Project slug (uses current if omitted)
        """
        return _analyze_dataset(analyzer, filename, project)

    @tool()
    def run_statistical_test(
        filename: str,
        test_type: str,
        variables: str,
        group_var: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Run a statistical test on CSV data.

        Args:
            filename: CSV filename in data/ directory
            test_type: "ttest", "paired_ttest", "anova", "chi2", "correlation", "mann_whitney", "kruskal"
            variables: Comma-separated variable names
            group_var: Grouping variable (required for ttest, anova, etc.)
            project: Project slug (uses current if omitted)
        """
        return _run_statistical_test(analyzer, filename, test_type, variables, group_var, project)

    return {
        "analyze_dataset": analyze_dataset,
        "run_statistical_test": run_statistical_test,
    }


def _register_plot_tools(
    tool: Callable[..., Any], analyzer: Analyzer
) -> dict[str, Callable[..., Any]]:
    @tool()
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
        Create a statistical plot, saved to results/figures/.

        Args:
            filename: CSV filename in data/ directory
            plot_type: "histogram", "boxplot", "scatter", "bar", "violin", "kaplan_meier"
            x_var: X-axis variable
            y_var: Y-axis variable (optional for histogram)
            hue_var: Color grouping variable (optional)
            title: Plot title (optional)
            output_name: Output filename (optional)
            project: Project slug (uses current if omitted)
        """
        return _create_plot(
            analyzer, filename, plot_type, x_var, y_var, hue_var, title, output_name, project
        )

    return {
        "create_plot": create_plot,
    }
