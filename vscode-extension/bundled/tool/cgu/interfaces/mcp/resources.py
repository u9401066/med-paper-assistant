"""Resources: method notes, operator cards, rubrics and trigger questions (static knowledge)."""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from cgu.application.services.frame import card_view
from cgu.domain.doubt import QUESTION_GATE_CRITERIA
from cgu.domain.operators import OPERATORS
from cgu.interfaces.mcp.deps import Deps

METHODS: dict[str, str] = {
    "scamper": (
        "SCAMPER（Eberle）：對既有做法逐一問 Substitute 替代、Combine 結合、Adapt 調整、"
        "Modify 修改／放大／縮小、Put to other use 另作他用、Eliminate 消除、Reverse 反轉／重排。\n"
        "對 LLM 的適用性：很適合當作「突變算子」，因為每一問都指向一個具體的改寫動作。\n"
        '用法：先用 cgu_frame(action="create") 寫出現有做法，再逐問改寫，並用 '
        'cgu_ideas(action="add", meta={"rewrote": ...}) 記下改了哪個元素。'
    ),
    "six_hats": (
        "六頂思考帽（de Bono）：白（事實）、紅（直覺）、黑（風險）、黃（價值）、綠（創意）、藍（流程）。\n"
        "對 LLM 的適用性：角色提示多半只改變語氣而不是內容，請讓每頂帽子產出「不同的具體論點」，"
        "並以不同 context 或不同模型執行，再比較差異。\n"
        '用法：cgu_diverge(action="fanout", vary=["prompt"]) 取得獨立工單，每張指定一頂帽子。'
    ),
    "triz": (
        "TRIZ 發明原理（Altshuller）：把「改善一項、惡化另一項」的技術矛盾，對應到 40 條發明原理"
        "（例如分割、抽離、局部品質、不對稱、預先反作用、反向、動態化、曲面化、複合材料）。\n"
        "對 LLM 的適用性：作為搜尋算子有用；要求每條原理都產出具體做法，而不是原理名稱。\n"
        '用法：先寫出矛盾（改善什麼、惡化什麼），再依原理逐條提出做法，最後用 cgu_ideas(action="measure") 檢查重複。'
    ),
    "5w2h": (
        "5W2H：What、Why、Who、When、Where、How、How much。用來把含糊的問題補成可行動的描述。\n"
        "對 LLM 的適用性：是澄清工具而不是發散工具；缺哪一項就問使用者，不要替使用者編造。\n"
        '用法：把答案整理進 cgu_frame(action="create") 的 problem、stakeholders、constraints。'
    ),
    "reverse": (
        "逆向腦力激盪：問「如何讓這件事更糟？」，把得到的做法逐條反轉成改善方案。\n"
        "對 LLM 的適用性：能繞開典型答案；與 negate 算子互補。\n"
        '用法：先 cgu_diverge(action="typical_set")，再要求反轉每個典型答案的核心假設。'
    ),
    "morphological": (
        "形態分析（Zwicky）：把問題拆成幾個獨立維度，每個維度列出選項，系統性組合。\n"
        "對 LLM 的適用性：適合「在明確限制空間內的探索」；組合爆炸時以 seed 抽樣，並檢查重複。\n"
        '用法：維度寫成 cgu_frame 的 constraints，組合結果以 cgu_ideas(action="add") 回交。'
    ),
}

PAIRWISE_RUBRIC = """成對比較 rubric
- 程序：每個配對各判兩次，AB 與 BA 位置交換；同一評審連續判兩個位置，才算得出一致率。
- 準則（逐項判斷，各選 idea_id 或 tie）：
  novelty_vs_typical：與典型答案的差異是否有意義；不看文字新奇。
  usefulness：對使用者的決策情境是否有用。
  framing：是否真的改寫了框架元素，而不是換句話說。
  feasibility：能否在限制內動手做（可設為非補償式門檻 gate.feasibility_min）。
- 護欄：不因篇幅、華麗或排在前面而判勝；自己寫的點子要聲明並請另一個模型評；
  至少使用兩個不同家族的評審模型。
- 讀結果：win_rate 依賴評審，不是品質；一致率高不代表評審正確；準則之間不可通約時看 Pareto 前緣，
  不要加權成單一分數。"""

