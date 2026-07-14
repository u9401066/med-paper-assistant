"""
CGU Phase 2: Agent-to-Agent Brainstorming Protocol

New MCP tools for structured multi-agent brainstorming in OpenClaw.
Designed to be added to server.py alongside existing tools.

These tools output structured discussion frameworks that real OpenClaw agents
(not internal LangGraph roles) can follow step-by-step in group chat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ─── Enums ───────────────────────────────────────────────────

class BrainstormPhase(str, Enum):
    """Phases of a brainstorm session."""
    DIVERGE = "diverge"      # 發散：盡量多想
    COLLIDE = "collide"      # 碰撞：交叉比較
    CONVERGE = "converge"    # 收斂：選出最佳
    EVALUATE = "evaluate"    # 評估：打分排序


class BrainstormMethod(str, Enum):
    """Structured creativity methods for brainstorming."""
    FREE = "free"                  # 自由聯想
    SIX_HATS = "six_hats"         # 六頂思考帽
    SCAMPER = "scamper"            # SCAMPER 七維度
    REVERSE = "reverse"            # 反向思考
    ANALOGY = "analogy"            # 類比遷移
    CONSTRAINT_REMOVAL = "constraint_removal"  # 去除限制
    WORST_IDEA = "worst_idea"      # 最爛點子法


# ─── Data Structures ─────────────────────────────────────────

@dataclass
class PhasePrompt:
    """A single phase in the brainstorm protocol."""
    phase: str
    title: str
    duration_hint: str
    instructions: str
    agent_a_prompt: str
    agent_b_prompt: str
    convergence_prompt: str = ""


@dataclass
class BrainstormProtocol:
    """Complete brainstorm protocol output."""
    topic: str
    method: str
    method_description: str
    participant_a: str
    participant_b: str
    phases: list[PhasePrompt]
    total_phases: int
    markdown_summary: str


@dataclass
class IdeaScore:
    """Evaluation score for a single idea."""
    idea: str
    feasibility: float      # 0-10: 技術可行性
    novelty: float           # 0-10: 新穎度
    impact: float            # 0-10: 潛在影響力
    effort: float            # 0-10: 實作成本（10=最輕鬆）
    weighted_score: float    # 加權總分
    rationale: str           # 評分理由


# ─── Protocol Generators ─────────────────────────────────────

def _generate_free_protocol(topic: str, a: str, b: str) -> list[PhasePrompt]:
    """Free-form brainstorm: diverge → share → collide → converge."""
    return [
        PhasePrompt(
            phase="diverge",
            title="🌊 Phase 1: 自由發散",
            duration_hint="5 min each",
            instructions="各自獨立思考，盡量多產生點子，不批判。",
            agent_a_prompt=f"{a}：請針對「{topic}」快速列出 5-8 個點子。不用完美，數量優先。想到什麼就寫什麼。",
            agent_b_prompt=f"{b}：請從你的專業角度，針對「{topic}」列出 5-8 個不同方向的點子。越多元越好。",
        ),
        PhasePrompt(
            phase="collide",
            title="💥 Phase 2: 概念碰撞",
            duration_hint="5 min",
            instructions="交換點子，找出意外的連結。",
            agent_a_prompt=f"{a}：看 {b} 的點子，找 2-3 個可以跟你的點子結合的。說明怎麼結合、為什麼有趣。",
            agent_b_prompt=f"{b}：看 {a} 的點子，找 2-3 個跟你的觀點互補或衝突的。衝突尤其有價值——說明為什麼。",
        ),
        PhasePrompt(
            phase="converge",
            title="🎯 Phase 3: 收斂聚焦",
            duration_hint="3 min",
            instructions="從碰撞中選出最有潛力的 top 3。",
            agent_a_prompt=f"{a}：綜合前兩輪，推薦你認為最有價值的 3 個方向，簡述理由。",
            agent_b_prompt=f"{b}：同樣推薦你的 top 3，標注跟 {a} 重疊或互補的部分。",
            convergence_prompt=f"兩位的 top 3 有重疊嗎？重疊的就是共識方向。沒重疊的需要再討論。",
        ),
    ]


def _generate_six_hats_protocol(topic: str, a: str, b: str) -> list[PhasePrompt]:
    """Six Thinking Hats: assign different hats to each agent."""
    return [
        PhasePrompt(
            phase="diverge",
            title="🎩 Phase 1: 分帽思考",
            duration_hint="5 min each",
            instructions="每人戴兩頂帽子，從該角度思考。",
            agent_a_prompt=f"""{a}：你戴 ⬜ 白帽（事實/數據）和 🟢 綠帽（創意/可能性）。
