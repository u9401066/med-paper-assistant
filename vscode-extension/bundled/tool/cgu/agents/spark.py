"""
Spark Engine - 火花引擎

模擬「靈感一閃」的核心機制

原理：
1. 收集所有 Agent 的獨立思考結果
2. 尋找「低關聯但有潛力」的概念對
3. 強制碰撞產生火花
4. 評估火花的創意價值

靈感 = 意外的連結 = 低關聯度 + 高潛在價值
"""

import random
from dataclasses import dataclass

from cgu.agents.base import AgentIdea, AgentPersonality


@dataclass
class Spark:
    """
    火花 - 兩個概念碰撞的產物
    """

    id: str
    concept_a: str
    concept_b: str
    source_a: str  # Agent ID
    source_b: str
    personality_a: AgentPersonality
    personality_b: AgentPersonality

    # 火花特性
    collision_type: str  # "cross-personality", "same-domain", "random"
    spark_content: str

    # 評分
    surprise_score: float  # 驚喜度（越意外越高）
    potential_score: float  # 潛力值
    coherence_score: float  # 連貫性（能否說得通）

    @property
    def spark_value(self) -> float:
        """
        火花價值 = 驚喜 × 潛力 × 連貫性

        最佳火花：意外但又說得通
        """
        return self.surprise_score * self.potential_score * self.coherence_score


