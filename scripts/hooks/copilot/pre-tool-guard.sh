#!/bin/bash
# =============================================================================
# PreToolUse Hook — Mode-Based File Protection & Safety Guard
# =============================================================================
# Fires: before agent invokes any tool.
# Purpose:
#   1. In normal/research mode → DENY writes to protected paths
#   2. Block destructive operations (rm -rf, DROP TABLE, etc.)
#   3. Enforce save_reference_mcp over save_reference
#   4. Track tool invocation for audit
# Chain: ... → PreToolUse → [tool executes] → PostToolUse → ...
#
# Input: { tool_name, tool_input, tool_use_id, ... }
# Output: { hookSpecificOutput: { permissionDecision, permissionDecisionReason } }
# =============================================================================
set -e

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
if [ -z "$TOOL_NAME" ]; then exit 0; fi

TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}' 2>/dev/null) || TOOL_INPUT="{}"

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STATE_DIR="$WORKSPACE_ROOT/.github/hooks/_state"
mkdir -p "$STATE_DIR"
CROSS_PLATFORM_REGEX='(^|/)(\.github/workflows/|vscode-extension/|scripts/setup(\.ps1|\.sh)?$|scripts/setup-integrations(\.ps1|\.sh)$|scripts/start-drawio(\.ps1|\.sh)$|src/med_paper_assistant/infrastructure/config\.py$|src/med_paper_assistant/infrastructure/services/template_reader\.py$|tests/test_config_paths\.py$)'

recent_cross_platform_changes() {
    {
        git diff --name-only --cached 2>/dev/null || true
        git diff --name-only 2>/dev/null || true
        git diff --name-only HEAD~1..HEAD 2>/dev/null || true
    } | awk 'NF' | sort -u | grep -E "$CROSS_PLATFORM_REGEX" || true
}

# Read current mode
MODE="normal"
SESSION_CTX="$STATE_DIR/session_context.json"
if [ -f "$SESSION_CTX" ]; then
    MODE=$(jq -r '.mode // "normal"' "$SESSION_CTX" 2>/dev/null) || MODE="normal"
fi
MODE_FILE="$WORKSPACE_ROOT/.copilot-mode.json"
if [ -f "$MODE_FILE" ]; then
    MODE=$(jq -r '.mode // "normal"' "$MODE_FILE" 2>/dev/null) || MODE="normal"
fi

# ── 1. Mode-based file protection (normal/research) ──
if [ "$MODE" = "normal" ] || [ "$MODE" = "research" ]; then
    # Check file-editing tools
    if echo "$TOOL_NAME" | grep -qiE 'editFiles|create_file|replace_string|multi_replace|write_file'; then
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.filePath // .path // .file // empty' 2>/dev/null) || true

        if [ -n "$FILE_PATH" ]; then
            # Protected paths in normal/research mode
            if echo "$FILE_PATH" | grep -qE '(\.claude/|\.github/|src/|tests/|integrations/|AGENTS\.md|CONSTITUTION\.md|ARCHITECTURE\.md|pyproject\.toml)'; then
                jq -n \
                    --arg reason "PROTECTED PATH in $MODE mode: '$FILE_PATH' is read-only. Switch to development mode first." \
                    '{
                        hookSpecificOutput: {
                            hookEventName: "PreToolUse",
                            permissionDecision: "deny",
                            permissionDecisionReason: $reason
                        }
                    }'
                exit 0
            fi
        fi
    fi
fi

# ── 2. Block destructive terminal commands ──
if echo "$TOOL_NAME" | grep -qiE 'run_in_terminal|terminal'; then
    COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null) || true

    if [ -n "$COMMAND" ]; then
        # Block dangerous patterns
        if echo "$COMMAND" | grep -qE '(rm\s+-rf\s+/|DROP\s+TABLE|DROP\s+DATABASE|--no-verify|--force\s+push|git\s+push\s+--force)'; then
            jq -n \
                --arg reason "DESTRUCTIVE COMMAND BLOCKED: '$COMMAND'. This operation is potentially dangerous and requires explicit user approval." \
                '{
                    hookSpecificOutput: {
                        hookEventName: "PreToolUse",
                        permissionDecision: "deny",
                        permissionDecisionReason: $reason
                    }
                }'
            exit 0
        fi

        # Require confirmation for git push
        if echo "$COMMAND" | grep -qE '(git\s+push|git\s+reset\s+--hard|git\s+tag\s+v[0-9])'; then
            RECENT_CROSS_PLATFORM=$(recent_cross_platform_changes)
            if [ -n "$RECENT_CROSS_PLATFORM" ]; then
                jq -n \
                    --arg reason "RELEASE/PUSH CHECK: recent cross-platform or installation files changed. Confirm CI smoke matrix passed before running '$COMMAND'." \
                    --arg changed "$RECENT_CROSS_PLATFORM" \
                    '{
                        hookSpecificOutput: {
                            hookEventName: "PreToolUse",
                            permissionDecision: "ask",
                            permissionDecisionReason: $reason,
                            additionalContext: ("Changed files requiring smoke evidence:\n" + $changed)
                        }
                    }'
                exit 0
            fi

            jq -n \
                --arg reason "GIT OPERATION requires confirmation: '$COMMAND'" \
                '{
                    hookSpecificOutput: {
                        hookEventName: "PreToolUse",
                        permissionDecision: "ask",
                        permissionDecisionReason: $reason
                    }
                }'
            exit 0
        fi
    fi
fi

# ── 3. Enforce save_reference_mcp priority ──
if echo "$TOOL_NAME" | grep -qiE 'mcp_mdpaper_save_reference$'; then
    # save_reference (not save_reference_mcp) → warn
    if ! echo "$TOOL_NAME" | grep -qiE 'save_reference_mcp'; then
        jq -n '{
            hookSpecificOutput: {
                hookEventName: "PreToolUse",
                permissionDecision: "ask",
                permissionDecisionReason: "CONSTITUTION RULE: Use save_reference_mcp(pmid) instead of save_reference(). save_reference is only for fallback when API is unavailable.",
                additionalContext: "save_reference_mcp fetches verified data directly from PubMed API, preventing metadata corruption."
            }
        }'
        exit 0
    fi
fi

# ── 4. Log tool invocation (non-blocking) ──
jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg tool "$TOOL_NAME" \
    --arg event "pre_tool_use" \
    '{timestamp: $timestamp, event: $event, tool: $tool}' \
    >> "$STATE_DIR/session_audit.jsonl" 2>/dev/null || true

# Default: allow
exit 0
