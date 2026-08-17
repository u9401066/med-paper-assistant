"""
Agent Orchestrator - 協調者

統籌多 Agent 並發創意生成流程

架構：
                    ┌─────────────────┐
                    │   Orchestrator  │
                    │   (協調者)       │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │ Explorer   │    │ Critic     │    │ Wildcard   │
    │ Agent      │    │ Agent      │    │ Agent      │
    │ (探索者)    │    │ (批判者)    │    │ (狂想者)    │
    └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
          │                 │                 │
          │ 獨立思考        │ 獨立思考         │ 獨立思考
          │                 │                 │
          ▼                 ▼                 ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │ Ideas A    │    │ Ideas B    │    │ Ideas C    │
    └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │   Spark Engine  │
                    │   (火花引擎)     │
                    │  碰撞 + 融合     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Final Ideas    │
                    │  (最終創意)      │
                    └─────────────────┘
"""

from dataclasses import dataclass, field
from typing import Any

from cgu.agents.base import AgentPool, CreativeAgent
from cgu.agents.critic import CriticAgent
from cgu.agents.explorer import ExplorerAgent
from cgu.agents.spark import Spark, SparkEngine
from cgu.agents.wildcard import WildcardAgent


@dataclass
class OrchestratorConfig:
    """協調者配置"""

    # Agent 配置
    enable_explorer: bool = True
    enable_critic: bool = True
    enable_wildcard: bool = True

    # 思考配置
    thinking_steps: int = 3  # 每個 Agent 思考幾步
    ideas_per_agent: int = 3  # 每個 Agent 產生幾個點子

    # 碰撞配置
    collision_count: int = 5  # 產生幾個火花
    top_sparks: int = 3  # 保留幾個最佳火花

    # 迭代配置
    max_iterations: int = 2  # 最多迭代幾輪


@dataclass
class CreativeSession:
    """創意會話結果"""

    topic: str
    agent_results: list[dict] = field(default_factory=list)
    sparks: list[Spark] = field(default_factory=list)
    final_ideas: list[dict] = field(default_factory=list)
    iterations: int = 0

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "iterations": self.iterations,
            "agent_count": len(self.agent_results),
            "agent_results": self.agent_results,
            "sparks": [
                {
                    "content": s.spark_content,
                    "source_ideas": [s.concept_a, s.concept_b],
                    "spark_value": s.spark_value,
                    "type": s.collision_type,
                    "surprise": s.surprise_score,
                    "potential": s.potential_score,
                }
                for s in self.sparks
            ],
            "final_ideas": self.final_ideas,
        }


