"""
AnalogyEngine - 跨領域類比搜尋器

核心理念：類比不是「找相似的詞」，是「找結構相同的問題」

Bisociation (Arthur Koestler):
- 創意 = 兩個原本不相關的「思維矩陣」突然找到結構上的連結點
- 關鍵：結構同構、非顯而易見、意外但有意義
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StructuralDimension(str, Enum):
    """問題的結構維度"""
    PATTERN = "pattern"          # 模式：累積、循環、突變...
    DYNAMIC = "dynamic"          # 動態：增長、衰減、震盪...
    CONSTRAINT = "constraint"    # 約束：資源、時間、規則...
    STAKEHOLDER = "stakeholder"  # 利害關係：衝突、合作、競爭...
    TRADEOFF = "tradeoff"        # 權衡：短期/長期、成本/品質...


@dataclass
class ProblemStructure:
    """
    問題的結構化表示

    不是關鍵字，是問題的「骨架」
    """
    domain: str                                    # 原始領域
    core_problem: str                              # 核心問題描述

    # 結構維度
    patterns: list[str] = field(default_factory=list)        # 問題的模式
    dynamics: list[str] = field(default_factory=list)        # 變化的動態
    constraints: list[str] = field(default_factory=list)     # 約束條件
    stakeholders: list[str] = field(default_factory=list)    # 利害關係人
    tradeoffs: list[str] = field(default_factory=list)       # 權衡關係

    # 抽象層級
    abstraction_level: int = 1  # 1=具體, 2=中等, 3=高度抽象

    def to_abstract_signature(self) -> str:
        """
        產生問題的抽象簽名

        用於跨域比對
        """
        parts = []
        if self.patterns:
            parts.append(f"P:{'+'.join(self.patterns[:2])}")
        if self.dynamics:
            parts.append(f"D:{'+'.join(self.dynamics[:2])}")
        if self.tradeoffs:
            parts.append(f"T:{'+'.join(self.tradeoffs[:2])}")
        return "|".join(parts)


class Analogy(BaseModel):
    """一個類比"""
    source_domain: str                    # 來源領域
    target_domain: str                    # 目標領域（原問題所在）

    # 類比內容
    source_concept: str                   # 來源概念
    mapping_explanation: str              # 映射說明
    insight: str                          # 產生的洞察

    # 結構匹配
    matched_dimensions: list[str] = Field(default_factory=list)

    # 品質評分
    structural_match: float = 0.0         # 結構匹配度
    surface_distance: float = 0.0         # 表面差異（越大越好）
    insight_potential: float = 0.0        # 洞察潛力
    transferability: float = 0.0          # 可遷移性

    @property
    def quality_score(self) -> float:
        """
        類比品質 = 結構匹配 × 表面差異 × 洞察潛力

        最佳類比：結構相同但領域很遠
        """
        return (
            self.structural_match * 0.4 +
            self.surface_distance * 0.3 +
            self.insight_potential * 0.3
        )


# === 預設的領域知識庫 ===

DOMAIN_STRUCTURES: dict[str, dict] = {
    "軟體開發": {
        "patterns": ["迭代", "累積", "重構"],
        "dynamics": ["複雜度增長", "技術債累積", "熵增"],
        "constraints": ["時間", "人力", "相容性"],
        "tradeoffs": ["速度/品質", "短期/長期", "彈性/穩定"],
    },
    "建築工程": {
        "patterns": ["分階段", "累積", "補強"],
        "dynamics": ["老化", "負載變化", "結構疲勞"],
        "constraints": ["預算", "法規", "地形"],
        "tradeoffs": ["成本/安全", "美觀/實用", "現在/未來"],
    },
    "醫療健康": {
        "patterns": ["預防", "診斷", "治療", "復健"],
        "dynamics": ["惡化", "恢復", "慢性累積"],
        "constraints": ["資源", "倫理", "時間窗口"],
        "tradeoffs": ["介入/觀察", "風險/效益", "個體/群體"],
    },
    "生態環境": {
        "patterns": ["循環", "累積", "臨界點"],
        "dynamics": ["退化", "恢復", "突變"],
        "constraints": ["承載力", "時間尺度", "不可逆"],
        "tradeoffs": ["發展/保護", "現在/未來", "局部/整體"],
    },
    "組織管理": {
        "patterns": ["層級", "網絡", "自組織"],
        "dynamics": ["成長", "僵化", "變革"],
        "constraints": ["文化", "制度", "利益"],
        "tradeoffs": ["控制/自主", "效率/創新", "穩定/變革"],
    },
    "教育學習": {
        "patterns": ["漸進", "螺旋", "突破"],
        "dynamics": ["累積", "遺忘", "頓悟"],
        "constraints": ["時間", "認知負荷", "動機"],
        "tradeoffs": ["深度/廣度", "理論/實踐", "個人/集體"],
    },
    "金融經濟": {
        "patterns": ["週期", "累積", "泡沫"],
        "dynamics": ["增長", "衰退", "震盪"],
        "constraints": ["資本", "風險", "監管"],
        "tradeoffs": ["風險/報酬", "流動性/收益", "短期/長期"],
    },
    "軍事戰略": {
        "patterns": ["攻防", "迂迴", "消耗"],
        "dynamics": ["集中", "分散", "機動"],
        "constraints": ["資源", "地形", "情報"],
        "tradeoffs": ["速度/安全", "集中/分散", "攻擊/防守"],
    },
}


class AnalogyEngine:
    """
    類比搜尋引擎

    核心功能：
    1. 將問題抽象成結構
    2. 在其他領域搜尋相同結構
    3. 映射回來產生洞察
    """

    def __init__(self, llm_client: Any = None):
        self.llm = llm_client
        self.domain_knowledge = DOMAIN_STRUCTURES.copy()

    def extract_structure(self, problem: str, domain: str | None = None) -> ProblemStructure:
        """
        從問題描述中抽取結構

        這是類比的第一步：把具體問題變成抽象結構
        """
        if self.llm:
            return self._extract_with_llm(problem, domain)
        return self._extract_heuristic(problem, domain)

    def _extract_heuristic(self, problem: str, domain: str | None = None) -> ProblemStructure:
        """啟發式結構抽取"""
        structure = ProblemStructure(
            domain=domain or "unknown",
            core_problem=problem,
        )

        # 模式識別
        pattern_keywords = {
            "累積": ["累積", "堆積", "增加", "債", "欠"],
            "循環": ["循環", "週期", "反覆", "迴圈"],
            "突變": ["突然", "轉折", "臨界", "崩潰"],
            "漸進": ["漸漸", "逐步", "慢慢", "演化"],
        }
        for pattern, keywords in pattern_keywords.items():
            if any(kw in problem for kw in keywords):
                structure.patterns.append(pattern)

        # 動態識別
        dynamic_keywords = {
            "增長": ["增長", "擴大", "成長", "膨脹"],
            "衰減": ["下降", "減少", "衰退", "萎縮"],
            "震盪": ["波動", "不穩", "起伏", "變化"],
        }
        for dynamic, keywords in dynamic_keywords.items():
            if any(kw in problem for kw in keywords):
                structure.dynamics.append(dynamic)

        # 權衡識別
        tradeoff_patterns = [
            ("短期", "長期"),
            ("成本", "品質"),
            ("速度", "安全"),
            ("效率", "彈性"),
        ]
        for a, b in tradeoff_patterns:
            if a in problem or b in problem:
                structure.tradeoffs.append(f"{a}/{b}")

        # 如果都沒識別到，給預設值
        if not structure.patterns:
            structure.patterns = ["一般問題"]
        if not structure.dynamics:
            structure.dynamics = ["靜態"]

        return structure

    def _extract_with_llm(self, problem: str, domain: str | None = None) -> ProblemStructure:
        """使用 LLM 抽取結構"""
        try:
            from cgu.llm import SYSTEM_PROMPT_CREATIVITY

            prompt = f"""分析以下問題的結構特徵：

