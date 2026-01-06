"""
Table 1 Generation Tools

Generate baseline characteristics tables for medical papers.
"""

import os
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


def register_table_one_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register Table 1 generation tools."""

    @mcp.tool()
    def generate_table_one(
        filename: str,
        group_col: str,
        continuous_cols: str,
        categorical_cols: str,
        output_name: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Generate Table 1 (baseline characteristics) for medical papers.

        This is a STANDARD table in medical research showing patient demographics
        and baseline characteristics, stratified by treatment/exposure groups.

        The tool automatically:
        - Calculates mean ± SD for continuous variables
        - Calculates n (%) for categorical variables
        - Performs statistical tests (t-test/ANOVA for continuous, chi-square for categorical)
        - Formats p-values according to medical conventions

        Args:
            filename: Name of the CSV file in data/ directory (e.g., "patients.csv").
            group_col: Column name for grouping (e.g., "treatment", "group", "arm").
            continuous_cols: Comma-separated continuous variable names
                            (e.g., "age,weight,height,bmi").
            categorical_cols: Comma-separated categorical variable names
                             (e.g., "sex,diabetes,hypertension,asa_class").
            output_name: Output filename for the table (optional, saves to tables/).
            project: Project slug. If not specified, uses current project.

        Returns:
            Markdown formatted Table 1 ready for insertion into draft.

        Example:
            generate_table_one(
                filename="study_data.csv",
                group_col="treatment",
                continuous_cols="age,weight,height",
                categorical_cols="sex,diabetes,hypertension"
            )

        Output format:
            | Variable | Overall (N=100) | Treatment (N=50) | Control (N=50) | P-value |
            |----------|-----------------|------------------|----------------|---------|
            | Age      | 65.2 ± 12.3     | 64.8 ± 11.9      | 65.6 ± 12.7    | 0.742   |
            | Sex: Male| 60 (60.0%)      | 32 (64.0%)       | 28 (56.0%)     | 0.413   |
        """
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

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Parse column lists
        continuous_list = [c.strip() for c in continuous_cols.split(",") if c.strip()]
        categorical_list = [c.strip() for c in categorical_cols.split(",") if c.strip()]

        if not continuous_list and not categorical_list:
            return "❌ Please specify at least one continuous or categorical column."

        try:
            result = analyzer.generate_table_one(
                filename=filename,
                group_col=group_col,
                continuous_cols=continuous_list,
                categorical_cols=categorical_list,
                output_name=output_name,
            )

            # Add usage tips
            tips = "\n\n---\n"
            tips += "💡 **Next Steps:**\n"
            tips += "1. Copy this table to your Methods or Results section\n"
            tips += "2. Use `write_draft` to insert into your manuscript\n"
            tips += "3. Verify variable labels match your study protocol\n"

            log_tool_result("generate_table_one", "success", success=True)
            return result + tips

        except FileNotFoundError as e:
            error_msg = f"❌ Data file not found: {e}\n\nMake sure '{filename}' exists in the data/ directory."
            log_tool_error("generate_table_one", e, {"filename": filename})
            return error_msg
        except KeyError as e:
            error_msg = f"❌ Column not found: {e}\n\nCheck column names in your CSV file."
            log_tool_error("generate_table_one", e, {"filename": filename})
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error generating Table 1: {str(e)}"
            log_tool_error("generate_table_one", e, {"filename": filename})
            return error_msg

    @mcp.tool()
    def detect_variable_types(filename: str, project: Optional[str] = None) -> str:
        """
        Analyze a CSV file and suggest variable types for Table 1.

        Automatically detects:
        - Continuous variables (numerical with many unique values)
        - Categorical variables (few unique values or non-numeric)
        - Potential grouping variables (binary or small number of categories)

        Use this BEFORE generate_table_one to understand your data structure.

        Args:
            filename: Name of the CSV file in data/ directory.
            project: Project slug. If not specified, uses current project.

        Returns:
            Suggested variable classifications for Table 1 generation.
        """
        import pandas as pd

        log_tool_call("detect_variable_types", {"filename": filename, "project": project})

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        try:
            df = analyzer.load_data(filename)
        except FileNotFoundError:
            return f"❌ Data file '{filename}' not found in data/ directory."

        output = f"## 📊 Variable Analysis: {filename}\n\n"
        output += f"**Total rows**: {len(df)}\n"
        output += f"**Total columns**: {len(df.columns)}\n\n"

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

        # Generate suggested command
        output += "---\n"
        output += "### 💡 Suggested Command\n\n"

        group_var = potential_groups[0][0] if potential_groups else "GROUP_COLUMN"
        cont_vars = ",".join(c[0] for c in continuous[:5]) if continuous else "age,weight"
        cat_vars = ",".join(c[0] for c in categorical[:5]) if categorical else "sex,diabetes"

        output += "```\n"
        output += 'generate_table_one(\n'
        output += f'    filename="{filename}",\n'
        output += f'    group_col="{group_var}",\n'
        output += f'    continuous_cols="{cont_vars}",\n'
        output += f'    categorical_cols="{cat_vars}"\n'
        output += ")\n"
        output += "```\n"

        log_tool_result("detect_variable_types", "success", success=True)
        return output

    @mcp.tool()
    def list_data_files(project: Optional[str] = None) -> str:
        """
        List all data files available for analysis.

        Args:
            project: Project slug. If not specified, uses current project.

        Returns:
            List of CSV files in the data/ directory with basic info.
        """
        import pandas as pd

        log_tool_call("list_data_files", {"project": project})

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        data_dir = analyzer.data_dir
        if not os.path.exists(data_dir):
            return "📁 No data/ directory found.\n\nCreate one and add your CSV files."

        files = [f for f in os.listdir(data_dir) if f.endswith((".csv", ".xlsx", ".xls"))]

        if not files:
            return "📁 No data files found in data/ directory.\n\nSupported formats: .csv, .xlsx, .xls"

        output = "## 📁 Available Data Files\n\n"
        output += "| File | Rows | Columns | Size |\n"
        output += "|------|------|---------|------|\n"

        for f in sorted(files):
            filepath = os.path.join(data_dir, f)
            size = os.path.getsize(filepath)
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"

            try:
                if f.endswith(".csv"):
                    df = pd.read_csv(filepath)
                else:
                    df = pd.read_excel(filepath)
                output += f"| {f} | {len(df)} | {len(df.columns)} | {size_str} |\n"
            except Exception:
                output += f"| {f} | Error | - | {size_str} |\n"

        output += "\n💡 Use `detect_variable_types(filename)` to analyze a file's structure."

        log_tool_result("list_data_files", f"found {len(files)} files", success=True)
        return output
