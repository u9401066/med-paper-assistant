"""
Wildcard Agent - 狂想者

人格特質：
- 打破規則
- 極端想法
- 隨機跳躍
- 不受限制

思考風格：刻意違反常規，產生「瘋狂」但可能有價值的點子
這是模擬「靈感一閃」的主要 Agent
"""

import random

from cgu.agents.base import (
    AgentIdea,
    AgentPersonality,
    CreativeAgent,
    ThinkingStep,
)


class WildcardAgent(CreativeAgent):
    """
    狂想者 Agent

    專門產生非常規、跨界、甚至「荒謬」的想法
    低關聯度 + 高新穎度 = 靈感火花的來源
    """

    def __init__(self, llm_client=None):
        super().__init__(AgentPersonality.WILDCARD, llm_client)

        # 狂想技巧
        self.wildcard_techniques = [
            "反轉",  # 完全相反
            "極端化",  # 放大 100 倍
            "隨機跨界",  # 隨機連結不相關領域
            "時間旅行",  # 放到過去/未來
            "擬人化",  # 如果它是人會怎樣
            "縮小化",  # 縮到極小
            "合併矛盾",  # 強制結合對立概念
            "荒謬假設",  # 如果物理定律不存在
        ]

        # 隨機跨界用的領域庫
        self.random_domains = [
            "烹飪",
            "太空",
            "音樂",
            "體育",
            "宗教",
            "昆蟲",
            "海洋",
            "童話",
            "武器",
            "醫療",
            "建築",
            "哲學",
            "遊戲",
            "時尚",
            "農業",
        ]

    async def think_step(self) -> ThinkingStep:
        """
        狂想式思考

        每步使用一個狂想技巧
        """
        ctx = self.context

        # 隨機選擇技巧
        technique = random.choice(self.wildcard_techniques)

        # 應用技巧
        wild_thoughts = self._apply_technique(technique, ctx.topic)

        ctx.associations.extend(wild_thoughts)
        ctx.add_thought(f"狂想技巧: {technique} → 產生 {len(wild_thoughts)} 個瘋狂想法")

        # 狂想者信心波動大
        ctx.confidence = 0.3 + random.random() * 0.4
        # 但興奮度很高！
        ctx.excitement = min(1.0, ctx.excitement + 0.15)

        return ThinkingStep(
            step_type="wildcard",
            input_context=f"對 {ctx.topic} 使用「{technique}」技巧",
            output=f"狂想: {'; '.join(wild_thoughts)}",
            confidence=ctx.confidence,
        )

    def _apply_technique(self, technique: str, topic: str) -> list[str]:
        """應用狂想技巧"""
        if technique == "反轉":
            return [
                f"如果 {topic} 完全相反會怎樣？",
                f"{topic} 的對立面是什麼？",
                f"反{topic} 的價值在哪？",
            ]
        elif technique == "極端化":
            return [
                f"{topic} 放大 100 倍",
                f"全世界都在用 {topic}",
                f"{topic} 成為唯一選擇",
            ]
        elif technique == "隨機跨界":
            domain = random.choice(self.random_domains)
            return [
                f"{topic} × {domain}",
                f"用 {domain} 的方式做 {topic}",
                f"如果 {domain} 專家來設計 {topic}",
            ]
        elif technique == "時間旅行":
            return [
                f"1000 年前的 {topic}",
                f"1000 年後的 {topic}",
                f"如果 {topic} 從不存在",
            ]
        elif technique == "擬人化":
            return [
                f"如果 {topic} 是一個人",
                f"{topic} 的情緒是什麼",
                f"{topic} 會夢到什麼",
            ]
        elif technique == "縮小化":
            return [
                f"極簡版的 {topic}",
                f"一個原子大小的 {topic}",
                f"{topic} 的最小可行版本",
            ]
        elif technique == "合併矛盾":
            opposites = ["快與慢", "大與小", "新與舊", "簡單與複雜"]
            opp = random.choice(opposites)
            return [
                f"{topic} 同時是 {opp}",
                f"矛盾的 {topic}",
                f"自相矛盾但有效的 {topic}",
            ]
        else:  # 荒謬假設
            return [
                f"如果重力消失，{topic} 會如何",
                f"如果時間倒流，{topic} 會如何",
                f"如果所有人都能讀心，{topic} 會如何",
            ]

    async def generate_ideas(self, count: int = 3) -> list[AgentIdea]:
        """
        產生狂想型點子

        特色：低關聯度但高新穎度
        """
        ctx = self.context
        ideas = []

        for i in range(count):
            # 隨機組合狂想
            if len(ctx.associations) >= 2:
                w1 = random.choice(ctx.associations)
                w2 = random.choice([w for w in ctx.associations if w != w1])
                content = f"狂想碰撞：{w1} + {w2}"
                parents = [w1, w2]
            elif ctx.associations:
                w1 = random.choice(ctx.associations)
                content = f"狂想：{w1}"
                parents = [w1]
            else:
                content = f"{ctx.topic} 的荒謬版本"
                parents = []

            idea = AgentIdea(
                content=content,
                source_agent=self.id,
                personality=self.personality,
                # 狂想者：低關聯但高新穎
                association_score=0.1 + random.random() * 0.3,
                novelty_score=0.7 + random.random() * 0.3,
                reasoning=f"透過「{random.choice(self.wildcard_techniques)}」狂想產生",
                parent_concepts=parents,
            )
            ideas.append(idea)
            ctx.ideas.append(idea)

        return ideas