問題：{problem}
領域：{domain or "未知"}

請識別：
1. 問題模式（累積？循環？突變？漸進？）
2. 變化動態（增長？衰減？震盪？）
3. 約束條件（資源？時間？規則？）
4. 利害關係（誰受影響？誰有權力？）
5. 權衡關係（短期/長期？成本/品質？）

請用 JSON 格式回答。"""

            # 簡化處理，直接返回啟發式結果
            return self._extract_heuristic(problem, domain)

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return self._extract_heuristic(problem, domain)

    def find_analogies(
        self,
        problem: str,
        source_domain: str | None = None,
        exclude_domains: list[str] | None = None,
        max_analogies: int = 5,
    ) -> list[Analogy]:
        """
        搜尋跨領域類比

        Args:
            problem: 問題描述
            source_domain: 問題所在領域
            exclude_domains: 要排除的領域
            max_analogies: 最多返回幾個類比
        """
        # 1. 抽取問題結構
        structure = self.extract_structure(problem, source_domain)

        # 2. 在其他領域搜尋
        candidates: list[Analogy] = []
        exclude = set(exclude_domains or [])
        if source_domain:
            exclude.add(source_domain)

        for domain, domain_struct in self.domain_knowledge.items():
            if domain in exclude:
                continue

            # 計算結構匹配度
            match_score = self._compute_structural_match(structure, domain_struct)

            if match_score > 0.3:  # 最低門檻
                analogy = self._create_analogy(
                    source_structure=structure,
                    target_domain=domain,
                    target_struct=domain_struct,
                    match_score=match_score,
                )
                candidates.append(analogy)

        # 3. 排序並返回最佳
        candidates.sort(key=lambda a: a.quality_score, reverse=True)
        return candidates[:max_analogies]

    def _compute_structural_match(
        self,
        problem_struct: ProblemStructure,
        domain_struct: dict,
    ) -> float:
        """計算結構匹配度"""
        scores = []

        # 模式匹配
        if problem_struct.patterns:
            pattern_match = len(
                set(problem_struct.patterns) & set(domain_struct.get("patterns", []))
            ) / max(len(problem_struct.patterns), 1)
            scores.append(pattern_match)

        # 動態匹配
        if problem_struct.dynamics:
            dynamic_match = len(
                set(problem_struct.dynamics) & set(domain_struct.get("dynamics", []))
            ) / max(len(problem_struct.dynamics), 1)
            scores.append(dynamic_match)

        # 權衡匹配
        if problem_struct.tradeoffs:
            tradeoff_match = len(
                set(problem_struct.tradeoffs) & set(domain_struct.get("tradeoffs", []))
            ) / max(len(problem_struct.tradeoffs), 1)
            scores.append(tradeoff_match)

        return sum(scores) / max(len(scores), 1) if scores else 0.3

    def _create_analogy(
        self,
        source_structure: ProblemStructure,
        target_domain: str,
        target_struct: dict,
        match_score: float,
    ) -> Analogy:
        """創建類比對象"""
        # 找出匹配的維度
        matched = []
        if set(source_structure.patterns) & set(target_struct.get("patterns", [])):
            matched.append("patterns")
        if set(source_structure.dynamics) & set(target_struct.get("dynamics", [])):
            matched.append("dynamics")
        if set(source_structure.tradeoffs) & set(target_struct.get("tradeoffs", [])):
            matched.append("tradeoffs")

        # 生成映射說明和洞察
        mapping, insight = self._generate_insight(
            source_structure, target_domain, target_struct, matched
        )

        # 計算表面差異（領域越不相關，差異越大）
        surface_distance = self._compute_surface_distance(
            source_structure.domain, target_domain
        )

        return Analogy(
            source_domain=target_domain,
            target_domain=source_structure.domain,
            source_concept=f"{target_domain}的解決模式",
            mapping_explanation=mapping,
            insight=insight,
            matched_dimensions=matched,
            structural_match=match_score,
            surface_distance=surface_distance,
            insight_potential=min(1.0, match_score * surface_distance * 1.5),
            transferability=match_score * 0.8,
        )

    def _generate_insight(
        self,
        source: ProblemStructure,
        target_domain: str,
        target_struct: dict,
        matched: list[str],
    ) -> tuple[str, str]:
        """生成映射說明和洞察"""
        if self.llm:
            # TODO: 使用 LLM 生成更有創意的洞察
            pass

        # 啟發式生成
        mapping_parts = []
        insight_parts = []

        if "patterns" in matched:
            common_patterns = set(source.patterns) & set(target_struct.get("patterns", []))
            if common_patterns:
                p = list(common_patterns)[0]
                mapping_parts.append(f"兩者都有「{p}」的問題模式")
                insight_parts.append(f"可以借鏡{target_domain}如何處理「{p}」")

        if "dynamics" in matched:
            common_dynamics = set(source.dynamics) & set(target_struct.get("dynamics", []))
            if common_dynamics:
                d = list(common_dynamics)[0]
                mapping_parts.append(f"兩者都面臨「{d}」的變化動態")

        if "tradeoffs" in matched:
            common_tradeoffs = set(source.tradeoffs) & set(target_struct.get("tradeoffs", []))
            if common_tradeoffs:
                t = list(common_tradeoffs)[0]
                mapping_parts.append(f"兩者都需要權衡「{t}」")
                insight_parts.append(f"{target_domain}在「{t}」的權衡上有成熟經驗")

        mapping = "；".join(mapping_parts) if mapping_parts else f"在結構層面與{target_domain}相似"
        insight = "。".join(insight_parts) if insight_parts else f"可以研究{target_domain}的解決方案"

        return mapping, insight

    def _compute_surface_distance(self, domain_a: str, domain_b: str) -> float:
        """
        計算兩個領域的表面差異

        領域越不相關，差異越大（越好）
        """
        # 定義領域群組
        domain_groups = {
            "tech": ["軟體開發", "資訊科技"],
            "engineering": ["建築工程", "機械工程"],
            "life": ["醫療健康", "生態環境"],
            "social": ["組織管理", "教育學習"],
            "economy": ["金融經濟"],
            "military": ["軍事戰略"],
        }

        group_a = None
        group_b = None
        for group, domains in domain_groups.items():
            if domain_a in domains:
                group_a = group
            if domain_b in domains:
                group_b = group

        if group_a == group_b and group_a is not None:
            return 0.3  # 同群組，差異小
        elif group_a is None or group_b is None:
            return 0.7  # 未知領域，中等差異
        else:
            return 0.9  # 不同群組，差異大

    def explain_analogy(self, analogy: Analogy) -> str:
        """產生類比的詳細解釋"""
        lines = [
            f"📊 類比分析：{analogy.source_domain} → {analogy.target_domain}",
            "",
            f"🔗 結構匹配：{analogy.structural_match:.0%}",
            f"📏 領域差異：{analogy.surface_distance:.0%}",
            f"💡 洞察潛力：{analogy.insight_potential:.0%}",
            f"⭐ 綜合品質：{analogy.quality_score:.0%}",
            "",
            f"📝 映射說明：{analogy.mapping_explanation}",
            "",
            f"💡 洞察：{analogy.insight}",
        ]
        return "\n".join(lines)


# === 便捷函數 ===

def find_analogy(problem: str, domain: str | None = None) -> list[Analogy]:
    """快速查找類比"""
    engine = AnalogyEngine()
    return engine.find_analogies(problem, domain)


def explain_problem_structure(problem: str) -> str:
    """解釋問題的結構"""
    engine = AnalogyEngine()
    structure = engine.extract_structure(problem)

    lines = [
        f"📋 問題結構分析",
        f"",
        f"🎯 核心問題：{structure.core_problem}",
        f"📁 領域：{structure.domain}",
        f"",
        f"📊 模式：{', '.join(structure.patterns) or '無'}",
        f"📈 動態：{', '.join(structure.dynamics) or '無'}",
        f"⚖️ 權衡：{', '.join(structure.tradeoffs) or '無'}",
        f"",
        f"🔑 抽象簽名：{structure.to_abstract_signature()}",
    ]
    return "\n".join(lines)
