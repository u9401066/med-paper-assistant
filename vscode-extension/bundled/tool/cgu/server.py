"""
CGU MCP Server

使用 FastMCP 提供創意生成工具
整合 Ollama LLM 進行真實創意生成

支援三種思考模式：
- simple: Ollama/Copilot 快速單次發想（預設）
- deep: Multi-Agent 並發深度思考
- spark: 概念碰撞產生靈感火花
"""

import os
import logging

from mcp.server.fastmcp import FastMCP

from cgu.core import (
    CreativityLevel,
    CreativityMethod,
    ThinkingMode,
    ThinkingSpeed,
    METHOD_CONFIGS,
    select_method_for_task,
)

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM 模式
# 預設 true - 啟用 Ollama LLM（確保 Ollama 服務已啟動）
USE_LLM = os.getenv("CGU_USE_LLM", "true").lower() == "true"
# 思考引擎：ollama (本地推理) | copilot (僅提供框架，讓 Copilot 填充)
LLM_PROVIDER = os.getenv("CGU_LLM_PROVIDER", "ollama").lower()
# 思考深度：shallow (快) | medium (中) | deep (深)
THINKING_DEPTH = os.getenv("CGU_THINKING_DEPTH", "medium").lower()
# Ollama 模型
OLLAMA_MODEL = os.getenv("CGU_OLLAMA_MODEL", "qwen2.5:3b")

# 初始化 FastMCP Server
mcp = FastMCP(
    name="creativity-generation-unit",
    instructions="CGU - MCP-based 創意發想服務，使用快思慢想架構。支援 generate_ideas, spark_collision, apply_method 等工具。",
)


# === LLM 輔助函數 ===

def _get_llm_client():
    """取得 LLM 客戶端"""
    # copilot 模式：不使用本地 LLM，返回框架讓 Copilot 思考
    if LLM_PROVIDER == "copilot":
        return None
    if not USE_LLM:
        return None
    try:
        from cgu.llm import get_llm_client, LLMConfig
        # 使用環境變數配置
        config = LLMConfig(model=OLLAMA_MODEL)
        return get_llm_client(config)
    except Exception as e:
        logger.warning(f"LLM 初始化失敗: {e}")
        logger.info("提示：請確保 Ollama 服務已啟動 (ollama serve)")
        return None


def _is_copilot_mode() -> bool:
    """檢查是否為 Copilot 模式"""
    return LLM_PROVIDER == "copilot"


def _get_thinking_engine():
    """取得統一思考引擎"""
    try:
        from cgu.thinking import ThinkingEngine, ThinkingConfig, ThinkingDepth

        depth_map = {
            "shallow": ThinkingDepth.SHALLOW,
            "medium": ThinkingDepth.MEDIUM,
            "deep": ThinkingDepth.DEEP,
        }

        config = ThinkingConfig(depth=depth_map.get(THINKING_DEPTH, ThinkingDepth.MEDIUM))
        engine = ThinkingEngine(config=config)

        if _is_copilot_mode():
            engine.set_copilot_mode(True)

        return engine
    except Exception as e:
        logger.warning(f"ThinkingEngine 初始化失敗: {e}")
        return None


# === MCP Tools ===


