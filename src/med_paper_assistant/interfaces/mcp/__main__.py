"""
Entry point for running the MedPaper Assistant MCP server.

Usage:
    python -m med_paper_assistant.interfaces.mcp
    
This module exists to avoid the RuntimeWarning about module execution order.
"""


def main():
    """Run the MCP server."""
    from med_paper_assistant.interfaces.mcp.server import create_server
    
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
