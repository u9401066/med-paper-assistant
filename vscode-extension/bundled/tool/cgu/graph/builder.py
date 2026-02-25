"""
CGU Graph Builder

LangGraph 圖形編排 - 實作快思慢想流程
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from cgu.core import ThinkingMode, CreativityLevel, FAST_SLOW_PATTERNS
from cgu.graph.state import CGUState
from cgu.graph.nodes import (
    react_node,
    associate_node,
    pattern_match_node,
    analyze_node,
    synthesize_node,
    evaluate_node,
    diverge_node,
    converge_node,
    transform_node,
)


def should_continue(state: CGUState) -> Literal["continue", "finalize"]:
    """判斷是否繼續思考"""
    if state.should_stop:
        return "finalize"
    if state.error:
        return "finalize"
    if len(state.final_ideas) >= state.target_count:
        return "finalize"
    if state.iteration >= state.max_iterations:
        return "finalize"
    return "continue"


def route_thinking(state: CGUState) -> str:
    """
    路由思考模式

    核心邏輯：快思慢想
    - 先做多個快步驟
    - 再做慢步驟評估
    - 循環直到產生足夠點子
    """
    # 檢查是否該停止
    if state.should_stop or state.error:
        return "finalize"

    # 檢查是否已有足夠點子
    if len(state.final_ideas) >= state.target_count:
        return "finalize"

    # 快思慢想邏輯
    if state.should_do_fast():
        # 快步驟：根據當前模式選擇
        mode = state.current_mode
        if mode == ThinkingMode.REACT:
            return "react"
        elif mode == ThinkingMode.ASSOCIATE:
            return "associate"
        elif mode == ThinkingMode.PATTERN_MATCH:
            return "pattern_match"
        elif mode == ThinkingMode.DIVERGE:
            return "diverge"
        else:
            # 預設快步驟
            return "associate"

    elif state.should_do_slow():
        # 慢步驟：分析、綜合、評估
        mode = state.current_mode
        if mode == ThinkingMode.ANALYZE:
            return "analyze"
        elif mode == ThinkingMode.SYNTHESIZE:
            return "synthesize"
        elif mode == ThinkingMode.EVALUATE:
            return "evaluate"
        elif mode == ThinkingMode.CONVERGE:
            return "converge"
        elif mode == ThinkingMode.TRANSFORM:
            return "transform"
        else:
            # 預設慢步驟
            return "evaluate"

    else:
        # 週期完成，評估是否繼續
        if len(state.candidate_ideas) >= state.target_count:
            return "finalize"
        else:
            # 重置週期，繼續發散
            return "reset_cycle"


async def reset_cycle_node(state: CGUState) -> dict:
    """重置快慢週期"""
    return {
        "fast_steps_count": 0,
        "slow_steps_count": 0,
        "iteration": state.iteration + 1,
        "current_mode": ThinkingMode.DIVERGE,  # 新週期從發散開始
    }


async def finalize_node(state: CGUState) -> dict:
    """
    最終化節點

    整理最終輸出
    """
    # 如果 final_ideas 還沒填充，從 candidate_ideas 選取
    if not state.final_ideas and state.candidate_ideas:
        sorted_ideas = sorted(
            state.candidate_ideas,
            key=lambda x: x.association_score,
            reverse=True
        )
        final = sorted_ideas[:state.target_count]
        return {"final_ideas": final, "should_stop": True}

    return {"should_stop": True}


def build_cgu_graph() -> StateGraph:
    """
    建構 CGU 思考圖

    結構：

        START
          │
          ▼
       ┌─────────────────────────────────────┐
       │           FAST THINKING             │
       │  react → associate → pattern_match  │
       │              or                     │
       │           diverge                   │
       └─────────────┬───────────────────────┘
                     │
                     ▼
       ┌─────────────────────────────────────┐
       │           SLOW THINKING             │
       │  analyze → synthesize → evaluate    │
       │              or                     │
       │    converge / transform             │
       └─────────────┬───────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
      reset_cycle           finalize
          │                     │
          └──────► ... ◄────────┘
                    │
                    ▼
                   END
    """
    # 建立圖
    graph = StateGraph(CGUState)

    # === 添加節點 ===

    # Fast Thinking (System 1)
    graph.add_node("react", react_node)
    graph.add_node("associate", associate_node)
    graph.add_node("pattern_match", pattern_match_node)

    # Slow Thinking (System 2)
    graph.add_node("analyze", analyze_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("evaluate", evaluate_node)

    # Creative Thinking
    graph.add_node("diverge", diverge_node)
    graph.add_node("converge", converge_node)
    graph.add_node("transform", transform_node)

    # Control nodes
    graph.add_node("reset_cycle", reset_cycle_node)
    graph.add_node("finalize", finalize_node)

    # === 設定入口點 ===
    graph.set_entry_point("react")

    # === 添加邊 ===

    # Fast thinking 流程
    graph.add_conditional_edges(
        "react",
        route_thinking,
        {
            "associate": "associate",
            "diverge": "diverge",
            "evaluate": "evaluate",
            "finalize": "finalize",
        }
    )

    graph.add_conditional_edges(
        "associate",
        route_thinking,
        {
            "pattern_match": "pattern_match",
            "diverge": "diverge",
            "analyze": "analyze",
            "finalize": "finalize",
        }
    )

    graph.add_conditional_edges(
        "pattern_match",
        route_thinking,
        {
            "diverge": "diverge",
            "analyze": "analyze",
            "evaluate": "evaluate",
            "finalize": "finalize",
        }
    )

    # Diverge 節點
    graph.add_conditional_edges(
        "diverge",
        route_thinking,
        {
            "associate": "associate",
            "diverge": "diverge",
            "converge": "converge",
            "evaluate": "evaluate",
            "reset_cycle": "reset_cycle",
            "finalize": "finalize",
        }
    )

    # Slow thinking 流程
    graph.add_conditional_edges(
        "analyze",
        route_thinking,
        {
            "synthesize": "synthesize",
            "evaluate": "evaluate",
            "finalize": "finalize",
        }
    )

    graph.add_conditional_edges(
        "synthesize",
        route_thinking,
        {
            "evaluate": "evaluate",
            "converge": "converge",
            "finalize": "finalize",
        }
    )

    graph.add_conditional_edges(
        "evaluate",
        route_thinking,
        {
            "react": "react",
            "diverge": "diverge",
            "reset_cycle": "reset_cycle",
            "finalize": "finalize",
        }
    )

    graph.add_conditional_edges(
        "converge",
        route_thinking,
        {
            "evaluate": "evaluate",
            "reset_cycle": "reset_cycle",
            "finalize": "finalize",
        }
    )

    graph.add_conditional_edges(
        "transform",
        route_thinking,
        {
            "converge": "converge",
            "evaluate": "evaluate",
            "finalize": "finalize",
        }
    )

    # Reset cycle 後繼續
    graph.add_conditional_edges(
        "reset_cycle",
        lambda s: "diverge",  # 新週期從發散開始
        {
            "diverge": "diverge",
        }
    )

    # Finalize 結束
    graph.add_edge("finalize", END)

    return graph


def create_cgu_agent(pattern: str = "explore"):
    """
    創建 CGU Agent

    Args:
        pattern: 快慢模式
            - sprint: 5 fast + 1 slow (快速嘗試)
            - explore: 3 fast + 1 slow (平衡探索)
            - refine: 2 fast + 2 slow (精煉模式)
            - deep: 1 fast + 3 slow (深度思考)

    Returns:
        編譯後的 LangGraph Agent
    """
    graph = build_cgu_graph()

    # 取得快慢配置
    fast_target, slow_target, description = FAST_SLOW_PATTERNS.get(
        pattern,
        FAST_SLOW_PATTERNS["explore"]
    )

    # 編譯圖
    agent = graph.compile()

    # 返回包裝的 agent 和配置
    return {
        "agent": agent,
        "pattern": pattern,
        "fast_target": fast_target,
        "slow_target": slow_target,
        "description": description,
    }


async def run_cgu(
    topic: str,
    creativity_level: int = 1,
    target_count: int = 5,
    pattern: str = "explore",
    constraints: list[str] | None = None,
) -> dict:
    """
    執行 CGU 創意生成

    Args:
        topic: 發想主題
        creativity_level: 創意層級 (1/2/3)
        target_count: 目標點子數量
        pattern: 快慢模式
        constraints: 限制條件

    Returns:
        生成結果
    """
    # 創建 agent
    cgu = create_cgu_agent(pattern)
    agent = cgu["agent"]

    # 準備初始狀態
    level = CreativityLevel(creativity_level)
    initial_state = CGUState(
        topic=topic,
        creativity_level=level,
        target_count=target_count,
        constraints=constraints or [],
        pattern=pattern,
        fast_target=cgu["fast_target"],
        slow_target=cgu["slow_target"],
    )

    # 執行圖
    final_state = await agent.ainvoke(initial_state.model_dump())

    # 整理輸出
    return {
        "topic": topic,
        "creativity_level": level.name,
        "pattern": f"{pattern} ({cgu['description']})",
        "iterations": final_state.get("iteration", 0),
        "total_fast_steps": final_state.get("fast_steps_count", 0),
        "total_slow_steps": final_state.get("slow_steps_count", 0),
        "thinking_steps": len(final_state.get("thinking_steps", [])),
        "ideas": [
            {
                "content": idea.content if hasattr(idea, "content") else idea.get("content"),
                "score": idea.association_score if hasattr(idea, "association_score") else idea.get("association_score"),
                "method": idea.source_method if hasattr(idea, "source_method") else idea.get("source_method"),
            }
            for idea in final_state.get("final_ideas", [])
        ],
    }
