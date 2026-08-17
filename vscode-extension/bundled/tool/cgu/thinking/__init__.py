"""
CGU Thinking Module

統一的思考深度層，整合：
- Simple: Copilot/Ollama 快速單次發想
- Deep: Multi-Agent 並發深度思考
- Hybrid: 快思慢想結合模式
"""

from cgu.thinking.engine import (
    ThinkingConfig,
    ThinkingDepth,
    ThinkingEngine,
    ThinkingMode,
    ThinkingResult,
)
from cgu.thinking.facade import (
    deep_think,
    quick_think,
    spark_think,
    think,
)

__all__ = [
    # Engine
    "ThinkingEngine",
    "ThinkingMode",
    "ThinkingDepth",
    "ThinkingConfig",
    "ThinkingResult",
    # Facade
    "think",
    "quick_think",
    "deep_think",
    "spark_think",
]
