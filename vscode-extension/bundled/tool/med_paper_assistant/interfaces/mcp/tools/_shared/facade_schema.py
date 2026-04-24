"""Machine-readable facade action schemas for agent self-inspection."""

from __future__ import annotations

import json
from typing import Any


def facade_schema_json(
    *,
    tool: str,
    actions: dict[str, dict[str, Any]],
    aliases: dict[str, str] | None = None,
    notes: list[str] | None = None,
) -> str:
    """Return a stable JSON schema describing a facade's supported actions."""
    payload = {
        "schema": "mdpaper.facade_actions.v1",
        "tool": tool,
        "actions": actions,
        "aliases": aliases or {},
        "notes": notes or [],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
