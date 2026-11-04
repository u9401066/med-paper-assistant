"""Shared types for the review facade."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

ToolMap = Mapping[str, Callable[..., Any]]


@dataclass(frozen=True)
class QualityTools:
    """Tool groups the ``run_quality_checks`` facade dispatches to."""

    audit_tools: ToolMap
    formatting_tools: ToolMap
    health_tools: ToolMap
    constraint_tools: ToolMap
