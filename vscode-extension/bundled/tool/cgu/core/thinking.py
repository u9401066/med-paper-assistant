"""
Thinking Mode Definitions

Based on Daniel Kahneman's "Thinking, Fast and Slow"
- System 1 (Fast): Intuitive, automatic, effortless
- System 2 (Slow): Deliberate, analytical, effortful

核心理念：多個快速小步驟 + 慢速大步驟的組合
"""

from enum import Enum

from pydantic import BaseModel, Field


class ThinkingSpeed(str, Enum):
    """思考速度"""
    FAST = "fast"      # System 1: 快速直覺
    SLOW = "slow"      # System 2: 慢速分析


class ThinkingMode(str, Enum):
    """思考模式 - 從 React 到 Creativity"""

    # === Fast Thinking (System 1) ===
    REACT = "react"                    # 基本反應：輸入 → 輸出
    ASSOCIATE = "associate"            # 快速聯想：概念 → 相關概念
    PATTERN_MATCH = "pattern_match"    # 模式匹配：識別已知模式

    # === Slow Thinking (System 2) ===
    ANALYZE = "analyze"                # 分析：拆解問題結構
    SYNTHESIZE = "synthesize"          # 綜合：組合多個概念
    EVALUATE = "evaluate"              # 評估：判斷品質與可行性

    # === Creative Thinking (System 1 + 2) ===
    DIVERGE = "diverge"                # 發散：產生多種可能
    CONVERGE = "converge"              # 收斂：選擇最佳方案
    TRANSFORM = "transform"            # 變革：打破規則創新


class ThinkingStep(BaseModel):
    """單一思考步驟"""

    mode: ThinkingMode
    speed: ThinkingSpeed
    input_context: str = Field(description="輸入上下文")
    output: str | None = Field(default=None, description="思考輸出")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="信心度")
    reasoning: str | None = Field(default=None, description="推理過程（慢思考才有）")

    @property
    def is_fast(self) -> bool:
        return self.speed == ThinkingSpeed.FAST

    @property
    def is_creative(self) -> bool:
        return self.mode in {
            ThinkingMode.DIVERGE,
            ThinkingMode.CONVERGE,
            ThinkingMode.TRANSFORM,
        }


class ThinkingChain(BaseModel):
    """思考鏈：多個步驟的組合"""

    steps: list[ThinkingStep] = Field(default_factory=list)
    total_fast_steps: int = 0
    total_slow_steps: int = 0

    def add_step(self, step: ThinkingStep) -> None:
        self.steps.append(step)
        if step.is_fast:
            self.total_fast_steps += 1
        else:
            self.total_slow_steps += 1

    @property
    def fast_slow_ratio(self) -> float:
        """快慢比例 - 理想是多快少慢"""
        if self.total_slow_steps == 0:
            return float("inf")
        return self.total_fast_steps / self.total_slow_steps


# === 快思慢想策略配置 ===

FAST_SLOW_PATTERNS: dict[str, tuple[int, int, str]] = {
    # 模式名稱: (快步驟數, 慢步驟數, 說明)
    "sprint": (5, 1, "5次快速嘗試 + 1次慢速評估"),
    "explore": (3, 1, "3次快速聯想 + 1次慢速分析"),
    "refine": (2, 2, "2次快速生成 + 2次慢速精煉"),
    "deep": (1, 3, "1次快速直覺 + 3次慢速深思"),
}


def get_thinking_pattern(name: str) -> tuple[int, int, str]:
    """取得思考模式配置"""
    return FAST_SLOW_PATTERNS.get(name, FAST_SLOW_PATTERNS["explore"])
