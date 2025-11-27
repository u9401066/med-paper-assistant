"""
MCP Interface - Model Context Protocol server for VS Code integration.

This module provides the MCP server that exposes tools and prompts
to AI assistants like GitHub Copilot.

Structure:
    server.py - Main entry point
    config.py - Server configuration
    instructions.py - Agent instructions
    tools/ - MCP tool definitions
    prompts/ - MCP prompt definitions
    templates/ - Concept templates
"""

from .server import create_server, mcp

__all__ = ["create_server", "mcp"]


def run_server():
    """Run the MCP server."""
    mcp.run()
