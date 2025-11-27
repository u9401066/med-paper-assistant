"""
MCP Interface - Model Context Protocol server for VS Code integration.

This module provides the MCP server that exposes tools and prompts
to AI assistants like GitHub Copilot.
"""

from .server import create_server, run_server

__all__ = ["create_server", "run_server"]
