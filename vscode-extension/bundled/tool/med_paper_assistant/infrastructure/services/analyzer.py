import os
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats


class Analyzer:
    def __init__(self, data_dir: str = "data", results_dir: str = "results"):
        """
        Initialize the Analyzer.

        Args:
            data_dir: Directory containing raw data files.
            results_dir: Directory to save results.
        """
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.figures_dir = os.path.join(results_dir, "figures")
        self.tables_dir = os.path.join(results_dir, "tables")
        # Note: Directories are created on-demand when saving files,
        # not at initialization to avoid polluting root directory

    def load_data(self, filename: str) -> pd.DataFrame:
        """Load data from a CSV file."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Data file {filename} not found in {self.data_dir}")
        return pd.read_csv(filepath)

    def describe_data(self, filename: str) -> str:
        """Return descriptive statistics for the dataset."""
        df = self.load_data(filename)
        desc = df.describe().to_markdown()
        return f"### Data Description for {filename}\n\n{desc}"

    def run_statistical_test(
        self, filename: str, test_type: str, col1: str, col2: Optional[str] = None
    ) -> str:
        """
        Run a statistical test.

        Args:
            filename: Data file.
            test_type: "t-test", "chi-square", "correlation".
            col1: First column name.
            col2: Second column name (required for most tests).

        Returns:
            Formatted result string.
        """
        df = self.load_data(filename)

        if test_type == "t-test":
            # Independent t-test
            # Assuming col1 is group (categorical) and col2 is value (numerical) OR two numerical cols?
            # Let's assume two numerical columns for paired or independent?
            # Common usage: Compare Value (col1) between Groups (col2)
            # OR Compare Value1 (col1) vs Value2 (col2)

            # Let's implement: Compare Value (col1) grouped by Categorical (col2)
            if not col2:
                return "Error: t-test requires two columns (Value, Group)."

            groups = df[col2].unique()
            if len(groups) != 2:
                return f"Error: t-test requires exactly 2 groups in {col2}, found {len(groups)}: {groups}"

            group1 = df[df[col2] == groups[0]][col1]
            group2 = df[df[col2] == groups[1]][col1]

            t_stat, p_val = stats.ttest_ind(group1, group2)
            return f"### T-Test Results\n\nComparing {col1} by {col2} ({groups[0]} vs {groups[1]})\n- T-statistic: {t_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        elif test_type == "correlation":
            if not col2:
                return "Error: correlation requires two numerical columns."

            corr, p_val = stats.pearsonr(df[col1], df[col2])
            return f"### Correlation Results\n\nPearson correlation between {col1} and {col2}\n- Coefficient: {corr:.4f}\n- P-value: {p_val:.4f}"

        else:
            return f"Test type '{test_type}' not supported yet."

    def create_plot(
        self,
        filename: str,
        plot_type: str,
        x_col: str,
        y_col: str,
        output_name: Optional[str] = None,
    ) -> str:
        """
        Create and save a plot.

        Args:
            filename: Data file.
            plot_type: "scatter", "bar", "box", "histogram".
            x_col: X-axis column.
            y_col: Y-axis column.
            output_name: Filename for the saved image.

        Returns:
            Path to saved image.
        """
        df = self.load_data(filename)
        plt.figure(figsize=(10, 6))

        if plot_type == "scatter":
            sns.scatterplot(data=df, x=x_col, y=y_col)
        elif plot_type == "box":
            sns.boxplot(data=df, x=x_col, y=y_col)
        elif plot_type == "bar":
            sns.barplot(data=df, x=x_col, y=y_col)
        elif plot_type == "histogram":
            sns.histplot(data=df, x=x_col)
        else:
            return f"Plot type '{plot_type}' not supported."

        plt.title(f"{plot_type.capitalize()} Plot: {y_col} vs {x_col}")

        if not output_name:
            output_name = f"{plot_type}_{x_col}_{y_col}.png"
        if not output_name.endswith(".png"):
            output_name += ".png"

        output_path = os.path.join(self.figures_dir, output_name)
        plt.savefig(output_path)
        plt.close()

        return output_path

    def generate_table_one(
        self,
        filename: str,
        group_col: str,
        continuous_cols: List[str],
        categorical_cols: List[str],
        output_name: Optional[str] = None,
    ) -> str:
        """
        Generate Table 1 (baseline characteristics) for medical papers.

        This is a standard table in medical research showing patient demographics
        and baseline characteristics, stratified by treatment groups.

        Args:
            filename: Name of the CSV file.
            group_col: Column name for grouping (e.g., "treatment", "group").
            continuous_cols: List of continuous variable column names (e.g., ["age", "weight"]).
            categorical_cols: List of categorical variable column names (e.g., ["sex", "diabetes"]).
            output_name: Output filename for the table (optional).

        Returns:
            Markdown formatted Table 1.
        """
        df = self.load_data(filename)

        # Get groups
        groups = df[group_col].unique()
        n_groups = len(groups)

        # Initialize results list
        rows = []

        # Header row
        header = ["Variable", "Overall (N={})".format(len(df))]
        for group in groups:
            n = len(df[df[group_col] == group])
            header.append(f"{group} (N={n})")
        header.append("P-value")

        # Process continuous variables
        for col in continuous_cols:
            if col not in df.columns:
                continue

            # Overall stats
            overall_mean = df[col].mean()
            overall_std = df[col].std()
            overall_str = f"{overall_mean:.1f} ± {overall_std:.1f}"

            row = [col, overall_str]

            # Group stats
            group_data = []
            for group in groups:
                group_vals = df[df[group_col] == group][col].dropna()
                mean_val = group_vals.mean()
                std_val = group_vals.std()
                row.append(f"{mean_val:.1f} ± {std_val:.1f}")
                group_data.append(group_vals)

            # P-value (t-test for 2 groups, ANOVA for >2 groups)
            if n_groups == 2:
                try:
                    _, p_val = stats.ttest_ind(group_data[0], group_data[1])
                    row.append(self._format_pvalue(p_val))
                except Exception:
                    row.append("N/A")
            elif n_groups > 2:
                try:
                    _, p_val = stats.f_oneway(*group_data)
                    row.append(self._format_pvalue(p_val))
                except Exception:
                    row.append("N/A")
            else:
                row.append("-")

            rows.append(row)

        # Process categorical variables
        for col in categorical_cols:
            if col not in df.columns:
                continue

            categories = df[col].dropna().unique()

            for cat in categories:
                # Overall count
                overall_count = (df[col] == cat).sum()
                overall_pct = overall_count / len(df) * 100
                overall_str = f"{overall_count} ({overall_pct:.1f}%)"

                row = [f"{col}: {cat}", overall_str]

                # Group counts for chi-square
                contingency_data = []
                for group in groups:
                    group_df = df[df[group_col] == group]
                    count = (group_df[col] == cat).sum()
                    pct = count / len(group_df) * 100 if len(group_df) > 0 else 0
                    row.append(f"{count} ({pct:.1f}%)")
                    contingency_data.append(count)

                # P-value only for first category of each variable
                if cat == categories[0]:
                    try:
                        # Create contingency table
                        contingency = pd.crosstab(df[group_col], df[col])
                        chi2, p_val, _, _ = stats.chi2_contingency(contingency)
                        row.append(self._format_pvalue(p_val))
                    except Exception:
                        row.append("N/A")
                else:
                    row.append("")

                rows.append(row)

        # Create markdown table
        markdown = self._create_markdown_table(header, rows)

        # Add title and footnote
        table_output = "## Table 1. Baseline Characteristics\n\n"
        table_output += markdown
        table_output += "\n\n*Values are presented as mean ± SD for continuous variables and n (%) for categorical variables.*\n"
        table_output += "*P-values: Student's t-test or ANOVA for continuous variables; Chi-square test for categorical variables.*\n"

        # Save to file if output_name specified
        if output_name:
            if not output_name.endswith(".md"):
                output_name += ".md"
            output_path = os.path.join(self.tables_dir, output_name)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(table_output)
            return f"Table 1 saved to: {output_path}\n\n{table_output}"

        return table_output

    def _format_pvalue(self, p: float) -> str:
        """Format p-value according to medical conventions."""
        if p < 0.001:
            return "<0.001"
        elif p < 0.01:
            return f"{p:.3f}"
        elif p < 0.05:
            return f"{p:.3f}*"
        else:
            return f"{p:.3f}"

    def _create_markdown_table(self, header: List[str], rows: List[List[str]]) -> str:
        """Create a markdown table from header and rows."""
        # Calculate column widths
        all_rows = [header] + rows
        col_widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(header))]

        # Create header
        header_str = "| " + " | ".join(str(h).ljust(w) for h, w in zip(header, col_widths)) + " |"
        separator = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"

        # Create rows
        row_strs = []
        for row in rows:
            # Ensure row has correct number of columns
            while len(row) < len(header):
                row.append("")
            row_str = (
                "| " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)) + " |"
            )
            row_strs.append(row_str)

        return header_str + "\n" + separator + "\n" + "\n".join(row_strs)
