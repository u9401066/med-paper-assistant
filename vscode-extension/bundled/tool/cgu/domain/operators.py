"""The 11 frame operators: source, guardrails, targets and the work-order instruction text."""

from __future__ import annotations

from string import Template
from typing import Any

from pydantic import BaseModel, Field

from cgu.domain.common import CGUError
from cgu.domain.frame import (
    RESTRICTED_KINDS,
    Change,
    Frame,
    FrameDraft,
    apply_draft,
    diff_frames,
    restricted_kinds,
)

SHAPE = (
    '回交格式（FrameDraft JSON，交給 cgu_frame(action="commit") 的 child）：只填你改動的種類；'
    "該種類要列出完整清單，未改的元素保留原 id，新元素不給 id。\n"
    '{"why": "一句話：為何這樣改", "checks": {"<檢查名>": "<結果>"}, "<種類>": [...]}\n'
    "種類名稱：goal、unit（字串）；assumptions、concepts、metaphors、criteria、"
    "stakeholders、constraints、hinges（清單）。"
)


class OperatorCard(BaseModel):
    name: str
    source: str
    summary: str
    targets: list[str]
    default_target: str | None = None
    restricted: bool
    guardrails: list[str]
    required_checks: list[str] = Field(default_factory=list)
    instruction_template: str
    example_domain: str


def _card(
    name: str,
    source: str,
    summary: str,
    targets: list[str],
    guardrails: list[str],
    example_domain: str,
    template: str,
    required_checks: list[str] | None = None,
    default_target: str | None = None,
) -> OperatorCard:
    return OperatorCard(
        name=name,
        source=source,
        summary=summary,
        targets=targets,
        default_target=default_target or (targets[0] if len(targets) == 1 else None),
        restricted=bool(set(targets) & RESTRICTED_KINDS),
        guardrails=guardrails,
        required_checks=required_checks or [],
        instruction_template=template,
        example_domain=example_domain,
    )


