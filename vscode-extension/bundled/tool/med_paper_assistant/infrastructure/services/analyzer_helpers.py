"""Pure helpers for the Analyzer service (table formatting and paired statistics)."""

import math
from typing import List

import pandas as pd


def format_pvalue(p: float) -> str:
    """Format p-value according to medical conventions ("N/A" when not finite)."""
    if not math.isfinite(p):
        return "N/A"
    if p < 0.001:
        return "<0.001"
    if p < 0.05 and p >= 0.01:
        return f"{p:.3f}*"
    return f"{p:.3f}"


def create_markdown_table(header: List[str], rows: List[List[str]]) -> str:
    """Create a markdown table from header and rows (short rows are padded in place)."""
    all_rows = [header] + rows
    col_widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(header))]

    header_str = "| " + " | ".join(str(h).ljust(w) for h, w in zip(header, col_widths)) + " |"
    separator = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"

    row_strs = []
    for row in rows:
        while len(row) < len(header):
            row.append("")
        row_strs.append(
            "| " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)) + " |"
        )

    return header_str + "\n" + separator + "\n" + "\n".join(row_strs)


def paired_ttest_report(df: pd.DataFrame, var1: str, var2: str) -> str:
    """Paired t-test on complete pairs only (NaN dropped row-wise, keeping pairs aligned)."""
    from scipy import stats

    pairs = df[[var1, var2]].dropna()
    if len(pairs) < 2:
        return f"Error: paired t-test needs at least 2 complete pairs of {var1} and {var2}."
    t_stat, p_val = stats.ttest_rel(pairs[var1], pairs[var2])
    return f"### Paired T-Test Results\n\nComparing {var1} vs {var2}\n- T-statistic: {t_stat:.4f}\n- P-value: {p_val:.4f}\n- Significant: {'Yes' if p_val < 0.05 else 'No'}"


def correlation_report(df: pd.DataFrame, var1: str, var2: str) -> str:
    """Pearson correlation on complete pairs only."""
    from scipy import stats

    pairs = df[[var1, var2]].dropna()
    corr, p_val = stats.pearsonr(pairs[var1], pairs[var2])
    return f"### Correlation Results\n\nPearson correlation between {var1} and {var2}\n- Coefficient: {corr:.4f}\n- P-value: {p_val:.4f}"
