#!/usr/bin/env bash
# Build the example video (examples/acme, video "tour") in a throwaway folder and, unless
# --draft, voice it, render it, run QA on it and deliver it. Used by setup.sh and
# tests/cases/example.sh. Nothing is written inside the workbench.
#
#   bash scripts/example-chain.sh [--draft] [--dir DIR] [--keep]
#
#   --draft   fast: fetch sources, check the truth table, draft build and motion lint (no voice, no render)
#   --dir     where to put the copy (default: a new temp folder)
#   --keep    keep the folder after a --draft run (a full run always keeps it, for the MP4)
#
# Last lines on success: "mp4 <path>" and "qa passed" (full), or "draft built" (--draft).
# The voice is macOS `say` (product.yaml voice.provider), so no key is needed.
set -uo pipefail

WB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PY="$WB/bin/pvs-py"
DRAFT=0; KEEP=0; DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --draft) DRAFT=1 ;;
    --keep) KEEP=1 ;;
    --dir) DIR="$2"; shift ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$DIR" ] || DIR="$(mktemp -d "${TMPDIR:-/tmp}/pvs-example.XXXXXX")"
P="$DIR/acme"; V="$P/videos/tour"
PIN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dependencies"]["hyperframes"].lstrip("^~="))' "$WB/package.json")"
if [ -x "$WB/node_modules/.bin/hyperframes" ]; then HF=("$WB/node_modules/.bin/hyperframes"); else HF=(npx --yes "hyperframes@$PIN"); fi

now() { python3 -c 'import time; print("%.2f" % time.time())'; }
T0="$(now)"
step() {  # step <label> <command...>: run quietly, print the label and its time, stop on failure
  local label="$1"; shift
  local t0 out rc
  t0="$(now)"
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" != 0 ]; then
    printf '  FAIL %-12s (exit %s)\n' "$label" "$rc"
    printf '%s\n' "$out" | tail -20 | sed 's/^/       /'
    echo "  kept $DIR for inspection"
    exit 1
  fi
  printf '  ok   %-12s %5.1f s\n' "$label" "$(python3 -c 'import sys; print(float(sys.argv[2]) - float(sys.argv[1]))' "$t0" "$(now)")"
}

[ -e "$P" ] && { echo "$P already exists" >&2; exit 1; }
mkdir -p "$DIR"
# The same copy /product-new --from examples/acme makes, without git or skill links.
step copy "$PY" "$WB/skills/product-new/scripts/new_product.py" acme --from examples/acme --dest "$DIR" --no-git --no-link
step sources "$PY" "$WB/skills/source-recon/scripts/fetch_sources.py" "$P"
step truth "$PY" "$WB/skills/product-truth/scripts/truth_check.py" "$V"
if [ "$DRAFT" = 1 ]; then
  step build "$PY" "$V/video/build.py" --draft --quiet
  step lint "$PY" "$WB/skills/seek-safe-motion/scripts/lint_motion.py" "$V/video"
  [ "$KEEP" = 1 ] || { chmod -R u+w "$DIR"; rm -rf "$DIR"; }   # sources/ is read-only
  echo "draft built in $(python3 -c 'import sys; print("%.1f" % (float(sys.argv[2]) - float(sys.argv[1])))' "$T0" "$(now)") s"
  exit 0
fi
MP4="$V/video/renders/tour-v1.mp4"
step voice "$PY" "$WB/skills/script-and-voice/scripts/tts.py" "$V" --provider say
step build "$PY" "$V/video/build.py" --quiet
step lint "$PY" "$WB/skills/seek-safe-motion/scripts/lint_motion.py" "$V/video"
step render bash -c 'cd "$1/video" && shift && "$@" render . -o renders/tour-v1.mp4 --fps 30 --quality standard --quiet' _ "$V" "${HF[@]}"
step qa "$PY" "$WB/skills/render-qa/scripts/qa.py" "$V" "$MP4"
step deliver "$PY" "$WB/skills/render-qa/scripts/deliver.py" "$V" "$MP4"
python3 - "$V/qa/REPORT.json" <<'PY' || exit 1
import json, sys
r = json.load(open(sys.argv[1]))
ok = r.get("passed") is True and r.get("draft") is False
print("  report: passed=%s draft=%s, %d checks" % (r.get("passed"), r.get("draft"), len(r.get("checks", []))))
sys.exit(0 if ok else 1)
PY
echo "done in $(python3 -c 'import sys; print("%.1f" % (float(sys.argv[2]) - float(sys.argv[1])))' "$T0" "$(now)") s"
echo "folder $DIR (the full run keeps it; delete it when done)"
echo "mp4 $(ls "$P"/deliveries/*.mp4)"
echo "qa passed"
