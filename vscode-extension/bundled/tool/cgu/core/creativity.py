"""
Creativity Level and Methods

CGU 核心：創意層級與方法論
參考文檔：docs/creativity-generation-unit.md
"""

from enum import Enum

from pydantic import BaseModel, Field


class CreativityLevel(int, Enum):
    """
    創意層級 - 對應關聯性範圍

    L1: 組合創意 (Combinational) - 高關聯 (0.7-1.0) - 已知元素的新組合
    L2: 探索創意 (Exploratory) - 中關聯 (0.3-0.7) - 在既有規則內探索邊界
    L3: 變革創意 (Transformational) - 低關聯 (0.0-0.3) - 打破規則，創造新範式
    """

    L1_COMBINATIONAL = 1
    L2_EXPLORATORY = 2
    L3_TRANSFORMATIONAL = 3

    @property
    def association_range(self) -> tuple[float, float]:
        """取得關聯性範圍"""
        ranges = {
            1: (0.7, 1.0),
            2: (0.3, 0.7),
            3: (0.0, 0.3),
        }
        return ranges[self.value]


class CreativityMethod(str, Enum):
    """
    創意方法論 - 人類智慧的結晶

    分類：
    - 發散類：產生大量點子
    - 結構類：系統化思考
    - 觀點類：多角度審視
    - 流程類：完整創意流程
    - 系統類：工程化創新
    """

    # === 發散類 (Divergent) ===
    MIND_MAP = "mind_map"                 # 心智圖 - Tony Buzan
    BRAINSTORM = "brainstorm"             # 腦力激盪
    SCAMPER = "scamper"                   # SCAMPER 檢核表 - Bob Eberle
    RANDOM_INPUT = "random_input"         # 隨機輸入法 - de Bono

    # === 結構類 (Structural) ===
    MANDALA_9GRID = "mandala_9grid"       # 曼陀羅九宮格 - 今泉浩晃
    MORPHOLOGICAL = "morphological"       # 形態分析法 - Fritz Zwicky
    FIVE_W_TWO_H = "5w2h"                 # 5W2H
    FISHBONE = "fishbone"                 # 魚骨圖 - 石川馨

    # === 觀點類 (Perspective) ===
    SIX_HATS = "six_hats"                 # 六頂思考帽 - de Bono
    REVERSE = "reverse"                   # 逆向腦力激盪
    ANALOGY = "analogy"                   # 類比思考

    # === 流程類 (Process) ===
    DOUBLE_DIAMOND = "double_diamond"     # 雙鑽石 - 英國設計協會
    DESIGN_SPRINT = "design_sprint"       # 設計衝刺 - Google Ventures
    KJ_METHOD = "kj_method"               # KJ 法 - 川喜田二郎
    WORLD_CAFE = "world_cafe"             # 世界咖啡館

    # === 系統類 (Systematic) ===
    TRIZ = "triz"                         # TRIZ 40原理 - Altshuller


class MethodCategory(str, Enum):
    """方法分類"""
    DIVERGENT = "divergent"      # 發散類
    STRUCTURAL = "structural"    # 結構類
    PERSPECTIVE = "perspective"  # 觀點類
    PROCESS = "process"          # 流程類
    SYSTEMATIC = "systematic"    # 系統類


class MethodConfig(BaseModel):
    """方法配置"""

    method: CreativityMethod
    category: MethodCategory
    thinking_speed: str = "fast"  # fast / slow
    suitable_levels: list[int] = Field(default_factory=lambda: [1, 2, 3])
    description: str = ""

    # 方法特性
    is_divergent: bool = True      # 是否發散型
    requires_iteration: bool = False  # 是否需要迭代
    min_inputs: int = 1            # 最少輸入數
    agent_strategy: str = ""       # Agent 實現策略


# === 方法配置表 ===

