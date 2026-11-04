"""Frame: the first-class object that ideas are generated inside, with lineage and diffs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from cgu.domain.common import CGUError

ELEMENT_KINDS = (
    "goal",
    "assumption",
    "concept",
    "metaphor",
    "criterion",
    "stakeholder",
    "constraint",
    "unit",
    "hinge",
)
RESTRICTED_KINDS = frozenset({"goal", "stakeholder", "criterion"})
LIST_FIELDS = {
    "assumption": "assumptions",
    "concept": "concepts",
    "metaphor": "metaphors",
    "criterion": "criteria",
    "stakeholder": "stakeholders",
    "constraint": "constraints",
    "hinge": "hinges",
}
ID_PREFIX = {
    "assumption": "a",
    "concept": "c",
    "metaphor": "m",
    "criterion": "k",
    "stakeholder": "s",
    "constraint": "n",
    "hinge": "h",
}
SINGLE_KINDS = {"goal": "goal", "unit": "unit"}


def kind_of_id(element_id: str) -> str | None:
    if element_id in SINGLE_KINDS:
        return SINGLE_KINDS[element_id]
    for kind, prefix in ID_PREFIX.items():
        if element_id[:1] == prefix and element_id[1:].isdigit():
            return kind
    return None


class Element(BaseModel):
    id: str | None = None

    def describe(self) -> str:
        raise NotImplementedError

    def core(self) -> dict[str, Any]:
        dumped: dict[str, Any] = self.model_dump(exclude={"id"})
        return dumped


class Assumption(Element):
    text: str = Field(min_length=1)
    kind: Literal["core", "belt"] = "belt"
    source: str | None = None

    def describe(self) -> str:
        return f"[{self.kind}] {self.text}"


class Concept(Element):
    term: str = Field(min_length=1)
    working_definition: str = ""
    alternatives: list[str] = Field(default_factory=list)

    def describe(self) -> str:
        return f"{self.term}: {self.working_definition}" if self.working_definition else self.term


class Metaphor(Element):
    text: str = Field(min_length=1)

    def describe(self) -> str:
        return self.text


class Criterion(Element):
    text: str = Field(min_length=1)
    serves: str | None = None
    mode: Literal["threshold", "tradeoff"] = "tradeoff"

    def describe(self) -> str:
        serves = f" (serves {self.serves})" if self.serves else ""
        return f"{self.text}{serves} [{self.mode}]"


class Stakeholder(Element):
    who: str = Field(min_length=1)
    bears_costs: bool | None = None

    def describe(self) -> str:
        cost = {True: " (bears costs)", False: " (does not bear costs)", None: ""}[self.bears_costs]
        return f"{self.who}{cost}"


class Constraint(Element):
    text: str = Field(min_length=1)
    type: Literal["hard", "soft", "self_imposed"] = "soft"

    def describe(self) -> str:
        return f"[{self.type}] {self.text}"


class Hinge(Element):
    text: str = Field(min_length=1)

    def describe(self) -> str:
        return self.text


class Change(BaseModel):
    kind: str
    id: str
    change: Literal["added", "removed", "modified"]
    before: str | None = None
    after: str | None = None


class Consent(BaseModel):
    granted: bool
    note: str = ""


class ConsentRecord(BaseModel):
    granted: bool
    note: str = ""
    via: Literal["caller", "elicitation"]


class Disclosure(BaseModel):
    changed: list[Change]
    why: str
    operator: str
    source: str
    restricted_kinds: list[str] = Field(default_factory=list)
    consent: ConsentRecord | None = None
    checks: dict[str, str] = Field(default_factory=dict)


class FrameDraft(BaseModel):
    """A child frame. Omitted kinds are inherited; a given list replaces that kind in full."""

    why: str = Field(min_length=4, description="One sentence: why this rewrite")
    checks: dict[str, str] = Field(default_factory=dict)
    problem: str | None = None
    goal: str | None = None
    unit: str | None = None
    stakeholders: list[Stakeholder] | None = None
    concepts: list[Concept] | None = None
    assumptions: list[Assumption] | None = None
    constraints: list[Constraint] | None = None
    metaphors: list[Metaphor] | None = None
    criteria: list[Criterion] | None = None
    hinges: list[Hinge] | None = None


class Frame(BaseModel):
    frame_id: str
    session_id: str
    problem: str
    goal: str | None = None
    unit: str | None = None
    stakeholders: list[Stakeholder] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    metaphors: list[Metaphor] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
    hinges: list[Hinge] = Field(default_factory=list)
    parent_id: str | None = None
    operator: str | None = None
    disclosure: Disclosure | None = None
    id_counters: dict[str, int] = Field(default_factory=dict)
    created_at: str = ""

    def items(self, kind: str) -> list[Any]:
        return list(getattr(self, LIST_FIELDS[kind]))

    def element_ids(self) -> set[str]:
        ids = {item.id for kind in LIST_FIELDS for item in self.items(kind) if item.id}
        if self.goal:
            ids.add("goal")
        if self.unit:
            ids.add("unit")
        return ids

    def view(self) -> dict[str, Any]:
        dumped: dict[str, Any] = self.model_dump(
            mode="json",
            exclude={"session_id", "created_at", "disclosure", "id_counters", "parent_id"},
            exclude_none=True,
        )
        return dumped


def _next_id(counters: dict[str, int], prefix: str) -> str:
    counters[prefix] = counters.get(prefix, 0) + 1
    return f"{prefix}{counters[prefix]}"


def _merge_items(
    kind: str,
    parent_items: list[Any],
    draft_items: list[Any],
    counters: dict[str, int],
) -> list[Any]:
    parent_ids = {item.id for item in parent_items}
    seen: set[str] = set()
    merged: list[Any] = []
    for item in draft_items:
        element = item.model_copy()
        if element.id is not None:
            if element.id not in parent_ids:
                raise CGUError(
                    "invalid_input",
                    f"{kind} id {element.id!r} is not in the parent frame",
                    "Keep the original id for unchanged or edited elements; give new elements no id.",
                )
            if element.id in seen:
                raise CGUError("invalid_input", f"duplicate {kind} id {element.id!r} in draft")
            seen.add(element.id)
        else:
            element.id = _next_id(counters, ID_PREFIX[kind])
        merged.append(element)
    return merged


def seed_counters(frame: Frame) -> dict[str, int]:
    counters = dict(frame.id_counters)
    for kind, prefix in ID_PREFIX.items():
        for item in frame.items(kind):
            if item.id and item.id[1:].isdigit():
                counters[prefix] = max(counters.get(prefix, 0), int(item.id[1:]))
    return counters


def build_frame(
    *,
    frame_id: str,
    session_id: str,
    problem: str,
    created_at: str,
    goal: str | None = None,
    unit: str | None = None,
    elements: dict[str, list[Any]] | None = None,
) -> Frame:
    counters: dict[str, int] = {}
    fields: dict[str, Any] = {}
    for kind, field in LIST_FIELDS.items():
        given = (elements or {}).get(kind) or []
        fields[field] = [
            item.model_copy(update={"id": _next_id(counters, ID_PREFIX[kind])}) for item in given
        ]
    return Frame(
        frame_id=frame_id,
        session_id=session_id,
        problem=problem,
        goal=goal or None,
        unit=unit or None,
        id_counters=counters,
        created_at=created_at,
        **fields,
    )


def apply_draft(parent: Frame, draft: FrameDraft, *, frame_id: str, created_at: str) -> Frame:
    if draft.problem is not None and draft.problem.strip() != parent.problem.strip():
        raise CGUError(
            "invalid_input",
            "a child frame must keep the parent's problem",
            "The problem is the shared reference of a lineage; call cgu_frame(create) for a new one.",
        )
    counters = seed_counters(parent)
    fields: dict[str, Any] = {}
    for kind, field in LIST_FIELDS.items():
        given = getattr(draft, field)
        fields[field] = (
            parent.items(kind)
            if given is None
            else _merge_items(kind, parent.items(kind), given, counters)
        )
    return Frame(
        frame_id=frame_id,
        session_id=parent.session_id,
        problem=parent.problem,
        goal=parent.goal if draft.goal is None else (draft.goal.strip() or None),
        unit=parent.unit if draft.unit is None else (draft.unit.strip() or None),
        id_counters=counters,
        created_at=created_at,
        **fields,
    )


def diff_frames(parent: Frame, child: Frame) -> list[Change]:
    changes: list[Change] = []
    for kind in ("goal", "unit"):
        before, after = getattr(parent, kind), getattr(child, kind)
        if before != after:
            label = "added" if before is None else "removed" if after is None else "modified"
            changes.append(
                Change(kind=kind, id=kind, change=label, before=before, after=after)  # type: ignore[arg-type]
            )
    for kind in LIST_FIELDS:
        old = {item.id: item for item in parent.items(kind)}
        new = {item.id: item for item in child.items(kind)}
        for element_id, item in old.items():
            if element_id not in new:
                changes.append(
                    Change(
                        kind=kind,
                        id=str(element_id),
                        change="removed",
                        before=item.describe(),
                    )
                )
            elif new[element_id].core() != item.core():
                changes.append(
                    Change(
                        kind=kind,
                        id=str(element_id),
                        change="modified",
                        before=item.describe(),
                        after=new[element_id].describe(),
                    )
                )
        for element_id, item in new.items():
            if element_id not in old:
                changes.append(
                    Change(kind=kind, id=str(element_id), change="added", after=item.describe())
                )
    return changes


def restricted_kinds(changes: list[Change]) -> list[str]:
    return sorted({c.kind for c in changes if c.kind in RESTRICTED_KINDS})