class AgentOrchestrator:
    """
    Agent 協調者

    負責：
    1. 創建和管理多個 Agent
    2. 並發執行思考
    3. 協調火花碰撞
    4. 整合最終結果
    """

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        llm_client: Any = None,
    ):
        self.config = config or OrchestratorConfig()
        self.llm = llm_client
        self.pool = AgentPool()
        self.spark_engine = SparkEngine(llm_client)

        # 根據配置創建 Agents
        self._setup_agents()

    def _setup_agents(self) -> None:
        """設置 Agent 池"""
        if self.config.enable_explorer:
            self.pool.register(ExplorerAgent(self.llm))

        if self.config.enable_critic:
            self.pool.register(CriticAgent(self.llm))

        if self.config.enable_wildcard:
            self.pool.register(WildcardAgent(self.llm))

    def add_custom_agent(self, agent: CreativeAgent) -> None:
        """添加自定義 Agent"""
        self.pool.register(agent)

    async def run_creative_session(
        self,
        topic: str,
        creativity_level: int = 1,
        thinking_steps: int | None = None,
        idea_count: int | None = None,
        collision_count: int | None = None,
    ) -> CreativeSession:
        """
        執行完整的創意會話

        流程：
        1. 並發執行所有 Agent 的獨立思考
        2. 收集結果進行火花碰撞
        3. 整合最終創意
        """
        session = CreativeSession(topic=topic)

        # 使用傳入參數或預設配置
        _thinking_steps = thinking_steps or self.config.thinking_steps
        _idea_count = idea_count or self.config.ideas_per_agent
        _collision_count = collision_count or self.config.collision_count

        for iteration in range(self.config.max_iterations):
            session.iterations = iteration + 1

            # === Phase 1: 並發思考 ===
            agent_results = await self.pool.run_all_parallel(
                topic=topic,
                thinking_steps=_thinking_steps,
                idea_count=_idea_count,
            )
            session.agent_results = agent_results

            # === Phase 2: 火花碰撞 ===
            sparks = self.spark_engine.collect_and_collide(
                agent_results,
                collision_count=_collision_count,
            )
            session.sparks = sparks  # 直接使用返回的火花列表

            # === Phase 3: 整合結果 ===
            session.final_ideas = self._integrate_results(agent_results, session.sparks)

            # 檢查是否需要繼續迭代
            if self._should_stop(session):
                break

        return session

    def _integrate_results(
        self,
        agent_results: list[dict],
        best_sparks: list[Spark],
    ) -> list[dict]:
        """
        整合 Agent 結果和火花
        """
        final = []

        # 從各 Agent 取最佳點子
        for result in agent_results:
            for idea in result["ideas"][:2]:  # 每個 Agent 取 2 個
                final.append(
                    {
                        "content": idea["content"],
                        "source": result["personality"],
                        "type": "agent_idea",
                        "score": idea.get("novelty", 0.5) * idea.get("association", 0.5),
                    }
                )

        # 加入火花
        for spark in best_sparks:
            final.append(
                {
                    "content": spark.spark_content,
                    "source": f"{spark.personality_a.value} × {spark.personality_b.value}",
                    "type": "spark",
                    "score": spark.spark_value,
                }
            )

        # 按分數排序
        final.sort(key=lambda x: x["score"], reverse=True)

        return final

    def _should_stop(self, session: CreativeSession) -> bool:
        """判斷是否應該停止迭代"""
        # 有足夠好的火花就停止
        return bool(session.sparks and session.sparks[0].spark_value > 0.7)

    def print_session_report(self, session: CreativeSession) -> str:
        """產生會話報告"""
        lines = [
            "=" * 60,
            f"🎯 創意會話報告：{session.topic}",
            "=" * 60,
            "",
            f"📊 統計：{len(session.agent_results)} 個 Agent，{session.iterations} 輪迭代",
            "",
            "🤖 Agent 貢獻：",
        ]

        for result in session.agent_results:
            lines.append(f"  [{result['personality']}] {len(result['ideas'])} 個點子")

        lines.extend(["", "⚡ 最佳火花："])
        for i, spark in enumerate(session.sparks, 1):
            lines.append(f"  #{i} ({spark.spark_value:.2f}): {spark.spark_content}")

        lines.extend(["", "💡 最終創意 Top 5："])
        for i, idea in enumerate(session.final_ideas[:5], 1):
            lines.append(f"  {i}. [{idea['source']}] {idea['content']}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# === 便捷函數 ===


async def quick_brainstorm(
    topic: str,
    creativity_level: int = 1,
) -> dict:
    """
    快速腦力激盪

    一行程式碼啟動多 Agent 並發創意生成
    """
    orchestrator = AgentOrchestrator()
    session = await orchestrator.run_creative_session(topic, creativity_level)

    print(orchestrator.print_session_report(session))

    return session.to_dict()


async def deep_brainstorm(
    topic: str,
    thinking_steps: int = 5,
    collision_count: int = 10,
) -> dict:
    """
    深度腦力激盪

    更多思考步驟，更多碰撞
    """
    config = OrchestratorConfig(
        thinking_steps=thinking_steps,
        ideas_per_agent=5,
        collision_count=collision_count,
        top_sparks=5,
        max_iterations=3,
    )

    orchestrator = AgentOrchestrator(config)
    session = await orchestrator.run_creative_session(topic)

    print(orchestrator.print_session_report(session))

    return session.to_dict()
