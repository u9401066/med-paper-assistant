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
from cgu.brainstorm_protocol import (
    generate_brainstorm_protocol,
    evaluate_ideas as evaluate_ideas_framework,
)
from cgu.tools import CreativityToolbox

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM 模式
# 預設 true - 啟用 Ollama LLM（確保 Ollama 服務已啟動）
USE_LLM = os.getenv("CGU_USE_LLM", "true").lower() == "true"
# 思考引擎：
#   ollama      — 本地推理（需要 Ollama 服務）
#   copilot     — (deprecated, 等同 passthrough)
#   passthrough — 不用 LLM，返回完整方法論框架讓呼叫者（OpenClaw agent）自行思考填充
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
    # passthrough / copilot 模式：不使用本地 LLM，返回框架讓呼叫者思考
    if LLM_PROVIDER in ("copilot", "passthrough"):
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
    """檢查是否為 Passthrough 模式（copilot 為舊名稱）"""
    return LLM_PROVIDER in ("copilot", "passthrough")


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
    
    # Fallback 到 passthrough 框架
    if not ideas:
        if _is_copilot_mode():
            # Passthrough 模式：返回結構化思考框架，讓呼叫的 agent 填充
            constraints_text = "、".join(constraints) if constraints else "無"
            ideas = [
                {
                    "id": i + 1,
                    "prompt": f"從「{topic}」的第 {i + 1} 個角度思考（{['功能面', '使用者面', '技術面', '商業面', '社會面', '跨領域', '極端情境'][i % 7]}）",
                    "thinking_angle": ['功能面', '使用者面', '技術面', '商業面', '社會面', '跨領域', '極端情境'][i % 7],
                    "association_score": 0.5,
                }
                for i in range(count)
            ]
            method_used = "passthrough_framework"
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
    """Passthrough SCAMPER 框架 — 提供完整 7 維度引導"""
    return {
        "S_substitute": {
            "prompt": f"替代：{concept} 的哪個部分可以被替換？用什麼替代？",
            "thinking_angles": ["材料替代", "人員替代", "流程替代", "技術替代"],
        },
        "C_combine": {
            "prompt": f"結合：{concept} 可以跟什麼結合產生新價值？",
            "thinking_angles": ["跨領域結合", "功能合併", "與互補概念結合"],
        },
        "A_adapt": {
            "prompt": f"調適：其他領域的什麼做法可以改造後用在 {concept}？",
            "thinking_angles": ["借鑑自然界", "借鑑其他產業", "借鑑歷史案例"],
        },
        "M_modify": {
            "prompt": f"修改：放大或縮小 {concept} 的某個面向會怎樣？",
            "thinking_angles": ["放大規模", "縮小範圍", "改變形狀/結構", "改變頻率/速度"],
        },
        "P_put_to_other_uses": {
            "prompt": f"他用：{concept} 或其副產品還能用在哪裡？",
            "thinking_angles": ["換一個使用者", "換一個場景", "換一個目的"],
        },
        "E_eliminate": {
            "prompt": f"消除：{concept} 的哪個部分可以移除？簡化後會如何？",
            "thinking_angles": ["移除步驟", "移除功能", "移除限制", "移除假設"],
        },
        "R_reverse": {
            "prompt": f"重排：反轉 {concept} 的順序或角色會怎樣？",
            "thinking_angles": ["顛倒順序", "互換角色", "從結果反推", "逆向工程"],
        },
        "_meta": {
            "method": "SCAMPER",
            "instruction": "依序思考每個維度，每個維度至少產生 1 個具體點子",
        },
    }


def _simulate_six_hats(concept: str) -> dict:
    """Passthrough 六頂帽框架 — 提供 6 個角度的具體引導"""
    return {
        "white_facts": {
            "hat": "⚪ 白帽：客觀事實",
            "prompt": f"關於 {concept}，我們已知的事實和數據是什麼？缺少什麼資訊？",
            "focus": "數據、事實、資訊缺口——不帶判斷",
        },
        "red_feelings": {
            "hat": "🔴 紅帽：直覺感受",
            "prompt": f"對 {concept} 的第一直覺是什麼？喜歡/不喜歡的感覺從何而來？",
            "focus": "情緒、直覺、gut feeling——不需要理由",
        },
        "black_risks": {
            "hat": "⚫ 黑帽：批判風險",
            "prompt": f"{concept} 最可能失敗的原因是什麼？最壞的情況？",
            "focus": "風險、障礙、缺陷、潛在問題",
        },
        "yellow_benefits": {
            "hat": "🟡 黃帽：樂觀價值",
            "prompt": f"{concept} 最大的價值和好處是什麼？最佳情況？",
            "focus": "優點、機會、正面影響",
        },
        "green_ideas": {
            "hat": "🟢 綠帽：創意替代",
            "prompt": f"有沒有完全不同的方式來實現 {concept}？瘋狂的點子？",
            "focus": "新點子、替代方案、創意——越大膽越好",
        },
        "blue_summary": {
            "hat": "🔵 藍帽：全局統整",
            "prompt": f"綜合以上五個角度，對 {concept} 的結論和下一步行動是什麼？",
            "focus": "整合、流程管理、行動方案",
        },
        "_meta": {
            "method": "Six Thinking Hats (de Bono)",
            "instruction": "按順序戴每頂帽子，每頂帽子只用該角度思考，不混合",
        },
    }