METHOD_CONFIGS: dict[CreativityMethod, MethodConfig] = {
    # --- 發散類 ---
    CreativityMethod.MIND_MAP: MethodConfig(
        method=CreativityMethod.MIND_MAP,
        category=MethodCategory.DIVERGENT,
        thinking_speed="fast",
        suitable_levels=[1, 2],
        description="從中心概念向外放射擴展",
        is_divergent=True,
        agent_strategy="樹狀概念圖遍歷，BFS/DFS 擴展",
    ),
    CreativityMethod.BRAINSTORM: MethodConfig(
        method=CreativityMethod.BRAINSTORM,
        category=MethodCategory.DIVERGENT,
        thinking_speed="fast",
        suitable_levels=[1, 2, 3],
        description="不批判的快速點子生成",
        is_divergent=True,
        agent_strategy="Multi-agent 並行生成，不批判",
    ),
    CreativityMethod.SCAMPER: MethodConfig(
        method=CreativityMethod.SCAMPER,
        category=MethodCategory.DIVERGENT,
        thinking_speed="fast",
        suitable_levels=[1, 2],
        description="7種變形技巧：替代、結合、調適、修改、他用、消除、重排",
        is_divergent=True,
        agent_strategy="7 種變形提示模板",
    ),
    CreativityMethod.RANDOM_INPUT: MethodConfig(
        method=CreativityMethod.RANDOM_INPUT,
        category=MethodCategory.DIVERGENT,
        thinking_speed="fast",
        suitable_levels=[2, 3],
        description="隨機詞強制聯想",
        is_divergent=True,
        agent_strategy="低關聯詞注入 + 強制連結",
    ),

    # --- 結構類 ---
    CreativityMethod.MANDALA_9GRID: MethodConfig(
        method=CreativityMethod.MANDALA_9GRID,
        category=MethodCategory.STRUCTURAL,
        thinking_speed="slow",
        suitable_levels=[1, 2],
        description="強制8方向聯想，可遞迴展開",
        is_divergent=True,
        requires_iteration=True,
        agent_strategy="強制 8 方向聯想，可遞迴",
    ),
    CreativityMethod.MORPHOLOGICAL: MethodConfig(
        method=CreativityMethod.MORPHOLOGICAL,
        category=MethodCategory.STRUCTURAL,
        thinking_speed="slow",
        suitable_levels=[1, 2],
        description="多維度選項的排列組合",
        is_divergent=True,
        agent_strategy="排列組合 + 可行性過濾",
    ),
    CreativityMethod.FIVE_W_TWO_H: MethodConfig(
        method=CreativityMethod.FIVE_W_TWO_H,
        category=MethodCategory.STRUCTURAL,
        thinking_speed="fast",
        suitable_levels=[1, 2, 3],
        description="What, Why, Who, When, Where, How, How much",
        is_divergent=False,
        agent_strategy="7 維度系統化提問",
    ),
    CreativityMethod.FISHBONE: MethodConfig(
        method=CreativityMethod.FISHBONE,
        category=MethodCategory.STRUCTURAL,
        thinking_speed="slow",
        suitable_levels=[1, 2],
        description="6M 因果分析：人員、方法、材料、設備、測量、環境",
        is_divergent=False,
        agent_strategy="6M 維度拆解分析",
    ),

    # --- 觀點類 ---
    CreativityMethod.SIX_HATS: MethodConfig(
        method=CreativityMethod.SIX_HATS,
        category=MethodCategory.PERSPECTIVE,
        thinking_speed="slow",
        suitable_levels=[1, 2, 3],
        description="6種觀點：白(事實)、紅(情感)、黑(批判)、黃(樂觀)、綠(創意)、藍(統籌)",
        is_divergent=False,
        requires_iteration=True,
        agent_strategy="6 個角色 Agent 平行思考",
    ),
    CreativityMethod.REVERSE: MethodConfig(
        method=CreativityMethod.REVERSE,
        category=MethodCategory.PERSPECTIVE,
        thinking_speed="fast",
        suitable_levels=[2, 3],
        description="反向思考：如何製造問題？如何讓情況更糟？",
        is_divergent=True,
        agent_strategy="反向約束推理",
    ),
    CreativityMethod.ANALOGY: MethodConfig(
        method=CreativityMethod.ANALOGY,
        category=MethodCategory.PERSPECTIVE,
        thinking_speed="slow",
        suitable_levels=[2, 3],
        description="跨域類比：直接、擬人、符號、幻想類比",
        is_divergent=True,
        agent_strategy="Cross-domain embedding 搜尋",
    ),

    # --- 流程類 ---
    CreativityMethod.DOUBLE_DIAMOND: MethodConfig(
        method=CreativityMethod.DOUBLE_DIAMOND,
        category=MethodCategory.PROCESS,
        thinking_speed="slow",
        suitable_levels=[1, 2, 3],
        description="發散-收斂-發散-收斂：探索、定義、發展、交付",
        is_divergent=False,
        requires_iteration=True,
        agent_strategy="4 階段 Agent 流水線",
    ),
    CreativityMethod.DESIGN_SPRINT: MethodConfig(
        method=CreativityMethod.DESIGN_SPRINT,
        category=MethodCategory.PROCESS,
        thinking_speed="slow",
        suitable_levels=[1, 2, 3],
        description="5日流程：理解、發想、決策、原型、測試",
        is_divergent=False,
        requires_iteration=True,
        agent_strategy="5 日 Pipeline 編排",
    ),
    CreativityMethod.KJ_METHOD: MethodConfig(
        method=CreativityMethod.KJ_METHOD,
        category=MethodCategory.PROCESS,
        thinking_speed="slow",
        suitable_levels=[1, 2],
        description="收集、分群、命名",
        is_divergent=False,
        requires_iteration=True,
        agent_strategy="Clustering + 自動標籤",
    ),
    CreativityMethod.WORLD_CAFE: MethodConfig(
        method=CreativityMethod.WORLD_CAFE,
        category=MethodCategory.PROCESS,
        thinking_speed="slow",
        suitable_levels=[1, 2, 3],
        description="多桌輪替討論，桌長傳遞脈絡",
        is_divergent=True,
        requires_iteration=True,
        agent_strategy="Agent 輪替 + 上下文傳遞",
    ),

    # --- 系統類 ---
    CreativityMethod.TRIZ: MethodConfig(
        method=CreativityMethod.TRIZ,
        category=MethodCategory.SYSTEMATIC,
        thinking_speed="slow",
        suitable_levels=[1, 2, 3],
        description="40條發明原理",
        is_divergent=True,
        agent_strategy="40 原理提示庫匹配",
    ),
}