針對「{topic}」：
- 白帽：目前有什麼已知的事實和數據？缺什麼資料？
- 綠帽：有什麼創新的做法？不受限制的話會怎麼做？""",
            agent_b_prompt=f"""{b}：你戴 🔴 紅帽（直覺/感受）和 ⬛ 黑帽（風險/問題）。
針對「{topic}」：
- 紅帽：你的第一直覺是什麼？哪裡讓你興奮或不安？
- 黑帽：最大的風險是什麼？哪裡可能出錯？""",
        ),
        PhasePrompt(
            phase="collide",
            title="💥 Phase 2: 帽子碰撞",
            duration_hint="5 min",
            instructions="交換帽子觀點，找衝突與互補。",
            agent_a_prompt=f"""{a}：用 🟡 黃帽（樂觀/價值）重新審視 {b} 提出的風險。
哪些風險其實有解法？哪些「問題」反而是機會？""",
            agent_b_prompt=f"""{b}：用 🔵 藍帽（統整/流程）綜合所有觀點。
目前的共識是什麼？還有什麼分歧需要解決？""",
        ),
        PhasePrompt(
            phase="converge",
            title="🎯 Phase 3: 藍帽總結",
            duration_hint="3 min",
            instructions="統整所有帽子的觀點，形成行動方案。",
            agent_a_prompt=f"{a}：根據所有角度的分析，提出最終建議方案。",
            agent_b_prompt=f"{b}：補充 {a} 遺漏的考量，確認方案完整性。",
            convergence_prompt="整合為一份包含：方案摘要、關鍵數據、主要風險、創意元素、行動步驟 的結論。",
        ),
    ]


def _generate_scamper_protocol(topic: str, a: str, b: str) -> list[PhasePrompt]:
    """SCAMPER: each agent tackles different dimensions."""
    return [
        PhasePrompt(
            phase="diverge",
            title="🔧 Phase 1: SCAMPER 分工",
            duration_hint="5 min each",
            instructions="每人負責 SCAMPER 的不同維度。",
            agent_a_prompt=f"""{a}：針對「{topic}」思考這四個維度：
- **S** (Substitute) — 什麼可以替換？
- **C** (Combine) — 什麼可以合併？
- **A** (Adapt) — 可以從哪裡借鏡？
- **M** (Modify/Magnify) — 放大或縮小什麼？
每個維度至少 1-2 個具體想法。""",
            agent_b_prompt=f"""{b}：針對「{topic}」思考這三個維度：
- **P** (Put to other uses) — 還能用在哪？
- **E** (Eliminate) — 可以去掉什麼？
- **R** (Reverse/Rearrange) — 顛倒或重排會怎樣？
每個維度至少 1-2 個具體想法。""",
        ),
        PhasePrompt(
            phase="collide",
            title="💥 Phase 2: 維度碰撞",
            duration_hint="5 min",
            instructions="看對方的 SCAMPER 結果，找出可以 cross-pollinate 的組合。",
            agent_a_prompt=f"{a}：從 {b} 的 P/E/R 裡找靈感，跟你的 S/C/A/M 結合。至少提出 2 個 cross 組合。",
            agent_b_prompt=f"{b}：從 {a} 的 S/C/A/M 裡找靈感，跟你的 P/E/R 結合。至少提出 2 個 cross 組合。",
        ),
        PhasePrompt(
            phase="converge",
            title="🎯 Phase 3: SCAMPER 精選",
            duration_hint="3 min",
            instructions="從 7 個維度 + cross 組合中，選出最有潛力的 3-5 個。",
            agent_a_prompt=f"{a}：推薦 top 3，標注哪個 SCAMPER 維度最有突破性。",
            agent_b_prompt=f"{b}：推薦 top 3，特別關注哪些在臨床上最可行。",
            convergence_prompt="合併 top 3，如果有重疊就是強共識。最終產出：每個選中的 idea 標注它用了哪些 SCAMPER 維度。",
        ),
    ]


def _generate_reverse_protocol(topic: str, a: str, b: str) -> list[PhasePrompt]:
    """Reverse brainstorming: how to make it WORSE, then flip."""
    return [
        PhasePrompt(
            phase="diverge",
            title="🔄 Phase 1: 反向思考 — 如何讓它更糟？",
            duration_hint="5 min each",
            instructions="故意想：怎樣可以讓這件事做得最差？",
            agent_a_prompt=f"""{a}：如果目標是讓「{topic}」**徹底失敗**，你會怎麼做？
