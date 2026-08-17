"""
CreativityCore - 統一創意引擎

整合三大核心機制：
1. AnalogyEngine - 跨領域類比搜尋
2. GraphTraversalEngine - 概念圖譜遍歷
3. AdversarialEngine - 對抗式創意進化

這不是「模擬創意」，而是「實現創意的機制」
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from cgu.core.adversarial import (
    AdversarialEngine,
)
from cgu.core.analogy import AnalogyEngine
from cgu.core.graph import (
    GraphTraversalEngine,
    get_graph_engine,
)

logger = logging.getLogger(__name__)


class CreativityMode(StrEnum):
    """創意模式"""

    ANALOGY = "analogy"  # 類比搜尋
    EXPLORATION = "exploration"  # 圖譜探索
    ADVERSARIAL = "adversarial"  # 對抗進化
    FULL = "full"  # 完整流程（三者結合）


@dataclass
class CreativityConfig:
    """創意配置"""

    # 類比配置
    max_analogies: int = 5
    min_structural_match: float = 0.3

    # 圖譜配置
    max_paths: int = 5
    min_path_hops: int = 3
    max_path_hops: int = 7

    # 對抗配置
    adversarial_rounds: int = 5
    min_evolution_threshold: float = 0.1

    # 整體配置
    timeout_seconds: float = 60.0


class CreativityResult(BaseModel):
    """創意生成結果"""

    mode: str
    topic: str

    # 類比結果
    analogies: list[dict] = Field(default_factory=list)
    best_analogy: dict | None = None

    # 圖譜結果
    concept_paths: list[dict] = Field(default_factory=list)
    unexpected_connections: list[dict] = Field(default_factory=list)

    # 對抗結果
    evolved_idea: str = ""
    evolution_trajectory: list[str] = Field(default_factory=list)
    adversarial_rounds: int = 0

    # 整合洞察
    insights: list[str] = Field(default_factory=list)
    final_creative_output: str = ""

    # 品質指標
    novelty_score: float = 0.0
    usefulness_score: float = 0.0
    surprise_score: float = 0.0

    @property
    def quality_score(self) -> float:
        """NUS 模型：Novelty × Usefulness × Surprise"""
        return self.novelty_score * self.usefulness_score * self.surprise_score


class CreativityCore:
    """
    統一創意引擎

    核心價值：
    - 不是 Prompt 模板，是結構化機制
    - 不是隨機碰撞，是有意義的連結
    - 不是一次性生成，是對抗式進化
    """

    def __init__(
        self,
        config: CreativityConfig | None = None,
        llm_client: Any = None,
    ):
        self.config = config or CreativityConfig()
        self.llm = llm_client

        # 三大引擎
        self._analogy_engine: AnalogyEngine | None = None
        self._graph_engine: GraphTraversalEngine | None = None
        self._adversarial_engine: AdversarialEngine | None = None

    @property
    def analogy_engine(self) -> AnalogyEngine:
        """懶加載類比引擎"""
        if self._analogy_engine is None:
            self._analogy_engine = AnalogyEngine(self.llm)
        return self._analogy_engine

    @property
    def graph_engine(self) -> GraphTraversalEngine:
        """懶加載圖譜引擎"""
        if self._graph_engine is None:
            self._graph_engine = get_graph_engine()
        return self._graph_engine

    @property
    def adversarial_engine(self) -> AdversarialEngine:
        """懶加載對抗引擎"""
        if self._adversarial_engine is None:
            self._adversarial_engine = AdversarialEngine(self.llm)
        return self._adversarial_engine

    async def generate(
        self,
        topic: str,
        mode: CreativityMode = CreativityMode.FULL,
        initial_idea: str | None = None,
        source_domain: str | None = None,
    ) -> CreativityResult:
        """
        統一創意生成入口

        Args:
            topic: 創意主題/問題
            mode: 創意模式
            initial_idea: 初始想法（用於對抗模式）
            source_domain: 問題所在領域（用於類比模式）
        """
        result = CreativityResult(mode=mode.value, topic=topic)

        if mode == CreativityMode.ANALOGY:
            await self._run_analogy(topic, source_domain, result)
        elif mode == CreativityMode.EXPLORATION:
            await self._run_exploration(topic, result)
        elif mode == CreativityMode.ADVERSARIAL:
            await self._run_adversarial(topic, initial_idea, result)
        else:  # FULL
            await self._run_full_pipeline(topic, initial_idea, source_domain, result)

        return result

    async def _run_analogy(
        self,
        topic: str,
        source_domain: str | None,
        result: CreativityResult,
    ) -> None:
        """執行類比搜尋"""
        analogies = self.analogy_engine.find_analogies(
            problem=topic,
            source_domain=source_domain,
            max_analogies=self.config.max_analogies,
        )

        result.analogies = [
            {
                "source_domain": a.source_domain,
                "target_domain": a.target_domain,
                "mapping": a.mapping_explanation,
                "insight": a.insight,
                "quality": a.quality_score,
            }
            for a in analogies
        ]

        if analogies:
            best = analogies[0]
            result.best_analogy = {
                "source_domain": best.source_domain,
                "insight": best.insight,
                "mapping": best.mapping_explanation,
            }
            result.insights.append(f"類比洞察：{best.insight}")
            result.novelty_score = best.surface_distance
            result.surprise_score = best.insight_potential

    async def _run_exploration(
        self,
        topic: str,
        result: CreativityResult,
    ) -> None:
        """執行圖譜探索"""
        # 提取主題中的概念
        concepts = self._extract_concepts(topic)

        if len(concepts) >= 2:
            # 找概念間的連結
            for i, concept_a in enumerate(concepts[:-1]):
                for concept_b in concepts[i + 1 :]:
                    connection = self.graph_engine.find_unexpected_connection(concept_a, concept_b)
                    if connection.get("creative_paths"):
                        result.unexpected_connections.append(connection)

                        # 提取洞察
                        if connection.get("insight"):
                            result.insights.append(
                                f"意外連結：{concept_a} ↔ {concept_b} - {connection['insight']}"
                            )

        # 計算驚喜度
        if result.unexpected_connections:
            avg_surprise = sum(
                c.get("surprise_score", 0) for c in result.unexpected_connections
            ) / len(result.unexpected_connections)
            result.surprise_score = avg_surprise
            result.novelty_score = avg_surprise * 0.8

    async def _run_adversarial(
        self,
        topic: str,
        initial_idea: str | None,
        result: CreativityResult,
    ) -> None:
        """執行對抗進化"""
        idea = initial_idea or f"針對「{topic}」的初步想法"

        evolved = await self.adversarial_engine.adversarial_evolve(
            initial_idea=idea,
            topic=topic,
            max_rounds=self.config.adversarial_rounds,
        )

        result.evolved_idea = evolved.final_idea
        result.evolution_trajectory = evolved.evolution_trajectory
        result.adversarial_rounds = evolved.total_rounds
        result.novelty_score = evolved.novelty_improvement
        result.usefulness_score = evolved.robustness_score

        result.insights.append(
            f"經過 {evolved.total_rounds} 輪對抗進化，"
            f"想法穩健度提升至 {evolved.robustness_score:.0%}"
        )

    async def _run_full_pipeline(
        self,
        topic: str,
        initial_idea: str | None,
        source_domain: str | None,
        result: CreativityResult,
    ) -> None:
        """
        執行完整的創意流程

        流程：
        1. 圖譜探索 - 展開問題空間
        2. 類比搜尋 - 跨域尋找靈感
        3. 對抗進化 - 強化最終想法
        """
        # === Step 1: 圖譜探索 ===
        logger.info("Step 1: 圖譜探索")
        await self._run_exploration(topic, result)

        # === Step 2: 類比搜尋 ===
        logger.info("Step 2: 類比搜尋")
        await self._run_analogy(topic, source_domain, result)

        # === Step 3: 綜合產生初始想法 ===
        logger.info("Step 3: 綜合產生初始想法")
        synthesized_idea = self._synthesize_initial_idea(topic, result)

        # === Step 4: 對抗進化 ===
        logger.info("Step 4: 對抗進化")
        idea_to_evolve = initial_idea or synthesized_idea
        await self._run_adversarial(topic, idea_to_evolve, result)

        # === Step 5: 產生最終輸出 ===
        result.final_creative_output = self._generate_final_output(result)

        # 計算綜合品質
        result.usefulness_score = max(
            result.usefulness_score,
            0.5 if result.analogies else 0.3,
        )

    def _extract_concepts(self, text: str) -> list[str]:
        """從文本中提取概念"""
        # 簡單的關鍵詞提取
        # TODO: 使用 NLP 或 LLM 進行更好的提取
        import re

        # 移除標點，分詞
        words = re.split(r"[\s,，、。！？：；]+", text)
        words = [w.strip() for w in words if len(w.strip()) > 1]

        # 檢查哪些在圖譜中有
        concepts = []
        for word in words:
            if self.graph_engine.graph.has_node(word):
                concepts.append(word)

        # 如果圖譜中沒有，返回前幾個詞
        if not concepts and words:
            return words[:3]

        return concepts[:5]

    def _synthesize_initial_idea(
        self,
        topic: str,
        result: CreativityResult,
    ) -> str:
        """綜合探索和類比結果，產生初始想法"""
        parts = [f"針對「{topic}」："]

        # 從類比中提取
        if result.best_analogy:
            parts.append(
                f"借鏡「{result.best_analogy['source_domain']}」的經驗 - "
                f"{result.best_analogy['insight']}"
            )

        # 從圖譜連結中提取
        if result.unexpected_connections:
            conn = result.unexpected_connections[0]
            if conn.get("insight"):
                parts.append(f"利用意外連結：{conn['insight']}")

        return "；".join(parts) if len(parts) > 1 else f"關於「{topic}」的創意想法"

    def _generate_final_output(self, result: CreativityResult) -> str:
        """產生最終的創意輸出"""
        sections = []

        # 核心創意
        if result.evolved_idea:
            sections.append(f"💡 核心創意\n{result.evolved_idea}")

        # 類比靈感
        if result.best_analogy:
            sections.append(
                f"🔗 類比靈感\n"
                f"從「{result.best_analogy['source_domain']}」領域獲得啟發：\n"
                f"{result.best_analogy['insight']}"
            )

        # 意外連結
        if result.unexpected_connections:
            conn_texts = []
            for conn in result.unexpected_connections[:2]:
                if conn.get("insight"):
                    conn_texts.append(f"  • {conn['insight']}")
            if conn_texts:
                sections.append("🌉 意外連結\n" + "\n".join(conn_texts))

        # 進化過程
        if result.evolution_trajectory and len(result.evolution_trajectory) > 1:
            sections.append(
                f"🔄 經過 {result.adversarial_rounds} 輪對抗進化\n"
                f"穩健度：{result.usefulness_score:.0%} | "
                f"新穎度：{result.novelty_score:.0%}"
            )

        return "\n\n".join(sections) if sections else result.evolved_idea

    def format_report(self, result: CreativityResult) -> str:
        """產生完整的創意報告"""
        lines = [
            "═" * 70,
            "🎨 CGU v2 創意報告",
            "═" * 70,
            "",
            f"📋 主題：{result.topic}",
            f"🎯 模式：{result.mode}",
            f"⭐ 品質分數：{result.quality_score:.2f}",
            "",
            "─" * 70,
            "📊 品質指標",
            f"  • 新穎度 (Novelty)：{result.novelty_score:.0%}",
            f"  • 實用度 (Usefulness)：{result.usefulness_score:.0%}",
            f"  • 驚喜度 (Surprise)：{result.surprise_score:.0%}",
            "",
        ]

        if result.analogies:
            lines.extend(
                [
                    "─" * 70,
                    f"🔗 類比搜尋（找到 {len(result.analogies)} 個）",
                ]
            )
            for a in result.analogies[:3]:
                lines.append(
                    f"  • [{a['source_domain']}] {a['insight'][:60]}... (品質: {a['quality']:.0%})"
                )
            lines.append("")

        if result.unexpected_connections:
            lines.extend(
                [
                    "─" * 70,
                    f"🌉 意外連結（找到 {len(result.unexpected_connections)} 個）",
                ]
            )
            for conn in result.unexpected_connections[:3]:
                if conn.get("creative_paths"):
                    path = conn["creative_paths"][0]
                    lines.append(f"  • {path['path'][:60]}... (新穎度: {path['novelty']:.0%})")
            lines.append("")

        if result.evolution_trajectory:
            lines.extend(
                [
                    "─" * 70,
                    f"⚔️ 對抗進化（{result.adversarial_rounds} 輪）",
                    f"  起點：{result.evolution_trajectory[0][:50]}...",
                    f"  終點：{result.evolution_trajectory[-1][:50]}...",
                    "",
                ]
            )

        lines.extend(
            [
                "═" * 70,
                "🏆 最終創意輸出",
                "═" * 70,
                "",
                result.final_creative_output or result.evolved_idea or "（無輸出）",
                "",
                "═" * 70,
            ]
        )

        return "\n".join(lines)


# === 便捷函數 ===

_core: CreativityCore | None = None


def get_creativity_core() -> CreativityCore:
    """取得全域創意引擎"""
    global _core
    if _core is None:
        _core = CreativityCore()
    return _core


async def create(
    topic: str,
    mode: str = "full",
    initial_idea: str | None = None,
    domain: str | None = None,
) -> CreativityResult:
    """
    快速創意生成

    Args:
        topic: 創意主題
        mode: "analogy" / "exploration" / "adversarial" / "full"
        initial_idea: 初始想法
        domain: 問題領域

    Example:
        >>> result = await create("如何讓遠端工作更有效率")
        >>> print(result.final_creative_output)
    """
    core = get_creativity_core()
    mode_enum = CreativityMode(mode)
    return await core.generate(topic, mode_enum, initial_idea, domain)


def create_sync(
    topic: str,
    mode: str = "full",
    initial_idea: str | None = None,
    domain: str | None = None,
) -> CreativityResult:
    """同步版本的 create"""
    import asyncio

    return asyncio.run(create(topic, mode, initial_idea, domain))
