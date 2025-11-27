"""
MedPaper Assistant - Medical Paper Writing Assistant

A comprehensive tool for medical research paper writing, providing:
- Literature search and reference management
- Draft creation and editing
- Data analysis and visualization
- Word document export with templates

Architecture (DDD):
    domain/         - Core business logic and entities
    application/    - Use cases and application services
    infrastructure/ - External services, persistence, and services
    interfaces/     - MCP server (interfaces/mcp/)
    shared/         - Shared constants and utilities
"""

__version__ = "0.1.0"

# Interface exports (main entry point)
from med_paper_assistant.interfaces.mcp import create_server, mcp

def run_server():
    """Run the MCP server."""
    mcp.run()

__all__ = [
    "__version__",
    "create_server",
    "mcp",
    "run_server",
]
