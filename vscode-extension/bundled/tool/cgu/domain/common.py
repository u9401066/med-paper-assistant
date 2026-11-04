"""Shared result types. A float may only travel inside a Measurement."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from cgu import __version__

ErrorCode = Literal["not_found", "invalid_input", "consent_required", "unavailable", "conflict"]
Engine = Literal["passthrough", "ollama", "heuristic", "retrieval", "archive"]


class CGUError(Exception):
    """A domain error; the tool boundary turns it into ToolResult(ok=False)."""

    def __init__(self, code: ErrorCode, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint


class Measurement(BaseModel):
    """The only carrier of a float. No measurement procedure means no Measurement."""

    value: float
    method: str
    reference: str
    calibrated: bool = False
    n: int | None = None


class Provenance(BaseModel):
    engine: Engine
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)
    seed: int | None = None
    model: str | None = None
    version: str = __version__
    sources: list[dict[str, Any]] = Field(default_factory=list)


class WorkOrder(BaseModel):
    id: str
    kind: str
    instructions: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    submit_with: dict[str, Any] = Field(default_factory=dict)
    independence: Literal["same_context_ok", "separate_context_recommended"] = "same_context_ok"


class ErrorInfo(BaseModel):
    code: ErrorCode
    message: str
    hint: str | None = None


class Session(BaseModel):
    id: str
    topic: str
    domain: str | None = None
    language: str = "zh-TW"
    seed: int
    created_at: str
    meta: dict[str, Any] = Field(default_factory=dict)


def _is_measurement_dict(obj: dict[Any, Any]) -> bool:
    return set(obj) == set(Measurement.model_fields) and isinstance(obj.get("value"), float)


def iter_stray_floats(obj: Any, path: str = "$") -> Iterator[str]:
    """Yield the path of every float that is not inside a Measurement."""
    if isinstance(obj, Measurement):
        return
    if isinstance(obj, float):
        yield path
    elif isinstance(obj, BaseModel):
        for name in type(obj).model_fields:
            yield from iter_stray_floats(getattr(obj, name), f"{path}.{name}")
    elif isinstance(obj, dict):
        if _is_measurement_dict(obj):
            return
        for key, value in obj.items():
            yield from iter_stray_floats(value, f"{path}.{key}")
    elif isinstance(obj, list | tuple | set | frozenset):
        for index, value in enumerate(obj):
            yield from iter_stray_floats(value, f"{path}[{index}]")


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    work_order: WorkOrder | None = None
    work_orders: list[WorkOrder] = Field(default_factory=list)
    provenance: Provenance
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def _only_measurements_carry_floats(self) -> ToolResult:
        stray = list(iter_stray_floats(self))
        if stray:
            raise ValueError(f"floats outside Measurement: {stray[:5]}")
        return self

    @classmethod
    def success(
        cls,
        provenance: Provenance,
        data: dict[str, Any] | None = None,
        *,
        work_order: WorkOrder | None = None,
        work_orders: list[WorkOrder] | None = None,
    ) -> ToolResult:
        return cls(
            ok=True,
            data=data or {},
            work_order=work_order,
            work_orders=work_orders or [],
            provenance=provenance,
        )

    @classmethod
    def failure(
        cls,
        code: ErrorCode,
        message: str,
        hint: str | None = None,
        *,
        provenance: Provenance | None = None,
        data: dict[str, Any] | None = None,
    ) -> ToolResult:
        return cls(
            ok=False,
            data=data or {},
            provenance=provenance or Provenance(engine="archive"),
            error=ErrorInfo(code=code, message=message, hint=hint),
        )