class SparkEngine:
    """
    火花引擎

    負責收集各 Agent 的輸出，進行碰撞，產生靈感火花
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.sparks: list[Spark] = []

    def collect_and_collide(
        self,
        input_data: list[dict] | list[AgentIdea],
        max_collisions: int = 5,
        collision_count: int | None = None,
    ) -> list[Spark]:
        """
        收集結果並產生碰撞（同步版本）

        Args:
            input_data: 可以是 Agent 結果列表 或 AgentIdea 列表
            max_collisions: 要產生的碰撞數量
            collision_count: max_collisions 的別名（向後兼容）
        """
        count = collision_count or max_collisions

        # 收集所有點子
        all_ideas: list[AgentIdea] = []

        for item in input_data:
            if isinstance(item, AgentIdea):
                all_ideas.append(item)
            elif isinstance(item, dict):
                # 從 agent result 提取
                agent_id = item.get("agent_id", "unknown")
                personality_str = item.get("personality", "explorer")
                try:
                    personality = AgentPersonality(personality_str)
                except ValueError:
                    personality = AgentPersonality.EXPLORER

                for idea_dict in item.get("ideas", []):
                    idea = AgentIdea(
                        id=str(idea_dict.get("id", "")),
                        content=idea_dict.get("content", ""),
                        source_agent=agent_id,
                        personality=personality,
                        association_score=idea_dict.get("association", 0.5),
                        novelty_score=idea_dict.get("novelty", 0.5),
                        reasoning=idea_dict.get("reasoning", ""),
                    )
                    all_ideas.append(idea)

        # 產生碰撞
        sparks = self._generate_collisions_sync(all_ideas, count)
        self.sparks.extend(sparks)

        return sparks

    def _get_personality(self, idea: AgentIdea) -> AgentPersonality:
        """取得 idea 的 personality（處理可能是字串或 enum 的情況）"""
        if isinstance(idea.personality, AgentPersonality):
            return idea.personality
        elif isinstance(idea.personality, str):
            return AgentPersonality(idea.personality)
        return AgentPersonality.EXPLORER

    def _generate_collisions_sync(
        self,
        ideas: list[AgentIdea],
        count: int,
    ) -> list[Spark]:
        """
        產生碰撞（同步版本）

        策略：
        1. 優先跨人格碰撞（Explorer × Critic × Wildcard）
        2. 尋找低關聯度的組合
        3. 強制連結
        """
        sparks = []

        if len(ideas) < 2:
            return sparks

        # 按人格分組
        by_personality: dict[AgentPersonality, list[AgentIdea]] = {}
        for idea in ideas:
            p = self._get_personality(idea)
            if p not in by_personality:
                by_personality[p] = []
            by_personality[p].append(idea)

        personalities = list(by_personality.keys())

        for i in range(count):
            spark = self._create_single_collision_sync(ideas, by_personality, personalities, i)
            if spark:
                sparks.append(spark)

        return sparks

    def _create_single_collision_sync(
        self,
        all_ideas: list[AgentIdea],
        by_personality: dict[AgentPersonality, list[AgentIdea]],
        personalities: list[AgentPersonality],
        index: int,
    ) -> Spark | None:
        """創建單一碰撞（同步版本）"""

        collision_type = "random"

        # 策略選擇
        if len(personalities) >= 2 and random.random() < 0.7:
            # 70% 機率跨人格碰撞
            collision_type = "cross-personality"
            p1, p2 = random.sample(personalities, 2)

            if by_personality[p1] and by_personality[p2]:
                idea_a = random.choice(by_personality[p1])
                idea_b = random.choice(by_personality[p2])
            else:
                return None
        else:
            # 隨機碰撞
            if len(all_ideas) >= 2:
                idea_a, idea_b = random.sample(all_ideas, 2)
            else:
                return None

        # 計算碰撞
        spark_content = self._compute_collision_sync(idea_a, idea_b)

        # 計算分數
        surprise = self._compute_surprise(idea_a, idea_b)
        potential = self._compute_potential(idea_a, idea_b)
        coherence = self._compute_coherence(idea_a, idea_b, spark_content)

        # 取得人格（處理字串或 enum）
        personality_a = self._get_personality(idea_a)
        personality_b = self._get_personality(idea_b)

        return Spark(
            id=f"spark_{index}_{random.randint(1000, 9999)}",
            concept_a=idea_a.content,
            concept_b=idea_b.content,
            source_a=idea_a.source_agent,
            source_b=idea_b.source_agent,
            personality_a=personality_a,
            personality_b=personality_b,
            collision_type=collision_type,
            spark_content=spark_content,
            surprise_score=surprise,
            potential_score=potential,
            coherence_score=coherence,
        )

    def _compute_collision_sync(
        self,
        idea_a: AgentIdea,
        idea_b: AgentIdea,
    ) -> str:
        """
        計算碰撞結果

        如果有 LLM，使用 LLM 產生連結
        否則使用模板
        """
        if self.llm:
            # TODO: 使用 LLM 產生更有創意的連結
            pass

        # 取得人格名稱
        p_a = self._get_personality(idea_a).value
        p_b = self._get_personality(idea_b).value

        # 模板方式
        templates = [
            f"如果「{idea_a.content}」遇上「{idea_b.content}」",
            f"結合 {p_a} 的「{idea_a.content}」與 {p_b} 的「{idea_b.content}」",
            f"從「{idea_a.content}」到「{idea_b.content}」的意外連結",
            f"當「{idea_a.content}」被「{idea_b.content}」重新詮釋",
        ]

        return random.choice(templates)

    def _compute_surprise(self, a: AgentIdea, b: AgentIdea) -> float:
        """
        計算驚喜度

        跨人格 + 低關聯 = 高驚喜
        """
        base = 0.5

        # 取得人格
        p_a = self._get_personality(a)
        p_b = self._get_personality(b)

        # 跨人格加分
        if p_a != p_b:
            base += 0.2

        # 關聯度差異大加分（一個高一個低 = 有趣的組合）
        assoc_diff = abs(a.association_score - b.association_score)
        base += assoc_diff * 0.2

        # Wildcard 參與加分
        if AgentPersonality.WILDCARD in (p_a, p_b):
            base += 0.1

        return min(1.0, base + random.random() * 0.1)

    def _compute_potential(self, a: AgentIdea, b: AgentIdea) -> float:
        """
        計算潛力值

        基於兩個點子的新穎度
        """
        avg_novelty = (a.novelty_score + b.novelty_score) / 2
        return min(1.0, avg_novelty + random.random() * 0.2)

    def _compute_coherence(
        self,
        a: AgentIdea,
        b: AgentIdea,
        spark_content: str,
    ) -> float:
        """
        計算連貫性

        TODO: 使用 LLM 評估是否「說得通」
        """
        # 簡單啟發式：如果有共同的 parent_concepts，連貫性較高
        common = set(a.parent_concepts) & set(b.parent_concepts)
        base = 0.5 + len(common) * 0.1

        return min(1.0, base + random.random() * 0.2)

    def get_best_sparks(self, top_k: int = 3) -> list[Spark]:
        """取得最佳火花"""
        sorted_sparks = sorted(
            self.sparks,
            key=lambda s: s.spark_value,
            reverse=True,
        )
        return sorted_sparks[:top_k]

    def format_spark_report(self) -> str:
        """產生火花報告"""
        lines = ["=" * 50, "⚡ 火花報告 ⚡", "=" * 50, ""]

        for i, spark in enumerate(self.get_best_sparks(5), 1):
            lines.extend(
                [
                    f"#{i} 火花值: {spark.spark_value:.2f}",
                    f"   類型: {spark.collision_type}",
                    f"   概念A ({spark.personality_a.value}): {spark.concept_a}",
                    f"   概念B ({spark.personality_b.value}): {spark.concept_b}",
                    f"   火花: {spark.spark_content}",
                    f"   驚喜: {spark.surprise_score:.2f} | 潛力: {spark.potential_score:.2f} | 連貫: {spark.coherence_score:.2f}",
                    "",
                ]
            )

        return "\n".join(lines)