@mcp.tool()
async def generate_ideas(
    topic: str,
    creativity_level: int = 1,
    count: int = 5,
    constraints: list[str] | None = None,
) -> dict:
    """
    生成創意點子

    Args:
        topic: 要發想的主題
        creativity_level: 創意層級 (1=組合, 2=探索, 3=變革)
        count: 要產生的點子數量
        constraints: 限制條件列表

    Returns:
        包含點子和連結的字典
    """
    level = CreativityLevel(creativity_level)
    assoc_range = level.association_range

    ideas = []
    method_used = "brainstorm"

    client = _get_llm_client()
    if client is not None:
        try:
            from cgu.llm import IdeasOutput, SYSTEM_PROMPT_CREATIVITY

            constraints_text = "\n".join(f"- {c}" for c in (constraints or []))
            prompt = f"""為以下主題產生 {count} 個創意點子：

主題：{topic}
創意層級：{level.name}（{level.value}=組合創意, 2=探索創意, 3=變革創意）
{f"限制條件：{constraints_text}" if constraints else ""}

請產生 {count} 個具體、可執行的創意點子。"""

            result = client.generate_structured(
                prompt=prompt,
                response_model=IdeasOutput,
                system_prompt=SYSTEM_PROMPT_CREATIVITY,
            )
            ideas = [{"id": i+1, "content": idea, "association_score": 0.7 - i*0.05}
                     for i, idea in enumerate(result.ideas[:count])]
            method_used = "llm_brainstorm"
        except Exception as e:
            logger.warning(f"LLM 生成失敗: {e}")

    # Fallback 到模擬（或 Copilot 模式框架）
    if not ideas:
        if _is_copilot_mode():
            # Copilot 模式：返回思考框架，讓 Copilot 填充
            ideas = [
                {"id": i + 1, "content": f"[請 Copilot 思考] {topic} 的第 {i + 1} 個點子", "association_score": 0.5}
                for i in range(count)
            ]
            method_used = "copilot_framework"
        else:
            ideas = [
                {"id": i + 1, "content": f"[模擬] {topic} 的點子 {i + 1}", "association_score": 0.5}
                for i in range(count)
            ]

    return {
        "topic": topic,
        "creativity_level": level.name,
        "association_range": f"{assoc_range[0]:.1f} - {assoc_range[1]:.1f}",
        "constraints": constraints or [],
        "ideas": ideas,
        "method_used": method_used,
        "llm_provider": LLM_PROVIDER,
        "copilot_hint": "請根據上述框架，用你的創意填充具體點子" if _is_copilot_mode() else None,
        "thinking_steps": [
            {"mode": "REACT", "speed": "fast"},
            {"mode": "ASSOCIATE", "speed": "fast"},
            {"mode": "DIVERGE", "speed": "fast"},
        ],
    }


@mcp.tool()
async def spark_collision(
    concept_a: str,
    concept_b: str,
) -> dict:
    """
    概念碰撞 - 讓兩個概念產生火花

    低關聯但有潛力的連結往往能產生最有創意的點子

    Args:
        concept_a: 第一個概念
        concept_b: 第二個概念

    Returns:
        碰撞產生的火花和理由
    """
    sparks = []
    rationale = f"從 {concept_a} 的特性與 {concept_b} 的特性中找到意想不到的連結"

    client = _get_llm_client()
    if client is not None:
        try:
            from cgu.llm import SparkOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_SPARK

            prompt = PROMPT_SPARK.format(
                concept_a=concept_a,
                concept_b=concept_b,
                count=5,
            )
            result = client.generate_structured(
                prompt=prompt,
                response_model=SparkOutput,
                system_prompt=SYSTEM_PROMPT_CREATIVITY,
            )
            sparks = result.sparks
            rationale = result.reasoning
        except Exception as e:
            logger.warning(f"LLM 碰撞失敗: {e}")

    # Fallback
    if not sparks:
        sparks = [
            f"[模擬] {concept_a} + {concept_b} 的創意組合 {i}"
            for i in range(1, 4)
        ]

    return {
        "concept_a": concept_a,
        "concept_b": concept_b,
        "sparks": sparks,
        "rationale": rationale,
        "association_score": 0.3,
    }


