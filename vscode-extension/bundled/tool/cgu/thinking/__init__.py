"""
CGU Thinking Module

統一的思考深度層，整合：
- Simple: Copilot/Ollama 快速單次發想
- Deep: Multi-Agent 並發深度思考
- Hybrid: 快思慢想結合模式
"""

from cgu.thinking.engine import (
    ThinkingEngine,
    ThinkingMode,
    ThinkingDepth,
    ThinkingConfig,
    ThinkingResult,
)
from cgu.thinking.facade import (
    think,
    quick_think,
    deep_think,
    spark_think,
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
