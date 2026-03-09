#!/bin/bash
# =============================================================================
# PostToolUse Hook — Writing Hooks Trigger & Quality Feedback
# =============================================================================
# Fires: after a tool completes successfully.
# Purpose:
#   1. After draft edits → inject reminder to run writing hooks (A1-A6, A3b)
#   2. After write_draft/patch_draft → remind run_writing_hooks(hooks='post-write')
#   3. After file creation/edit in projects/ → remind validate_wikilinks
#   4. After git commit → remind pre-commit checks
#   5. Audit trail: log tool result metadata
# Chain: ... → [tool executed] → PostToolUse → (next tool) → PreToolUse → ...
#
# Input: { tool_name, tool_input, tool_use_id, tool_result, ... }
# Output: { hookSpecificOutput: { additionalContext, decision? } }
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

CONTEXT=""
CROSS_PLATFORM_REGEX='(^|/)(\.github/workflows/|vscode-extension/|scripts/setup(\.ps1|\.sh)?$|scripts/setup-integrations(\.ps1|\.sh)$|scripts/start-drawio(\.ps1|\.sh)$|src/med_paper_assistant/infrastructure/config\.py$|src/med_paper_assistant/infrastructure/services/template_reader\.py$|tests/test_config_paths\.py$)'

extract_paths_from_patch() {
    echo "$TOOL_INPUT" | jq -r '.input // empty' 2>/dev/null | \
        grep -E '^\*\*\* (Update|Add|Delete) File:' | \
        sed -E 's/^\*\*\* (Update|Add|Delete) File: //' | \
        cut -d' ' -f1
}

# ── 1. After MCP write_draft / patch_draft / draft_section ──
if echo "$TOOL_NAME" | grep -qiE 'mcp_mdpaper_(write_draft|patch_draft|draft_section)'; then
    CONTEXT="[WRITING HOOKS REQUIRED] Draft modified via $TOOL_NAME. You MUST run run_writing_hooks(hooks='post-write') to check A1-A6 + A3b before proceeding. This is Code-Enforced and cannot be skipped."
fi

# ── 2. After file edits to draft files ──
if echo "$TOOL_NAME" | grep -qiE 'apply_patch|editFiles|replace_string|multi_replace|create_file'; then
    FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.filePath // .path // empty' 2>/dev/null) || true

    if [ -n "$FILE_PATH" ]; then
        # Draft file edited directly (bypass MCP tool)
        if echo "$FILE_PATH" | grep -qE 'projects/.*/drafts/.*\.md$'; then
            if [ -z "$CONTEXT" ]; then
                CONTEXT="[WRITING HOOKS REQUIRED] Draft file '$FILE_PATH' was edited directly. Run run_writing_hooks(hooks='post-write') to check A1-A6 + A3b."
            fi
        fi

        # Concept file edited
        if echo "$FILE_PATH" | grep -qE 'projects/.*/concept\.md$'; then
            CONTEXT="[CONCEPT CHANGED] concept.md was modified. Remember: validate_concept() must pass (novelty ≥ 75) before any draft writing."
        fi

        # Project config edited
        if echo "$FILE_PATH" | grep -qE 'projects/.*/\.project\.yaml$'; then
            CONTEXT="[PROJECT CONFIG CHANGED] .project.yaml was modified. Run get_current_project() to verify the changes are correct."
        fi

        # Hook/config files edited
        if echo "$FILE_PATH" | grep -qE '\.(copilot-mode|mdpaper-state)\.json$'; then
            CONTEXT="[STATE FILE CHANGED] Mode or workspace state was updated. The next SessionStart hook will pick up these changes."
        fi

        if echo "$FILE_PATH" | grep -qE "$CROSS_PLATFORM_REGEX"; then
            CONTEXT="[CROSS-PLATFORM SMOKE ADVISED] You changed installation, workflow, extension, or path-resolution code at '$FILE_PATH'. Before wrapping up, run the focused smoke checks or ensure the GitHub Actions cross-platform smoke matrix covers this change."
        fi
    fi

    if [ -z "$FILE_PATH" ] && echo "$TOOL_NAME" | grep -qiE 'apply_patch'; then
        PATCH_PATHS=$(extract_paths_from_patch || true)
        if [ -n "$PATCH_PATHS" ] && echo "$PATCH_PATHS" | grep -qE "$CROSS_PLATFORM_REGEX"; then
            CONTEXT="[CROSS-PLATFORM SMOKE ADVISED] You modified installation, workflow, extension, or path-resolution files via apply_patch. Before wrapping up, run focused smoke tests or confirm the GitHub Actions cross-platform smoke matrix covers this change."
        fi
    fi
fi

# ── 3. After insert_citation / sync_references ──
if echo "$TOOL_NAME" | grep -qiE 'mcp_mdpaper_insert_citation'; then
    CONTEXT="[CITATION ADDED] After inserting citations, remember to run sync_references() when done to generate the References section."
fi

# ── 4. After save_reference / save_reference_mcp ──
if echo "$TOOL_NAME" | grep -qiE 'mcp_mdpaper_save_reference'; then
    CONTEXT="[REFERENCE SAVED] Reference saved. Use get_available_citations() to see citation keys for use in drafts."
fi

# ── 5. After git commit ──
if echo "$TOOL_NAME" | grep -qiE 'run_in_terminal|terminal'; then
    COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null) || true
    if echo "$COMMAND" | grep -qE 'git\s+commit'; then
        CONTEXT="[POST-COMMIT] Git commit detected. Remember to: 1) Update memory-bank (progress.md, activeContext.md), 2) sync_workspace_state, 3) Consider CHANGELOG update."
    fi
fi

# ── 6. After validate_concept ──
if echo "$TOOL_NAME" | grep -qiE 'mcp_mdpaper_validate_concept$'; then
    CONTEXT="[CONCEPT VALIDATED] Check the novelty score. If < 75, concept needs improvement before drafting. Consider CGU tools (deep_think, spark_collision) for enhancement."
fi

# ── 7. Audit trail ──
jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg tool "$TOOL_NAME" \
    --arg event "post_tool_use" \
    '{timestamp: $timestamp, event: $event, tool: $tool}' \
    >> "$STATE_DIR/session_audit.jsonl" 2>/dev/null || true

# Emit context if any
if [ -n "$CONTEXT" ]; then
    jq -n \
        --arg ctx "$CONTEXT" \
        '{
            hookSpecificOutput: {
                hookEventName: "PostToolUse",
                additionalContext: $ctx
            }
        }'
    exit 0
fi

# Default: no additional context
exit 0
