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
        self,
        filename: str,
        test_type: str,
        col1: Optional[str] = None,
        col2: Optional[str] = None,
        variables: Optional[List[str]] = None,
        group_var: Optional[str] = None,
    ) -> str:
        """
        Run a statistical test.

        Args:
            filename: Data file.
            test_type: "t-test", "ttest", "paired_ttest", "chi-square", "chi2",
                       "correlation", "anova", "mann_whitney", "kruskal".
            col1: First column name (legacy).
            col2: Second column name (legacy).
            variables: List of variable names (new API).
            group_var: Grouping variable (new API).

        Returns:
            Formatted result string.
        """
        df = self.load_data(filename)

        # Handle legacy API (col1, col2)
        if variables is None and col1 is not None:
            variables = [col1]
            if col2:
                group_var = col2

        if not variables:
            return "Error: No variables specified."

        # Normalize test type
        test_type = test_type.lower().replace("-", "_").replace(" ", "_")
        if test_type == "t_test":
            test_type = "ttest"
        if test_type == "chi_square":
            test_type = "chi2"

        if test_type == "ttest":
            # Independent t-test: compare variable between groups
            if not group_var:
                return "Error: t-test requires a grouping variable (group_var)."

            var = variables[0]
            groups = df[group_var].dropna().unique()
            if len(groups) != 2:
                return f"Error: t-test requires exactly 2 groups in {group_var}, found {len(groups)}: {list(groups)}"

            group1 = df[df[group_var] == groups[0]][var].dropna()
            group2 = df[df[group_var] == groups[1]][var].dropna()

            t_stat, p_val = stats.ttest_ind(group1, group2)
            return f"### T-Test Results\n\nComparing {var} by {group_var} ({groups[0]} vs {groups[1]})\n- T-statistic: {t_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        elif test_type == "paired_ttest":
            if len(variables) < 2:
                return "Error: paired t-test requires two variables."
            var1, var2 = variables[0], variables[1]
            t_stat, p_val = stats.ttest_rel(df[var1].dropna(), df[var2].dropna())
            return f"### Paired T-Test Results\n\nComparing {var1} vs {var2}\n- T-statistic: {t_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        elif test_type == "anova":
            if not group_var:
                return "Error: ANOVA requires a grouping variable (group_var)."
            var = variables[0]
            groups_data = [
                df[df[group_var] == g][var].dropna() for g in df[group_var].dropna().unique()
            ]
            f_stat, p_val = stats.f_oneway(*groups_data)
            return f"### ANOVA Results\n\nComparing {var} across groups in {group_var}\n- F-statistic: {f_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        elif test_type == "chi2":
            if len(variables) < 2:
                return "Error: chi-square test requires two categorical variables."
            var1, var2 = variables[0], variables[1]
            contingency = pd.crosstab(df[var1], df[var2])
            chi2, p_val, dof, expected = stats.chi2_contingency(contingency)
            return f"### Chi-Square Test Results\n\nAssociation between {var1} and {var2}\n- Chi-square: {chi2:.4f}\n- P-value: {p_val:.4f}\n- Degrees of freedom: {dof}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        elif test_type == "correlation":
            if len(variables) < 2:
                return "Error: correlation requires two numerical variables."
            var1, var2 = variables[0], variables[1]
            corr, p_val = stats.pearsonr(df[var1].dropna(), df[var2].dropna())
            return f"### Correlation Results\n\nPearson correlation between {var1} and {var2}\n- Coefficient: {corr:.4f}\n- P-value: {p_val:.4f}"

        elif test_type == "mann_whitney":
            if not group_var:
                return "Error: Mann-Whitney test requires a grouping variable."
            var = variables[0]
            groups = df[group_var].dropna().unique()
            if len(groups) != 2:
                return f"Error: Mann-Whitney requires exactly 2 groups, found {len(groups)}"
            group1 = df[df[group_var] == groups[0]][var].dropna()
            group2 = df[df[group_var] == groups[1]][var].dropna()
            u_stat, p_val = stats.mannwhitneyu(group1, group2)
            return f"### Mann-Whitney U Test Results\n\nComparing {var} by {group_var}\n- U-statistic: {u_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        elif test_type == "kruskal":
            if not group_var:
                return "Error: Kruskal-Wallis test requires a grouping variable."
            var = variables[0]
            groups_data = [
                df[df[group_var] == g][var].dropna() for g in df[group_var].dropna().unique()
            ]
            h_stat, p_val = stats.kruskal(*groups_data)
            return f"### Kruskal-Wallis Test Results\n\nComparing {var} across groups in {group_var}\n- H-statistic: {h_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"

        else:
            return f"Test type '{test_type}' not supported yet."

    def create_plot(
        self,
        filename: str,
        plot_type: str,
        x_col: str,
        y_col: Optional[str] = None,
        hue_col: Optional[str] = None,
        title: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> str:
        """
        Create and save a plot.

        Args:
            filename: Data file.
            plot_type: "scatter", "bar", "box", "boxplot", "histogram", "violin", "kaplan_meier".
            x_col: X-axis column.
            y_col: Y-axis column (optional for histogram).
            hue_col: Column for color grouping (optional).
            title: Plot title (optional).
            output_name: Filename for the saved image.

        Returns:
            Path to saved image.
        """
        df = self.load_data(filename)
        plt.figure(figsize=(10, 6))

        # Normalize plot type
        plot_type = plot_type.lower()
        if plot_type == "box":
            plot_type = "boxplot"

        if plot_type == "scatter":
            sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col)
        elif plot_type == "boxplot":
            sns.boxplot(data=df, x=x_col, y=y_col, hue=hue_col)
        elif plot_type == "bar":
            sns.barplot(data=df, x=x_col, y=y_col, hue=hue_col)
        elif plot_type == "histogram":
            sns.histplot(data=df, x=x_col, hue=hue_col)
        elif plot_type == "violin":
            sns.violinplot(data=df, x=x_col, y=y_col, hue=hue_col)
        elif plot_type == "kaplan_meier":
            # Basic survival curve - requires lifelines package
            try:
                from lifelines import KaplanMeierFitter

                kmf = KaplanMeierFitter()
                if hue_col:
                    for group in df[hue_col].dropna().unique():
                        mask = df[hue_col] == group
                        kmf.fit(
                            df.loc[mask, x_col],
                            event_observed=df.loc[mask, y_col] if y_col else None,
                            label=str(group),
                        )
                        kmf.plot_survival_function()
                else:
                    kmf.fit(df[x_col], event_observed=df[y_col] if y_col else None)
                    kmf.plot_survival_function()
            except ImportError:
                return "Error: lifelines package required for Kaplan-Meier plots. Install with: uv add lifelines"
        else:
            return f"Plot type '{plot_type}' not supported."

        # Set title
        if title:
            plt.title(title)
        elif y_col:
            plt.title(f"{plot_type.capitalize()} Plot: {y_col} vs {x_col}")
        else:
            plt.title(f"{plot_type.capitalize()} Plot: {x_col}")

        if not output_name:
            output_name = f"{plot_type}_{x_col}_{y_col or 'dist'}.png"
        if not output_name.endswith(".png"):
            output_name += ".png"

        # Ensure directory exists
        os.makedirs(self.figures_dir, exist_ok=True)

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
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
