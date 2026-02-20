"""
AdversarialEngine - 對抗式創意引擎

核心理念：真正的創新來自「被迫突破」，不是「隨便想想」

對抗流程：
1. Generator 提出想法
2. Critic 攻擊弱點（不是評分，是找死穴）
3. Generator 必須回應攻擊（不能換題目）
4. 重複直到想法真正新穎

經過對抗的想法，才可能是真正創新的
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AttackType(str, Enum):
    """攻擊類型"""

    ALREADY_EXISTS = "already_exists"  # 已經有人做過
    NOT_FEASIBLE = "not_feasible"  # 不可行
    TOO_OBVIOUS = "too_obvious"  # 太顯而易見
    MISSING_DETAIL = "missing_detail"  # 缺乏細節
    WRONG_ASSUMPTION = "wrong_assumption"  # 假設錯誤
    BETTER_ALTERNATIVE = "better_alternative"  # 有更好的替代方案


class DefenseType(str, Enum):
    """防禦/進化類型"""

    DIFFERENTIATE = "differentiate"  # 差異化：說明與現有方案的不同
    PIVOT = "pivot"  # 轉向：改變方向但保持核心
    DEEPEN = "deepen"  # 深化：增加細節和可行性
    REFRAME = "reframe"  # 重構：用新角度詮釋
    COMBINE = "combine"  # 結合：整合其他概念


@dataclass
class Attack:
    """一次攻擊"""

    attack_type: AttackType
    content: str
    severity: float = 0.5  # 嚴重程度 0-1

    # 攻擊的依據
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.attack_type.value,
            "content": self.content,
            "severity": self.severity,
            "evidence": self.evidence,
        }


@dataclass
class Defense:
    """一次防禦/進化"""

    defense_type: DefenseType
    evolved_idea: str
    reasoning: str

    # 如何回應攻擊
    addressed_attack: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.defense_type.value,
            "evolved_idea": self.evolved_idea,
            "reasoning": self.reasoning,
            "addressed_attack": self.addressed_attack,
        }


@dataclass
class AdversarialRound:
    """一輪對抗"""

    round_number: int
    idea_before: str
    attack: Attack
    defense: Defense
    idea_after: str

    # 這輪的進化程度
    evolution_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "round": self.round_number,
            "idea_before": self.idea_before,
            "attack": self.attack.to_dict(),
            "defense": self.defense.to_dict(),
            "idea_after": self.idea_after,
            "evolution_score": self.evolution_score,
        }


class AdversarialResult(BaseModel):
    """對抗式創意的最終結果"""

    original_idea: str
    final_idea: str
    topic: str

    rounds: list[dict] = Field(default_factory=list)
    total_rounds: int = 0

    # 品質指標
    novelty_improvement: float = 0.0  # 新穎度提升
    robustness_score: float = 0.0  # 穩健度（經受了多少攻擊）
    evolution_trajectory: list[str] = Field(default_factory=list)

    @property
    def quality_score(self) -> float:
        """品質 = 新穎度提升 × 穩健度"""
        return self.novelty_improvement * self.robustness_score


# === 攻擊模板庫 ===

ATTACK_TEMPLATES: dict[AttackType, list[str]] = {
    AttackType.ALREADY_EXISTS: [
        "這個想法已經有人做過了：{evidence}",
        "市面上已經有類似的產品/服務：{evidence}",
        "這不是新的，{evidence} 早就有這個概念",
    ],
    AttackType.NOT_FEASIBLE: [
        "這在技術上不可行，因為 {evidence}",
        "實現這個需要的資源太多：{evidence}",
        "這違反了 {evidence} 的基本原理",
    ],
    AttackType.TOO_OBVIOUS: [
        "這太顯而易見了，任何人都會想到",
        "這就是最直接的解法，沒有創意",
        "這只是把現有方案換個說法而已",
    ],
    AttackType.MISSING_DETAIL: [
        "這個想法太模糊，缺乏 {evidence}",
        "你沒有說明具體如何 {evidence}",
        "關鍵細節缺失：{evidence}",
    ],
    AttackType.WRONG_ASSUMPTION: [
        "你假設 {evidence}，但這個假設是錯的",
        "這個想法基於一個錯誤前提：{evidence}",
        "現實情況是 {evidence}，不是你假設的那樣",
    ],
    AttackType.BETTER_ALTERNATIVE: [
        "有更好的方法：{evidence}",
        "為什麼不直接 {evidence}？更簡單有效",
        "相比之下，{evidence} 是更優的選擇",
    ],
}


class AdversarialEngine:
    """
    對抗式創意引擎

    核心規則：
    1. no_retreat: 不能換題目
    2. must_address: 必須回應攻擊
    3. escalating_difficulty: 攻擊越來越難
    """

    def __init__(self, llm_client: Any = None):
        self.llm = llm_client

        # 對抗規則
        self.max_rounds = 5
        self.min_evolution_per_round = 0.1
        self.attack_escalation = 1.2  # 每輪攻擊強度倍增

    async def adversarial_evolve(
        self,
        initial_idea: str,
        topic: str,
        max_rounds: int | None = None,
    ) -> AdversarialResult:
        """
        對抗式進化

        流程：
        1. 從初始想法開始
        2. 每輪：攻擊 → 防禦 → 進化
        3. 直到想法足夠穩健或達到最大輪數
        """
        rounds_limit = max_rounds or self.max_rounds

        result = AdversarialResult(
            original_idea=initial_idea,
            final_idea=initial_idea,
            topic=topic,
            evolution_trajectory=[initial_idea],
        )

        current_idea = initial_idea
        cumulative_severity = 0.0

        for round_num in range(1, rounds_limit + 1):
            # 1. 生成攻擊
            attack = await self._generate_attack(
                current_idea, topic, round_num, cumulative_severity
            )

            # 2. 生成防禦/進化
            defense = await self._generate_defense(current_idea, attack, topic)

            evolved_idea = defense.evolved_idea

            # 3. 計算進化程度
            evolution_score = self._compute_evolution(current_idea, evolved_idea, attack)

            # 4. 記錄這輪
            round_record = AdversarialRound(
                round_number=round_num,
                idea_before=current_idea,
                attack=attack,
                defense=defense,
                idea_after=evolved_idea,
                evolution_score=evolution_score,
            )
            result.rounds.append(round_record.to_dict())
            result.evolution_trajectory.append(evolved_idea)

            # 5. 更新狀態
            current_idea = evolved_idea
            cumulative_severity += attack.severity

            # 6. 檢查是否足夠穩健（如果進化很小，可能已經足夠好了）
            if evolution_score < self.min_evolution_per_round:
                logger.info(f"Round {round_num}: Evolution plateaued, stopping")
                break

        # 最終結果
        result.final_idea = current_idea
        result.total_rounds = len(result.rounds)
        result.novelty_improvement = self._compute_novelty_improvement(initial_idea, current_idea)
        result.robustness_score = min(1.0, cumulative_severity / 2.0)

        return result

    async def _generate_attack(
        self,
        idea: str,
        topic: str,
        round_num: int,
        cumulative_severity: float,
    ) -> Attack:
        """
        生成攻擊

        攻擊策略隨輪數升級：
        - 前期：TOO_OBVIOUS, MISSING_DETAIL
        - 中期：ALREADY_EXISTS, NOT_FEASIBLE
        - 後期：WRONG_ASSUMPTION, BETTER_ALTERNATIVE
        """
        if self.llm:
            return await self._generate_attack_with_llm(idea, topic, round_num)

        return self._generate_attack_heuristic(idea, topic, round_num)

    def _generate_attack_heuristic(
        self,
        idea: str,
        topic: str,
        round_num: int,
    ) -> Attack:
        """啟發式攻擊生成"""
        import random

        # 根據輪數選擇攻擊類型
        if round_num <= 2:
            attack_types = [AttackType.TOO_OBVIOUS, AttackType.MISSING_DETAIL]
        elif round_num <= 4:
            attack_types = [AttackType.ALREADY_EXISTS, AttackType.NOT_FEASIBLE]
        else:
            attack_types = [AttackType.WRONG_ASSUMPTION, AttackType.BETTER_ALTERNATIVE]

        attack_type = random.choice(attack_types)

        # 生成攻擊內容
        templates = ATTACK_TEMPLATES[attack_type]
        template = random.choice(templates)

        # 填充 evidence（啟發式）
        evidence_map = {
            AttackType.ALREADY_EXISTS: "類似的解決方案",
            AttackType.NOT_FEASIBLE: "技術限制",
            AttackType.TOO_OBVIOUS: "",
            AttackType.MISSING_DETAIL: "具體實現步驟",
            AttackType.WRONG_ASSUMPTION: "用戶需求",
            AttackType.BETTER_ALTERNATIVE: "更直接的方法",
        }
        evidence = evidence_map.get(attack_type, "")
        content = template.format(evidence=evidence)

        # 攻擊強度隨輪數增加
        severity = min(1.0, 0.3 + round_num * 0.15)

        return Attack(
            attack_type=attack_type,
            content=content,
            severity=severity,
            evidence=evidence,
        )

    async def _generate_attack_with_llm(
        self,
        idea: str,
        topic: str,
        round_num: int,
    ) -> Attack:
        """使用 LLM 生成攻擊"""
        try:
            prompt = f"""你是一個嚴格的創意評論家。你的任務是找出以下想法的最大弱點。

