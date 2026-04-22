#!/bin/bash
# =============================================================================
# SessionStart Hook — MedPaper Workspace Initializer
# =============================================================================
# Fires: when a new agent session begins.
# Purpose:
#   1. Read .copilot-mode.json → inject mode context
#   2. Check .mdpaper-state.json → inject recovery context
#   3. Check pending evolutions → remind agent
#   4. Detect active project → inject project context
# Output: JSON { hookSpecificOutput: { additionalContext: "..." } }
# Chain: SessionStart → [UserPromptSubmit] → ...
# =============================================================================
set -e

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

# --- Dependency check ---
if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)

STATE_DIR="$WORKSPACE_ROOT/.github/hooks/_state"
mkdir -p "$STATE_DIR"

# Clear stale state
rm -f "$STATE_DIR/session_context.json" 2>/dev/null

CONTEXT_PARTS=()
WORKFLOW_MODE=""

# --- 1. Read mode ---
MODE_FILE="$WORKSPACE_ROOT/.copilot-mode.json"
if [ -f "$MODE_FILE" ]; then
    MODE=$(jq -r '.mode // "normal"' "$MODE_FILE" 2>/dev/null) || MODE="normal"
    CONTEXT_PARTS+=("MODE: $MODE")

    if [ "$MODE" = "development" ]; then
        CONTEXT_PARTS+=("All skills enabled. Static analysis ON.")
    elif [ "$MODE" = "research" ] || [ "$MODE" = "normal" ]; then
        CONTEXT_PARTS+=("Research skills only. Protected paths: .claude/ .github/ src/ tests/ AGENTS.md CONSTITUTION.md pyproject.toml")
    fi
fi

# --- 2. Check workspace state ---
STATE_FILE="$WORKSPACE_ROOT/.mdpaper-state.json"
if [ -f "$STATE_FILE" ]; then
    DOING=$(jq -r '.doing // empty' "$STATE_FILE" 2>/dev/null) || true
    NEXT=$(jq -r '.next_action // empty' "$STATE_FILE" 2>/dev/null) || true
    ACTIVE_PROJECT=$(jq -r '.active_project // empty' "$STATE_FILE" 2>/dev/null) || true

    if [ -n "$DOING" ] && [ "$DOING" != "null" ]; then
        CONTEXT_PARTS+=("RECOVERY: Was doing '$DOING'")
    fi
    if [ -n "$NEXT" ] && [ "$NEXT" != "null" ]; then
        CONTEXT_PARTS+=("NEXT ACTION: $NEXT")
    fi
    if [ -n "$ACTIVE_PROJECT" ] && [ "$ACTIVE_PROJECT" != "null" ]; then
        CONTEXT_PARTS+=("ACTIVE PROJECT: $ACTIVE_PROJECT")
    fi

    # Check writing session
    HAS_WRITING=$(jq -r '.writing_session // empty' "$STATE_FILE" 2>/dev/null) || true
    if [ -n "$HAS_WRITING" ] && [ "$HAS_WRITING" != "null" ] && [ "$HAS_WRITING" != "{}" ]; then
        WS_SECTION=$(jq -r '.writing_session.section // empty' "$STATE_FILE" 2>/dev/null) || true
        if [ -n "$WS_SECTION" ] && [ "$WS_SECTION" != "null" ]; then
            CONTEXT_PARTS+=("WRITING SESSION: section=$WS_SECTION (call get_workspace_state() for details)")
        fi
    fi
fi

# --- 3. Check pending evolutions ---
EVOL_FILE="$WORKSPACE_ROOT/.audit/pending-evolutions.yaml"
if [ -f "$EVOL_FILE" ]; then
    EVOL_COUNT=$(grep -c "^  - id:" "$EVOL_FILE" 2>/dev/null) || EVOL_COUNT=0
    if [ "$EVOL_COUNT" -gt 0 ]; then
        CONTEXT_PARTS+=("PENDING EVOLUTIONS: $EVOL_COUNT items (call get_workspace_state() for details)")
    fi
fi

# --- 4. Detect active project ---
PROJECTS_DIR="$WORKSPACE_ROOT/projects"
if [ -d "$PROJECTS_DIR" ]; then
    PROJECT_COUNT=$(find "$PROJECTS_DIR" -maxdepth 1 -mindepth 1 -type d ! -name 'temp-*' | wc -l)
    CONTEXT_PARTS+=("PROJECTS: $PROJECT_COUNT active")
fi

if [ -z "$ACTIVE_PROJECT" ] && [ -f "$WORKSPACE_ROOT/.current_project" ]; then
    ACTIVE_PROJECT="$(tr -d '\n' < "$WORKSPACE_ROOT/.current_project")"
fi

if [ -n "$ACTIVE_PROJECT" ] && [ "$ACTIVE_PROJECT" != "null" ]; then
    PROJECT_CONFIG="$WORKSPACE_ROOT/projects/$ACTIVE_PROJECT/project.json"
    if [ -f "$PROJECT_CONFIG" ]; then
        WORKFLOW_MODE=$(jq -r '.workflow_mode // "manuscript"' "$PROJECT_CONFIG" 2>/dev/null) || WORKFLOW_MODE="manuscript"
        CONTEXT_PARTS+=("WORKFLOW MODE: $WORKFLOW_MODE")
    fi
fi

# --- Build output ---
if [ ${#CONTEXT_PARTS[@]} -eq 0 ]; then
    exit 0
fi

CONTEXT=""
for PART in "${CONTEXT_PARTS[@]}"; do
    CONTEXT="${CONTEXT}${PART}\n"
done

# Log session start
jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg event "session_start" \
    --arg mode "${MODE:-unknown}" \
    '{timestamp: $timestamp, event: $event, mode: $mode}' \
    >> "$STATE_DIR/session_audit.jsonl" 2>/dev/null || true

# Save session context for other hooks
jq -n \
    --arg mode "${MODE:-normal}" \
    --arg active_project "${ACTIVE_PROJECT:-}" \
    --arg workflow_mode "${WORKFLOW_MODE:-}" \
    --arg started_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{mode: $mode, active_project: $active_project, workflow_mode: $workflow_mode, started_at: $started_at}' \
    > "$STATE_DIR/session_context.json" 2>/dev/null || true

# Output additionalContext
jq -n \
    --arg ctx "$(echo -e "$CONTEXT")" \
    '{
        hookSpecificOutput: {
            hookEventName: "SessionStart",
            additionalContext: $ctx
        }
    }'
