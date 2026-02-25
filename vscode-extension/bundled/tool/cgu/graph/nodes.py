"""
CGU Thinking Nodes

LangGraph 節點定義 - 實作快思慢想的各種思考模式
整合 vLLM + Instructor 進行真實 LLM 呼叫
"""

import os
import logging
from typing import Optional, Any

from cgu.core import (
    ThinkingMode,
    ThinkingSpeed,
    ThinkingStep,
    CreativityMethod,
    METHOD_CONFIGS,
    select_method_for_task,
)
from cgu.graph.state import CGUState, Idea, NodeOutput

# LLM 整合（可選，fallback 到模擬模式）
USE_LLM = os.getenv("CGU_USE_LLM", "false").lower() == "true"

logger = logging.getLogger(__name__)

# 延遲載入 LLM 相關模組
_llm_client: Optional[Any] = None
_llm_available: bool = False

def _init_llm():
    """延遲初始化 LLM 客戶端"""
    global _llm_client, _llm_available
    if not USE_LLM:
        return False

    if _llm_client is not None:
        return _llm_available

    try:
        from cgu.llm import get_llm_client
        _llm_client = get_llm_client()
        _llm_available = True
        logger.info("LLM 客戶端已初始化")
        return True
    except Exception as e:
        logger.warning(f"LLM 初始化失敗: {e}")
        _llm_available = False
        return False

def _get_llm_client():
    """取得 LLM 客戶端"""
    global _llm_client
    if _init_llm():
        return _llm_client
    return None


# === Fast Thinking Nodes (System 1) ===


async def react_node(state: CGUState) -> dict:
    """
    REACT 節點 - 基本反應

    最快速的思考：直接對輸入產生反應
    """
    output_text = f"初步反應：關於 '{state.topic}' 的第一印象"
    associations = []

    client = _get_llm_client()
    if client is not None:
        try:
            from cgu.llm import AssociationList, SYSTEM_PROMPT_CREATIVITY
            prompt = f"針對主題「{state.topic}」，快速列出 5 個直覺聯想的概念或詞彙，每個用一行表示。"
            result = client.generate_structured(
                prompt=prompt,
                response_model=AssociationList,
                system_prompt=SYSTEM_PROMPT_CREATIVITY,
            )
            associations = result.associations
            output_text = f"初步反應：產生 {len(associations)} 個聯想"
        except Exception as e:
            logger.warning(f"LLM 呼叫失敗: {e}，使用模擬模式")
            associations = [
                f"{state.topic} 的核心概念",
                f"{state.topic} 的常見應用",
                f"{state.topic} 的相關領域",
            ]
    else:
        # 模擬模式
        associations = [
            f"{state.topic} 的核心概念",
            f"{state.topic} 的常見應用",
            f"{state.topic} 的相關領域",
        ]

    step = ThinkingStep(
        mode=ThinkingMode.REACT,
        speed=ThinkingSpeed.FAST,
        input_context=state.topic,
        output=output_text,
        confidence=0.6,
    )

    return {
        "thinking_steps": [step],
        "raw_associations": associations,
        "current_mode": ThinkingMode.ASSOCIATE,
        "fast_steps_count": state.fast_steps_count + 1,
    }