def _simulate_mandala(concept: str) -> dict:
    """Passthrough 九宮格框架"""
    return {
        "center": concept,
        "extensions": {
            "instruction": f"以「{concept}」為中心，向 8 個方向擴展相關概念",
            "positions": [
                {"position": "上", "prompt": "核心目標/願景"},
                {"position": "右上", "prompt": "相關技術/工具"},
                {"position": "右", "prompt": "主要受眾/使用者"},
                {"position": "右下", "prompt": "競爭對手/替代方案"},
                {"position": "下", "prompt": "資源需求/成本"},
                {"position": "左下", "prompt": "風險/障礙"},
                {"position": "左", "prompt": "潛在合作者/盟友"},
                {"position": "左上", "prompt": "靈感來源/參考案例"},
            ],
        },
        "_meta": {
            "method": "Mandala 九宮格",
            "instruction": "每個格子填入 1-3 個具體概念，然後觀察格子之間的關聯",
        },
    }


def _simulate_5w2h(concept: str) -> dict:
    """Passthrough 5W2H 框架"""
    return {
        "what": {"prompt": f"{concept} 具體是什麼？核心定義？", "focus": "清晰定義問題或概念"},
        "why": {"prompt": f"為什麼要做 {concept}？解決什麼痛點？", "focus": "動機、價值、意義"},
        "who": {"prompt": f"誰參與？誰受益？誰受影響？", "focus": "利害關係人分析"},
        "when": {"prompt": f"什麼時候開始？什麼時候是最佳時機？", "focus": "時間框架和里程碑"},
        "where": {"prompt": f"在哪裡進行？適用場景？", "focus": "空間、平台、環境"},
        "how": {"prompt": f"如何實現？關鍵步驟？", "focus": "方法、流程、技術路線"},
        "how_much": {"prompt": f"需要多少資源？投入產出比？", "focus": "成本、時間、人力估算"},
        "_meta": {
            "method": "5W2H",
            "instruction": "逐一回答每個問題，答案越具體越好",
        },
    }


def _simulate_reverse(concept: str) -> dict:
    """Passthrough 逆向思考框架"""
    return {
        "reverse_question": f"如何確保 {concept} 一定會失敗？",
        "failure_prompts": [
            "列出 5 種最有效的破壞方法",
            "哪些假設如果錯了就會全盤崩潰？",
            "最常見的失敗模式是什麼？",
            "忽略什麼會導致最大的傷害？",
            "競爭對手會怎麼打敗這個方案？",
        ],
        "reversal_instruction": "把每個失敗方法反轉 → 變成防禦策略或改進方向",
        "_meta": {
            "method": "Reverse Brainstorming (逆向思考)",
            "instruction": "先盡情想怎麼搞砸，然後逐一反轉成解決方案",
        },
    }


def _simulate_mind_map(concept: str) -> dict:
    """Passthrough 心智圖框架"""
    return {
        "center": concept,
        "branch_prompts": [
            {"name": "核心功能/特性", "sub_prompts": ["最重要的功能？", "必須具備的特性？", "區別於其他方案的特點？"]},
            {"name": "使用者/受眾", "sub_prompts": ["主要使用者是誰？", "次要使用者？", "潛在的意外使用者？"]},
            {"name": "技術/實現", "sub_prompts": ["需要什麼技術？", "現有技術是否足夠？", "技術風險在哪？"]},
            {"name": "挑戰/風險", "sub_prompts": ["最大的障礙？", "最容易被忽略的風險？", "資源瓶頸？"]},
        ],
        "_meta": {
            "method": "Mind Map (心智圖)",
            "instruction": "從中心向外擴展，每個分支再延伸 2-3 個子分支",
        },
    }


