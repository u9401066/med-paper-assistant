"""
CGU Graph Builder - LangGraph 1.0 Functional API 版本

使用 @entrypoint 和 @task 裝飾器重構快思慢想流程
支援 Python 3.12 新特性
"""

from typing import TypedDict, override
from langgraph.func import entrypoint, task
from langgraph.types import Command, interrupt

from cgu.core import ThinkingMode, CreativityLevel, ThinkingStep, ThinkingSpeed
from cgu.graph.state import CGUState, Idea


# === Python 3.12 新語法：Type Parameter Syntax (PEP 695) ===
type IdeaList = list[Idea]
type AssociationList = list[str]


class ThinkingResult(TypedDict):
    """思考結果類型"""
    ideas: IdeaList
    associations: AssociationList
    step: ThinkingStep
    should_continue: bool


# === Fast Thinking Tasks (System 1) ===

@task
async def react_task(topic: str, context: str = "") -> ThinkingResult:
    """
    REACT 任務 - 基本反應

    Python 3.12 f-string 新特性：可嵌套、多行
    """
    # 多行 f-string with comments (PEP 701)
    output = f"""初步反應：
        主題: {topic}
        上下文: {context if context else "無"}
    """

    associations = [
        f"{topic} 的核心概念",
        f"{topic} 的常見應用",
        f"{topic} 的相關領域",
    ]

    step = ThinkingStep(
        mode=ThinkingMode.REACT,
        speed=ThinkingSpeed.FAST,
        input_context=topic,
        output=output.strip(),
        confidence=0.6,
    )

    return {
        "ideas": [],
        "associations": associations,
        "step": step,
        "should_continue": True,
    }


@task
async def associate_task(
    topic: str,
    existing: AssociationList,
) -> ThinkingResult:
    """
    ASSOCIATE 任務 - 快速聯想
    """
    new_associations = []
    for concept in existing[:3]:
        new_associations.extend([
            f"{concept} 的延伸",
            f"{concept} 的變體",
        ])

    step = ThinkingStep(
        mode=ThinkingMode.ASSOCIATE,
        speed=ThinkingSpeed.FAST,
        input_context=f"基於: {', '.join(existing[:3])}",
        output=f"聯想擴展：產生 {len(new_associations)} 個新聯想",
        confidence=0.5,
    )

    return {
        "ideas": [],
        "associations": new_associations,
        "step": step,
        "should_continue": True,
    }


@task
async def pattern_match_task(
    associations: AssociationList,
) -> ThinkingResult:
    """
    PATTERN_MATCH 任務 - 模式匹配
    """
    # 將聯想轉換為初步點子
    ideas = [
        Idea(
            content=f"基於 '{assoc}' 的創意點子",
            association_score=0.6 - (i * 0.05),
            source_method="pattern_match",
        )
        for i, assoc in enumerate(associations[-5:])
    ]

    step = ThinkingStep(
        mode=ThinkingMode.PATTERN_MATCH,
        speed=ThinkingSpeed.FAST,
        input_context=f"分析 {len(associations)} 個聯想",
        output="識別到的模式：主題群聚、概念橋接",
        confidence=0.55,
    )

    return {
        "ideas": ideas,
        "associations": [],
        "step": step,
        "should_continue": True,
    }


# === Slow Thinking Tasks (System 2) ===

@task
async def analyze_task(
    topic: str,
    ideas: IdeaList,
    creativity_level: CreativityLevel,
) -> ThinkingResult:
    """
    ANALYZE 任務 - 慢速分析
    """
    # Python 3.12 f-string 多行 + 嵌套
    reasoning = f"""
分析維度：
1. 主題核心：{topic}
2. 創意層級：{creativity_level.name}
3. 已有點子：{len(ideas)}
4. 關聯範圍：{creativity_level.association_range}
"""

    step = ThinkingStep(
        mode=ThinkingMode.ANALYZE,
        speed=ThinkingSpeed.SLOW,
        input_context=f"分析主題 '{topic}' 和 {len(ideas)} 個候選點子",
        output="結構化分析完成",
        confidence=0.7,
        reasoning=reasoning,
    )

    return {
        "ideas": ideas,
        "associations": [],
        "step": step,
        "should_continue": True,
    }


