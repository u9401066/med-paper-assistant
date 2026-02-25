"""
CGU Graph State

LangGraph 狀態定義
"""

from typing import Annotated, Literal
from operator import add

from pydantic import BaseModel, Field

from cgu.core import (
    ThinkingMode,
    ThinkingSpeed,
    ThinkingStep,
    CreativityLevel,
    CreativityMethod,
)


class Idea(BaseModel):
    """單一創意點子"""
    content: str
    association_score: float = Field(ge=0.0, le=1.0)
    source_method: str | None = None
    reasoning: str | None = None


class CGUState(BaseModel):
    """
    CGU Agent 狀態

    這是 LangGraph 的核心狀態，在各節點間傳遞
    """

    # === 輸入 ===
    topic: str = Field(description="發想主題")
    creativity_level: CreativityLevel = Field(
        default=CreativityLevel.L1_COMBINATIONAL,
        description="創意層級"
    )
    target_count: int = Field(default=5, description="目標點子數量")
    constraints: list[str] = Field(default_factory=list, description="限制條件")

    # === 思考過程 ===
    current_mode: ThinkingMode = Field(
        default=ThinkingMode.REACT,
        description="當前思考模式"
    )
    current_speed: ThinkingSpeed = Field(
        default=ThinkingSpeed.FAST,
        description="當前思考速度"
    )
    thinking_steps: Annotated[list[ThinkingStep], add] = Field(
        default_factory=list,
        description="思考步驟歷史（可累加）"
    )

    # === 創意方法 ===
    selected_method: CreativityMethod | None = Field(
        default=None,
        description="選用的創意方法"
    )
    method_context: dict = Field(
        default_factory=dict,
        description="方法特定上下文"
    )

    # === 中間產物 ===
    raw_associations: Annotated[list[str], add] = Field(
        default_factory=list,
        description="原始聯想（可累加）"
    )
    candidate_ideas: Annotated[list[Idea], add] = Field(
        default_factory=list,
        description="候選點子（可累加）"
    )

    # === 輸出 ===
    final_ideas: list[Idea] = Field(
        default_factory=list,
        description="最終點子"
    )

    # === 控制流 ===
    iteration: int = Field(default=0, description="當前迭代次數")
    max_iterations: int = Field(default=10, description="最大迭代次數")
    fast_steps_count: int = Field(default=0, description="快步驟計數")
    slow_steps_count: int = Field(default=0, description="慢步驟計數")
    should_stop: bool = Field(default=False, description="是否停止")
    error: str | None = Field(default=None, description="錯誤訊息")

    # === 快思慢想策略 ===
    pattern: str = Field(
        default="explore",
        description="快慢模式: sprint(5:1), explore(3:1), refine(2:2), deep(1:3)"
    )
    fast_target: int = Field(default=3, description="快步驟目標數")
    slow_target: int = Field(default=1, description="慢步驟目標數")

    def should_do_fast(self) -> bool:
        """是否該做快步驟"""
        if self.fast_steps_count < self.fast_target:
            return True
        return False

    def should_do_slow(self) -> bool:
        """是否該做慢步驟"""
        if self.fast_steps_count >= self.fast_target:
            return self.slow_steps_count < self.slow_target
        return False

    def is_cycle_complete(self) -> bool:
        """一個快慢週期是否完成"""
        return (
            self.fast_steps_count >= self.fast_target and
            self.slow_steps_count >= self.slow_target
        )

    def reset_cycle(self) -> None:
        """重置快慢週期計數"""
        self.fast_steps_count = 0
        self.slow_steps_count = 0
        self.iteration += 1

    def has_enough_ideas(self) -> bool:
        """是否已產生足夠點子"""
        return len(self.candidate_ideas) >= self.target_count

    def should_continue(self) -> bool:
        """是否應該繼續"""
        if self.should_stop:
            return False
        if self.error:
            return False
        if self.iteration >= self.max_iterations:
            return False
        if self.has_enough_ideas():
            return False
        return True


class NodeOutput(BaseModel):
    """節點輸出"""
    step: ThinkingStep
    associations: list[str] = Field(default_factory=list)
    ideas: list[Idea] = Field(default_factory=list)
    next_mode: ThinkingMode | None = None
    should_stop: bool = False
    error: str | None = None