def _simulate_brainstorm(concept: str) -> dict:
    """Passthrough 腦力激盪框架"""
    return {
        "warm_up": f"花 30 秒自由聯想：想到 {concept} 你第一個聯想到什麼？",
        "round_1_wild": {
            "instruction": "瘋狂發想：不評判，不過濾，想到什麼寫什麼",
            "target": "至少 10 個點子",
            "prompt": f"如果沒有任何限制，{concept} 可以怎麼做？",
        },
        "round_2_build": {
            "instruction": "接力改良：從 Round 1 挑 3 個最有趣的，各自延伸",
            "prompt": "如果把這個點子推到極致會怎樣？如果結合另一個點子呢？",
        },
        "round_3_ground": {
            "instruction": "落地篩選：評估可行性，挑出 Top 3",
            "criteria": ["技術可行性", "影響力", "獨特性", "實作難度"],
        },
        "_meta": {
            "method": "Brainstorming (腦力激盪)",
            "instruction": "三輪：發散 → 改良 → 收斂。第一輪嚴禁批評！",
        },
    }


def _simulate_random_input(concept: str, random_word: str) -> dict:
    """Passthrough 隨機輸入框架"""
    return {
        "random_word": random_word,
        "collision_prompts": [
            f"{random_word} 有什麼特性？列出 5 個",
            f"這些特性怎麼跟 {concept} 產生連結？",
            f"如果 {concept} 具有 {random_word} 的某個特性，會變成什麼？",
            f"在 {random_word} 的世界裡，{concept} 會如何運作？",
            f"{random_word} 的使用者會怎麼看 {concept}？",
        ],
        "_meta": {
            "method": "Random Input (隨機輸入法)",
            "instruction": "強制連結看似無關的概念，越遠的連結越有創意價值",
        },
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


# === Phase 2: Agent-to-Agent Brainstorming Protocol ===


@mcp.tool()
async def brainstorm_protocol(
    topic: str,
    method: str = "free",
    participant_a: str = "Agent A",
    participant_b: str = "Agent B",
) -> dict:
    """
    產生結構化的雙 Agent 腦力激盪討論框架

    為兩個 OpenClaw agent 產生分階段的討論 protocol（發散→碰撞→收斂），
    每個階段有各自的 prompt。Agent 按步驟執行，在群組裡進行真正的討論。

    Args:
        topic: 要討論的主題
        method: 方法論 (free/six_hats/scamper/reverse)
        participant_a: Agent A 的名字（例如 "星澄"）
        participant_b: Agent B 的名字（例如 "寧寧"）

    Returns:
        完整的 protocol（JSON phases + Markdown 摘要）
    """
    return generate_brainstorm_protocol(topic, method, participant_a, participant_b)


@mcp.tool()
async def evaluate_brainstorm_ideas(
    ideas: list[str],
    context: str = "",
    feasibility_weight: float = 0.30,
    novelty_weight: float = 0.25,
    impact_weight: float = 0.30,
    effort_weight: float = 0.15,
) -> dict:
    """
    評估並排序腦力激盪產生的點子

    提供四維度評估框架（可行性/新穎度/影響力/成本），
    附 rubric 和評分模板，讓呼叫的 Agent 根據框架打分。

    Args:
        ideas: 要評估的點子列表
        context: 評估脈絡（背景資訊）
        feasibility_weight: 可行性權重 (0-1)
        novelty_weight: 新穎度權重 (0-1)
        impact_weight: 影響力權重 (0-1)
        effort_weight: 成本權重 (0-1, 10=最輕鬆)

    Returns:
        評估框架（rubric + template），Agent 填入分數後排序
    """
    weights = {
        "feasibility": feasibility_weight,
        "novelty": novelty_weight,
        "impact": impact_weight,
        "effort": effort_weight,
    }
    return evaluate_ideas_framework(ideas, criteria_weights=weights, context=context)


# === Phase 3: Agent-Driven Creativity Tools (v3) ===
# 將 CreativityToolbox 的工具註冊為 MCP Tools，
# 讓 Agent 可以透過 MCP 協定自主調用。

# 全域 toolbox 實例（session 內共用，保持 logger 狀態）
_toolbox: CreativityToolbox | None = None


def _get_toolbox() -> CreativityToolbox:
    """取得全域 CreativityToolbox 實例"""
    global _toolbox
    if _toolbox is None:
        _toolbox = CreativityToolbox()
    return _toolbox


@mcp.tool()
async def explore_concept(
    concept: str,
    include_cross_domain: bool = True,
) -> dict:
    """
    探索一個概念，找出相關概念、所屬領域、以及跨域的意外發現

    Agent 可以用這個工具搜尋概念空間，發現相關概念和跨域靈感。

    Args:
        concept: 要探索的概念（例如 "AI"、"教育"、"咖啡"）
        include_cross_domain: 是否包含跨領域的意外發現

    Returns:
        dict 包含 query, related（相關概念）, domains（所屬領域）, unexpected（跨域發現）
    """
    toolbox = _get_toolbox()
    return toolbox.explore_concept(concept, include_cross_domain)


@mcp.tool()
async def find_connections(
    concept_a: str,
    concept_b: str,
) -> dict:
    """
    尋找兩個概念之間的連結

    支援直接連結、間接連結、跨域連結、未探索連結。
    新穎度評分：直接連結(0.2) < 間接(0.5) < 跨域(0.8) < 未探索(0.95)。

    Args:
        concept_a: 第一個概念
        concept_b: 第二個概念

    Returns:
        dict 包含 concept_a, concept_b, connection_type, path, explanation, novelty_score
    """
    toolbox = _get_toolbox()
    return toolbox.find_connection(concept_a, concept_b)


@mcp.tool()
async def check_novelty(
    idea: str,
) -> dict:
    """
    檢查想法的新穎度

    將想法與已知想法庫比對，計算新穎度分數，並提供差異化建議。
    新穎度 > 0.6 被視為「新穎」。

    Args:
        idea: 要檢查的想法描述

    Returns:
        dict 包含 idea, is_novel, novelty_score, similar_existing（類似的已存在想法）, suggestions（差異化建議）
    """
    toolbox = _get_toolbox()
    return toolbox.check_novelty(idea)


@mcp.tool()
async def evolve_idea_tool(
    idea: str,
    mutation_type: str = "",
) -> dict:
    """
    對想法進行突變演化

    支援 5 種突變方式：combine（與隨機概念結合）、split（拆分成子想法）、
    reverse（反向思考）、analogize（類比到其他領域）、extreme（極端化）。
    不指定 mutation_type 時隨機選擇。

    Args:
        idea: 要演化的想法
        mutation_type: 突變方式（combine/split/reverse/analogize/extreme，留空隨機選擇）

    Returns:
        dict 包含 original, evolved, mutation_type, reasoning
    """
    toolbox = _get_toolbox()
    mt = mutation_type if mutation_type else None
    return toolbox.evolve_idea(idea, mt)


@mcp.tool()
async def random_concept() -> dict:
    """
    隨機取得一個概念

    用於「隨機探索」，當 Agent 想要跳出舒適圈時使用。

    Returns:
        dict 包含 concept（隨機概念名稱）
    """
    toolbox = _get_toolbox()
    concept = toolbox.get_random_concept()
    return {"concept": concept}


@mcp.tool()
async def suggest_bridges(
    concept_a: str,
    concept_b: str,
) -> dict:
    """
    建議可能的橋接概念，連接兩個看似不相關的概念

    當兩個概念沒有直接關係時，找出可能的中間橋接點。

    Args:
        concept_a: 第一個概念
        concept_b: 第二個概念

    Returns:
        dict 包含 concept_a, concept_b, bridges（橋接概念列表）
    """
    toolbox = _get_toolbox()
    bridges = toolbox.suggest_bridges(concept_a, concept_b)
    return {
        "concept_a": concept_a,
        "concept_b": concept_b,
        "bridges": bridges,
    }


@mcp.tool()
async def creativity_session_start(
    topic: str,
) -> dict:
    """
    開始一個新的創意探索會話

    Agent 可以用這個工具追蹤自己的創意探索過程。
    會話會記錄所有探索動作、想法和進度。

    Args:
        topic: 探索主題

    Returns:
        dict 包含 session_id 和 topic
    """
    toolbox = _get_toolbox()
    session_id = toolbox.start_session(topic)
    return {"session_id": session_id, "topic": topic}


@mcp.tool()
async def creativity_session_record(
    idea: str,
) -> dict:
    """
    記錄並驗證一個想法到當前會話

    自動計算新穎度分數，並追蹤是否為目前最佳想法。

    Args:
        idea: 要記錄的想法

    Returns:
        dict 包含 idea, novelty_score, is_best_so_far
    """
    toolbox = _get_toolbox()
    try:
        result = toolbox.record_idea(idea)
        result["success"] = True
        return result
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def creativity_session_progress() -> dict:
    """
    查看當前創意探索會話的進度摘要

    顯示探索次數、想法數量、最佳想法等。

    Returns:
        dict 包含 session_id, topic, total_explorations, total_ideas, best_idea, best_novelty_score
    """
    toolbox = _get_toolbox()
    return toolbox.get_progress()


# === Entry Point ===


def main():
    """啟動 MCP Server"""
    mcp.run()


if __name__ == "__main__":
    main()