@task
async def evaluate_task(
    ideas: IdeaList,
    target_count: int,
    creativity_level: CreativityLevel,
) -> ThinkingResult:
    """
    EVALUATE 任務 - 評估判斷
    """
    min_score, max_score = creativity_level.association_range

    sorted_ideas = sorted(
        ideas,
        key=lambda x: x.association_score,
        reverse=True,
    )

    final_count = min(target_count, len(sorted_ideas))
    final_ideas = sorted_ideas[:final_count]

    step = ThinkingStep(
        mode=ThinkingMode.EVALUATE,
        speed=ThinkingSpeed.SLOW,
        input_context=f"評估 {len(ideas)} 個候選點子",
        output=f"評估完成，篩選出 {final_count} 個高潛力點子",
        confidence=0.8,
        reasoning=f"根據分數範圍 {min_score}-{max_score} 進行篩選",
    )

    should_continue = len(final_ideas) < target_count

    return {
        "ideas": final_ideas,
        "associations": [],
        "step": step,
        "should_continue": should_continue,
    }


# === Main Entrypoint ===

@entrypoint()
async def cgu_workflow(
    topic: str,
    creativity_level: int = 1,
    target_count: int = 5,
    pattern: str = "explore",
) -> dict:
    """
    CGU 創意生成工作流 - Functional API 入口點

    Args:
        topic: 發想主題
        creativity_level: 創意層級 (1/2/3)
        target_count: 目標點子數量
        pattern: 快慢模式

    Returns:
        生成結果
    """
    level = CreativityLevel(creativity_level)
    all_steps: list[ThinkingStep] = []
    associations: AssociationList = []
    ideas: IdeaList = []

    # === Fast Thinking Phase ===

    # Step 1: React
    react_result = await react_task(topic)
    all_steps.append(react_result["step"])
    associations.extend(react_result["associations"])

    # Step 2: Associate
    associate_result = await associate_task(topic, associations)
    all_steps.append(associate_result["step"])
    associations.extend(associate_result["associations"])

    # Step 3: Pattern Match
    pattern_result = await pattern_match_task(associations)
    all_steps.append(pattern_result["step"])
    ideas.extend(pattern_result["ideas"])

    # === Slow Thinking Phase ===

    # Step 4: Analyze
    analyze_result = await analyze_task(topic, ideas, level)
    all_steps.append(analyze_result["step"])

    # Step 5: Evaluate
    evaluate_result = await evaluate_task(ideas, target_count, level)
    all_steps.append(evaluate_result["step"])
    final_ideas = evaluate_result["ideas"]

    # === Iteration if needed ===
    iteration = 1
    max_iterations = 3

    while evaluate_result["should_continue"] and iteration < max_iterations:
        iteration += 1

        # More association
        associate_result = await associate_task(topic, associations)
        all_steps.append(associate_result["step"])
        associations.extend(associate_result["associations"])

        # Pattern match
        pattern_result = await pattern_match_task(associations)
        all_steps.append(pattern_result["step"])
        ideas.extend(pattern_result["ideas"])

        # Re-evaluate
        evaluate_result = await evaluate_task(ideas, target_count, level)
        all_steps.append(evaluate_result["step"])
        final_ideas = evaluate_result["ideas"]

    # === Format Output ===
    return {
        "topic": topic,
        "creativity_level": level.name,
        "pattern": pattern,
        "iterations": iteration,
        "thinking_steps": len(all_steps),
        "ideas": [
            {
                "content": idea.content,
                "score": idea.association_score,
                "method": idea.source_method,
            }
            for idea in final_ideas
        ],
    }


# === Alternative: Using Command for more control ===

@entrypoint()
async def cgu_workflow_with_commands(
    topic: str,
    creativity_level: int = 1,
    target_count: int = 5,
) -> dict:
    """
    使用 Command 進行更精細控制的工作流

    展示 LangGraph 1.0 的 Command 和 interrupt 特性
    """
    level = CreativityLevel(creativity_level)

    # 使用 Command 進行條件控制
    react_result = await react_task(topic)

    if not react_result["associations"]:
        # 可以在這裡使用 interrupt 暫停等待人工輸入
        # user_input = interrupt("需要更多上下文，請提供...")
        pass

    # 繼續處理...
    associate_result = await associate_task(topic, react_result["associations"])
    pattern_result = await pattern_match_task(associate_result["associations"])

    evaluate_result = await evaluate_task(
        pattern_result["ideas"],
        target_count,
        level,
    )

    return {
        "topic": topic,
        "ideas": [
            {"content": i.content, "score": i.association_score}
            for i in evaluate_result["ideas"]
        ],
    }


# === Convenience function ===

async def run_cgu_functional(
    topic: str,
    creativity_level: int = 1,
    target_count: int = 5,
    pattern: str = "explore",
) -> dict:
    """
    便捷函數：執行 CGU Functional API
    """
    return await cgu_workflow(
        topic=topic,
        creativity_level=creativity_level,
        target_count=target_count,
        pattern=pattern,
    )