主題：{topic}
想法：{idea}
這是第 {round_num} 輪攻擊

請找出這個想法最致命的弱點，選擇以下攻擊角度之一：
1. 已經有人做過（說明是誰、什麼時候）
2. 技術上不可行（說明具體障礙）
3. 太顯而易見（說明為什麼無聊）
4. 缺乏關鍵細節（說明缺什麼）
5. 基於錯誤假設（說明假設錯在哪）
6. 有更好的替代方案（說明是什麼）

你的攻擊要具體、有理有據，不是泛泛而談。"""

            # TODO: 呼叫 LLM 並解析回應
            # 目前返回啟發式結果
            return self._generate_attack_heuristic(idea, topic, round_num)

        except Exception as e:
            logger.warning(f"LLM attack generation failed: {e}")
            return self._generate_attack_heuristic(idea, topic, round_num)

    async def _generate_defense(
        self,
        idea: str,
        attack: Attack,
        topic: str,
    ) -> Defense:
        """
        生成防禦/進化

        核心規則：不能換題目，必須回應攻擊
        """
        if self.llm:
            return await self._generate_defense_with_llm(idea, attack, topic)

        return self._generate_defense_heuristic(idea, attack, topic)

    def _generate_defense_heuristic(
        self,
        idea: str,
        attack: Attack,
        topic: str,
    ) -> Defense:
        """啟發式防禦生成"""
        # 根據攻擊類型選擇防禦策略
        defense_map = {
            AttackType.ALREADY_EXISTS: DefenseType.DIFFERENTIATE,
            AttackType.NOT_FEASIBLE: DefenseType.PIVOT,
            AttackType.TOO_OBVIOUS: DefenseType.REFRAME,
            AttackType.MISSING_DETAIL: DefenseType.DEEPEN,
            AttackType.WRONG_ASSUMPTION: DefenseType.REFRAME,
            AttackType.BETTER_ALTERNATIVE: DefenseType.COMBINE,
        }

        defense_type = defense_map.get(attack.attack_type, DefenseType.DEEPEN)

        # 生成進化後的想法
        evolution_templates = {
            DefenseType.DIFFERENTIATE: f"與現有方案不同，這個想法專注於：{idea} + 獨特差異化",
            DefenseType.PIVOT: f"保留核心但改變方向：基於 {idea} 但使用更可行的方法",
            DefenseType.DEEPEN: f"具體化：{idea}，具體步驟是...",
            DefenseType.REFRAME: f"從新角度看：{idea} 其實是關於...",
            DefenseType.COMBINE: f"整合方案：{idea} 結合替代方案的優點",
        }

        evolved = evolution_templates.get(defense_type, idea)

        # 生成推理
        reasoning = f"針對「{attack.attack_type.value}」的攻擊，採用「{defense_type.value}」策略"

        return Defense(
            defense_type=defense_type,
            evolved_idea=evolved,
            reasoning=reasoning,
            addressed_attack=attack.content,
        )

    async def _generate_defense_with_llm(
        self,
        idea: str,
        attack: Attack,
        topic: str,
    ) -> Defense:
        """使用 LLM 生成防禦"""
        try:
            prompt = f"""你是一個創意捍衛者。你的想法被攻擊了，你必須進化它。