@mcp.tool()
async def associative_expansion(
    seed: str,
    direction: str = "similar",
    depth: int = 2,
) -> dict:
    """
    聯想擴展 - 從種子概念向外擴展

    Args:
        seed: 種子概念
        direction: 擴展方向 (similar/opposite/random/cross-domain)
        depth: 擴展深度

    Returns:
        擴展後的聯想樹
    """
    valid_directions = ["similar", "opposite", "random", "cross-domain"]
    if direction not in valid_directions:
        direction = "similar"

    associations = []

    client = _get_llm_client()
    if client is not None:
        try:
            from cgu.llm import AssociationList, SYSTEM_PROMPT_CREATIVITY

            for level in range(1, depth + 1):
                prompt = f"""從「{seed}」進行 {direction} 方向的聯想，第 {level} 層擴展。
請列出 3-5 個聯想概念。

方向說明：
- similar: 相似概念
- opposite: 相反或對比概念
- random: 隨機但有趣的連結
- cross-domain: 跨領域的概念"""

                result = client.generate_structured(
                    prompt=prompt,
                    response_model=AssociationList,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                associations.append({
                    "level": level,
                    "concepts": result.associations[:5],
                })
        except Exception as e:
            logger.warning(f"LLM 聯想失敗: {e}")

    # Fallback
    if not associations:
        associations = [
            {"level": i+1, "concepts": [f"[模擬] {seed} 的 {direction} 聯想 {j}" for j in range(1, 4)]}
            for i in range(depth)
        ]

    return {
        "seed": seed,
        "direction": direction,
        "depth": depth,
        "associations": associations,
        "thinking_mode": ThinkingMode.ASSOCIATE.value,
        "thinking_speed": ThinkingSpeed.FAST.value,
    }


@mcp.tool()
async def apply_method(
    method: str,
    input_concept: str,
    options: dict | None = None,
) -> dict:
    """
    應用特定創意方法

    Args:
        method: 方法名稱 (mind_map/scamper/six_hats/mandala_9grid/...)
        input_concept: 輸入概念
        options: 方法特定選項

    Returns:
        方法應用結果
    """
    # 驗證方法
    try:
        creativity_method = CreativityMethod(method)
    except ValueError:
        available = [m.value for m in CreativityMethod]
        return {
            "error": f"Unknown method: {method}",
            "available_methods": available,
        }

    config = METHOD_CONFIGS.get(creativity_method)
    if not config:
        return {"error": f"Method config not found: {method}"}

    result = {
        "method": method,
        "method_description": config.description,
        "category": config.category.value,
        "thinking_speed": config.thinking_speed,
        "agent_strategy": config.agent_strategy,
        "input": input_concept,
        "options": options or {},
    }

    client = _get_llm_client()

    # SCAMPER 方法
    if method == "scamper":
        if client is not None:
            try:
                from cgu.llm import ScamperOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_SCAMPER
                prompt = PROMPT_SCAMPER.format(topic=input_concept)
                scamper_result = client.generate_structured(
                    prompt=prompt,
                    response_model=ScamperOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "S_substitute": scamper_result.substitute,
                    "C_combine": scamper_result.combine,
                    "A_adapt": scamper_result.adapt,
                    "M_modify": scamper_result.modify,
                    "P_put_to_other_uses": scamper_result.put_to_other_uses,
                    "E_eliminate": scamper_result.eliminate,
                    "R_reverse": scamper_result.reverse,
                    "best_idea": scamper_result.best_idea,
                }
            except Exception as e:
                logger.warning(f"SCAMPER LLM 失敗: {e}")
                result["output"] = _simulate_scamper(input_concept)
        else:
            result["output"] = _simulate_scamper(input_concept)

    # 六頂思考帽
    elif method == "six_hats":
        if client is not None:
            try:
                from cgu.llm import SixHatsOutput, SYSTEM_PROMPT_CREATIVITY
                prompt = f"使用六頂思考帽方法分析主題「{input_concept}」，從白、紅、黑、黃、綠、藍六個角度思考。"
                hats_result = client.generate_structured(
                    prompt=prompt,
                    response_model=SixHatsOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "white_facts": hats_result.white,
                    "red_feelings": hats_result.red,
                    "black_risks": hats_result.black,
                    "yellow_benefits": hats_result.yellow,
                    "green_ideas": hats_result.green,
                    "blue_summary": hats_result.blue,
                }
            except Exception as e:
                logger.warning(f"六頂帽 LLM 失敗: {e}")
                result["output"] = _simulate_six_hats(input_concept)
        else:
            result["output"] = _simulate_six_hats(input_concept)

    # 九宮格
    elif method == "mandala_9grid":
        if client is not None:
            try:
                from cgu.llm import MandalaOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_MANDALA
                prompt = PROMPT_MANDALA.format(concept=input_concept)
                mandala_result = client.generate_structured(
                    prompt=prompt,
                    response_model=MandalaOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "center": mandala_result.center,
                    "extensions": mandala_result.extensions,
                }
            except Exception as e:
                logger.warning(f"九宮格 LLM 失敗: {e}")
                result["output"] = _simulate_mandala(input_concept)
        else:
            result["output"] = _simulate_mandala(input_concept)
    # 5W2H 方法
    elif method == "5w2h":
        if client is not None:
            try:
                from cgu.llm import SYSTEM_PROMPT_CREATIVITY
                from pydantic import BaseModel

                class FiveW2HOutput(BaseModel):
                    what: str
                    why: str
                    who: str
                    when: str
                    where: str
                    how: str
                    how_much: str

                prompt = f"""使用 5W2H 方法分析以下主題：

主題：{input_concept}

請回答：
- What（是什麼）：這是什麼？
- Why（為什麼）：為什麼要做這件事？
- Who（誰）：誰來做？誰受益？
- When（何時）：什麼時候做？
- Where（哪裡）：在哪裡進行？
- How（如何）：如何實現？
- How much（多少）：需要多少資源？"""

                output = client.generate_structured(
                    prompt=prompt,
                    response_model=FiveW2HOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "what": output.what,
                    "why": output.why,
                    "who": output.who,
                    "when": output.when,
                    "where": output.where,
                    "how": output.how,
                    "how_much": output.how_much,
                }
            except Exception as e:
                logger.warning(f"5W2H LLM 失敗: {e}")
                result["output"] = _simulate_5w2h(input_concept)
        else:
            result["output"] = _simulate_5w2h(input_concept)

    # 逆向思考
    elif method == "reverse":
        if client is not None:
            try:
                from cgu.llm import ReverseOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_REVERSE
                prompt = PROMPT_REVERSE.format(problem=input_concept)
                reverse_result = client.generate_structured(
                    prompt=prompt,
                    response_model=ReverseOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "reverse_question": reverse_result.reverse_question,
                    "failure_methods": reverse_result.failure_methods,
                    "solutions": reverse_result.solutions,
                }
            except Exception as e:
                logger.warning(f"Reverse LLM 失敗: {e}")
                result["output"] = _simulate_reverse(input_concept)
        else:
            result["output"] = _simulate_reverse(input_concept)

    # 心智圖
    elif method == "mind_map":
        if client is not None:
            try:
                from cgu.llm import MindMapOutput, SYSTEM_PROMPT_CREATIVITY, PROMPT_MIND_MAP
                branches = (options or {}).get("branches", 4)
                sub_branches = (options or {}).get("sub_branches", 3)
                prompt = PROMPT_MIND_MAP.format(topic=input_concept, branches=branches, sub_branches=sub_branches)
                mindmap_result = client.generate_structured(
                    prompt=prompt,
                    response_model=MindMapOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "center": mindmap_result.center,
                    "branches": [
                        {"name": b.name, "sub_branches": b.sub_branches}
                        for b in mindmap_result.branches
                    ],
                }
            except Exception as e:
                logger.warning(f"MindMap LLM 失敗: {e}")
                result["output"] = _simulate_mind_map(input_concept)
        else:
            result["output"] = _simulate_mind_map(input_concept)

    # 腦力激盪
    elif method == "brainstorm":
        if client is not None:
            try:
                from cgu.llm import IdeasOutput, SYSTEM_PROMPT_CREATIVITY
                count = (options or {}).get("count", 10)
                prompt = f"""對以下主題進行腦力激盪，產生 {count} 個不受限制的創意點子：

主題：{input_concept}

規則：
1. 不批判任何想法
2. 越瘋狂越好
3. 數量優先於質量
4. 可以結合他人想法

請列出 {count} 個點子："""
                brainstorm_result = client.generate_structured(
                    prompt=prompt,
                    response_model=IdeasOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {"ideas": brainstorm_result.ideas}
            except Exception as e:
                logger.warning(f"Brainstorm LLM 失敗: {e}")
                result["output"] = _simulate_brainstorm(input_concept)
        else:
            result["output"] = _simulate_brainstorm(input_concept)

    # 隨機輸入
    elif method == "random_input":
        import random
        random_words = ["星空", "咖啡", "森林", "機器人", "音樂", "海洋", "夢想", "旅行", "魔法", "時間"]
        random_word = random.choice(random_words)
        if client is not None:
            try:
                from cgu.llm import SparkOutput, SYSTEM_PROMPT_CREATIVITY
                prompt = f"""使用隨機詞強制聯想法：

原始主題：{input_concept}
隨機詞：{random_word}

請思考：
1. 這個隨機詞讓你聯想到什麼？
2. 如何將隨機詞與原始主題連結？
3. 產生 5 個結合兩者的創意點子"""
                random_result = client.generate_structured(
                    prompt=prompt,
                    response_model=SparkOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                result["output"] = {
                    "random_word": random_word,
                    "sparks": random_result.sparks,
                    "reasoning": random_result.reasoning,
                }
            except Exception as e:
                logger.warning(f"RandomInput LLM 失敗: {e}")
                result["output"] = _simulate_random_input(input_concept, random_word)
        else:
            result["output"] = _simulate_random_input(input_concept, random_word)
    else:
        result["output"] = f"[模擬] {method} 方法應用於 {input_concept}"

    return result


def _simulate_scamper(concept: str) -> dict:
    """模擬 SCAMPER 輸出"""
    return {
        "S_substitute": f"[模擬] 替代 {concept}",
        "C_combine": f"[模擬] 結合 {concept}",
        "A_adapt": f"[模擬] 調適 {concept}",
        "M_modify": f"[模擬] 修改 {concept}",
        "P_put_to_other_uses": f"[模擬] 他用 {concept}",
        "E_eliminate": f"[模擬] 消除 {concept}",
        "R_reverse": f"[模擬] 重排 {concept}",
    }


def _simulate_six_hats(concept: str) -> dict:
    """模擬六頂帽輸出"""
    return {
        "white_facts": f"[模擬] 關於 {concept} 的事實",
        "red_feelings": f"[模擬] 對 {concept} 的感覺",
        "black_risks": f"[模擬] {concept} 的風險",
        "yellow_benefits": f"[模擬] {concept} 的好處",
        "green_ideas": f"[模擬] {concept} 的新點子",
        "blue_summary": f"[模擬] {concept} 的總結",
    }


def _simulate_mandala(concept: str) -> dict:
    """模擬九宮格輸出"""
    return {
        "center": concept,
        "extensions": [f"[模擬] {concept} 延伸 {i}" for i in range(1, 9)],
    }


def _simulate_5w2h(concept: str) -> dict:
    """模擬 5W2H 輸出"""
    return {
        "what": f"[模擬] {concept} 是什麼",
        "why": f"[模擬] 為什麼要 {concept}",
        "who": f"[模擬] 誰參與 {concept}",
        "when": f"[模擬] 何時進行 {concept}",
        "where": f"[模擬] 在哪裡進行 {concept}",
        "how": f"[模擬] 如何實現 {concept}",
        "how_much": f"[模擬] {concept} 需要多少資源",
    }


def _simulate_reverse(concept: str) -> dict:
    """模擬逆向思考輸出"""
    return {
        "reverse_question": f"[模擬] 如何讓 {concept} 失敗？",
        "failure_methods": [f"[模擬] 失敗方法 {i}" for i in range(1, 6)],
        "solutions": [f"[模擬] 反轉解法 {i}" for i in range(1, 6)],
    }


def _simulate_mind_map(concept: str) -> dict:
    """模擬心智圖輸出"""
    return {
        "center": concept,
        "branches": [
            {"name": f"分支 {i}", "sub_branches": [f"子分支 {i}.{j}" for j in range(1, 4)]}
            for i in range(1, 5)
        ],
    }


def _simulate_brainstorm(concept: str) -> dict:
    """模擬腦力激盪輸出"""
    return {
        "ideas": [f"[模擬] {concept} 的瘋狂點子 {i}" for i in range(1, 11)],
    }


def _simulate_random_input(concept: str, random_word: str) -> dict:
    """模擬隨機輸入輸出"""
    return {
        "random_word": random_word,
        "sparks": [f"[模擬] {concept} + {random_word} 的組合 {i}" for i in range(1, 6)],
        "reasoning": f"[模擬] 將 {random_word} 的特性與 {concept} 結合",
    }


@mcp.tool()
async def select_method(
    creativity_level: int = 1,
    prefer_fast: bool = True,
    is_stuck: bool = False,
    purpose: str | None = None,
) -> dict:
    """
    根據情況選擇合適的創意方法

    Args:
        creativity_level: 創意層級 (1/2/3)
        prefer_fast: 是否偏好快速方法
        is_stuck: 是否卡關中
        purpose: 目的 (廣泛探索/結構化分析/強制創新/系統性組合/多元觀點/問題反轉/完整流程)

    Returns:
        推薦的方法和配置
    """
    level = CreativityLevel(creativity_level)
    method = select_method_for_task(
        creativity_level=level,
        prefer_fast=prefer_fast,
        is_stuck=is_stuck,
        purpose=purpose,
    )

    config = METHOD_CONFIGS.get(method)

    return {
        "recommended_method": method.value,
        "description": config.description if config else "",
        "category": config.category.value if config else "",
        "thinking_speed": config.thinking_speed if config else "fast",
        "agent_strategy": config.agent_strategy if config else "",
        "selection_reason": {
            "creativity_level": level.name,
            "prefer_fast": prefer_fast,
            "is_stuck": is_stuck,
            "purpose": purpose,
        },
    }


# === 新增：深度思考工具 ===


@mcp.tool()
async def deep_think(
    topic: str,
    depth: str = "medium",
    mode: str | None = None,
) -> dict:
    """
    統一思考介面 - 智能選擇思考深度

    Args:
        topic: 思考主題
        depth: 思考深度 - "shallow"（快速）/ "medium"（適中）/ "deep"（深入）
        mode: 強制模式 - "simple"（單次）/ "deep"（多Agent）/ "spark"（碰撞）/ None（自動）

    Returns:
        包含點子、火花、推理過程的完整結果
    """
    engine = _get_thinking_engine()

    if engine is None:
        # Fallback 到傳統模式
        return await generate_ideas(topic=topic, count=5)

    try:
        from cgu.thinking import ThinkingMode as TMode, ThinkingDepth

        # 解析深度
        depth_map = {
            "shallow": ThinkingDepth.SHALLOW,
            "medium": ThinkingDepth.MEDIUM,
            "deep": ThinkingDepth.DEEP,
        }

        # 解析模式
        mode_map = {
            "simple": TMode.SIMPLE,
            "deep": TMode.DEEP,
            "spark": TMode.SPARK,
            "hybrid": TMode.HYBRID,
        }

        result = await engine.think(
            topic=topic,
            mode=mode_map.get(mode) if mode else None,
            depth=depth_map.get(depth, ThinkingDepth.MEDIUM),
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"深度思考失敗: {e}")
        return {
            "error": str(e),
            "fallback": await generate_ideas(topic=topic, count=5),
        }


@mcp.tool()
async def multi_agent_brainstorm(
    topic: str,
    agents: int = 3,
    thinking_steps: int = 3,
    collision_count: int = 5,
) -> dict:
    """
    多 Agent 並發腦力激盪

    多個獨立 Agent（Explorer、Critic、Wildcard）並發思考同一主題，
    各自維護獨立 Context 避免污染，最後碰撞產生火花。

    Args:
        topic: 思考主題
        agents: Agent 數量（1-5）
        thinking_steps: 每個 Agent 的思考步數
        collision_count: 概念碰撞次數

    Returns:
        包含各 Agent 貢獻、火花、最佳想法的結果
    """
    engine = _get_thinking_engine()

    if engine is None:
        return {
            "error": "ThinkingEngine 未初始化",
            "hint": "請確認 cgu.thinking 模組可用",
        }

    try:
        from cgu.thinking import ThinkingMode

        result = await engine.think(
            topic=topic,
            mode=ThinkingMode.DEEP,
            agent_count=min(max(agents, 1), 5),  # 限制 1-5
            thinking_steps=thinking_steps,
            collision_count=collision_count,
        )

        return {
            "topic": topic,
            "mode": "multi_agent",
            "agent_contributions": result.agent_contributions,
            "all_ideas": result.ideas,
            "sparks": result.sparks,
            "best_ideas": result.best_ideas,
            "best_spark": result.best_spark,
            "stats": {
                "total_time_ms": result.total_time_ms,
                "idea_count": len(result.ideas),
                "spark_count": len(result.sparks),
            },
        }

    except Exception as e:
        logger.error(f"Multi-Agent 腦力激盪失敗: {e}")
        return {"error": str(e)}


@mcp.tool()
async def spark_collision_deep(
    concept_a: str,
    concept_b: str,
    collision_count: int = 5,
) -> dict:
    """
    深度概念碰撞 - 使用 Multi-Agent 產生意外火花

    不同於簡單的 spark_collision，此工具使用多個 Agent
    從不同角度探索兩個概念的連結可能性。

    Args:
        concept_a: 第一個概念
        concept_b: 第二個概念
        collision_count: 碰撞次數

    Returns:
        包含多層次火花和驚喜度評分的結果
    """
    engine = _get_thinking_engine()

    if engine is None:
        return await spark_collision(concept_a, concept_b)

    try:
        from cgu.thinking import ThinkingMode

        topic = f"{concept_a} × {concept_b}"

        result = await engine.think(
            topic=topic,
            mode=ThinkingMode.SPARK,
            collision_count=collision_count,
        )

        return {
            "concept_a": concept_a,
            "concept_b": concept_b,
            "collision_count": collision_count,
            "sparks": result.sparks,
            "best_spark": result.best_spark,
            "ideas": result.ideas,
            "reasoning": result.reasoning_chains,
        }

    except Exception as e:
        logger.error(f"深度碰撞失敗: {e}")
        return await spark_collision(concept_a, concept_b)


@mcp.tool()
async def list_methods() -> dict:
    """
    列出所有可用的創意方法

    Returns:
        所有方法的清單和說明
    """
    methods_by_category: dict[str, list[dict]] = {}

    for method, config in METHOD_CONFIGS.items():
        category = config.category.value
        if category not in methods_by_category:
            methods_by_category[category] = []

        methods_by_category[category].append({
            "name": method.value,
            "description": config.description,
            "thinking_speed": config.thinking_speed,
            "suitable_levels": config.suitable_levels,
        })

    return {
        "total_methods": len(METHOD_CONFIGS),
        "categories": list(methods_by_category.keys()),
        "methods_by_category": methods_by_category,
    }


# === Spark-Soup: Context Stuffing for Creativity ===


@mcp.tool()
async def spark_soup_generate(
    topic: str,
    fragment_count: int = 20,
    topic_repetition: int = 5,
    auto_search: bool = False,
    custom_fragments: list[str] | None = None,
    trigger_categories: list[str] | None = None,
    randomness: float = 0.5,
) -> dict:
    """
    組裝「創意湯」- 用碎片化資訊填充 context，激發意外連結

    模擬人類接收新聞/書籍/體驗後產生創意的過程。

    Args:
        topic: 主題（會在 soup 中重複多次避免遺忘）
        fragment_count: 碎片數量（預設 20）
        topic_repetition: 主題重複次數（預設 5，避免被 context 壓縮遺忘）
        auto_search: 是否自動搜尋外部資訊（需要網路）
        custom_fragments: 使用者自訂碎片列表
        trigger_categories: 觸發詞類別
            可選: ["combination", "inversion", "scale", "time", "perspective", "emotion"]
        randomness: 隨機性 0-1（越高碎片越隨機）

    Returns:
        包含創意湯、碎片資訊、多樣性評分的結果
    """
    try:
        from cgu.soup import spark_soup

        result = await spark_soup(
            topic=topic,
            fragment_count=fragment_count,
            topic_repetition=topic_repetition,
            auto_search=auto_search,
            custom_fragments=custom_fragments,
            trigger_categories=trigger_categories,
            randomness=randomness,
        )

        return {
            "success": True,
            "soup": result.soup,
            "topic": result.topic,
            "fragments_count": len(result.fragments_used),
            "diversity_score": result.diversity_score,
            "trigger_words_used": result.trigger_words_used,
            "sources": list(set(f.source.value for f in result.fragments_used)),
            "usage_hint": "請將 soup 內容傳給 LLM，讓它從碎片中尋找意外連結來產生創意想法",
        }

    except Exception as e:
        logger.error(f"Spark Soup 失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "hint": "請確認 cgu.soup 模組可用",
        }


@mcp.tool()
async def spark_soup_quick(
    topic: str,
    creativity_boost: float = 0.7,
) -> dict:
    """
    快速創意湯 - 一鍵產生創意湯並直接生成想法

    結合 spark_soup + generate_ideas，適合快速發想。

    Args:
        topic: 主題
        creativity_boost: 創意增強程度 0-1（影響隨機性和碎片多樣性）

    Returns:
        創意湯和基於湯底產生的想法
    """
    try:
        from cgu.soup import spark_soup

        # 生成創意湯
        soup_result = await spark_soup(
            topic=topic,
            fragment_count=15,
            topic_repetition=3,
            auto_search=False,
            randomness=creativity_boost,
            trigger_categories=["combination", "perspective"],
        )

        # 使用 LLM 基於創意湯生成想法
        client = _get_llm_client()
        ideas = []

        if client is not None:
            try:
                from cgu.llm import IdeasOutput, SYSTEM_PROMPT_CREATIVITY

                prompt = f"""請基於以下「創意湯」產生 5 個創意想法。

{soup_result.soup}

請從碎片中尋找意外的連結，產生新穎的想法。"""

                result = client.generate_structured(
                    prompt=prompt,
                    response_model=IdeasOutput,
                    system_prompt=SYSTEM_PROMPT_CREATIVITY,
                )
                ideas = [
                    {"id": i+1, "content": idea, "source": "spark_soup"}
                    for i, idea in enumerate(result.ideas[:5])
                ]
            except Exception as e:
                logger.warning(f"LLM 生成失敗: {e}")

        # Fallback
        if not ideas:
            ideas = [
                {"id": i+1, "content": f"[請基於創意湯思考] {topic} 的想法 {i+1}", "source": "framework"}
                for i in range(5)
            ]

        return {
            "success": True,
            "topic": topic,
            "ideas": ideas,
            "soup_preview": soup_result.soup[:500] + "..." if len(soup_result.soup) > 500 else soup_result.soup,
            "diversity_score": soup_result.diversity_score,
            "fragments_count": len(soup_result.fragments_used),
        }

    except Exception as e:
        logger.error(f"Quick Spark Soup 失敗: {e}")
        return await generate_ideas(topic=topic, count=5)


@mcp.tool()
async def collect_creativity_fragments(
    topic: str,
    count: int = 10,
    include_quotes: bool = True,
    include_random_concepts: bool = True,
    include_search: bool = False,
    randomness: float = 0.5,
) -> dict:
    """
    收集創意碎片 - 從多個來源收集碎片化資訊

    可用於自訂創意湯的組裝，或單獨使用碎片進行聯想。

    Args:
        topic: 相關主題（用於引導搜尋）
        count: 收集數量
        include_quotes: 是否包含名言金句
        include_random_concepts: 是否包含隨機概念
        include_search: 是否進行網路搜尋（需要網路）
        randomness: 隨機性 0-1

    Returns:
        收集到的碎片列表
    """
    try:
        from cgu.soup import collect_fragments

        sources = []
        if include_quotes:
            sources.append("quotes")
        if include_random_concepts:
            sources.append("random")
        if include_search:
            sources.append("duckduckgo")

        if not sources:
            sources = ["quotes", "random"]

        fragments = await collect_fragments(
            topic=topic,
            sources=sources,
            count_per_source=max(3, count // len(sources)),
            randomness=randomness,
        )

        return {
            "success": True,
            "topic": topic,
            "fragments": [
                {
                    "content": f.content,
                    "source": f.source.value,
                    "relevance": f.relevance,
                }
                for f in fragments[:count]
            ],
            "total": len(fragments),
        }

    except Exception as e:
        logger.error(f"收集碎片失敗: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
async def get_trigger_words(
    categories: list[str] | None = None,
    count: int = 10,
) -> dict:
    """
    取得創意觸發詞 - 用於激發創意的提問

    Args:
        categories: 類別列表
            可選: ["combination", "inversion", "scale", "time", "perspective", "emotion"]
        count: 數量

    Returns:
        觸發詞列表
    """
    try:
        from cgu.soup import TRIGGER_WORDS
        import random

        requested_cats = categories or list(TRIGGER_WORDS.keys())

        all_triggers = []
        triggers_by_category = {}

        for cat in requested_cats:
            if cat in TRIGGER_WORDS:
                triggers = TRIGGER_WORDS[cat]
                triggers_by_category[cat] = triggers
                all_triggers.extend(triggers)

        # 隨機選擇
        selected = random.sample(all_triggers, min(count, len(all_triggers)))

        return {
            "success": True,
            "selected": selected,
            "by_category": triggers_by_category,
            "available_categories": list(TRIGGER_WORDS.keys()),
        }

    except Exception as e:
        logger.error(f"取得觸發詞失敗: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# === MCP Resources ===


@mcp.resource("cgu://creativity-levels")
async def get_creativity_levels() -> str:
    """取得創意層級說明"""
    return """
# CGU Creativity Levels

## Level 1: Combinational (組合創意)
- Association Range: 0.7 - 1.0
- Description: 已知元素的新組合
- Example: 將現有功能重新組合

## Level 2: Exploratory (探索創意)
- Association Range: 0.3 - 0.7
- Description: 在既有規則內探索邊界
- Example: 延伸現有概念到新領域

## Level 3: Transformational (變革創意)
- Association Range: 0.0 - 0.3
- Description: 打破規則，創造新範式
- Example: 顛覆性的全新概念
"""


@mcp.resource("cgu://thinking-modes")
async def get_thinking_modes() -> str:
    """取得思考模式說明"""
    return """
# CGU Thinking Modes (Fast/Slow)

## System 1 - Fast Thinking ⚡
- REACT: 基本反應，輸入 → 輸出
- ASSOCIATE: 快速聯想，概念 → 相關概念
- PATTERN_MATCH: 模式匹配，識別已知模式

## System 2 - Slow Thinking 🐢
- ANALYZE: 分析，拆解問題結構
- SYNTHESIZE: 綜合，組合多個概念
- EVALUATE: 評估，判斷品質與可行性

## Creative Thinking 🎨
- DIVERGE: 發散，產生多種可能
- CONVERGE: 收斂，選擇最佳方案
- TRANSFORM: 變革，打破規則創新

## Fast/Slow Patterns
- sprint: 5 fast + 1 slow (快速嘗試 + 評估)
- explore: 3 fast + 1 slow (快速聯想 + 分析)
- refine: 2 fast + 2 slow (生成 + 精煉)
- deep: 1 fast + 3 slow (直覺 + 深思)
"""


# === Entry Point ===


def main():
    """啟動 MCP Server"""
    mcp.run()


if __name__ == "__main__":
    main()
