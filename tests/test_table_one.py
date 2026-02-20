"""Test cases for Table 1 generator functionality."""

import os

import numpy as np
import pandas as pd
import pytest

from med_paper_assistant.infrastructure.services.analyzer import Analyzer


def _create_sample_clinical_data(data_dir: str) -> None:
    """Create sample clinical trial CSV for testing."""
    np.random.seed(42)
    n = 40
    groups = ["Treatment"] * 20 + ["Control"] * 20
    df = pd.DataFrame(
        {
            "group": groups,
            "age": np.random.randint(35, 63, n),
            "weight": np.round(np.random.uniform(62, 86, n), 1),
            "height": np.round(np.random.uniform(159, 181, n), 1),
            "sex": np.random.choice(["Male", "Female"], n),
            "diabetes": np.random.choice(["Yes", "No"], n, p=[0.2, 0.8]),
        }
    )
    df.to_csv(os.path.join(data_dir, "sample_clinical_trial.csv"), index=False)


class TestTableOneGenerator:
    """Test suite for Table 1 generation."""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer instance with tmp test directories."""
        data_dir = str(tmp_path / "data")
        results_dir = str(tmp_path / "results")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        _create_sample_clinical_data(data_dir)
        return Analyzer(data_dir=data_dir, results_dir=results_dir)

    def test_generate_table_one_basic(self, analyzer):
        """Test basic Table 1 generation."""
        result = analyzer.generate_table_one(
            filename="sample_clinical_trial.csv",
            group_col="group",
            continuous_cols=["age", "weight", "height"],
            categorical_cols=["sex", "diabetes"],
        )

        # Check that result is a string
        assert isinstance(result, str)

        # Check that it contains expected sections
        assert "Table 1" in result
        assert "Baseline Characteristics" in result

        # Check that it contains variable names
        assert "age" in result
        assert "weight" in result
        assert "sex" in result

        # Check that it contains group names
        assert "Treatment" in result
        assert "Control" in result

        # Check that p-values are present
        assert "P-value" in result

    def test_generate_table_one_with_output(self, analyzer):
        """Test Table 1 generation with file output."""
        result = analyzer.generate_table_one(
            filename="sample_clinical_trial.csv",
            group_col="group",
            continuous_cols=["age", "weight"],
            categorical_cols=["sex"],
            output_name="test_table1",
        )

        # Check that file was saved
        assert "saved to" in result

        # Check that file exists
        output_path = os.path.join(analyzer.results_dir, "tables", "test_table1.md")
        assert os.path.exists(output_path)

    def test_pvalue_formatting(self, analyzer):
        """Test p-value formatting."""
        # Test very small p-value
        assert analyzer._format_pvalue(0.0001) == "<0.001"

        # Test small p-value
        assert "0.00" in analyzer._format_pvalue(0.005)

        # Test moderate p-value (should have asterisk if significant)
        result = analyzer._format_pvalue(0.03)
        assert "0.030" in result

        # Test non-significant p-value
        result = analyzer._format_pvalue(0.15)
        assert "0.150" in result

    def test_markdown_table_creation(self, analyzer):
        """Test markdown table creation helper."""
        header = ["A", "B", "C"]
        rows = [["1", "2", "3"], ["4", "5", "6"]]

        result = analyzer._create_markdown_table(header, rows)

        # Check markdown table structure
        assert "|" in result
        assert "---" in result
        assert "A" in result
        assert "1" in result


class TestTableOneMCPTool:
    """Test Table 1 MCP tool integration."""

    def test_mcp_tool_exists(self):
        """Test that the MCP tool is registered."""
        import asyncio

        from med_paper_assistant.interfaces.mcp.server import create_server

        async def check_tool():
            server = create_server()
            tools = await server.list_tools()
            tool_names = [t.name for t in tools]
            return "generate_table_one" in tool_names

        result = asyncio.run(check_tool())
        assert result, "generate_table_one tool should be registered"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
