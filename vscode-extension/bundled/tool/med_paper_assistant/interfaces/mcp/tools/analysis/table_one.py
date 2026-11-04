"""
Table 1 Generation Tools

Generate baseline characteristics tables for medical papers.
Every tool call records provenance to data-artifacts.yaml for reproducibility.
"""

import os
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
from .provenance import _record_table_provenance, _scoped_analyzer


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
        _, _, project_info = ensure_project_context()
    return project_info, None


def _build_table_one(
    analyzer: Analyzer,
    project_info: dict | None,
    filename: str,
    group_col: str,
    output_name: Optional[str],
    continuous_list: list[str],
    categorical_list: list[str],
) -> str:
    active_analyzer = _scoped_analyzer(analyzer, project_info)
    result = active_analyzer.generate_table_one(
        filename=filename,
        group_col=group_col,
        continuous_cols=continuous_list,
        categorical_cols=categorical_list,
        output_name=output_name,
    )

    _record_table_provenance(
        filename,
        group_col,
        output_name,
        categorical_list,
        continuous_list,
        project_info,
        result,
    )

    # Add usage tips
    tips = "\n\n---\n"
    tips += "💡 **Next Steps:**\n"
    tips += "1. Copy this table to your Methods or Results section\n"
    tips += "2. Use `write_draft` to insert into your manuscript\n"
    tips += "3. Verify variable labels match your study protocol\n"

    log_tool_result("generate_table_one", "success", success=True)
    return result + tips


def _table_one_failure(e: Exception, filename: str) -> str:
    if isinstance(e, FileNotFoundError):
        error_msg = (
            f"❌ Data file not found: {e}\n\nMake sure '{filename}' exists in the data/ directory."
        )
    elif isinstance(e, KeyError):
        error_msg = f"❌ Column not found: {e}\n\nCheck column names in your CSV file."
    else:
        error_msg = f"❌ Error generating Table 1: {str(e)}"
    log_tool_error("generate_table_one", e, {"filename": filename})
    return error_msg


def _generate_table_one(
    analyzer: Analyzer,
    filename: str,
    group_col: str,
    continuous_cols: str,
    categorical_cols: str,
    output_name: Optional[str],
    project: Optional[str],
) -> str:
    log_tool_call(
        "generate_table_one",
        {
            "filename": filename,
            "group_col": group_col,
            "continuous_cols": continuous_cols,
            "categorical_cols": categorical_cols,
            "project": project,
        },
    )

    project_info, guard_error = _resolve_project_info(project)
    if guard_error:
        return guard_error

    # Parse column lists
    continuous_list = [c.strip() for c in continuous_cols.split(",") if c.strip()]
    categorical_list = [c.strip() for c in categorical_cols.split(",") if c.strip()]

    if not continuous_list and not categorical_list:
        return "❌ Please specify at least one continuous or categorical column."

    try:
        return _build_table_one(
            analyzer,
            project_info,
            filename,
            group_col,
            output_name,
            continuous_list,
            categorical_list,
        )

    except Exception as e:
        return _table_one_failure(e, filename)


def _render_suggested_command(
    filename: str, categorical: list, continuous: list, potential_groups: list
) -> str:
    # Generate suggested command
    output = "---\n"
    output += "### 💡 Suggested Command\n\n"

    group_var = potential_groups[0][0] if potential_groups else "GROUP_COLUMN"
    cont_vars = ",".join(c[0] for c in continuous[:5]) if continuous else "age,weight"
    cat_vars = ",".join(c[0] for c in categorical[:5]) if categorical else "sex,diabetes"

    output += "```\n"
    output += "generate_table_one(\n"
    output += f'    filename="{filename}",\n'
    output += f'    group_col="{group_var}",\n'
    output += f'    continuous_cols="{cont_vars}",\n'
    output += f'    categorical_cols="{cat_vars}"\n'
    output += ")\n"
    output += "```\n"
    return output


def _classify_columns(df: Any) -> tuple[list, list, list, list]:
    import pandas as pd

    continuous = []
    categorical = []
    potential_groups = []
    id_cols = []

    for col in df.columns:
        n_unique = df[col].nunique()
        n_missing = df[col].isna().sum()
        dtype = df[col].dtype

        # Detect ID columns (too many unique values)
        if n_unique == len(df) or n_unique > len(df) * 0.9:
            id_cols.append((col, n_unique))
            continue

        # Detect potential grouping variables
        if n_unique <= 5:
            potential_groups.append((col, n_unique, list(df[col].unique())))

        # Classify by type
        if pd.api.types.is_numeric_dtype(dtype):
            if n_unique <= 10:
                categorical.append((col, n_unique, n_missing))
            else:
                continuous.append((col, df[col].mean(), df[col].std(), n_missing))
        else:
            categorical.append((col, n_unique, n_missing))
    return continuous, categorical, potential_groups, id_cols


