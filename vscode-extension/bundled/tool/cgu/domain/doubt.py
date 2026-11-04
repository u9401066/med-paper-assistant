"""Economy of doubt and the question gate: when to doubt, what to doubt, when to stop."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cgu.domain.common import Measurement

STALLED_ROUNDS_TRIGGER = 2
LOAD_BEARING_FLOOR = 0.5

QUESTION_GATE_CRITERIA: dict[str, str] = {
    "decision_relevant": "答案不同時，行動或方案的排序會改變嗎？（要說出會怎麼變）",
    "operable": "能指出要蒐集什麼證據、找誰、做什麼實驗來回答嗎？",
    "load_bearing": "它指向的假設被推翻時，結論會翻轉嗎？（反事實依賴）",
    "non_verbal": "禁用問題中的關鍵詞後，問題仍然存在嗎？（若分歧消失，只是口頭之爭）",
    "non_typical": "（加分項，不是否決項）這是不是模型面對此類情境的預設深刻提問？",
}
REQUIRED_CRITERIA = ("decision_relevant", "operable", "load_bearing", "non_verbal")


class DoubtSignals(BaseModel):
    stalled_rounds: int = Field(default=0, ge=0)
    anomalies: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    high_stakes: bool = False
    user_requested: bool = False


class AssumptionEstimate(BaseModel):
    load_bearing: float = Field(ge=0, le=1, description="How much the conclusion depends on it")
    uncertainty: float = Field(ge=0, le=1, description="How likely it is wrong")
    decision_impact: float = Field(ge=0, le=1, description="Would changing it change the action")
    irreversibility: float = Field(ge=0, le=1, description="How hard to repair if wrong")


class DoubtBudget(BaseModel):
    max_questions: int = Field(default=3, ge=0, le=20)


class RankedAssumption(BaseModel):
    assumption_id: str
    text: str
    priority: Measurement


class DoubtReport(BaseModel):
    escalate: bool
    triggers: list[str]
    ranked: list[RankedAssumption]
    selected: list[str]
    stop_reasons: list[str]
    untested_load_bearing: list[str]
    unestimated: list[str]


def evaluate_doubt(
    assumptions: dict[str, str],
    signals: DoubtSignals,
    estimates: dict[str, AssumptionEstimate],
    budget: DoubtBudget,
) -> DoubtReport:
    triggers: list[str] = []
    if signals.stalled_rounds >= STALLED_ROUNDS_TRIGGER:
        triggers.append("stalled")
    if signals.anomalies:
        triggers.append("anomaly")
    if signals.conflicts:
        triggers.append("conflict")
    if signals.high_stakes:
        triggers.append("high_stakes")
    if signals.user_requested:
        triggers.append("user_requested")
    escalate = bool(triggers)

    scored: list[tuple[str, float, AssumptionEstimate]] = []
    for assumption_id, estimate in estimates.items():
        product = (
            estimate.load_bearing
            * estimate.uncertainty
            * estimate.decision_impact
            * estimate.irreversibility
        )
        scored.append((assumption_id, product, estimate))
    scored.sort(key=lambda item: (-item[1], item[0]))

    method = (
        "load_bearing x uncertainty x decision_impact x irreversibility; "
        "product of caller-supplied estimates; uncalibrated heuristic"
    )
    reference = f"caller estimates for {len(estimates)} of {len(assumptions)} assumptions"
    ranked = [
        RankedAssumption(
            assumption_id=assumption_id,
            text=assumptions[assumption_id],
            priority=Measurement(value=product, method=method, reference=reference, n=len(scored)),
        )
        for assumption_id, product, _ in scored
    ]

    positive = [item for item in scored if item[1] > 0]
    selected = [item[0] for item in positive[: budget.max_questions]] if escalate else []

    stop_reasons: list[str] = []
    if not escalate:
        stop_reasons.append("no_trigger")
    if not estimates:
        stop_reasons.append("no_estimates")
    elif escalate and not positive:
        stop_reasons.append("no_decision_impact")
    if escalate and len(positive) > budget.max_questions:
        stop_reasons.append("budget_exhausted")

    untested = [
        assumption_id
        for assumption_id, _, estimate in scored
        if estimate.load_bearing >= LOAD_BEARING_FLOOR and assumption_id not in selected
    ]
    return DoubtReport(
        escalate=escalate,
        triggers=triggers,
        ranked=ranked,
        selected=selected,
        stop_reasons=stop_reasons,
        untested_load_bearing=untested,
        unestimated=sorted(set(assumptions) - set(estimates)),
    )


class QuestionVerdicts(BaseModel):
    decision_relevant: bool
    operable: bool
    load_bearing: bool
    non_verbal: bool
    non_typical: bool | None = None


class GateResult(BaseModel):
    passed: bool
    failed: list[str]
    non_typical: bool | None


def evaluate_question_gate(verdicts: QuestionVerdicts) -> GateResult:
    failed = [name for name in REQUIRED_CRITERIA if not getattr(verdicts, name)]
    return GateResult(passed=not failed, failed=failed, non_typical=verdicts.non_typical)