# === 方法選擇指南 ===

METHOD_SELECTION_GUIDE: dict[str, list[CreativityMethod]] = {
    "廣泛探索": [CreativityMethod.MIND_MAP, CreativityMethod.BRAINSTORM],
    "結構化分析": [CreativityMethod.MANDALA_9GRID, CreativityMethod.FIVE_W_TWO_H, CreativityMethod.FISHBONE],
    "強制創新": [CreativityMethod.SCAMPER, CreativityMethod.RANDOM_INPUT],
    "系統性組合": [CreativityMethod.MORPHOLOGICAL, CreativityMethod.TRIZ],
    "多元觀點": [CreativityMethod.SIX_HATS, CreativityMethod.WORLD_CAFE],
    "問題反轉": [CreativityMethod.REVERSE],
    "完整流程": [CreativityMethod.DOUBLE_DIAMOND, CreativityMethod.DESIGN_SPRINT],
}


def select_method_for_task(
    creativity_level: CreativityLevel,
    prefer_fast: bool = True,
    is_stuck: bool = False,
    purpose: str | None = None,
) -> CreativityMethod:
    """
    根據任務選擇合適的創意方法

    Args:
        creativity_level: 需要的創意層級
        prefer_fast: 是否偏好快速方法
        is_stuck: 是否卡關中
        purpose: 目的（對應 METHOD_SELECTION_GUIDE）

    Returns:
        推薦的創意方法
    """
    # 卡關時用逆向思考
    if is_stuck:
        return CreativityMethod.REVERSE

    # 有特定目的時從指南選擇
    if purpose and purpose in METHOD_SELECTION_GUIDE:
        candidates = METHOD_SELECTION_GUIDE[purpose]
        return candidates[0]

    # 根據層級和速度篩選
    level = creativity_level.value
    speed = "fast" if prefer_fast else "slow"

    candidates = [
        method for method, config in METHOD_CONFIGS.items()
        if level in config.suitable_levels and config.thinking_speed == speed
    ]

    if not candidates:
        return CreativityMethod.BRAINSTORM

    return candidates[0]


def get_method_config(method: CreativityMethod) -> MethodConfig:
    """取得方法配置"""
    return METHOD_CONFIGS.get(method, METHOD_CONFIGS[CreativityMethod.BRAINSTORM])