_CARDS = [
    _card(
        "explicate",
        "Peirce 溯因；Lakatos 硬核／保護帶",
        "從典型答案溯因出它們默默依賴的隱性框架（假設、隱喻）。",
        ["assumption", "metaphor", "hinge"],
        ["推出的只是候選假設，需經使用者確認", "每條假設必須能指回某個典型答案"],
        "醫療研究構想",
        """任務（explicate，浮現隱性假設）：從「典型答案」反推它們默默依賴的假設。
問題：$problem
作用對象：$target
做法：
1. 讀 inputs.typical_ideas。若為空，先用 cgu_diverge(action="typical_set") 取得典型答案，再回來。
2. 對每個典型答案自問：「什麼假設必須成立，這個答案才合理？」寫成 3–6 條。
3. 每條標 kind：core（推翻它就變成另一個方案）或 belt（可調整的輔助假設），source 填 "abduced_from_typical_answers"。
$shape
護欄：你推出的只是「候選假設」，不是事實，必須經使用者確認；每條必須能指回某個典型答案，不得憑空新增。
範例（醫療研究）：問題「如何降低老年人術後譫妄」，典型答案「減少苯二氮平類藥物」「早期下床」。回交：{"why": "從典型答案溯因", "assumptions": [{"text": "譫妄主要由藥物引起", "kind": "belt", "source": "abduced_from_typical_answers"}, {"text": "評估期限為術後 7 天內", "kind": "belt", "source": "abduced_from_typical_answers"}]}""",
        default_target="assumption",
    ),
    _card(
        "bracket",
        "Husserl 存而不論；Gadamer 前見",
        "暫時把一個假設放進括號，在不使用它的前提下重寫情境。",
        ["assumption"],
        ["一次只懸置一個明示的假設", "懸置是暫時的，必須說明放回去會失去什麼"],
        "行政流程變革",
        """任務（bracket，存而不論）：暫時把一個假設「放進括號」，在不使用它的前提下重寫情境。
問題：$problem
作用對象：$target（必須是 assumption 的 id）
做法：
1. 在 inputs.parent_frame 找到該假設，把原文抄進 why。
2. 子框架的 assumptions 清單移除這一條，其餘保留原 id。
3. checks.restated：寫一段「若不假設它，情境變成什麼樣子」。
4. checks.cost_of_restoring：若把它放回去，會失去什麼。
$shape
護欄：只能懸置一個明示的假設；不要同時懸置 core 與多個 belt；懸置是暫時的。
範例（行政流程）：問題「縮短門診病歷申請時間」，假設「申請必須由本人到櫃檯送出」。移除後 checks.restated：「家屬或線上系統可代送」；cost_of_restoring：「失去簡單的身分確認，須新增授權查核」。""",
    ),
    _card(
        "negate",
        "辯證反轉；逆向腦力激盪",
        "把一個假設反轉，問「如果相反才對呢」。",
        ["assumption"],
        ["反面必須能推出具體做法，推不出就換一個假設", "反轉 core 假設等於換方案，要在 why 明說"],
        "醫療商品開發",
        """任務（negate，反轉假設）：把一個假設反過來，問「如果相反才對呢？」
問題：$problem
作用對象：$target（assumption 的 id）
做法：
1. 抄下原假設。
2. 寫出它的反面：一個可以成立的具體相反主張，不是加上否定詞。
3. 在 assumptions 就地改寫該假設（保留原 id），kind 維持原樣。
4. checks.what_would_follow：反面成立時會出現的新做法，至少一項。
$shape
護欄：反面若推不出任何具體做法，改選別的假設，不要硬湊；反轉 core 假設等於換方案，why 要明說。
範例（醫療商品開發）：問題「設計居家高血壓血壓計」，假設「使用者要主動記得量血壓」。反面：「血壓計不要求使用者記得」。what_would_follow：「綁在每天打開藥盒的動作上，自動啟動量測」。""",
    ),
    _card(
        "tetralemma",
        "龍樹四句（catuṣkoṭi）",
        "對二元對立的限制，系統性生成四種立場：是、非、亦是亦非、非是非非。",
        ["constraint", "assumption"],
        ["每一句都要能想像出具體做法", "想不出來就誠實寫「無法具體化」"],
        "行政流程變革",
        """任務（tetralemma，四句）：對二元對立的限制，系統性寫出四種立場。
問題：$problem
作用對象：$target（constraint 或 assumption 的 id，內容須是「A 或 B」型的對立）
做法：
1. 把對立寫成 A / B（例如「集中 / 分散」）。
2. 寫四句：①是 A；②是 B；③亦是 A 亦是 B（常對應分層或聯邦式）；④非 A 非 B（常對應「讓這個維度不再重要」）。
3. 子框架的 constraints（或 assumptions）：保留原項，並新增四條，text 開頭標 [①][②][③][④]。
$shape
護欄：每一句都要能想像出一個具體做法；想不出來就寫「無法具體化」並說明原因，不得空泛。
範例（行政流程）：限制「檢驗申請單由護理站集中處理 / 由各科自行處理」。③分層：常規項目各科直送、特殊項目由護理站審核；④非集中非分散：電子醫囑自動路由，不需人工分流。""",
    ),
    _card(
        "re_explicate",
        "Carnap 闡明；Peirce 實用準則",
        "為模糊概念設計精確的替代定義，並檢查不同定義是否導致不同決策。",
        ["concept"],
        ["沒有 practical_difference 就不算數", "「有成果」要對照下游用途判斷"],
        "醫療研究構想",
        """任務（re_explicate，闡明概念）：為模糊概念設計更精確的替代定義。
問題：$problem
作用對象：$target（concept 的 id）
做法：
1. 抄原概念的 term 與 working_definition。
2. 提出 1–3 個替代定義放進該 concept 的 alternatives，並把最推薦的寫成新的 working_definition。
3. checks.carnap：用四項準則自評——與原概念相似？夠精確？有成果（下游能用）？夠簡單？
4. checks.practical_difference：不同定義各會導致什麼不同的決策或測量？若完全相同，寫明這只是字面之爭。
$shape
護欄：沒有 practical_difference 就不算數。
範例（醫療研究）：概念「譫妄」，原定義「術後意識混亂」。替代：「CAM-ICU 陽性且持續兩次以上評估」。practical_difference：「前者納入短暫嗜睡個案，發生率較高；後者決定收案與排除標準」。""",
        required_checks=["practical_difference"],
    ),
    _card(
        "swap_metaphor",
        "Black 互動論；Lakoff & Johnson；Schön 生成性隱喻",
        "找出問題背後的隱喻，換成另一個，觀察解空間如何改變。",
        ["metaphor"],
        ["每個隱喻必須推出具體做法", "檢查隱喻隱含的價值：誰被放進、誰被排除"],
        "醫療商品開發",
        """任務（swap_metaphor，換隱喻）：找出問題背後的隱喻，換成另一個，觀察解空間如何改變。
問題：$problem
作用對象：$target
做法：
1. 寫出現有隱喻。若 metaphors 為空，從問題用語推出（例如「戰鬥」「肌肉」「管線」）。
2. 提出 2 個替代隱喻，各自推出 1 個新做法。
3. 在 metaphors 清單把被換掉的隱喻就地改寫（保留原 id），或新增。
4. checks.consequence：新隱喻讓哪些做法變得「看得見」、哪些變得「看不見」。
$shape
護欄：隱喻不是裝飾；每個隱喻必須推出一個具體做法，並檢查它隱含的價值（誰被放進、誰被排除）。
範例（醫療商品開發）：問題「讓長者持續服藥」，隱喻「服藥是任務打卡」。換成「服藥是每天的小儀式」→ 做法：藥盒設計成和早茶時間綁定，用氣味與聲音提示，而不是鬧鐘。""",
    ),
    _card(
        "recut_unit",
        "本體論透鏡；系統思考",
        "改變分析單位（個人→團隊→系統；事件→關係；流程→產物）。",
        ["unit"],
        ["新單位必須可觀察、可介入", "不可觀察或無法介入時，要在 why 說明為何仍保留"],
        "醫療研究構想",
        """任務（recut_unit，改分析單位）：改變看問題的單位，例如 個人→團隊→系統、事件→關係、流程→產物。
問題：$problem
作用對象：$target
做法：
1. 寫出現有單位（unit 欄位；若空白，從問題推論）。
2. 提出一個新單位。
3. 子框架的 unit 填新單位（字串）。
4. checks.observable：新單位可觀察嗎？用什麼資料觀察？
5. checks.intervenable：能對它採取行動嗎？誰來做？
$shape
護欄：新單位若無法觀察或無法介入，不要採用；仍想保留時在 why 說明理由。
範例（醫療研究）：問題「為何手術室準時開刀率偏低」，現有單位「單一病人」→ 新單位「同一手術室當日連續三台刀的排程串」。observable：「麻醉紀錄的進出室時間」；intervenable：「排程組可調整接台順序」。""",
        required_checks=["observable", "intervenable"],
    ),
    _card(
        "shift_stakeholder",
        "Rawls 無知之幕；Haslanger 概念工程",
        "改寫誰受益、誰承擔成本，並做無知之幕檢查。",
        ["stakeholder", "criterion"],
        ["改寫利害關係人屬受限元素，須使用者同意", "不得替使用者決定誰重要", "必含無知之幕檢查"],
        "行政流程變革",
        """任務（shift_stakeholder，換利害關係人視角）：改寫「誰受益、誰承擔成本」，並做無知之幕檢查。
問題：$problem
作用對象：$target（stakeholder 或 criterion 的 id，或種類名稱）。這是受限元素：改寫須使用者同意。
做法：
1. 列出現有利害關係人與 bears_costs。
2. 補上被忽略的一方（例如代理人、病人、基層行政），或改寫 bears_costs。
3. checks.new_view：以新視角寫一個會改變方案的觀察。
4. checks.veil_of_ignorance：「在不知道自己會是誰的前提下，這個方案我仍願意接受嗎？」誰會說不？
$shape
護欄：不得替使用者決定誰重要；改寫後必須讓使用者看到 disclosure（誰被加入或移除）。
範例（行政流程）：問題「簡化請假簽核」，原利害關係人「主管」(bears_costs=false)。新增「代理人」(bears_costs=true)：簽核簡化後，代理人臨時接手的風險上升。veil_of_ignorance：「若我是代理人，我要求事前交接清單才接受」。""",
        required_checks=["veil_of_ignorance"],
    ),
    _card(
        "invert_criterion",
        "《莊子》無用之用；Goodhart／Campbell 指標腐化",
        "反轉評估準則：若拿掉目前的價值指標，什麼會變得有價值？",
        ["criterion"],
        ["改寫評估準則屬受限元素，須使用者同意", "只是更慢更貴而沒有新價值時退回"],
        "醫療商品開發",
        """任務（invert_criterion，無用之用）：反轉評估準則——若拿掉目前的價值指標，什麼會變得有價值？
問題：$problem
作用對象：$target（criterion 的 id）。這是受限元素：改寫須使用者同意。
做法：
1. 抄原準則。
2. 寫出相反或被排除的準則（例如「速度」→「刻意放慢」）。
3. 在 criteria 就地改寫（保留原 id）或新增；說明反轉後仍是門檻（threshold）還是取捨（tradeoff）。
4. checks.what_becomes_valuable：反轉後，哪些原本被淘汰的方案變得可取，至少一個。
$shape
護欄：這是挑戰評分準則，不是推翻目標；若結果只是「更慢更貴」而沒有新價值，退回重做。
範例（醫療商品開發）：準則「量測次數越多越好」→ 反轉為「量測次數越少越好」。what_becomes_valuable：「只在趨勢異常時才量測的穿戴貼片，電池續航與使用者依從性都更好」。""",
        required_checks=["what_becomes_valuable"],
    ),
    _card(
        "genealogize",
        "Nietzsche／Foucault 系譜學；Chesterton 籬笆",
        "追問準則或慣例怎麼來的、原本保護什麼。",
        ["criterion", "goal", "hinge"],
        [
            "必含籬笆檢查：知道它為何存在之前不得建議拆除",
            "來源查不到就寫「來源不明」，不得編造",
            "改寫準則或目標屬受限元素，須使用者同意",
        ],
        "行政流程變革",
        """任務（genealogize，系譜追溯）：追問準則或慣例「怎麼來的、原本為了解決什麼」。
問題：$problem
作用對象：$target（criterion 或 goal 的 id）。這是受限元素：改寫須使用者同意。
做法：
1. 抄原準則。
2. 寫出可查證的來源（事件、法規、成本結構）；查不到就寫「來源不明」，不得編造。
3. 推出它原本保護什麼，寫入 checks.protects。
4. 若要放寬或替換，就地改寫該元素（保留原 id），並在 hinges 新增「必須繼續保護的東西」。
5. checks.fence_check（必填）：「這道籬笆原本保護什麼？現在仍需要嗎？」回答之前不得建議拆除。
$shape
護欄：Chesterton 的籬笆——不知道為何存在，就不要拆；來源不明時，建議小範圍試驗而不是廢止。
範例（行政流程）：準則「採購超過一萬元須三層簽核」。來源：一次舞弊事件。fence_check：「保護下單與核銷不由同一人」。調整：「三萬元以下兩層簽核，但下單與核銷分離」，hinges 新增「下單與核銷不同人」。""",
        required_checks=["fence_check"],
    ),
    _card(
        "thought_experiment",
        "Galileo／Einstein 思想實驗；Dennett 轉旋鈕",
        "把一個參數推到極端，再有系統地轉動，看直覺是否穩健。",
        ["constraint", "assumption"],
        ["必須轉旋鈕；直覺在所有刻度下不變就寫「穩健」", "不要硬找翻轉點"],
        "醫療研究構想",
        """任務（thought_experiment，思想實驗與轉旋鈕）：把一個參數推到極端，看規則是否失效；再轉動參數，看直覺是否穩健。
問題：$problem
作用對象：$target（constraint 或 assumption 的 id）
做法：
1. 指出一個可轉動的參數（人數、時間、成本、風險、資訊量）。
2. 推到極端（0、全部、千倍），寫出會發生什麼。
3. 依序轉三個刻度，記錄結論在哪裡翻轉。
4. 把發現寫回子框架：新增或改寫 constraints／assumptions，註明來自實驗。
5. checks.knob_turned：「參數＝…；刻度＝…；翻轉點＝…」
$shape
護欄：直覺泵可能誤導，所以必須轉旋鈕；若直覺在所有刻度下都不變，寫「穩健」，不要硬找翻轉點。
範例（醫療研究）：假設「每位病人都要術前住院評估」。參數＝需評估的病人比例：極端 0% 與 100%。刻度 20%／50%／80%：低風險族群在 50% 以下沒有差異，翻轉點落在 ASA I–II 與 III 之間。""",
        required_checks=["knob_turned"],
    ),
]

