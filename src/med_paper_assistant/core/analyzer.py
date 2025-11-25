import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from typing import Dict, Any, List, Optional

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
        
        for d in [self.data_dir, self.results_dir, self.figures_dir, self.tables_dir]:
            if not os.path.exists(d):
                os.makedirs(d)

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

    def run_statistical_test(self, filename: str, test_type: str, col1: str, col2: Optional[str] = None) -> str:
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

    def create_plot(self, filename: str, plot_type: str, x_col: str, y_col: str, output_name: str = None) -> str:
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