主題：{topic}
原始想法：{idea}
攻擊：{attack.content}

規則：
1. 你不能換題目，必須基於原始想法進化
2. 你必須直接回應攻擊，不能迴避
3. 你的進化必須讓想法更強、更新穎、更可行

請選擇一種防禦策略：
- 差異化：說明你的想法與現有方案的本質區別
- 轉向：改變方向但保持核心價值
- 深化：增加具體細節和可行性
- 重構：用全新角度重新詮釋
- 結合：整合攻擊中提到的替代方案

輸出進化後的想法。"""

            # TODO: 呼叫 LLM 並解析回應
            return self._generate_defense_heuristic(idea, attack, topic)

        except Exception as e:
            logger.warning(f"LLM defense generation failed: {e}")
            return self._generate_defense_heuristic(idea, attack, topic)

    def _compute_evolution(
        self,
        before: str,
        after: str,
        attack: Attack,
    ) -> float:
        """
        計算進化程度

        好的進化：長度增加、回應了攻擊、有新元素
        """
        # 長度變化
        length_ratio = len(after) / max(len(before), 1)
        length_score = min(1.0, length_ratio - 0.5) if length_ratio > 1 else 0.3

        # 是否有新內容
        new_chars = set(after) - set(before)
        novelty_score = min(1.0, len(new_chars) / 20)

        # 攻擊嚴重程度越高，進化越難
        difficulty_factor = 1 - attack.severity * 0.3

        return (length_score * 0.4 + novelty_score * 0.6) * difficulty_factor

    def _compute_novelty_improvement(
        self,
        original: str,
        final: str,
    ) -> float:
        """
        計算新穎度提升

        比較原始想法和最終想法的差異
        """
        if original == final:
            return 0.0

        # 簡單的差異度計算
        original_set = set(original.split())
        final_set = set(final.split())

        new_words = final_set - original_set
        ratio = len(new_words) / max(len(final_set), 1)

        return min(1.0, ratio * 2)

    def format_evolution_report(self, result: AdversarialResult) -> str:
        """產生進化報告"""
        lines = [
            "═" * 60,
            "⚔️ 對抗式創意進化報告",
            "═" * 60,
            "",
            f"📋 主題：{result.topic}",
            f"🔄 總輪數：{result.total_rounds}",
            f"📈 新穎度提升：{result.novelty_improvement:.0%}",
            f"🛡️ 穩健度：{result.robustness_score:.0%}",
            "",
            "─" * 60,
            "📝 原始想法",
            result.original_idea,
            "",
        ]

        for r in result.rounds:
            lines.extend(
                [
                    "─" * 60,
                    f"🔄 第 {r['round']} 輪",
                    f"⚔️ 攻擊 [{r['attack']['type']}]：{r['attack']['content']}",
                    f"🛡️ 防禦 [{r['defense']['type']}]：{r['defense']['reasoning']}",
                    f"💡 進化後：{r['defense']['evolved_idea'][:100]}...",
                    "",
                ]
            )

        lines.extend(
            [
                "═" * 60,
                "🏆 最終想法",
                result.final_idea,
                "═" * 60,
            ]
        )

        return "\n".join(lines)


# === 便捷函數 ===


async def evolve_idea(idea: str, topic: str, rounds: int = 5) -> AdversarialResult:
    """快速進化一個想法"""
    engine = AdversarialEngine()
    return await engine.adversarial_evolve(idea, topic, rounds)


def evolve_idea_sync(idea: str, topic: str, rounds: int = 5) -> AdversarialResult:
    """同步版本的 evolve_idea"""
    import asyncio

    return asyncio.run(evolve_idea(idea, topic, rounds))
