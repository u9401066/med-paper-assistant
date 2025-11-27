"""
MCP Server - Model Context Protocol server for VS Code integration.

This module provides the main entry point for the MCP server.
It wraps the existing mcp_server implementation for DDD compatibility.

Usage:
    # Direct import
    from med_paper_assistant.interfaces.mcp import create_server, run_server
    
    # Or run as module
    python -m med_paper_assistant.interfaces.mcp
"""

from mcp.server.fastmcp import FastMCP

# Import from existing implementation for backward compatibility
from med_paper_assistant.mcp_server.server import create_server as _create_server


def create_server() -> FastMCP:
    """
    Create and configure the MedPaper Assistant MCP server.
    
    This function delegates to the existing implementation while
    maintaining a clean interface for the DDD architecture.
    
    Returns:
        Configured FastMCP server instance
    """
    return _create_server()


def run_server():
    """
    Run the MCP server.
    """
    server = create_server()
    server.run()


# For direct execution
if __name__ == "__main__":
    run_server()
