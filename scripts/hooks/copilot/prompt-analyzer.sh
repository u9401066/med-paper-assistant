#!/usr/bin/env bash
# Thin POSIX shim: the single implementation lives in hook_dispatch.py (mdpaper_hooks/).
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for py in "$here/../../../.venv/bin/python" "$here/../../../.venv/Scripts/python.exe" python3 python; do
  if command -v "$py" >/dev/null 2>&1; then exec "$py" "$here/hook_dispatch.py" prompt-analyzer; fi
done
printf '{"continue": true}\n'
exit 0