async def associate_node(state: CGUState) -> dict:
    """
    ASSOCIATE 節點 - 快速聯想

    從現有概念快速聯想到相關概念
    """
    # 從現有聯想擴展
    existing = state.raw_associations[-3:] if state.raw_associations else [state.topic]
    new_associations = []
    output_text = "聯想擴展中..."

    client = _get_llm_client()
    if client is not None:
        try:
            from cgu.llm import AssociationList, SYSTEM_PROMPT_CREATIVITY, PROMPT_ASSOCIATE_SIMPLE
            prompt = PROMPT_ASSOCIATE_SIMPLE.format(
                topic=state.topic,
                existing=", ".join(existing),
            )
            result = client.generate_structured(
                prompt=prompt,
                response_model=AssociationList,
                system_prompt=SYSTEM_PROMPT_CREATIVITY,
            )
            new_associations = result.associations
            output_text = f"聯想擴展：產生 {len(new_associations)} 個新聯想"
        except Exception as e:
            logger.warning(f"LLM 呼叫失敗: {e}，使用模擬模式")
            for concept in existing[:2]:
                new_associations.extend([
                    f"{concept} 的延伸",
                    f"{concept} 的變體",
                ])
    else:
        # 模擬模式
        for concept in existing[:2]:
            new_associations.extend([
                f"{concept} 的延伸",
                f"{concept} 的變體",
            ])

    step = ThinkingStep(
        mode=ThinkingMode.ASSOCIATE,
        speed=ThinkingSpeed.FAST,
        input_context=f"基於: {', '.join(existing)}",
        output=output_text,
        confidence=0.5,
    )

    return {
        "thinking_steps": [step],
        "raw_associations": new_associations,
        "current_mode": ThinkingMode.PATTERN_MATCH,
        "fast_steps_count": state.fast_steps_count + 1,
    }


async def pattern_match_node(state: CGUState) -> dict:
    """
    PATTERN_MATCH 節點 - 模式匹配

    識別聯想中的模式和規律
    """
    step = ThinkingStep(
        mode=ThinkingMode.PATTERN_MATCH,
        speed=ThinkingSpeed.FAST,
        input_context=f"分析 {len(state.raw_associations)} 個聯想",
        output="識別到的模式：主題群聚、概念橋接",
        confidence=0.55,
    )

    # 將聯想轉換為初步點子
    ideas = []
    for i, assoc in enumerate(state.raw_associations[-5:]):
        ideas.append(Idea(
            content=f"基於 '{assoc}' 的創意點子",
            association_score=0.6 - (i * 0.05),
            source_method="pattern_match",
        ))

    return {
        "thinking_steps": [step],
        "candidate_ideas": ideas,
        "current_mode": ThinkingMode.DIVERGE,
        "fast_steps_count": state.fast_steps_count + 1,
    }


# === Slow Thinking Nodes (System 2) ===


async def analyze_node(state: CGUState) -> dict:
    """
    ANALYZE 節點 - 慢速分析

    深入分析問題結構和現有點子
    """
    reasoning = f"""
分析維度：
1. 主題核心：{state.topic}
2. 創意層級：{state.creativity_level.name}
3. 已有點子：{len(state.candidate_ideas)}
4. 關聯範圍：{state.creativity_level.association_range}
"""
    output_text = "結構化分析完成"

    client = _get_llm_client()
    if client is not None:
        try:
            from cgu.llm import AnalysisOutput, SYSTEM_PROMPT_ANALYSIS, PROMPT_ANALYZE, format_ideas_list

            ideas_text = format_ideas_list([i.content for i in state.candidate_ideas[:10]])
            prompt = PROMPT_ANALYZE.format(
                topic=state.topic,
                ideas=ideas_text,
                creativity_level=state.creativity_level.name,
            )
            result = client.generate_structured(
                prompt=prompt,
                response_model=AnalysisOutput,
                system_prompt=SYSTEM_PROMPT_ANALYSIS,
            )
            reasoning = f"""
分析結果：
- 主題理解：{result.topic_understanding}
- 關鍵維度：{', '.join(result.key_dimensions)}
- 缺口識別：{', '.join(result.gaps)}
- 建議方向：{', '.join(result.suggestions)}
"""
            output_text = f"深度分析完成：識別 {len(result.key_dimensions)} 個維度，{len(result.gaps)} 個缺口"
        except Exception as e:
            logger.warning(f"LLM 分析失敗: {e}，使用預設分析")

    step = ThinkingStep(
        mode=ThinkingMode.ANALYZE,
        speed=ThinkingSpeed.SLOW,
        input_context=f"分析主題 '{state.topic}' 和 {len(state.candidate_ideas)} 個候選點子",
        output=output_text,
        confidence=0.7,
        reasoning=reasoning,
    )

    return {
        "thinking_steps": [step],
        "current_mode": ThinkingMode.SYNTHESIZE,
        "slow_steps_count": state.slow_steps_count + 1,
    }


