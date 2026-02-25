"""
Explorer Agent - 探索者

人格特質：
- 廣度優先
- 好奇心強
- 喜歡發現新可能性
- 聯想豐富

思考風格：從主題向外擴散，尋找各種可能的連結
"""

import random
from cgu.agents.base import (
    CreativeAgent,
    AgentPersonality,
    AgentIdea,
    ThinkingStep,
)


class ExplorerAgent(CreativeAgent):
    """
    探索者 Agent

    專注於廣度探索，產生多樣化的聯想
    """

    def __init__(self, llm_client=None):
        super().__init__(AgentPersonality.EXPLORER, llm_client)

        # 探索方向
        self.exploration_dimensions = [
            "功能", "用戶", "場景", "技術", "情感",
            "歷史", "未來", "文化", "自然", "藝術",
        ]

    async def think_step(self) -> ThinkingStep:
        """
        探索式思考

        每步選擇一個維度進行發散
        """
        ctx = self.context

        # 選擇探索維度
        dim = random.choice(self.exploration_dimensions)

        # 模擬思考（實際應呼叫 LLM）
        if self.llm:
            # TODO: 實際 LLM 呼叫
            pass

        # 模擬聯想
        new_associations = [
            f"{ctx.topic} 在 {dim} 方面的應用",
            f"{dim} 如何影響 {ctx.topic}",
            f"從 {dim} 角度重新定義 {ctx.topic}",
        ]

        ctx.associations.extend(new_associations)
        ctx.add_thought(f"探索維度: {dim} → 發現 {len(new_associations)} 個新連結")

        # 探索越多，信心越高
        ctx.confidence = min(0.9, ctx.confidence + 0.1)
        ctx.excitement = min(1.0, ctx.excitement + 0.05)

        return ThinkingStep(
            step_type="explore",
            input_context=f"探索 {ctx.topic} 的 {dim} 維度",
            output=f"發現連結: {', '.join(new_associations)}",
            confidence=ctx.confidence,
        )

    async def generate_ideas(self, count: int = 3) -> list[AgentIdea]:
        """
        基於探索結果產生點子
        """
        ctx = self.context
        ideas = []

        # 從聯想中組合產生點子
        for i in range(min(count, max(1, len(ctx.associations)))):
            # 隨機組合兩個聯想
            parent_concepts: list[str] = []
            if len(ctx.associations) >= 2:
                a1 = random.choice(ctx.associations)
                a2 = random.choice([a for a in ctx.associations if a != a1])
                content = f"結合「{a1}」與「{a2}」"
                parent_concepts = [a1, a2]
            elif ctx.associations:
                content = ctx.associations[i % len(ctx.associations)]
                parent_concepts = [content]
            else:
                content = f"{ctx.topic} 的新可能"

            idea = AgentIdea(
                content=content,
                source_agent=self.id,
                personality=self.personality,
                association_score=0.6 + random.random() * 0.2,
                novelty_score=0.5 + random.random() * 0.3,
                reasoning=f"透過 {ctx.thinking_depth} 步探索發現",
                parent_concepts=parent_concepts,
            )
            ideas.append(idea)
            ctx.ideas.append(idea)

        return ideas
