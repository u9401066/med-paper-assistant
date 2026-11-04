"""Pairwise judging: matchups, position-swapped verdicts, Wilson intervals, Pareto front."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, Field

from cgu.domain.common import CGUError, Measurement

DEFAULT_CRITERIA = ("novelty_vs_typical", "usefulness", "framing")
DEFAULT_ROUNDS = 3
ROUND_ROBIN_LIMIT = 6
MAX_PAIRS = 100
TIE = "tie"


class Verdict(BaseModel):
    matchup_id: str
    order: Literal["AB", "BA"]
    winner: str = Field(description="An idea_id of this matchup, or 'tie'")
    criteria_winners: dict[str, str] = Field(default_factory=dict)
    judge_model: str | None = None
    reason: str | None = None


class Matchup(BaseModel):
    id: str
    session_id: str
    idea_a: str
    idea_b: str
    criteria: list[str]
    feasibility_min: str | None = Field(
        default=None, description="Stored as text so that no bare float is ever exported"
    )
    created_at: str = ""


def generate_pairs(ids: list[str], rounds: int | None, seed: int) -> list[tuple[str, str]]:
    """All pairs for small sets, otherwise a seeded ring plus random pairs up to `rounds` each."""
    unique = sorted(set(ids))
    n = len(unique)
    if n < 2:
        raise CGUError("invalid_input", "judging needs at least two ideas")
    target = rounds if rounds is not None else DEFAULT_ROUNDS
    if (rounds is None and n <= ROUND_ROBIN_LIMIT) or n - 1 <= target:
        pairs = {(unique[i], unique[j]) for i in range(n) for j in range(i + 1, n)}
    else:
        rng = random.Random(seed)
        order = unique[:]
        rng.shuffle(order)
        pairs = {tuple(sorted((order[i], order[(i + 1) % n]))) for i in range(n)}  # type: ignore[misc]
        degree: dict[str, int] = defaultdict(int)
        for a, b in pairs:
            degree[a] += 1
            degree[b] += 1
        attempts = 0
        while min(degree[i] for i in unique) < target and attempts < 50 * n * target:
            attempts += 1
            a, b = sorted(rng.sample(unique, 2))
            if (a, b) not in pairs and degree[a] < target + 1 and degree[b] < target + 1:
                pairs.add((a, b))
                degree[a] += 1
                degree[b] += 1
    result = sorted(pairs)
    if len(result) > MAX_PAIRS:
        raise CGUError(
            "invalid_input",
            f"{len(result)} pairs exceed the limit of {MAX_PAIRS}",
            "Pass fewer idea_ids or a smaller rounds.",
        )
    return result


def wilson_interval(successes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


class IdeaStanding(BaseModel):
    idea_id: str
    wins: int
    losses: int
    ties: int
    judgments: int
    win_rate: Measurement
    wilson_95_low: Measurement
    wilson_95_high: Measurement
    criteria_win_rates: dict[str, Measurement] = Field(default_factory=dict)
    gate: Literal["passed", "failed", "no_feasibility_data", "not_applied"] = "not_applied"
    on_pareto_front: bool = False


class OrderConsistency(BaseModel):
    consistent: int
    inconsistent: int
    unpaired: int
    rate: Measurement | None


class RankReport(BaseModel):
    standings: list[IdeaStanding]
    order_consistency: OrderConsistency
    first_position_wins: int
    decided_verdicts: int
    pareto_front: list[str] | None
    judge_models: list[str]
    warnings: list[str]


def pareto_front(rates: dict[str, dict[str, float]], excluded: set[str]) -> list[str]:
    """Ideas not dominated on the criteria they share; excluded ideas never enter the front."""
    pool = [i for i in rates if i not in excluded]

    def dominates(a: str, b: str) -> bool:
        common = set(rates[a]) & set(rates[b])
        if not common:
            return False
        return all(rates[a][c] >= rates[b][c] for c in common) and any(
            rates[a][c] > rates[b][c] for c in common
        )

    return sorted(i for i in pool if not any(dominates(j, i) for j in pool if j != i))


def rank(matchups: list[Matchup], verdicts: list[Verdict]) -> RankReport:
    by_id = {m.id: m for m in matchups}
    wins: dict[str, int] = defaultdict(int)
    losses: dict[str, int] = defaultdict(int)
    ties: dict[str, int] = defaultdict(int)
    judgments: dict[str, int] = defaultdict(int)
    crit: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    first_position_wins = 0
    decided = 0
    paired: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)

    for v in verdicts:
        m = by_id.get(v.matchup_id)
        if m is None:
            continue
        ids = (m.idea_a, m.idea_b)
        for i in ids:
            judgments[i] += 1
        if v.winner == TIE:
            for i in ids:
                ties[i] += 1
        else:
            loser = m.idea_b if v.winner == m.idea_a else m.idea_a
            wins[v.winner] += 1
            losses[loser] += 1
            decided += 1
            first_shown = m.idea_a if v.order == "AB" else m.idea_b
            first_position_wins += int(v.winner == first_shown)
        for name, winner in v.criteria_winners.items():
            for i in ids:
                crit[i][name][1] += 1
                if winner == i:
                    crit[i][name][0] += 1
                elif winner == TIE:
                    crit[i][name][0] += 0.5
        paired[(v.matchup_id, v.judge_model or "unknown")][v.order] = v.winner

    consistent = inconsistent = unpaired = 0
    for orders in paired.values():
        if len(orders) == 2:
            if orders["AB"] == orders["BA"]:
                consistent += 1
            else:
                inconsistent += 1
        else:
            unpaired += 1
    pairs_total = consistent + inconsistent
    consistency = OrderConsistency(
        consistent=consistent,
        inconsistent=inconsistent,
        unpaired=unpaired,
        rate=(
            Measurement(
                value=consistent / pairs_total,
                method="share of AB/BA pairs by one judge that pick the same winner; "
                "high consistency does not mean the judge is correct",
                reference=f"paired verdicts (n={pairs_total})",
                n=pairs_total,
            )
            if pairs_total
            else None
        ),
    )

    gate_values = {float(m.feasibility_min) for m in matchups if m.feasibility_min is not None}
    gate_min = max(gate_values) if gate_values else None
    rates: dict[str, dict[str, float]] = {}
    standings: list[IdeaStanding] = []
    for idea_id in sorted(judgments):
        n = judgments[idea_id]
        successes = wins[idea_id] + 0.5 * ties[idea_id]
        low, high = wilson_interval(successes, n)
        method = (
            "win rate (tie = 0.5) from pairwise verdicts; Wilson 95% interval; "
            "depends on the judge model(s) and is not a quality measurement"
        )
        reference = f"verdicts involving this idea (n={n})"
        criteria_rates: dict[str, Measurement] = {}
        rates[idea_id] = {}
        for name, (c_wins, c_trials) in crit[idea_id].items():
            value = c_wins / c_trials
            rates[idea_id][name] = value
            criteria_rates[name] = Measurement(
                value=value,
                method=f"criterion '{name}' win rate (tie = 0.5) from pairwise verdicts",
                reference=f"verdicts with a '{name}' judgment (n={int(c_trials)})",
                n=int(c_trials),
            )
        standings.append(
            IdeaStanding(
                idea_id=idea_id,
                wins=wins[idea_id],
                losses=losses[idea_id],
                ties=ties[idea_id],
                judgments=n,
                win_rate=Measurement(value=successes / n, method=method, reference=reference, n=n),
                wilson_95_low=Measurement(
                    value=low,
                    method="Wilson 95% lower bound of the win rate",
                    reference=reference,
                    n=n,
                ),
                wilson_95_high=Measurement(
                    value=high,
                    method="Wilson 95% upper bound of the win rate",
                    reference=reference,
                    n=n,
                ),
                criteria_win_rates=criteria_rates,
            )
        )

    excluded: set[str] = set()
    if gate_min is not None:
        for s in standings:
            feasibility = rates[s.idea_id].get("feasibility")
            if feasibility is None:
                s.gate = "no_feasibility_data"
                excluded.add(s.idea_id)
            elif feasibility < gate_min:
                s.gate = "failed"
                excluded.add(s.idea_id)
            else:
                s.gate = "passed"

    has_criteria = any(rates[i] for i in rates)
    front = pareto_front(rates, excluded) if has_criteria else None
    for s in standings:
        s.on_pareto_front = front is not None and s.idea_id in front
    standings.sort(key=lambda s: (-s.win_rate.value, s.idea_id))

    judge_models = sorted({v.judge_model or "unknown" for v in verdicts if v.matchup_id in by_id})
    known = [m for m in judge_models if m != "unknown"]
    warnings: list[str] = []
    if len(known) < 2:
        warnings.append(
            f"{len(known)} named judge model(s) recorded; a single model family tends to prefer "
            "its own outputs and the first position. Use at least two different families."
        )
    return RankReport(
        standings=standings,
        order_consistency=consistency,
        first_position_wins=first_position_wins,
        decided_verdicts=decided,
        pareto_front=front,
        judge_models=judge_models,
        warnings=warnings,
    )


def judge_matchup_inputs(matchup: Matchup, order: str, texts: dict[str, str]) -> dict[str, Any]:
    first, second = (
        (matchup.idea_a, matchup.idea_b) if order == "AB" else (matchup.idea_b, matchup.idea_a)
    )
    return {
        "matchup_id": matchup.id,
        "order": order,
        "first": {"idea_id": first, "text": texts[first]},
        "second": {"idea_id": second, "text": texts[second]},
        "criteria": matchup.criteria,
    }
