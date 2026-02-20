"""
Critic Agent - 批判者

人格特質：
- 深度分析
- 質疑假設
- 找出漏洞
- 嚴謹邏輯

思考風格：深入挖掘問題，從批判中發現新視角
"""

import random

from cgu.agents.base import (
    AgentIdea,
    AgentPersonality,
    CreativeAgent,
    ThinkingStep,
)


class CriticAgent(CreativeAgent):
    """
    批判者 Agent

    專注於深度分析，透過質疑產生洞見
    """

    def __init__(self, llm_client=None):
        super().__init__(AgentPersonality.CRITIC, llm_client)

        # 批判視角
        self.critical_lenses = [
            "可行性",
            "成本效益",
            "風險",
            "倫理",
            "永續性",
            "擴展性",
            "用戶體驗",
            "技術債",
        ]

    async def think_step(self) -> ThinkingStep:
        """
        批判式思考

        每步從一個批判視角分析
        """
        ctx = self.context

        # 選擇批判視角
        lens = random.choice(self.critical_lenses)

        # 模擬批判分析
        critiques = [
            f"{ctx.topic} 在 {lens} 方面的問題是什麼？",
            f"如果 {lens} 失敗，{ctx.topic} 會如何？",
            f"有什麼方法可以改善 {ctx.topic} 的 {lens}？",
        ]

        ctx.associations.extend(critiques)
        ctx.add_thought(f"批判視角: {lens} → 發現 {len(critiques)} 個問題點")

        # 批判者信心隨質疑增加
        ctx.confidence = min(0.85, ctx.confidence + 0.08)
        # 但興奮度較低（謹慎）
        ctx.excitement = max(0.3, ctx.excitement - 0.02)

        return ThinkingStep(
            step_type="critique",
            input_context=f"從 {lens} 視角批判 {ctx.topic}",
            output=f"批判點: {'; '.join(critiques)}",
            confidence=ctx.confidence,
        )

    async def generate_ideas(self, count: int = 3) -> list[AgentIdea]:
        """
        基於批判產生改進型點子

        批判者的點子傾向於「修正」而非「創造」
        """
        ctx = self.context
        ideas = []

        for i in range(count):
            # 從批判中找改進機會
            critique: str | None = None
            if ctx.associations:
                critique = random.choice(ctx.associations)
                content = f"針對「{critique}」的改進方案"
            else:
                content = f"重新審視 {ctx.topic} 的基本假設"

            idea = AgentIdea(
                content=content,
                source_agent=self.id,
                personality=self.personality,
                # 批判者的點子關聯性高但新穎度中等
                association_score=0.7 + random.random() * 0.2,
                novelty_score=0.3 + random.random() * 0.3,
                reasoning=f"透過 {ctx.thinking_depth} 步批判分析發現改進空間",
                parent_concepts=[critique] if critique else [],
            )
            ideas.append(idea)
            ctx.ideas.append(idea)

        return ideas
