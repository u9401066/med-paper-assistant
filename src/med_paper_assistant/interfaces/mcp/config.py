"""
MCP Server Configuration Module

Centralized configuration for the MedPaper Assistant MCP server.
"""

from pathlib import Path

from .instructions import get_server_instructions

# ====================
# Paths
# ====================
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONSTITUTION_PATH = PROJECT_ROOT / ".memory" / ".agent_constitution.md"


# ====================
# Server Settings
# ====================
DEFAULT_EMAIL = "your.email@example.com"

DEFAULT_WORD_LIMITS = {
    "Abstract": 250,
    "Introduction": 800,
    "Methods": 1500,
    "Materials and Methods": 1500,
    "Results": 1500,
    "Discussion": 1500,
    "Conclusions": 300,
}


# ====================
# Server Instructions
# ====================
def load_constitution() -> str:
    """Load agent constitution from .memory/.agent_constitution.md"""
    try:
        if CONSTITUTION_PATH.exists():
            return CONSTITUTION_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Failed to load constitution: {e}")
    return ""


# Generate server instructions (with constitution if available)
SERVER_INSTRUCTIONS = get_server_instructions(load_constitution())
