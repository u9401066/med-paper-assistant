"""
CGU Thinking Engine

統一思考引擎 - 智能選擇最適合的思考模式

核心理念：
- 簡單問題用快思（Ollama/Copilot 單次）
- 複雜問題用慢想（Multi-Agent 並發）
- 靈感火花需要碰撞（Spark Engine）
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from cgu.llm import CGULLMClient
    from cgu.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


class ThinkingMode(Enum):
    """思考模式"""
    SIMPLE = "simple"       # 單次 LLM 呼叫（快）
    DEEP = "deep"           # Multi-Agent 多步思考（深）
    SPARK = "spark"         # 碰撞產生火花（創）
    HYBRID = "hybrid"       # 快思 + 慢想結合（混合）


class ThinkingDepth(Enum):
    """思考深度"""
    SHALLOW = 1    # 1-2 步，快速出結果
    MEDIUM = 2     # 3-5 步，適度深入
    DEEP = 3       # 5+ 步，深度探索


class ThinkingConfig(BaseModel):
    """思考配置"""
    mode: ThinkingMode = ThinkingMode.HYBRID
    depth: ThinkingDepth = ThinkingDepth.MEDIUM

    # Simple 模式配置
    simple_temperature: float = 0.7
    simple_max_tokens: int = 1024

    # Deep 模式配置
    agent_count: int = 3
    thinking_steps: int = 3
    ideas_per_agent: int = 3

    # Spark 模式配置
    collision_count: int = 5
    spark_threshold: float = 0.6

    # 超時設定
    timeout_seconds: float = 60.0

    class Config:
        use_enum_values = True


@dataclass
class ThinkingResult:
    """思考結果"""
    mode_used: ThinkingMode
    topic: str

    # 核心輸出
    ideas: list[dict] = field(default_factory=list)
    sparks: list[dict] = field(default_factory=list)

    # 過程追蹤
    reasoning_chains: list[dict] = field(default_factory=list)
    agent_contributions: list[dict] = field(default_factory=list)

    # 元數據
    total_time_ms: int = 0
    llm_calls: int = 0

    # 最佳結果
    best_ideas: list[dict] = field(default_factory=list)
    best_spark: dict | None = None

    def to_dict(self) -> dict:
        return {
            "mode_used": self.mode_used.value if isinstance(self.mode_used, ThinkingMode) else self.mode_used,
            "topic": self.topic,
            "ideas": self.ideas,
            "sparks": self.sparks,
            "best_ideas": self.best_ideas,
            "best_spark": self.best_spark,
            "reasoning_chains": self.reasoning_chains,
            "agent_contributions": self.agent_contributions,
            "stats": {
                "total_time_ms": self.total_time_ms,
                "llm_calls": self.llm_calls,
            },
        }


class ThinkingEngine:
    """
    統一思考引擎

    根據配置智能選擇思考模式，並整合多種後端：
    - Ollama（本地）
    - OpenAI-compatible（vLLM、Groq 等）
    - Copilot（框架模式，讓 Copilot 填充）
    """

    def __init__(
        self,
        llm_client: "CGULLMClient | None" = None,
        orchestrator: "AgentOrchestrator | None" = None,
        config: ThinkingConfig | None = None,
    ):
        self.config = config or ThinkingConfig()
        self._llm = llm_client
        self._orchestrator = orchestrator
        self._is_copilot_mode = False

    @property
    def llm(self) -> "CGULLMClient | None":
        """懶加載 LLM Client"""
        if self._llm is None:
            try:
                from cgu.llm import get_llm_client
                self._llm = get_llm_client()
            except Exception as e:
                logger.warning(f"LLM client not available: {e}")
        return self._llm

    @property
    def orchestrator(self) -> "AgentOrchestrator":
        """懶加載 Agent Orchestrator"""
        if self._orchestrator is None:
            from cgu.agents.orchestrator import AgentOrchestrator
            self._orchestrator = AgentOrchestrator(llm_client=self.llm)
        return self._orchestrator

    def set_copilot_mode(self, enabled: bool = True) -> None:
        """設定 Copilot 模式（返回框架讓 Copilot 填充）"""
        self._is_copilot_mode = enabled

    async def think(
        self,
        topic: str,
        mode: ThinkingMode | None = None,
        **kwargs: Any,
    ) -> ThinkingResult:
        """
        統一思考入口

        Args:
            topic: 思考主題
            mode: 強制指定模式，None 則自動選擇
            **kwargs: 覆蓋配置參數

        Returns:
            ThinkingResult 包含所有思考結果
        """
        import time
        start_time = time.time()

        # 合併配置
        config = self.config.model_copy()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # 決定模式
        actual_mode = mode or self._auto_select_mode(topic, config)

        # 執行思考
        if actual_mode == ThinkingMode.SIMPLE:
            result = await self._think_simple(topic, config)
        elif actual_mode == ThinkingMode.DEEP:
            result = await self._think_deep(topic, config)
        elif actual_mode == ThinkingMode.SPARK:
            result = await self._think_spark(topic, config)
        else:  # HYBRID
            result = await self._think_hybrid(topic, config)

        # 計算時間
        result.total_time_ms = int((time.time() - start_time) * 1000)

        return result

    def _auto_select_mode(self, topic: str, config: ThinkingConfig) -> ThinkingMode:
        """
        智能選擇思考模式

        規則：
        - 短主題（<10字）+ 淺度 → SIMPLE
        - 中等主題 + 中等深度 → HYBRID
        - 長主題或深度要求 → DEEP
        - 包含"碰撞"、"火花"、"跨界"關鍵字 → SPARK
        """
        # 關鍵字檢測
        spark_keywords = ["碰撞", "火花", "跨界", "結合", "混搭", "collision", "spark"]
        if any(kw in topic.lower() for kw in spark_keywords):
            return ThinkingMode.SPARK

        # 根據深度配置
        if config.depth == ThinkingDepth.SHALLOW:
            return ThinkingMode.SIMPLE
        elif config.depth == ThinkingDepth.DEEP:
            return ThinkingMode.DEEP

        # 預設混合模式
        return ThinkingMode.HYBRID

    async def _think_simple(
        self,
        topic: str,
        config: ThinkingConfig,
    ) -> ThinkingResult:
        """
        簡單思考 - 單次 LLM 呼叫

        適合：快速發想、初步探索
        """
        result = ThinkingResult(mode_used=ThinkingMode.SIMPLE, topic=topic)

        if self._is_copilot_mode or self.llm is None:
            # Copilot 模式：返回框架
            result.ideas = [
                {
                    "id": i + 1,
                    "content": f"【請 Copilot 思考】{topic} 的創意點子 #{i + 1}",
                    "hint": self._get_thinking_hint(i),
                    "association_score": 0.5,
                }
                for i in range(5)
            ]
            result.reasoning_chains = [{
                "step": "framework",
                "content": f"為 {topic} 建立思考框架，請 Copilot 填充具體內容",
            }]
        else:
            # LLM 模式：實際呼叫
            try:
                from cgu.llm import IdeasOutput, SYSTEM_PROMPT_CREATIVITY

                prompt = f"""請為以下主題產生 5 個創意點子：

