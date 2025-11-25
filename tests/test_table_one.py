"""
Test cases for Table 1 generator functionality.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from med_paper_assistant.core.analyzer import Analyzer


class TestTableOneGenerator:
    """Test suite for Table 1 generation."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance with test data directory."""
        return Analyzer(data_dir="data", results_dir="results")
    
    def test_generate_table_one_basic(self, analyzer):
        """Test basic Table 1 generation."""
        result = analyzer.generate_table_one(
            filename="sample_clinical_trial.csv",
            group_col="group",
            continuous_cols=["age", "weight", "height"],
            categorical_cols=["sex", "diabetes"]
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
            output_name="test_table1"
        )
        
        # Check that file was saved
        assert "saved to" in result
        
        # Check that file exists
        output_path = os.path.join("results", "tables", "test_table1.md")
        assert os.path.exists(output_path)
        
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)
    
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
    
    @pytest.fixture
    def analyzer(self):
        return Analyzer(data_dir="data", results_dir="results")
    
    def test_mcp_tool_exists(self):
        """Test that the MCP tool is registered."""
        sys.path.insert(0, 'src')
        from med_paper_assistant.mcp_server.server import mcp
        import asyncio
        
        async def check_tool():
            tools = await mcp.list_tools()
            tool_names = [t.name for t in tools]
            return "generate_table_one" in tool_names
        
        result = asyncio.run(check_tool())
        assert result, "generate_table_one tool should be registered"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
