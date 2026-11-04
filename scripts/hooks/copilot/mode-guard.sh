#!/usr/bin/env bash
# Fail-open PreToolUse launcher for scripts/copilot_hook_guard.py (POSIX).
# Never use `uv run` here: it can re-resolve uv.lock or block on a busy .venv,
# which turns every hook invocation into an error and blocks all tools.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
script="$root/scripts/copilot_hook_guard.py"
payload="$(cat)"

for candidate in "$root/.venv/bin/python" python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if output="$(printf '%s' "$payload" | "$candidate" "$script" 2>/dev/null)" && [ -n "$output" ]; then
      printf '%s\n' "$output"
      exit 0
    fi
  fi
done

printf '{"continue": true}\n'
exit 0
