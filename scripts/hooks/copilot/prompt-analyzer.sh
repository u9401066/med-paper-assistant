#!/bin/bash
# =============================================================================
# UserPromptSubmit Hook — Intent Detection & Mode Enforcement
# =============================================================================
# Fires: when user submits a prompt.
# Purpose:
#   1. Detect research intent → inject workflow guidance
#   2. Detect mode-switch requests → remind to update .copilot-mode.json
#   3. Detect commit intent → remind pre-commit hooks
# Chain: [SessionStart] → UserPromptSubmit → [PreToolUse] → ...
# =============================================================================
set -e

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null) || exit 0
if [ -z "$PROMPT" ]; then exit 0; fi

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STATE_DIR="$WORKSPACE_ROOT/.github/hooks/_state"
mkdir -p "$STATE_DIR"

CONTEXT_PARTS=()

get_active_workflow_mode() {
    local active_project=""

    if [ -f "$WORKSPACE_ROOT/.current_project" ]; then
        active_project="$(tr -d '\n' < "$WORKSPACE_ROOT/.current_project")"
    fi

    if [ -z "$active_project" ] && [ -f "$WORKSPACE_ROOT/.mdpaper-state.json" ]; then
        active_project=$(jq -r '.active_project // empty' "$WORKSPACE_ROOT/.mdpaper-state.json" 2>/dev/null) || true
    fi

    if [ -z "$active_project" ] || [ "$active_project" = "null" ]; then
        return 0
    fi

    local config="$WORKSPACE_ROOT/projects/$active_project/project.json"
    if [ -f "$config" ]; then
        jq -r '.workflow_mode // "manuscript"' "$config" 2>/dev/null || true
    fi
}

ACTIVE_WORKFLOW_MODE="$(get_active_workflow_mode)"
if [ -n "$ACTIVE_WORKFLOW_MODE" ] && [ "$ACTIVE_WORKFLOW_MODE" != "null" ]; then
    CONTEXT_PARTS+=("ACTIVE WORKFLOW MODE: $ACTIVE_WORKFLOW_MODE")
fi

# --- 1. Detect mode-switch intent ---
if echo "$PROMPT" | grep -qiE '(開發模式|development mode|dev mode)'; then
    CONTEXT_PARTS+=("MODE SWITCH DETECTED: User wants development mode. Check .copilot-mode.json.")
elif echo "$PROMPT" | grep -qiE '(一般模式|normal mode|研究模式|research mode)'; then
    CONTEXT_PARTS+=("MODE SWITCH DETECTED: User wants normal/research mode. Check .copilot-mode.json.")
fi

# --- 2. Detect commit intent → chain to git-precommit skill ---
if echo "$PROMPT" | grep -qiE '(commit|提交|推送|push|收工|做完了)'; then
    CONTEXT_PARTS+=("COMMIT INTENT: Load git-precommit SKILL.md. Run G1-G9 + P1-P8 if paper files changed.")
fi

# --- 3. Detect library/wiki intent ---
LIBRARY_INTENT=0
if echo "$PROMPT" | grep -qiE '(文獻庫|知識庫|wiki|library dashboard|knowledge map|synthesis page|閱讀隊列|reading queue|個人文獻庫)'; then
    LIBRARY_INTENT=1
    CONTEXT_PARTS+=("LIBRARY-WIKI INTENT: Prefer workflow_mode=library-wiki. Route via search/save_reference_mcp/materialize_agent_wiki or dashboards. Do not require concept validation unless the user explicitly switches to manuscript.")
fi

# --- 4. Detect writing intent → remind concept validation ---
if echo "$PROMPT" | grep -qiE '(寫草稿|draft|撰寫|Introduction|Methods|Results|Discussion|write section)'; then
    if [ "$ACTIVE_WORKFLOW_MODE" = "library-wiki" ]; then
        CONTEXT_PARTS+=("WRITING INTENT IN LIBRARY-WIKI PROJECT: Confirm whether to switch workflow_mode to manuscript before applying concept-validation and draft pipeline gates.")
    else
        CONTEXT_PARTS+=("WRITING INTENT: Remember to validate_concept() before drafting (CONSTITUTION rule).")
    fi
fi

# --- 5. Detect autopilot intent ---
if echo "$PROMPT" | grep -qiE '(autopilot|全自動|一鍵|auto.?paper|從頭到尾)'; then
    if [ "$ACTIVE_WORKFLOW_MODE" = "library-wiki" ] || [ "$LIBRARY_INTENT" -eq 1 ]; then
        CONTEXT_PARTS+=("AUTOPILOT NOTE: The 11-phase auto-paper pipeline is manuscript-only. Stay on the library-wiki loop unless the user explicitly requests a manuscript transition.")
    else
        CONTEXT_PARTS+=("AUTOPILOT INTENT: Load auto-paper SKILL.md. Follow 11-phase pipeline.")
    fi
fi

# --- 6. Detect checkpoint/memory intent ---
if echo "$PROMPT" | grep -qiE '(存檔|checkpoint|save|要離開|暫停|pause|怕忘記)'; then
    CONTEXT_PARTS+=("CHECKPOINT INTENT: Load memory-checkpoint SKILL.md. Externalize context now.")
fi

# --- Output ---
if [ ${#CONTEXT_PARTS[@]} -eq 0 ]; then
    exit 0
fi

CONTEXT=""
for PART in "${CONTEXT_PARTS[@]}"; do
    CONTEXT="${CONTEXT}${PART}\n"
done

jq -n \
    --arg ctx "$(echo -e "$CONTEXT")" \
    '{
        hookSpecificOutput: {
            hookEventName: "UserPromptSubmit",
            additionalContext: $ctx
        }
    }'
