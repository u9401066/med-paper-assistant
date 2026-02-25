"""
CGU Thinking Facade

簡化的統一介面 - 讓使用者一行程式碼就能思考
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cgu.thinking.engine import (
    ThinkingEngine,
    ThinkingMode,
    ThinkingDepth,
    ThinkingConfig,
    ThinkingResult,
    get_thinking_engine,
)

if TYPE_CHECKING:
    pass


async def think(
    topic: str,
    depth: str = "medium",
    mode: str | None = None,
) -> dict:
    """
    統一思考入口 - 最簡單的介面

    Args:
        topic: 思考主題
        depth: 深度 - "shallow"（快）/ "medium"（中）/ "deep"（深）
        mode: 強制模式 - "simple" / "deep" / "spark" / "hybrid" / None（自動）

    Returns:
        思考結果字典

    Example:
        >>> result = await think("AI 在教育領域的應用")
        >>> print(result["best_ideas"])
    """
    engine = get_thinking_engine()

    # 解析深度
    depth_map = {
        "shallow": ThinkingDepth.SHALLOW,
        "medium": ThinkingDepth.MEDIUM,
        "deep": ThinkingDepth.DEEP,
    }
    thinking_depth = depth_map.get(depth, ThinkingDepth.MEDIUM)

    # 解析模式
    mode_map = {
        "simple": ThinkingMode.SIMPLE,
        "deep": ThinkingMode.DEEP,
        "spark": ThinkingMode.SPARK,
        "hybrid": ThinkingMode.HYBRID,
    }
    thinking_mode = mode_map.get(mode) if mode else None

    # 執行思考
    result = await engine.think(
        topic=topic,
        mode=thinking_mode,
        depth=thinking_depth,
    )

    return result.to_dict()


async def quick_think(topic: str, count: int = 5) -> list[dict]:
    """
    快速思考 - 直接返回點子列表

    Args:
        topic: 思考主題
        count: 需要的點子數量

    Returns:
        點子列表

    Example:
        >>> ideas = await quick_think("智慧家居", count=3)
        >>> for idea in ideas:
        ...     print(idea["content"])
    """
    engine = get_thinking_engine()

    result = await engine.think(
        topic=topic,
        mode=ThinkingMode.SIMPLE,
        depth=ThinkingDepth.SHALLOW,
    )

    return result.ideas[:count]


async def deep_think(
    topic: str,
    agents: int = 3,
    steps: int = 3,
) -> dict:
    """
    深度思考 - Multi-Agent 並發探索

    Args:
        topic: 思考主題
        agents: 參與的 Agent 數量
        steps: 每個 Agent 的思考步數

    Returns:
        完整思考結果

    Example:
        >>> result = await deep_think("未來教育模式", agents=3, steps=5)
        >>> print(result["best_spark"])  # 最佳靈感火花
        >>> print(result["agent_contributions"])  # 各 Agent 貢獻
    """
    engine = get_thinking_engine()

    result = await engine.think(
        topic=topic,
        mode=ThinkingMode.DEEP,
        agent_count=agents,
        thinking_steps=steps,
    )

    return result.to_dict()


async def spark_think(
    concept_a: str,
    concept_b: str | None = None,
    count: int = 5,
) -> list[dict]:
    """
    火花思考 - 概念碰撞產生靈感

    Args:
        concept_a: 第一個概念
        concept_b: 第二個概念（可選，若無則自動擴展）
        count: 需要的火花數量

    Returns:
        火花列表

    Example:
        >>> sparks = await spark_think("咖啡", "程式設計")
        >>> for spark in sparks:
        ...     print(f"{spark['content']} (驚喜度: {spark['spark_value']})")
    """
    engine = get_thinking_engine()

    if concept_b:
        topic = f"{concept_a} + {concept_b} 的碰撞"
    else:
        topic = concept_a

    result = await engine.think(
        topic=topic,
        mode=ThinkingMode.SPARK,
        collision_count=count,
    )

    return result.sparks[:count]


# ===== 同步版本包裝 =====


def think_sync(topic: str, depth: str = "medium", mode: str | None = None) -> dict:
    """同步版本的 think"""
    import asyncio
    return asyncio.run(think(topic, depth, mode))


def quick_think_sync(topic: str, count: int = 5) -> list[dict]:
    """同步版本的 quick_think"""
    import asyncio
    return asyncio.run(quick_think(topic, count))


def deep_think_sync(topic: str, agents: int = 3, steps: int = 3) -> dict:
    """同步版本的 deep_think"""
    import asyncio
    return asyncio.run(deep_think(topic, agents, steps))


def spark_think_sync(concept_a: str, concept_b: str | None = None, count: int = 5) -> list[dict]:
    """同步版本的 spark_think"""
    import asyncio
    return asyncio.run(spark_think(concept_a, concept_b, count))