async def synthesize_node(state: CGUState) -> dict:
    """
    SYNTHESIZE 節點 - 綜合整合

    將多個概念和點子整合成更完整的創意
    """
    step = ThinkingStep(
        mode=ThinkingMode.SYNTHESIZE,
        speed=ThinkingSpeed.SLOW,
        input_context=f"整合 {len(state.candidate_ideas)} 個點子",
        output="概念整合完成",
        confidence=0.75,
        reasoning="將相似概念合併，創造更豐富的組合",
    )

    # 嘗試合併點子產生新點子
    synthesized_ideas = []
    if len(state.candidate_ideas) >= 2:
        for i in range(min(3, len(state.candidate_ideas) - 1)):
            idea_a = state.candidate_ideas[i]
            idea_b = state.candidate_ideas[i + 1]
            synthesized_ideas.append(Idea(
                content=f"整合: {idea_a.content} + {idea_b.content}",
                association_score=(idea_a.association_score + idea_b.association_score) / 2,
                source_method="synthesize",
                reasoning=f"結合兩個概念的優勢",
            ))

    return {
        "thinking_steps": [step],
        "candidate_ideas": synthesized_ideas,
        "current_mode": ThinkingMode.EVALUATE,
        "slow_steps_count": state.slow_steps_count + 1,
    }


async def evaluate_node(state: CGUState) -> dict:
    """
    EVALUATE 節點 - 評估判斷

    評估點子的品質和可行性
    """
    reasoning = f"根據關聯性分數和創意層級 {state.creativity_level.name} 進行篩選"
    output_text = "評估完成，篩選出高潛力點子"

    # 預設根據創意層級篩選
    min_score, max_score = state.creativity_level.association_range
    sorted_ideas = sorted(
        state.candidate_ideas,
        key=lambda x: x.association_score,
        reverse=True
    )

    client = _get_llm_client()
    if client is not None and len(state.candidate_ideas) > 0:
        try:
            from cgu.llm import EvaluationOutput, SYSTEM_PROMPT_EVALUATION, PROMPT_EVALUATE, format_ideas_list

            ideas_text = format_ideas_list([i.content for i in state.candidate_ideas[:10]])
            prompt = PROMPT_EVALUATE.format(
                topic=state.topic,
                ideas=ideas_text,
                creativity_level=state.creativity_level.name,
            )
            result = client.generate_structured(
                prompt=prompt,
                response_model=EvaluationOutput,
                system_prompt=SYSTEM_PROMPT_EVALUATION,
            )

            # 根據 LLM 評分重新排序
            score_map = {e.idea_index: e.score for e in result.evaluations}
            for i, idea in enumerate(sorted_ideas):
                if i in score_map:
                    idea.association_score = score_map[i] / 10.0  # 轉換為 0-1 分數

            sorted_ideas = sorted(sorted_ideas, key=lambda x: x.association_score, reverse=True)
            reasoning = f"LLM 評估完成，最佳點子：{result.best_ideas[:3]}"
            output_text = f"評估完成：{len(result.evaluations)} 個點子已評分"
        except Exception as e:
            logger.warning(f"LLM 評估失敗: {e}，使用預設排序")

    # 取前 N 個作為最終點子
    final_count = min(state.target_count, len(sorted_ideas))
    final_ideas = sorted_ideas[:final_count]

    step = ThinkingStep(
        mode=ThinkingMode.EVALUATE,
        speed=ThinkingSpeed.SLOW,
        input_context=f"評估 {len(state.candidate_ideas)} 個候選點子",
        output=output_text,
        confidence=0.8,
        reasoning=reasoning,
    )

    return {
        "thinking_steps": [step],
        "final_ideas": final_ideas,
        "slow_steps_count": state.slow_steps_count + 1,
        "should_stop": len(final_ideas) >= state.target_count,
    }


