"""
CGU Core Module

核心概念：
- 快思慢想 (Thinking Fast and Slow)
- 創意層級 (Creativity Levels)
- 創意方法論 (Creativity Methods)

v2 核心引擎：
- AnalogyEngine - 跨領域類比搜尋
- GraphTraversalEngine - 概念圖譜遍歷
- AdversarialEngine - 對抗式創意進化
- CreativityCore - 統一創意引擎
"""

from cgu.core.thinking import (
    ThinkingMode,
    ThinkingSpeed,
    ThinkingStep,
    ThinkingChain,
    FAST_SLOW_PATTERNS,
    get_thinking_pattern,
)
from cgu.core.creativity import (
    CreativityLevel,
    CreativityMethod,
    MethodCategory,
    MethodConfig,
    METHOD_CONFIGS,
    METHOD_SELECTION_GUIDE,
    select_method_for_task,
    get_method_config,
)

# v2 核心引擎
from cgu.core.analogy import (
    AnalogyEngine,
    Analogy,
    ProblemStructure,
    find_analogy,
    explain_problem_structure,
)
from cgu.core.graph import (
    GraphTraversalEngine,
    ConceptGraph,
    ConceptPath,
    EdgeType,
    get_graph_engine,
    find_connection,
    explore_concept,
)
from cgu.core.adversarial import (
    AdversarialEngine,
    AdversarialResult,
    Attack,
    Defense,
    evolve_idea,
    evolve_idea_sync,
)
from cgu.core.creativity_core import (
    CreativityCore,
    CreativityMode,
    CreativityConfig,
    CreativityResult,
    get_creativity_core,
    create,
    create_sync,
)

__all__ = [
    # Thinking (v1)
    "ThinkingMode",
    "ThinkingSpeed",
    "ThinkingStep",
    "ThinkingChain",
    "FAST_SLOW_PATTERNS",
    "get_thinking_pattern",
    # Creativity Methods (v1)
    "CreativityLevel",
    "CreativityMethod",
    "MethodCategory",
    "MethodConfig",
    "METHOD_CONFIGS",
    "METHOD_SELECTION_GUIDE",
    "select_method_for_task",
    "get_method_config",
    # === v2 核心引擎 ===
    # Analogy Engine
    "AnalogyEngine",
    "Analogy",
    "ProblemStructure",
    "find_analogy",
    "explain_problem_structure",
    # Graph Engine
    "GraphTraversalEngine",
    "ConceptGraph",
    "ConceptPath",
    "EdgeType",
    "get_graph_engine",
    "find_connection",
    "explore_concept",
    # Adversarial Engine
    "AdversarialEngine",
    "AdversarialResult",
    "Attack",
    "Defense",
    "evolve_idea",
    "evolve_idea_sync",
    # Creativity Core (統一入口)
    "CreativityCore",
    "CreativityMode",
    "CreativityConfig",
    "CreativityResult",
    "get_creativity_core",
    "create",
    "create_sync",
]