主題：{topic}

要求：
1. 每個點子要具體可執行
2. 嘗試不同角度思考
3. 包含至少一個意想不到的想法

請直接列出點子。"""

                output = self.llm.generate_structured(
                    prompt=prompt,
                    response_model=IdeasOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                    temperature=config.simple_temperature,
                )

                result.ideas = [
                    {"id": i + 1, "content": idea, "association_score": 0.7 - i * 0.05}
                    for i, idea in enumerate(output.ideas)
                ]
                result.llm_calls = 1
            except Exception as e:
                logger.warning(f"Simple thinking LLM error: {e}")
                result.ideas = [{"id": 1, "content": f"[Error] {e}", "association_score": 0}]

        # 選出最佳
        result.best_ideas = result.ideas[:3]
        return result

    async def _think_deep(
        self,
        topic: str,
        config: ThinkingConfig,
    ) -> ThinkingResult:
        """
        深度思考 - Multi-Agent 並發

        適合：複雜問題、需要多角度、深入探索
        """
        result = ThinkingResult(mode_used=ThinkingMode.DEEP, topic=topic)

        try:
            # 使用 Orchestrator 執行完整會話
            session = await self.orchestrator.run_creative_session(
                topic=topic,
                thinking_steps=config.thinking_steps,
                idea_count=config.ideas_per_agent,
                collision_count=config.collision_count,
            )

            # 收集所有點子
            all_ideas = []
            for agent_result in session.agent_results:
                result.agent_contributions.append({
                    "agent_id": agent_result["agent_id"],
                    "personality": agent_result["personality"],
                    "idea_count": len(agent_result["ideas"]),
                })

                for idea in agent_result["ideas"]:
                    all_ideas.append({
                        "id": idea["id"],
                        "content": idea["content"],
                        "source": agent_result["personality"],
                        "novelty": idea.get("novelty", 0.5),
                        "association_score": idea.get("association", 0.5),
                    })

            result.ideas = all_ideas

            # 收集火花
            if session.sparks:
                result.sparks = [
                    {
                        "content": spark.spark_content,
                        "source_ideas": [spark.concept_a, spark.concept_b],
                        "spark_value": spark.spark_value,
                    }
                    for spark in session.sparks
                ]
                # 最佳火花
                best = max(session.sparks, key=lambda s: s.spark_value)
                result.best_spark = {
                    "content": best.spark_content,
                    "spark_value": best.spark_value,
                }

            # 最佳點子（按 novelty 排序）
            sorted_ideas = sorted(all_ideas, key=lambda i: i.get("novelty", 0), reverse=True)
            result.best_ideas = sorted_ideas[:5]

        except Exception as e:
            logger.error(f"Deep thinking error: {e}")
            result.ideas = [{"id": 1, "content": f"[Error] {e}", "association_score": 0}]

        return result

    async def _think_spark(
        self,
        topic: str,
        config: ThinkingConfig,
    ) -> ThinkingResult:
        """
        火花思考 - 專注於概念碰撞

        適合：跨界創新、尋找意外連結
        """
        result = ThinkingResult(mode_used=ThinkingMode.SPARK, topic=topic)

        # 先快速產生多個概念
        concepts = await self._extract_concepts(topic)

        try:
            from cgu.agents.spark import SparkEngine
            from cgu.agents.base import AgentIdea, AgentPersonality

            # 將概念轉為 AgentIdea 格式
            ideas = [
                AgentIdea(
                    id=f"c{i}",
                    content=concept,
                    source_agent="concept_extractor",
                    personality=AgentPersonality.EXPLORER,
                    association_score=0.5,
                )
                for i, concept in enumerate(concepts)
            ]

            # 使用 SparkEngine 碰撞
            engine = SparkEngine()
            sparks = engine.collect_and_collide(ideas, max_collisions=config.collision_count)

            result.sparks = [
                {
                    "content": s.spark_content,
                    "source_ideas": [s.concept_a, s.concept_b],
                    "spark_value": s.spark_value,
                    "surprise_score": s.surprise_score,
                }
                for s in sparks
            ]

            # 最佳火花
            if sparks:
                best_sparks = engine.get_best_sparks(top_k=1)
                if best_sparks:
                    best = best_sparks[0]
                    result.best_spark = {
                        "content": best.spark_content,
                        "spark_value": best.spark_value,
                    }

            # 轉換火花為點子
            result.ideas = [
                {
                    "id": f"spark_{i}",
                    "content": s.spark_content,
                    "type": "spark",
                    "spark_value": s.spark_value,
                }
                for i, s in enumerate(sparks)
            ]
            result.best_ideas = result.ideas[:3]

        except Exception as e:
            logger.error(f"Spark thinking error: {e}")
            result.sparks = []

        return result

    async def _think_hybrid(
        self,
        topic: str,
        config: ThinkingConfig,
    ) -> ThinkingResult:
        """
        混合思考 - 快思慢想結合

        流程：
        1. 快思：快速產生初始想法（Simple）
        2. 慢想：深入探索有潛力的方向（Deep）
        3. 碰撞：產生火花（Spark）
        """
        result = ThinkingResult(mode_used=ThinkingMode.HYBRID, topic=topic)

        # Phase 1: 快思
        simple_result = await self._think_simple(topic, config)
        result.ideas.extend(simple_result.ideas)
        result.reasoning_chains.append({
            "phase": "fast_thinking",
            "output": f"快速產生了 {len(simple_result.ideas)} 個初始想法",
        })

        # Phase 2: 慢想（並發 Agent）
        deep_result = await self._think_deep(topic, config)
        result.ideas.extend(deep_result.ideas)
        result.agent_contributions = deep_result.agent_contributions
        result.reasoning_chains.append({
            "phase": "slow_thinking",
            "output": f"深度探索產生了 {len(deep_result.ideas)} 個想法",
        })

        # Phase 3: 碰撞
        if deep_result.sparks:
            result.sparks = deep_result.sparks
            result.best_spark = deep_result.best_spark
            result.reasoning_chains.append({
                "phase": "spark_collision",
                "output": f"概念碰撞產生了 {len(deep_result.sparks)} 個火花",
            })

        # 整合最佳結果
        all_ideas = result.ideas
        sorted_by_novelty = sorted(
            all_ideas,
            key=lambda i: i.get("novelty", i.get("association_score", 0)),
            reverse=True,
        )
        result.best_ideas = sorted_by_novelty[:5]

        # 統計
        result.llm_calls = simple_result.llm_calls + deep_result.llm_calls

        return result

    async def _extract_concepts(self, topic: str) -> list[str]:
        """從主題提取多個概念用於碰撞"""
        if self.llm is None:
            # 簡單分詞
            import re
            words = re.split(r'[\s,，、。！？]+', topic)
            return [w for w in words if len(w) > 1][:5]

        try:
            from cgu.llm import AssociationList, SYSTEM_PROMPT_CREATIVITY

            prompt = f"""從以下主題中提取 5-8 個可以用於創意碰撞的關鍵概念：

主題：{topic}

要求：
1. 概念要具體且有延伸空間
2. 盡量涵蓋不同面向
3. 可以包含隱含概念

請列出概念。"""

            output = self.llm.generate_structured(
                prompt=prompt,
                response_model=AssociationList,
                system_prompt=SYSTEM_PROMPT_CREATIVITY,
            )
            return output.associations[:8]
        except Exception:
            return [topic]

    def _get_thinking_hint(self, index: int) -> str:
        """為 Copilot 模式提供思考提示"""
        hints = [
            "從功能面思考：這能解決什麼問題？",
            "從用戶面思考：誰會需要這個？",
            "從技術面思考：如何實現？",
            "從創新面思考：有什麼意想不到的角度？",
            "從整合面思考：可以跟什麼結合？",
        ]
        return hints[index % len(hints)]


# 預設引擎實例
_engine: ThinkingEngine | None = None


def get_thinking_engine() -> ThinkingEngine:
    """取得全域 ThinkingEngine"""
    global _engine
    if _engine is None:
        _engine = ThinkingEngine()
    return _engine
