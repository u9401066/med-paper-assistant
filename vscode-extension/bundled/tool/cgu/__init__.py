"""
Creativity Generation Unit (CGU)

🎨 MCP-based Agent-to-Agent Creative Idea Generator

核心理念：
- 快思慢想 (Thinking Fast and Slow) - Daniel Kahneman
- 多個快速小步驟 + 慢速大步驟的組合
- 創意不需要完整知識，只需要足夠的連結能力

架構：
- MCP Server (official MCP Python SDK 2) - 提供創意生成工具
- LangGraph - Agent 編排
- vLLM + Qwen 4B - 本地推理
- Structured Output - Pydantic + Instructor
"""

__version__ = "0.6.0"

from cgu.core import (
    # Creativity
    CreativityLevel,
    CreativityMethod,
    MethodCategory,
    ThinkingChain,
    # Thinking
    ThinkingMode,
    ThinkingSpeed,
    ThinkingStep,
)

__all__ = [
    "__version__",
    # Thinking
    "ThinkingMode",
    "ThinkingSpeed",
    "ThinkingStep",
    "ThinkingChain",
    # Creativity
    "CreativityLevel",
    "CreativityMethod",
    "MethodCategory",
]