TRIGGERS: dict[str, list[str]] = {
    "浮現": [
        "什麼假設必須成立，這些典型答案才合理？",
        "如果不使用這個假設，情境會變成什麼樣子？",
        "這個假設是核心（改了就是另一個方案），還是可調整的輔助假設？",
        "這次探究中，哪些前提我們決定不質疑？",
    ],
    "澄清": [
        "這個詞的工作定義是什麼？典型例與邊界例各是什麼？",
        "如果兩種定義導致相同的決策，這場爭論只是字面上的嗎？",
        "禁用這個詞之後，我們的分歧還在嗎？",
    ],
    "生成": [
        "若換一個隱喻，解空間會出現什麼新做法？",
        "這個二元對立有沒有「亦是亦非」或「非是非非」的第三、第四種立場？",
        "如果分析單位從個人改成系統，會看見什麼？",
        "如果拿掉這個評估準則，什麼會變得有價值？",
    ],
    "檢驗": [
        "把這個參數推到極端，規則還成立嗎？",
        "什麼結果會證明這個點子是錯的？",
        "不知道自己是哪個利害關係人時，我還接受這個方案嗎？",
        "這個指標被當成目標之後，會有什麼被鑽漏洞的路徑？",
    ],
    "整合": [
        "這裡用的原則，和別處用的原則矛盾嗎？該消解還是保留？",
        "價值不可通約時，取捨是什麼？誰承擔代價？",
        "這個準則原本保護什麼？拆掉之前，籬笆的理由還在嗎？",
    ],
}


def _method_names() -> str:
    return ", ".join(METHODS)


def register(server: MCPServer[Deps]) -> None:
    @server.resource(
        "cgu://methods/{name}",
        name="method",
        title="Creativity method notes",
        description=f"創意方法說明（{_method_names()}）；說明用法與對 LLM 的適用性。",
        mime_type="text/plain",
    )
    def method(name: str) -> str:
        key = name.strip().lower().replace("-", "_")
        if key not in METHODS:
            raise ValueError(f"unknown method {name!r}; available: {_method_names()}")
        return METHODS[key]

    @server.resource(
        "cgu://operators",
        name="operators",
        title="Frame operator cards",
        description="11 張框架算子卡：來源、可作用元素、護欄與工單指示。",
        mime_type="application/json",
    )
    def operators() -> str:
        cards = [
            {**card_view(card), "instruction_template": card.instruction_template}
            for card in OPERATORS.values()
        ]
        return json.dumps(cards, ensure_ascii=False, indent=2)

    @server.resource(
        "cgu://rubrics/question-gate",
        name="rubric_question_gate",
        title="Question gate rubric",
        description="提問閘門的五項判準。",
        mime_type="text/plain",
    )
    def rubric_question_gate() -> str:
        lines = [f"- {name}：{text}" for name, text in QUESTION_GATE_CRITERIA.items()]
        return "提問閘門判準（前四項皆為 true 才通過；non_typical 只加分）\n" + "\n".join(lines)

    @server.resource(
        "cgu://rubrics/pairwise",
        name="rubric_pairwise",
        title="Pairwise judging rubric",
        description="成對比較的程序、準則與護欄。",
        mime_type="text/plain",
    )
    def rubric_pairwise() -> str:
        return PAIRWISE_RUBRIC

    @server.resource(
        "cgu://triggers",
        name="triggers",
        title="Trigger questions",
        description="觸發問句庫：依浮現、澄清、生成、檢驗、整合分組。",
        mime_type="application/json",
    )
    def triggers() -> str:
        return json.dumps(TRIGGERS, ensure_ascii=False, indent=2)

    @server.resource(
        "cgu://methods",
        name="methods_index",
        title="Method index",
        description="可讀取的方法清單。",
        mime_type="application/json",
    )
    def methods_index() -> str:
        return json.dumps(
            [{"name": name, "uri": f"cgu://methods/{name}"} for name in METHODS],
            ensure_ascii=False,
        )
