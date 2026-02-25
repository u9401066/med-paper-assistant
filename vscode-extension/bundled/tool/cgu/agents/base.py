"""
CGU Agent Base Classes

定義 Agent 的基礎結構和人格特質
每個 Agent 有獨立的 Context，避免污染
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel


class AgentPersonality(Enum):
    """Agent 人格類型 - 影響思考風格"""
    EXPLORER = "explorer"      # 探索者：廣度優先，尋找可能性
    CRITIC = "critic"          # 批判者：深度分析，找出問題
    WILDCARD = "wildcard"      # 狂想者：打破規則，極端想法
    SYNTHESIZER = "synthesizer" # 整合者：融合觀點，尋找共識
    CONTRARIAN = "contrarian"  # 反骨者：逆向思考，質疑一切


@dataclass
class AgentContext:
    """
    Agent 獨立 Context

    每個 Agent 維護自己的思考空間，避免污染其他 Agent
    """
    agent_id: str
    personality: AgentPersonality
    topic: str

    # 獨立的思考狀態
    associations: list[str] = field(default_factory=list)
    ideas: list["AgentIdea"] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)

    # 思考深度追蹤
    thinking_depth: int = 0
    max_depth: int = 5

    # 情緒/直覺狀態（模擬人類思考）
    confidence: float = 0.5
    excitement: float = 0.5  # 對主題的興奮度

    def add_thought(self, thought: str) -> None:
        """記錄一個思考步驟"""
        self.reasoning_chain.append(thought)
        self.thinking_depth += 1

    def is_exhausted(self) -> bool:
        """是否已經思考到極限"""
        return self.thinking_depth >= self.max_depth


class AgentIdea(BaseModel):
    """Agent 產生的點子"""
    id: str = ""
    content: str
    source_agent: str
    personality: AgentPersonality
    association_score: float = 0.5
    novelty_score: float = 0.5
    reasoning: str = ""

    # 點子的「基因」- 用於追蹤來源
    parent_concepts: list[str] = []

    model_config = {"use_enum_values": True}


@dataclass
class ThinkingStep:
    """單步思考記錄"""
    step_type: str
    input_context: str
    output: str
    confidence: float
    duration_ms: int = 0


class CreativeAgent(ABC):
    """
    創意 Agent 基類

    核心設計原則：
    1. 獨立 Context - 不共享思考空間
    2. 人格驅動 - 不同人格產生不同風格的想法
    3. 多步思考 - 可以深入思考多個回合
    4. 可並發 - 支援 asyncio 並發執行
    """

    def __init__(
        self,
        personality: AgentPersonality,
        llm_client: Any = None,
    ):
        self.id = f"{personality.value}_{uuid.uuid4().hex[:6]}"
        self.personality = personality
        self.llm = llm_client
        self._context: AgentContext | None = None

    @property
    def context(self) -> AgentContext:
        if self._context is None:
            raise RuntimeError("Agent context not initialized. Call start_session first.")
        return self._context

    def start_session(self, topic: str, max_depth: int = 5) -> None:
        """
        開始新的思考會話

        每次會話都是全新的 Context，避免污染
        """
        self._context = AgentContext(
            agent_id=self.id,
            personality=self.personality,
            topic=topic,
            max_depth=max_depth,
        )

    def end_session(self) -> list[AgentIdea]:
        """結束會話，返回所有點子"""
        ideas = self.context.ideas.copy()
        self._context = None
        return ideas

    @abstractmethod
    async def think_step(self) -> ThinkingStep:
        """
        執行一步思考

        子類實作不同的思考風格
        """
        pass

    @abstractmethod
    async def generate_ideas(self, count: int = 3) -> list[AgentIdea]:
        """
        產生點子

        基於當前 context 產生創意點子
        """
        pass

    async def deep_think(self, steps: int = 3) -> list[ThinkingStep]:
        """
        多步深入思考

        連續執行多個思考步驟，逐步深入
        """
        results = []
        for _ in range(steps):
            if self.context.is_exhausted():
                break
            step = await self.think_step()
            results.append(step)
        return results

    async def run_full_session(
        self,
        topic: str,
        thinking_steps: int = 3,
        idea_count: int = 3,
    ) -> dict:
        """
        執行完整的思考會話

        1. 初始化 context
        2. 多步思考
        3. 產生點子
        4. 清理並返回結果
        """
        self.start_session(topic)

        # 多步思考
        thinking = await self.deep_think(thinking_steps)

        # 產生點子
        ideas = await self.generate_ideas(idea_count)

        # 收集結果
        result = {
            "agent_id": self.id,
            "personality": self.personality.value,
            "topic": topic,
            "thinking_steps": [
                {
                    "type": s.step_type,
                    "output": s.output,
                    "confidence": s.confidence,
                }
                for s in thinking
            ],
            "ideas": [
                {
                    "id": i.id,
                    "content": i.content,
                    "novelty": i.novelty_score,
                    "association": i.association_score,
                    "reasoning": i.reasoning,
                }
                for i in ideas
            ],
            "reasoning_chain": self.context.reasoning_chain,
        }

        self.end_session()
        return result


class AgentMessage(BaseModel):
    """Agent 間通訊的訊息"""
    from_agent: str
    to_agent: str | None = None  # None = 廣播
    message_type: str  # "idea", "challenge", "spark", "merge"
    content: Any
    metadata: dict = {}


class AgentPool:
    """
    Agent 池 - 管理多個並發 Agent
    """

    def __init__(self):
        self.agents: dict[str, CreativeAgent] = {}
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()

    def register(self, agent: CreativeAgent) -> None:
        """註冊 Agent"""
        self.agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> CreativeAgent | None:
        return self.agents.get(agent_id)

    async def broadcast(self, message: AgentMessage) -> None:
        """廣播訊息給所有 Agent"""
        await self.message_queue.put(message)

    async def run_all_parallel(
        self,
        topic: str,
        thinking_steps: int = 3,
        idea_count: int = 3,
    ) -> list[dict]:
        """
        並發執行所有 Agent

        使用 asyncio.gather 實現真正的並發
        """
        tasks = [
            agent.run_full_session(topic, thinking_steps, idea_count)
            for agent in self.agents.values()
        ]

        # 並發執行，互不干擾
        results = await asyncio.gather(*tasks)
        return list(results)
