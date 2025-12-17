"""
MCP Interface - Model Context Protocol server for VS Code integration.

This module provides the MCP server that exposes tools and prompts
to AI assistants like GitHub Copilot.

Structure:
    __main__.py - Entry point for python -m execution
    server.py - Server creation and configuration
    config.py - Server configuration
    instructions.py - Agent instructions
    tools/ - MCP tool definitions
    prompts/ - MCP prompt definitions
    templates/ - Concept templates

Usage:
    python -m med_paper_assistant.interfaces.mcp
"""

__all__ = ["create_server", "main"]


def create_server():
    """Create the MCP server (lazy import to avoid circular imports)."""
    from .server import create_server as _create_server

    return _create_server()


def main():
    """Run the MCP server."""
    from .__main__ import main as _main

    _main()