# === Creative Thinking Nodes ===


async def diverge_node(state: CGUState) -> dict:
    """
    DIVERGE 節點 - 發散思考

    使用創意方法產生多種可能
    """
    # 選擇創意方法
    method = state.selected_method or select_method_for_task(
        creativity_level=state.creativity_level,
        prefer_fast=True,
    )

    output_text = f"發散中: {method.value}"
    new_ideas = []
    config = METHOD_CONFIGS.get(method)

    client = _get_llm_client()
    if client is not None:
        try:
            if method == CreativityMethod.SCAMPER:
                from cgu.llm import ScamperOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_SCAMPER
                prompt = PROMPT_SCAMPER.format(topic=state.topic)
                result = client.generate_structured(
                    prompt=prompt,
                    response_model=ScamperOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                for op, content in [
                    ("替代", result.substitute),
                    ("結合", result.combine),
                    ("調適", result.adapt),
                    ("修改", result.modify),
                    ("他用", result.put_to_other_uses),
                    ("消除", result.eliminate),
                    ("重排", result.rearrange),
                ]:
                    if content:
                        new_ideas.append(Idea(
                            content=f"SCAMPER-{op}: {content}",
                            association_score=0.6,
                            source_method="scamper",
                        ))
                output_text = f"SCAMPER 發散完成：產生 {len(new_ideas)} 個點子"

            elif method == CreativityMethod.SIX_HATS:
                from cgu.llm import SixHatsOutput, SYSTEM_PROMPT_CREATIVITY
                prompt = f"使用六頂思考帽方法分析主題「{state.topic}」，從白、紅、黑、黃、綠、藍六個角度思考。"
                result = client.generate_structured(
                    prompt=prompt,
                    response_model=SixHatsOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                for hat, content in [
                    ("白帽-事實", result.white),
                    ("紅帽-情感", result.red),
                    ("黑帽-風險", result.black),
                    ("黃帽-優點", result.yellow),
                    ("綠帽-創意", result.green),
                    ("藍帽-整合", result.blue),
                ]:
                    if content:
                        new_ideas.append(Idea(
                            content=f"{hat}: {content}",
                            association_score=0.65,
                            source_method="six_hats",
                        ))
                output_text = f"六頂思考帽分析完成：產生 {len(new_ideas)} 個觀點"

            else:
                # 通用創意產生
                from cgu.llm import IdeasOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_GENERATE_IDEAS
                prompt = PROMPT_GENERATE_IDEAS.format(
                    topic=state.topic,
                    creativity_level=state.creativity_level.value,
                    count=5,
                    constraints_text="",
                )
                result = client.generate_structured(
                    prompt=prompt,
                    response_model=IdeasOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                for idea_text in result.ideas:
                    new_ideas.append(Idea(
                        content=idea_text,
                        association_score=0.55,
                        source_method=method.value,
                    ))
                output_text = f"{method.value} 發散完成：產生 {len(new_ideas)} 個點子"

        except Exception as e:
            logger.warning(f"LLM 發散失敗: {e}，使用模擬模式")
            new_ideas = _simulate_diverge(state.topic, method)
    else:
        # 模擬模式
        new_ideas = _simulate_diverge(state.topic, method)

    step = ThinkingStep(
        mode=ThinkingMode.DIVERGE,
        speed=ThinkingSpeed.FAST,
        input_context=f"使用 {method.value} 方法發散思考",
        output=output_text,
        confidence=0.5,
    )

    return {
        "thinking_steps": [step],
        "candidate_ideas": new_ideas,
        "selected_method": method,
        "current_mode": ThinkingMode.CONVERGE,
        "fast_steps_count": state.fast_steps_count + 1,
    }


def _simulate_diverge(topic: str, method: CreativityMethod) -> list[Idea]:
    """模擬發散思考（無 LLM 時使用）"""
    ideas = []
    if method == CreativityMethod.SCAMPER:
        scamper_ops = ["替代", "結合", "調適", "修改", "他用", "消除", "重排"]
        for op in scamper_ops[:3]:
            ideas.append(Idea(
                content=f"SCAMPER-{op}: {topic} 的 {op} 變形",
                association_score=0.6,
                source_method="scamper",
            ))
    elif method == CreativityMethod.MIND_MAP:
        branches = ["功能", "用戶", "技術", "情感", "價值"]
        for branch in branches[:3]:
            ideas.append(Idea(
                content=f"心智圖-{branch}: {topic} 的 {branch} 面向",
                association_score=0.65,
                source_method="mind_map",
            ))
    else:
        for i in range(3):
            ideas.append(Idea(
                content=f"發散點子 {i+1}: {topic} 的創新變體",
                association_score=0.55,
                source_method=method.value,
            ))
    return ideas


async def converge_node(state: CGUState) -> dict:
    """
    CONVERGE 節點 - 收斂思考

    從多個可能中選擇最佳方案
    """
    step = ThinkingStep(
        mode=ThinkingMode.CONVERGE,
        speed=ThinkingSpeed.SLOW,
        input_context=f"從 {len(state.candidate_ideas)} 個點子中收斂",
        output="收斂評估完成",
        confidence=0.7,
        reasoning="根據關聯性和創意層級進行收斂篩選",
    )

    # 收斂邏輯：根據創意層級篩選合適的關聯性範圍
    min_score, max_score = state.creativity_level.association_range

    filtered_ideas = [
        idea for idea in state.candidate_ideas
        if min_score <= idea.association_score <= max_score
    ]

    # 如果篩選後太少，放寬條件
    if len(filtered_ideas) < state.target_count:
        filtered_ideas = sorted(
            state.candidate_ideas,
            key=lambda x: abs(x.association_score - (min_score + max_score) / 2)
        )[:state.target_count]

    return {
        "thinking_steps": [step],
        "final_ideas": filtered_ideas[:state.target_count],
        "slow_steps_count": state.slow_steps_count + 1,
    }


async def transform_node(state: CGUState) -> dict:
    """
    TRANSFORM 節點 - 變革思考

    打破規則，創造全新範式（Level 3 創意）
    """
    step = ThinkingStep(
        mode=ThinkingMode.TRANSFORM,
        speed=ThinkingSpeed.SLOW,
        input_context=f"對 '{state.topic}' 進行變革性思考",
        output="嘗試打破既有框架",
        confidence=0.4,  # 變革性思考信心較低但潛力高
        reasoning="質疑所有假設，尋找顛覆性可能",
    )

    # 變革性點子
    transform_ideas = [
        Idea(
            content=f"反轉: 如果 {state.topic} 完全相反會怎樣？",
            association_score=0.2,
            source_method="transform",
            reasoning="完全反轉假設",
        ),
        Idea(
            content=f"極端: 將 {state.topic} 放大 100 倍會怎樣？",
            association_score=0.15,
            source_method="transform",
            reasoning="極端化思考",
        ),
        Idea(
            content=f"跨界: {state.topic} 遇上完全無關的領域",
            association_score=0.1,
            source_method="transform",
            reasoning="強制跨域連結",
        ),
    ]

    return {
        "thinking_steps": [step],
        "candidate_ideas": transform_ideas,
        "slow_steps_count": state.slow_steps_count + 1,
    }


# === 節點映射 ===

NODE_MAP = {
    ThinkingMode.REACT: react_node,
    ThinkingMode.ASSOCIATE: associate_node,
    ThinkingMode.PATTERN_MATCH: pattern_match_node,
    ThinkingMode.ANALYZE: analyze_node,
    ThinkingMode.SYNTHESIZE: synthesize_node,
    ThinkingMode.EVALUATE: evaluate_node,
    ThinkingMode.DIVERGE: diverge_node,
    ThinkingMode.CONVERGE: converge_node,
    ThinkingMode.TRANSFORM: transform_node,
}