OPERATORS: dict[str, OperatorCard] = {card.name: card for card in _CARDS}
OPERATOR_NAMES = tuple(OPERATORS)


def get_operator(name: str) -> OperatorCard:
    card = OPERATORS.get(name)
    if card is None:
        raise CGUError(
            "invalid_input",
            f"unknown operator {name!r}",
            "Use one of: " + ", ".join(OPERATOR_NAMES),
        )
    return card


def render_instructions(
    card: OperatorCard, *, problem: str, target: str, params: dict[str, Any] | None = None
) -> str:
    text = Template(card.instruction_template).safe_substitute(
        problem=problem, target=target, shape=SHAPE
    )
    if params:
        extra = "；".join(f"{key}={value}" for key, value in params.items())
        text += f"\n額外參數：{extra}"
    return text


class CommitPlan(BaseModel):
    child: Frame
    changes: list[Change]
    restricted: list[str]
    card: OperatorCard


def plan_commit(
    parent: Frame, operator: str, draft: FrameDraft, *, frame_id: str, created_at: str
) -> CommitPlan:
    card = get_operator(operator)
    missing = [name for name in card.required_checks if not draft.checks.get(name, "").strip()]
    if missing:
        raise CGUError(
            "invalid_input",
            f"{operator} requires non-empty checks: {', '.join(missing)}",
            card.guardrails[0],
        )
    child = apply_draft(parent, draft, frame_id=frame_id, created_at=created_at)
    changes = diff_frames(parent, child)
    if not changes:
        raise CGUError(
            "invalid_input",
            "the child frame is identical to the parent",
            "A frame that changes nothing is not an alternative frame.",
        )
    outside = sorted({c.kind for c in changes} - set(card.targets))
    if outside:
        raise CGUError(
            "invalid_input",
            f"{operator} may only change {card.targets}, but the draft changed {outside}",
            "Revert the other kinds or use the operator that targets them.",
        )
    child.parent_id = parent.frame_id
    child.operator = operator
    return CommitPlan(child=child, changes=changes, restricted=restricted_kinds(changes), card=card)
