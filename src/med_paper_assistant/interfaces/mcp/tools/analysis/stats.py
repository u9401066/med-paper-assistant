"""
Statistical Analysis Tools

Expose statistical analysis capabilities for medical papers.
Every tool call records provenance to data-artifacts.yaml for reproducibility.
"""

from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker
from med_paper_assistant.infrastructure.services.analyzer import Analyzer

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)


def _get_tracker(project_info: dict) -> DataArtifactTracker | None:
    """Create a DataArtifactTracker for the current project, or None if no project."""
    if not project_info or not project_info.get("project_path"):
        return None
    project_dir = Path(project_info["project_path"])
    return DataArtifactTracker(project_dir / ".audit", project_dir)


def register_stats_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register statistical analysis tools."""

    @mcp.tool()
    def analyze_dataset(filename: str, project: Optional[str] = None) -> str:
        """
        Get descriptive statistics for a CSV dataset (count, mean, std, missing values).

        Args:
            filename: CSV filename in data/ directory
            project: Project slug (uses current if omitted)
        """
        log_tool_call("analyze_dataset", {"filename": filename, "project": project})

        project_info = None
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
        else:
            is_valid, _, project_info = ensure_project_context()

        try:
            result = analyzer.describe_data(filename)

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

    @mcp.tool()
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

        project_info = None
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
        else:
            is_valid, _, project_info = ensure_project_context()

        # Validate test type
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

            # Record provenance
            tracker = _get_tracker(project_info) if project_info else None
            if tracker:
                params = {
                    "filename": filename,
                    "test_type": test_type,
                    "variables": var_list,
                    "group_var": group_var,
                }
                vars_str = ", ".join(f"'{v}'" for v in var_list)
                group_arg = f", group_var='{group_var}'" if group_var else ""
                tracker.record_artifact(
                    tool_name="run_statistical_test",
                    artifact_type="statistics",
                    parameters=params,
                    data_source=filename,
                    result_summary=result[:300] if result else None,
                    provenance_code=(
                        f"from med_paper_assistant.infrastructure.services.analyzer import Analyzer\n"
                        f"analyzer = Analyzer()\n"
                        f"result = analyzer.run_statistical_test(\n"
                        f"    filename='{filename}',\n"
                        f"    test_type='{test_type}',\n"
                        f"    variables=[{vars_str}]{group_arg},\n"
                        f")\n"
                        f"print(result)"
                    ),
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

        project_info = None
        if project:
            is_valid, msg, project_info = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
        else:
            is_valid, _, project_info = ensure_project_context()

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

            # Record provenance — result is the output file path
            tracker = _get_tracker(project_info) if project_info else None
            if tracker and result and not result.startswith("Error"):
                assert project_info is not None
                # Compute relative path from project dir
                try:
                    rel_path = str(Path(result).relative_to(Path(project_info["project_path"])))
                except (ValueError, KeyError):
                    rel_path = result

                params = {
                    "filename": filename,
                    "plot_type": plot_type,
                    "x_var": x_var,
                    "y_var": y_var,
                    "hue_var": hue_var,
                    "title": title,
                    "output_name": output_name,
                }
                y_arg = f", y_col='{y_var}'" if y_var else ""
                hue_arg = f", hue_col='{hue_var}'" if hue_var else ""
                title_arg = f", title='{title}'" if title else ""
                out_arg = f", output_name='{output_name}'" if output_name else ""
                tracker.record_artifact(
                    tool_name="create_plot",
                    artifact_type="figure",
                    parameters=params,
                    output_path=rel_path,
                    data_source=filename,
                    provenance_code=(
                        f"from med_paper_assistant.infrastructure.services.analyzer import Analyzer\n"
                        f"analyzer = Analyzer()\n"
                        f"path = analyzer.create_plot(\n"
                        f"    filename='{filename}',\n"
                        f"    plot_type='{plot_type}',\n"
                        f"    x_col='{x_var}'{y_arg}{hue_arg}{title_arg}{out_arg},\n"
                        f")\n"
                        f"print(f'Saved to: {{path}}')"
                    ),
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
