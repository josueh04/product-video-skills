#!/usr/bin/env bash
# SessionStart hook: a 3 to 5 line status for the model (setup state, the product and video of
# the current folder, the next command), and PVS_HOME for every Bash call of the session.
# Never fails the session: any error ends in a one-line fallback.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
home="$(cd "$here/../.." && pwd)"

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  printf 'export PVS_HOME=%q\n' "$home" >> "$CLAUDE_ENV_FILE" 2>/dev/null || true
fi

cwd="$(python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("cwd") or "")
except Exception: print("")' 2>/dev/null)"
[ -n "$cwd" ] && [ -d "$cwd" ] || cwd="${CLAUDE_PROJECT_DIR:-$PWD}"

out="$(PVS_HOME="$home" "$home/bin/pvs-py" "$home/skills/video-ask/scripts/status.py" "$cwd" --short 2>/dev/null)"
if [ -n "$out" ]; then
  printf '%s\n' "$out"
else
  echo "Product Video Skills workbench at $home. Setup state unknown (status script failed). Next: /video-setup"
fi
echo "Workbench rules: $home/CLAUDE.md. Help at any point: /video-ask"
exit 0
