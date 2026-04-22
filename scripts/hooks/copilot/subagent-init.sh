#!/bin/bash
# =============================================================================
# SubagentStart Hook — Inject Project Context into Subagents
# =============================================================================
# Fires: when a subagent is spawned (e.g., literature-searcher, paper-reviewer).
# Purpose:
#   1. Inject active project context so subagent knows which project is active
#   2. Inject mode context so subagent respects file protection
#   3. Pass relevant state (active references, writing section, etc.)
# Chain: Main agent → SubagentStart → [subagent runs] → SubagentStop
#
# Input: { agentName?, ... }
# Output: { hookSpecificOutput: { additionalContext } }
# =============================================================================
set -e

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)
AGENT_NAME=$(echo "$INPUT" | jq -r '.agentName // "unknown"' 2>/dev/null) || AGENT_NAME="unknown"

WORKSPACE_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STATE_DIR="$WORKSPACE_ROOT/.github/hooks/_state"
mkdir -p "$STATE_DIR"

# Read current state
MODE="normal"
ACTIVE_PROJECT=""
WRITING_SECTION=""
WORKFLOW_MODE=""

MODE_FILE="$WORKSPACE_ROOT/.copilot-mode.json"
if [ -f "$MODE_FILE" ]; then
    MODE=$(jq -r '.mode // "normal"' "$MODE_FILE" 2>/dev/null) || MODE="normal"
fi

STATE_FILE="$WORKSPACE_ROOT/.mdpaper-state.json"
if [ -f "$STATE_FILE" ]; then
    ACTIVE_PROJECT=$(jq -r '.active_project // empty' "$STATE_FILE" 2>/dev/null) || true
    WRITING_SECTION=$(jq -r '.writing_session.section // empty' "$STATE_FILE" 2>/dev/null) || true
fi

if [ -z "$ACTIVE_PROJECT" ] && [ -f "$WORKSPACE_ROOT/.current_project" ]; then
    ACTIVE_PROJECT="$(tr -d '\n' < "$WORKSPACE_ROOT/.current_project")"
fi

if [ -n "$ACTIVE_PROJECT" ] && [ "$ACTIVE_PROJECT" != "null" ]; then
    PROJECT_CONFIG="$WORKSPACE_ROOT/projects/$ACTIVE_PROJECT/project.json"
    if [ -f "$PROJECT_CONFIG" ]; then
        WORKFLOW_MODE=$(jq -r '.workflow_mode // "manuscript"' "$PROJECT_CONFIG" 2>/dev/null) || WORKFLOW_MODE="manuscript"
    fi
fi

# Build subagent context
CONTEXT="[SUBAGENT CONTEXT] Agent: $AGENT_NAME | Mode: $MODE"
if [ -n "$ACTIVE_PROJECT" ]; then
    CONTEXT="$CONTEXT | Project: $ACTIVE_PROJECT"
fi
if [ -n "$WORKFLOW_MODE" ]; then
    CONTEXT="$CONTEXT | Workflow: $WORKFLOW_MODE"
fi
if [ -n "$WRITING_SECTION" ]; then
    CONTEXT="$CONTEXT | Writing: $WRITING_SECTION"
fi

# Agent-specific guidance
case "$AGENT_NAME" in
    literature-searcher)
        CONTEXT="$CONTEXT\nUse save_reference_mcp(pmid) for saving. Never use save_reference() directly."
        ;;
    paper-reviewer|domain-reviewer|methodology-reviewer|statistics-reviewer)
        CONTEXT="$CONTEXT\nRead-only mode: Do NOT modify any draft files. Produce a structured review report only."
        ;;
    reference-analyzer)
        CONTEXT="$CONTEXT\nFocus on extracting structured data from full text. Do not modify project files."
        ;;
    concept-challenger)
        CONTEXT="$CONTEXT\nBe critical and constructive. Challenge novelty claims with evidence."
        ;;
esac

if [ "$WORKFLOW_MODE" = "library-wiki" ]; then
    CONTEXT="$CONTEXT\nWORKFLOW NOTE: active project is library-wiki. Prioritize ingestion, organization, synthesis, and evidence traversal unless the user explicitly requests a manuscript transition."
fi

# Mode-specific restriction reminder
if [ "$MODE" = "normal" ] || [ "$MODE" = "research" ]; then
    CONTEXT="$CONTEXT\nMODE RESTRICTION: $MODE mode — .claude/, .github/, src/, tests/ are read-only."
fi

jq -n \
    --arg ctx "$CONTEXT" \
    '{
        hookSpecificOutput: {
            hookEventName: "SubagentStart",
            additionalContext: $ctx
        }
    }'
exit 0
