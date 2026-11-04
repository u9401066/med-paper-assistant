"""UserPromptSubmit hook: detect user intent and inject workflow guidance."""

from __future__ import annotations

import re

from .common import HookContext, HookResult, Payload, build_output, get_prompt
from .workspace import active_workflow_mode


def _intent(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


DEV_MODE_RE = _intent(r"(開發模式|development mode|dev mode)")
NORMAL_MODE_RE = _intent(r"(一般模式|normal mode|研究模式|research mode)")
COMMIT_RE = _intent(r"(commit|提交|推送|push|收工|做完了)")
LIBRARY_RE = _intent(
    r"(文獻庫|知識庫|wiki|library dashboard|knowledge map|synthesis page|閱讀隊列|reading queue|個人文獻庫)"
)
WRITING_RE = _intent(r"(寫草稿|draft|撰寫|Introduction|Methods|Results|Discussion|write section)")
AUTOPILOT_RE = _intent(r"(autopilot|全自動|一鍵|auto.?paper|從頭到尾)")
CHECKPOINT_RE = _intent(r"(存檔|checkpoint|save|要離開|暫停|pause|怕忘記)")

LIBRARY_WIKI = "library-wiki"


def _mode_switch(prompt: str) -> list[str]:
    if DEV_MODE_RE.search(prompt):
        return ["MODE SWITCH DETECTED: User wants development mode. Check .copilot-mode.json."]
    if NORMAL_MODE_RE.search(prompt):
        return ["MODE SWITCH DETECTED: User wants normal/research mode. Check .copilot-mode.json."]
    return []


def _writing(prompt: str, workflow: str) -> list[str]:
    if not WRITING_RE.search(prompt):
        return []
    if workflow == LIBRARY_WIKI:
        return [
            "WRITING INTENT IN LIBRARY-WIKI PROJECT: Confirm whether to switch workflow_mode "
            "to manuscript before applying concept-validation and draft pipeline gates."
        ]
    return ["WRITING INTENT: Remember to validate_concept() before drafting (CONSTITUTION rule)."]


def _autopilot(prompt: str, workflow: str, library_intent: bool) -> list[str]:
    if not AUTOPILOT_RE.search(prompt):
        return []
    if workflow == LIBRARY_WIKI or library_intent:
        return [
            "AUTOPILOT NOTE: The 11-phase auto-paper pipeline is manuscript-only. Stay on the "
            "library-wiki loop unless the user explicitly requests a manuscript transition."
        ]
    return ["AUTOPILOT INTENT: Load auto-paper SKILL.md. Follow 11-phase pipeline."]


def analyze_prompt(prompt: str, workflow: str) -> list[str]:
    """Context lines for a prompt, given the active project's workflow mode."""
    parts: list[str] = []
    if workflow and workflow != "null":
        parts.append(f"ACTIVE WORKFLOW MODE: {workflow}")
    parts += _mode_switch(prompt)
    if COMMIT_RE.search(prompt):
        parts.append(
            "COMMIT INTENT: Load git-precommit SKILL.md. Run G1-G9 + P1-P8 if paper files changed."
        )
    library_intent = bool(LIBRARY_RE.search(prompt))
    if library_intent:
        parts.append(
            "LIBRARY-WIKI INTENT: Prefer workflow_mode=library-wiki. Route via "
            "search/save_reference_mcp/materialize_agent_wiki or dashboards. Do not require "
            "concept validation unless the user explicitly switches to manuscript."
        )
    parts += _writing(prompt, workflow)
    parts += _autopilot(prompt, workflow, library_intent)
    if CHECKPOINT_RE.search(prompt):
        parts.append("CHECKPOINT INTENT: Load memory-checkpoint SKILL.md. Externalize context now.")
    return parts


def run(payload: Payload, ctx: HookContext) -> HookResult:
    prompt = get_prompt(payload)
    if not prompt:
        return None
    parts = analyze_prompt(prompt, active_workflow_mode(ctx.workspace_root))
    return build_output("UserPromptSubmit", "\n".join(parts)) if parts else None
