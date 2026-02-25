"""
CGU Structured Output Schemas

定義 LLM 結構化輸出的 Pydantic 模型
"""

from pydantic import BaseModel, Field


# === 基礎 Schemas ===


class Association(BaseModel):
    """單一聯想"""
    concept: str = Field(description="聯想到的概念")
    relation: str = Field(default="", description="與原概念的關係")
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="關聯強度 (0-1)")


class AssociationList(BaseModel):
    """聯想列表 - 簡化版（用於快速聯想）"""
    associations: list[str] = Field(description="聯想的概念列表")


class AssociationListDetailed(BaseModel):
    """聯想列表 - 詳細版"""
    seed: str = Field(description="原始概念")
    associations: list[Association] = Field(description="聯想列表")
    reasoning: str = Field(default="", description="聯想推理過程")


# === 創意點子 Schemas ===


class IdeaOutput(BaseModel):
    """單一創意點子"""
    content: str = Field(description="點子內容")
    novelty_score: float = Field(default=0.5, ge=0.0, le=1.0, description="新穎度 (0-1)")
    feasibility_score: float = Field(default=0.5, ge=0.0, le=1.0, description="可行性 (0-1)")
    reasoning: str = Field(default="", description="產生這個點子的推理過程")


class IdeasOutput(BaseModel):
    """多個創意點子 - 簡化版"""
    ideas: list[str] = Field(description="點子列表（字串）")


class IdeasOutputDetailed(BaseModel):
    """多個創意點子 - 詳細版"""
    topic: str = Field(description="主題")
    ideas: list[IdeaOutput] = Field(description="點子列表")
    method_used: str = Field(default="", description="使用的創意方法")


# === SCAMPER Schemas ===


class ScamperOutput(BaseModel):
    """SCAMPER 方法輸出"""
    original: str = Field(description="原始概念")
    substitute: str = Field(description="S - 替代：什麼可以替代？")
    combine: str = Field(description="C - 結合：可以與什麼結合？")
    adapt: str = Field(description="A - 調適：可以從哪裡借鑑？")
    modify: str = Field(description="M - 修改：可以放大/縮小什麼？")
    put_to_other_uses: str = Field(description="P - 他用：還能用在哪裡？")
    eliminate: str = Field(description="E - 消除：可以去掉什麼？")
    reverse: str = Field(description="R - 重排：可以顛倒什麼？")
    best_idea: str = Field(description="最有潛力的變形點子")


# === 六頂思考帽 Schemas ===


class SixHatsOutput(BaseModel):
    """六頂思考帽輸出"""
    white: str = Field(description="白帽：客觀事實和數據")
    red: str = Field(description="紅帽：直覺和情緒反應")
    black: str = Field(description="黑帽：風險和問題")
    yellow: str = Field(description="黃帽：好處和價值")
    green: str = Field(description="綠帽：創意新點子")
    blue: str = Field(description="藍帽：總結和下一步")


# === 九宮格 Schemas ===


class MandalaOutput(BaseModel):
    """曼陀羅九宮格輸出"""
    center: str = Field(description="中心概念")
    extension_1: str = Field(description="延伸 1（上）")
    extension_2: str = Field(description="延伸 2（右上）")
    extension_3: str = Field(description="延伸 3（右）")
    extension_4: str = Field(description="延伸 4（右下）")
    extension_5: str = Field(description="延伸 5（下）")
    extension_6: str = Field(description="延伸 6（左下）")
    extension_7: str = Field(description="延伸 7（左）")
    extension_8: str = Field(description="延伸 8（左上）")

    @property
    def extensions(self) -> list[str]:
        return [
            self.extension_1, self.extension_2, self.extension_3,
            self.extension_4, self.extension_5, self.extension_6,
            self.extension_7, self.extension_8,
        ]


# === 心智圖 Schemas ===


class MindMapBranch(BaseModel):
    """心智圖分支"""
    name: str = Field(description="分支名稱")
    sub_branches: list[str] = Field(description="子分支")


class MindMapOutput(BaseModel):
    """心智圖輸出"""
    center: str = Field(description="中心主題")
    branches: list[MindMapBranch] = Field(description="主要分支")


# === 分析 Schemas ===


class AnalysisOutput(BaseModel):
    """分析輸出"""
    topic_understanding: str = Field(description="主題理解")
    key_dimensions: list[str] = Field(description="關鍵維度")
    gaps: list[str] = Field(description="缺口識別")
    suggestions: list[str] = Field(description="建議方向")


# === 評估 Schemas ===


class IdeaEvaluationItem(BaseModel):
    """單一點子評估"""
    idea_index: int = Field(description="點子索引（從0開始）")
    score: float = Field(ge=0.0, le=10.0, description="分數 (0-10)")
    reason: str = Field(default="", description="評分理由")


class EvaluationOutput(BaseModel):
    """評估輸出"""
    evaluations: list[IdeaEvaluationItem] = Field(description="各點子評估")
    best_ideas: list[int] = Field(description="最佳點子索引列表")
    reasoning: str = Field(default="", description="評估推理過程")


# === 概念碰撞 Schemas ===


class SparkOutput(BaseModel):
    """概念碰撞輸出"""
    concept_a: str = Field(description="概念 A")
    concept_b: str = Field(description="概念 B")
    sparks: list[str] = Field(description="碰撞產生的火花")
    best_spark: str = Field(description="最有潛力的火花")
    reasoning: str = Field(description="碰撞推理過程")


# === 逆向思考 Schemas ===


class ReverseOutput(BaseModel):
    """逆向思考輸出"""
    original_problem: str = Field(description="原始問題")
    reversed_question: str = Field(description="反向問題")
    ways_to_fail: list[str] = Field(description="如何讓它失敗的方法")
    solutions: list[str] = Field(description="反轉後的解決方案")
