"""
Entry point for the MedPaper MCP Server.

Usage:
    python -m mdpaper_mcp
"""

import sys
import os


def main():
    """Run the MCP server."""
    # Add parent path for imports
    extension_path = os.environ.get('MDPAPER_EXTENSION_PATH', '')
    
    # For now, redirect to the main package
    # In production, this would be a standalone server
    try:
        from med_paper_assistant.interfaces.mcp import main as run_server
        run_server()
    except ImportError:
        # Fallback: minimal server for testing
        print("MedPaper MCP Server - Standalone mode not yet implemented", file=sys.stderr)
        print("Please install med-paper-assistant package or use uvx", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