列出 5 個保證搞砸的方法。越具體越好、越荒謬越好。""",
            agent_b_prompt=f"""{b}：同樣的問題 — 如何讓「{topic}」**成為災難**？
從你的專業角度，列出 5 個最糟糕的做法。""",
        ),
        PhasePrompt(
            phase="collide",
            title="💡 Phase 2: 翻轉 — 反面就是答案",
            duration_hint="5 min",
            instructions="把「最糟做法」翻轉成「最佳做法」。",
            agent_a_prompt=f"{a}：把 {b} 列的 5 個最糟做法，每個都翻轉成正面的策略。翻轉後哪個最有洞察力？",
            agent_b_prompt=f"{b}：把 {a} 列的 5 個最糟做法翻轉。有沒有翻轉後反而發現原本沒想到的好方向？",
        ),
        PhasePrompt(
            phase="converge",
            title="🎯 Phase 3: 精煉",
            duration_hint="3 min",
            instructions="從翻轉中選出真正有價值的 insight。",
            agent_a_prompt=f"{a}：Top 3 翻轉 insight + 為什麼它們比直接正面思考更有創意。",
            agent_b_prompt=f"{b}：Top 3 + 實際可行性評估。",
            convergence_prompt="最終產出要標注：這個 insight 是從哪個「最糟做法」翻轉來的。",
        ),
    ]


# ─── Method Router ────────────────────────────────────────────

PROTOCOL_GENERATORS = {
    BrainstormMethod.FREE: _generate_free_protocol,
    BrainstormMethod.SIX_HATS: _generate_six_hats_protocol,
    BrainstormMethod.SCAMPER: _generate_scamper_protocol,
    BrainstormMethod.REVERSE: _generate_reverse_protocol,
}


def generate_brainstorm_protocol(
    topic: str,
    method: str = "free",
    participant_a: str = "Agent A",
    participant_b: str = "Agent B",
) -> dict:
    """
    Generate a structured brainstorm protocol for two agents.
    
    Returns a complete discussion script with phase-by-phase prompts
    that real OpenClaw agents can follow in group chat.
    """
    try:
        bm = BrainstormMethod(method)
    except ValueError:
        available = [m.value for m in BrainstormMethod]
        return {
            "error": f"Unknown method: {method}",
            "available_methods": available,
            "hint": "Use 'free' for open brainstorming, 'six_hats' for structured analysis, 'scamper' for innovation, 'reverse' for contrarian thinking.",
        }
    
    generator = PROTOCOL_GENERATORS.get(bm)
    if not generator:
        return {
            "error": f"Protocol not yet implemented for: {method}",
            "available": [m.value for m, g in PROTOCOL_GENERATORS.items()],
        }
    
    phases = generator(topic, participant_a, participant_b)
    
    # Build markdown summary
    md_lines = [
        f"## 🧠 Brainstorm Protocol: {topic}",
        f"**方法**: {bm.value} | **參與者**: {participant_a} & {participant_b}",
        "",
    ]
    for i, p in enumerate(phases, 1):
        md_lines.append(f"### {p.title}")
        md_lines.append(f"*⏱ {p.duration_hint}* — {p.instructions}")
        md_lines.append(f"- **{participant_a}**: {p.agent_a_prompt[:80]}...")
        md_lines.append(f"- **{participant_b}**: {p.agent_b_prompt[:80]}...")
        if p.convergence_prompt:
            md_lines.append(f"- **收斂**: {p.convergence_prompt[:80]}...")
        md_lines.append("")
    
    protocol = BrainstormProtocol(
        topic=topic,
        method=bm.value,
        method_description=_method_descriptions()[bm],
        participant_a=participant_a,
        participant_b=participant_b,
        phases=[asdict(p) for p in phases],
        total_phases=len(phases),
        markdown_summary="\n".join(md_lines),
    )
    
    return asdict(protocol)


def evaluate_ideas(
    ideas: list[str],
    criteria_weights: Optional[dict] = None,
    context: str = "",
) -> dict:
    """
    Evaluate and rank a list of ideas.
    
    Returns structured scores on feasibility, novelty, impact, and effort,
    plus a weighted ranking. The calling agent fills in the actual assessment;
    this tool provides the evaluation framework and scoring rubric.
    """
    weights = criteria_weights or {
        "feasibility": 0.30,
        "novelty": 0.25,
        "impact": 0.30,
        "effort": 0.15,
    }
    
    # Normalize weights
    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}
    
    rubric = {
        "feasibility": {
            "description": "技術可行性 — 以現有資源和知識，能做到嗎？",
            "scale": "0=不可能, 3=需要突破, 5=有挑戰但可行, 8=相當可行, 10=已有先例",
        },
        "novelty": {
            "description": "新穎度 — 跟現有做法比，有多不同？",
            "scale": "0=已有人做, 3=小改進, 5=新角度, 8=創新組合, 10=全新概念",
        },
        "impact": {
            "description": "潛在影響力 — 如果成功，改變有多大？",
            "scale": "0=無影響, 3=小改善, 5=明顯改善, 8=重大突破, 10=改變遊戲規則",
        },
        "effort": {
            "description": "實作成本（反向：10=最輕鬆）",
            "scale": "0=需要數年/大團隊, 3=需要數月, 5=數週, 8=數天, 10=幾小時",
        },
    }
    
    evaluation_template = []
    for i, idea in enumerate(ideas, 1):
        evaluation_template.append({
            "rank": i,
            "idea": idea,
            "scores": {k: "?" for k in weights},
            "weighted_score": "?",
            "rationale": f"[請評估：{idea[:50]}...]",
        })
    
    return {
        "ideas_count": len(ideas),
        "context": context or "(no context provided)",
        "criteria_weights": weights,
        "rubric": rubric,
        "evaluation_template": evaluation_template,
        "agent_instruction": (
            "請根據 rubric 為每個 idea 打分（0-10），"
            "填入 scores 欄位，計算 weighted_score = Σ(score × weight)，"
            "然後按 weighted_score 排序。附上 rationale 說明理由。"
        ),
        "output_format": "填完後請依 weighted_score 由高到低排列。",
    }


# ─── Helpers ─────────────────────────────────────────────────

def _method_descriptions() -> dict:
    return {
        BrainstormMethod.FREE: "自由聯想 — 不設框架，各自發散再碰撞。適合開放性探索。",
        BrainstormMethod.SIX_HATS: "六頂思考帽 — 從事實、直覺、風險、價值、創意、統整六角度分析。適合需要全面評估的決策。",
        BrainstormMethod.SCAMPER: "SCAMPER — 替代/合併/借鏡/放大/他用/去除/顛倒 七維度創新。適合改善現有方案。",
        BrainstormMethod.REVERSE: "反向思考 — 先想怎麼搞砸，再翻轉成好方案。適合找盲點、打破慣性思維。",
        BrainstormMethod.ANALOGY: "類比遷移 — 從其他領域借鏡。（即將實作）",
        BrainstormMethod.CONSTRAINT_REMOVAL: "去除限制 — 如果沒有 X 限制會怎樣？（即將實作）",
        BrainstormMethod.WORST_IDEA: "最爛點子法 — 從最糟點子中找靈感。（即將實作）",
    }