def _render_variable_sections(
    continuous: list, categorical: list, potential_groups: list, id_cols: list
) -> str:
    output = ""

    # Output potential grouping variables
    if potential_groups:
        output += "### 🎯 Potential Grouping Variables\n"
        output += "| Column | Categories | Values |\n"
        output += "|--------|------------|--------|\n"
        for col, n, values in potential_groups:
            values_str = ", ".join(str(v) for v in values[:5])
            if len(values) > 5:
                values_str += "..."
            output += f"| {col} | {n} | {values_str} |\n"
        output += "\n"

    # Output continuous variables
    if continuous:
        output += "### 📈 Continuous Variables (for mean ± SD)\n"
        output += "| Column | Mean | SD | Missing |\n"
        output += "|--------|------|----|---------|\n"
        for col, mean, std, missing in continuous:
            output += f"| {col} | {mean:.2f} | {std:.2f} | {missing} |\n"
        output += "\n"

    # Output categorical variables
    if categorical:
        output += "### 📊 Categorical Variables (for n (%))\n"
        output += "| Column | Categories | Missing |\n"
        output += "|--------|------------|---------|\n"
        for col, n, missing in categorical:
            output += f"| {col} | {n} | {missing} |\n"
        output += "\n"

    # Skip ID columns
    if id_cols:
        output += "### ⏭️ Skipped (ID/unique columns)\n"
        for col, n in id_cols:
            output += f"- {col} ({n} unique values)\n"
        output += "\n"
    return output


def _detect_variable_types(analyzer: Analyzer, filename: str, project: Optional[str]) -> str:
    log_tool_call("detect_variable_types", {"filename": filename, "project": project})

    project_info, guard_error = _resolve_project_info(project)
    if guard_error:
        return guard_error

    try:
        active_analyzer = _scoped_analyzer(analyzer, project_info)
        df = active_analyzer.load_data(filename)
    except FileNotFoundError:
        return f"❌ Data file '{filename}' not found in data/ directory."

    output = f"## 📊 Variable Analysis: {filename}\n\n"
    output += f"**Total rows**: {len(df)}\n"
    output += f"**Total columns**: {len(df.columns)}\n\n"

    continuous, categorical, potential_groups, id_cols = _classify_columns(df)
    output += _render_variable_sections(continuous, categorical, potential_groups, id_cols)
    output += _render_suggested_command(filename, categorical, continuous, potential_groups)

    log_tool_result("detect_variable_types", "success", success=True)
    return output


def _describe_data_file(data_dir: str, f: str) -> str:
    import pandas as pd

    filepath = os.path.join(data_dir, f)
    size = os.path.getsize(filepath)
    size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"

    try:
        if f.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        return f"| {f} | {len(df)} | {len(df.columns)} | {size_str} |\n"
    except Exception:
        return f"| {f} | Error | - | {size_str} |\n"


def _list_data_files(analyzer: Analyzer, project: Optional[str]) -> str:
    log_tool_call("list_data_files", {"project": project})

    project_info, guard_error = _resolve_project_info(project)
    if guard_error:
        return guard_error

    data_dir = _scoped_analyzer(analyzer, project_info).data_dir
    if not os.path.exists(data_dir):
        return "📁 No data/ directory found.\n\nCreate one and add your CSV files."

    files = [f for f in os.listdir(data_dir) if f.endswith((".csv", ".xlsx", ".xls"))]

    if not files:
        return "📁 No data files found in data/ directory.\n\nSupported formats: .csv, .xlsx, .xls"

    output = "## 📁 Available Data Files\n\n"
    output += "| File | Rows | Columns | Size |\n"
    output += "|------|------|---------|------|\n"

    for f in sorted(files):
        output += _describe_data_file(data_dir, f)

    output += "\n💡 Use `detect_variable_types(filename)` to analyze a file's structure."

    log_tool_result("list_data_files", f"found {len(files)} files", success=True)
    return output


def _register_generate_tool(
    tool: Callable[..., Any], analyzer: Analyzer
) -> dict[str, Callable[..., Any]]:
    @tool()
    def generate_table_one(
        filename: str,
        group_col: str,
        continuous_cols: str,
        categorical_cols: str,
        output_name: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Generate Table 1 (baseline characteristics) with mean±SD, n(%), and p-values.

        Args:
            filename: CSV filename in data/ directory
            group_col: Grouping column name (e.g., "treatment")
            continuous_cols: Comma-separated continuous variables
            categorical_cols: Comma-separated categorical variables
            output_name: Output filename (optional, saves to tables/)
            project: Project slug (uses current if omitted)
        """
        return _generate_table_one(
            analyzer,
            filename,
            group_col,
            continuous_cols,
            categorical_cols,
            output_name,
            project,
        )

    return {"generate_table_one": generate_table_one}


def register_table_one_tools(
    mcp: MCPServer,
    analyzer: Analyzer,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register Table 1 generation tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    generate_tools = _register_generate_tool(tool, analyzer)

    @tool()
    def detect_variable_types(filename: str, project: Optional[str] = None) -> str:
        """
        Analyze CSV and suggest variable types for Table 1 (continuous vs categorical).

        Args:
            filename: CSV filename in data/ directory
            project: Project slug (uses current if omitted)
        """
        return _detect_variable_types(analyzer, filename, project)

    @tool()
    def list_data_files(project: Optional[str] = None) -> str:
        """
        List all CSV/Excel files in data/ directory with row/column counts.

        Args:
            project: Project slug (uses current if omitted)
        """
        return _list_data_files(analyzer, project)

    return {
        **generate_tools,
        "detect_variable_types": detect_variable_types,
        "list_data_files": list_data_files,
    }
