"""
CGU LLM Module

vLLM + Instructor 整合
"""

from cgu.llm.client import (
    CGULLMClient,
    LLMConfig,
    get_llm_client,
    get_llm_config,
    reset_llm_client,
)
from cgu.llm.prompts import (
    PROMPT_ANALYZE,
    PROMPT_ASSOCIATE,
    PROMPT_ASSOCIATE_SIMPLE,
    PROMPT_EVALUATE,
    PROMPT_GENERATE_IDEAS,
    PROMPT_MANDALA,
    PROMPT_MIND_MAP,
    PROMPT_REVERSE,
    PROMPT_SCAMPER,
    PROMPT_SIX_HATS,
    PROMPT_SPARK,
    SYSTEM_PROMPT_ANALYSIS,
    SYSTEM_PROMPT_CREATIVITY,
    SYSTEM_PROMPT_EVALUATION,
    format_constraints,
    format_ideas_list,
)
from cgu.llm.schemas import (
    # 分析評估
    AnalysisOutput,
    # 基礎
    Association,
    AssociationList,
    AssociationListDetailed,
    EvaluationOutput,
    IdeaEvaluationItem,
    IdeaOutput,
    IdeasOutput,
    IdeasOutputDetailed,
    MandalaOutput,
    MindMapBranch,
    MindMapOutput,
    ReverseOutput,
    # 方法
    ScamperOutput,
    SixHatsOutput,
    # 其他
    SparkOutput,
)

__all__ = [
    # Client
    "LLMConfig",
    "CGULLMClient",
    "get_llm_config",
    "get_llm_client",
    "reset_llm_client",
    # Schemas
    "Association",
    "AssociationList",
    "AssociationListDetailed",
    "IdeaOutput",
    "IdeasOutput",
    "IdeasOutputDetailed",
    "ScamperOutput",
    "SixHatsOutput",
    "MandalaOutput",
    "MindMapOutput",
    "MindMapBranch",
    "AnalysisOutput",
    "IdeaEvaluationItem",
    "EvaluationOutput",
    "SparkOutput",
    "ReverseOutput",
    # Prompts
    "SYSTEM_PROMPT_CREATIVITY",
    "SYSTEM_PROMPT_ANALYSIS",
    "SYSTEM_PROMPT_EVALUATION",
    "PROMPT_ASSOCIATE",
    "PROMPT_ASSOCIATE_SIMPLE",
    "PROMPT_SCAMPER",
    "PROMPT_SIX_HATS",
    "PROMPT_MANDALA",
    "PROMPT_MIND_MAP",
    "PROMPT_SPARK",
    "PROMPT_REVERSE",
    "PROMPT_GENERATE_IDEAS",
    "PROMPT_ANALYZE",
    "PROMPT_EVALUATE",
    "format_constraints",
    "format_ideas_list",
]
