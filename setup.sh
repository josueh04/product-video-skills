#!/usr/bin/env bash
# Install and check everything the workbench needs. Safe to run again: each step skips what is
# already in place.
#
#   bash setup.sh            check, say what will be downloaded, ask, install, self-check
#   bash setup.sh --yes      same, without asking (what /video-setup runs after you approve)
#   bash setup.sh --check    report only: installs nothing, downloads nothing, writes nothing
#   bash setup.sh --no-example   skip the last step (render the example video and run QA on it)
#
# Every step prints one line: ok, fixed, or FAIL with the exact fix. Nothing here reads or
# prints the content of .env.
set -uo pipefail

WB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$WB" || exit 1

MODE=install
YES=0
EXAMPLE=1
for a in "$@"; do
  case "$a" in
    --check|check) MODE=check ;;
    --yes|-y) YES=1 ;;
    --no-example) EXAMPLE=0 ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $a (use --check, --yes, --no-example or --help)"; exit 2 ;;
  esac
done

FAILS=0
ok()    { printf '  %-6s %s\n' ok "$1"; }
fixed() { printf '  %-6s %s\n' fixed "$1"; }
warn()  { printf '  %-6s %s\n' warn "$1"; }
fail()  { printf '  %-6s %s\n' FAIL "$1"; FAILS=$((FAILS+1)); }
now()   { python3 -c 'import time; print("%.3f" % time.time())' 2>/dev/null || date +%s; }
took()  { python3 -c 'import sys; print("%.1f s" % (float(sys.argv[2]) - float(sys.argv[1])))' "$1" "$(now)" 2>/dev/null || echo "?"; }
T_START="$(now)"
LOG="${TMPDIR:-/tmp}/pvs-setup.$$.log"
: > "$LOG" 2>/dev/null || LOG=/dev/null
OS="$(uname -s)"
HF_BIN="$WB/node_modules/.bin/hyperframes"
export HYPERFRAMES_SKIP_SKILLS=1   # the skills come from vendor/ at the pinned tag, never from a live update

if [ "$MODE" = check ]; then echo "Checking the workbench at $WB (report only)"; else echo "Setting up the workbench at $WB"; fi

# ---------------------------------------------------------------- 1. the machine
echo "Machine"
case "$OS" in
  Darwin) ok "macOS $(sw_vers -productVersion 2>/dev/null)" ;;
  Linux)  ok "Linux (untested: everything except OCR of screen recordings should work)" ;;
  *)      fail "unsupported system $OS. Fix: use macOS or Linux (on Windows, WSL2)" ;;
esac

if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
  if [ "${NODE_MAJOR:-0}" -ge 22 ] 2>/dev/null; then ok "node $(node -v)"
  else fail "node $(node -v) is older than 22. Fix: brew install node (macOS) or nvm install 22"; fi
else
  fail "node not found. Fix: brew install node (macOS), or install Node 22+ from nodejs.org or with nvm"
fi
command -v npm >/dev/null 2>&1 || fail "npm not found. Fix: reinstall Node 22+ (npm ships with it)"

if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
  if python3 -c 'import venv, ensurepip' 2>/dev/null; then ok "python $(python3 -c 'import platform; print(platform.python_version())')"
  else fail "python3 has no venv module. Fix: sudo apt install python3-venv (Debian, Ubuntu)"; fi
else
  fail "python 3.9+ not found. Fix: xcode-select --install (macOS ships 3.9) or brew install python"
fi

for t in ffmpeg ffprobe; do
  if command -v "$t" >/dev/null 2>&1; then ok "$t $("$t" -version 2>/dev/null | head -1 | awk '{print $3}')"
  elif [ "$OS" = Darwin ]; then fail "$t not found. Fix: brew install ffmpeg"
  else fail "$t not found. Fix: sudo apt install ffmpeg"; fi
done

if command -v git >/dev/null 2>&1; then ok "git $(git --version | awk '{print $3}')"
elif [ "$OS" = Darwin ]; then fail "git not found. Fix: xcode-select --install"
else fail "git not found. Fix: sudo apt install git"; fi

if command -v claude >/dev/null 2>&1; then
  CV="$(claude --version 2>/dev/null | awk '{print $1}')"
  if python3 -c 'import sys; v=[int(x) for x in sys.argv[1].split(".")[:2]]; sys.exit(0 if v >= [2, 1] else 1)' "${CV:-0.0}" 2>/dev/null; then ok "Claude Code $CV"
  else warn "Claude Code ${CV:-unknown} is older than 2.1. Fix: claude update"; fi
else
  warn "Claude Code not found (setup works without it, the skills need it). Fix: npm install -g @anthropic-ai/claude-code"
fi

if [ "$FAILS" -gt 0 ]; then
  echo "Fix the FAIL lines above, then run bash setup.sh again."
  exit 1
fi

PIN="$(python3 -c 'import json; print(json.load(open("package.json"))["dependencies"]["hyperframes"].lstrip("^~="))' 2>/dev/null)"
if [ -z "$PIN" ]; then echo "  FAIL   package.json does not pin hyperframes. Fix: restore package.json from git"; exit 1; fi
TAG="v$PIN"
WHISPER_PT="${XDG_CACHE_HOME:-$HOME/.cache}/whisper/small.en.pt"
REQ_HASH="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' requirements.txt)"

# ---------------------------------------------------------------- state probes (read only)
hf_installed() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' node_modules/hyperframes/package.json 2>/dev/null; }
chrome_path()  { [ -x "$HF_BIN" ] || return 1; local p; p="$("$HF_BIN" browser path 2>/dev/null | tail -1)"; [ -n "$p" ] && [ -e "$p" ] && echo "$p"; }
vendor_tag()   { [ -d vendor/hyperframes/.git ] && git -C vendor/hyperframes describe --tags --exact-match 2>/dev/null; }
venv_ok()      { [ -x .venv/bin/python ] && .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; }
pip_ok()       { venv_ok && [ "$(cat .venv/.requirements.sha256 2>/dev/null)" = "$REQ_HASH" ] \
                   && .venv/bin/python -c 'import numpy, PIL, yaml, fontTools, brotli, whisper' 2>/dev/null; }
whisper_ok()   { [ -f "$WHISPER_PT" ] && [ "$(wc -c < "$WHISPER_PT" | tr -d ' ')" -gt 400000000 ]; }

NEED_NPM=0; [ "$(hf_installed)" = "$PIN" ] || NEED_NPM=1
NEED_CHROME=0; chrome_path >/dev/null || NEED_CHROME=1
NEED_VENDOR=0; [ "$(vendor_tag)" = "$TAG" ] || NEED_VENDOR=1
NEED_PIP=0; pip_ok || NEED_PIP=1
NEED_WHISPER=0; whisper_ok || NEED_WHISPER=1

# ---------------------------------------------------------------- report only
if [ "$MODE" = check ]; then
  echo "Toolchain"
  if [ "$NEED_NPM" = 0 ]; then ok "HyperFrames CLI $PIN (node_modules)"; else fail "HyperFrames CLI $PIN not installed (found: $(hf_installed || echo none)). Fix: bash setup.sh"; fi
  if [ "$NEED_CHROME" = 0 ]; then ok "rendering Chrome"; else fail "rendering Chrome not found. Fix: bash setup.sh"; fi
  if [ "$NEED_VENDOR" = 0 ]; then ok "HyperFrames skills $TAG (vendor/hyperframes)"; else fail "HyperFrames skills at $TAG missing (found: $(vendor_tag || echo none)). Fix: bash setup.sh"; fi
  if [ "$NEED_PIP" = 0 ]; then ok "Python environment (.venv, requirements.txt)"; else fail "Python environment missing or out of date. Fix: bash setup.sh"; fi
  if [ "$NEED_WHISPER" = 0 ]; then ok "speech model small.en"; else fail "speech model small.en not downloaded. Fix: bash setup.sh"; fi
  if [ -f .env ]; then ok ".env exists"; else fail ".env missing. Fix: bash setup.sh (or cp .env.example .env)"; fi
  BROKEN="$(find .claude/skills -maxdepth 1 -type l ! -exec test -e {} \; -print 2>/dev/null | wc -l | tr -d ' ')"
  NLINKS="$(find .claude/skills -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${NLINKS:-0}" -gt 0 ] && [ "${BROKEN:-0}" = 0 ]; then ok "$NLINKS skill links in .claude/skills"
  else fail "skill links missing or broken ($NLINKS links, $BROKEN broken). Fix: bash scripts/link-skills.sh"; fi
  if [ -x "$HF_BIN" ]; then
    DOC="$("$HF_BIN" doctor --json 2>/dev/null)"
  else DOC=""; fi
  if [ -n "$DOC" ]; then
    R="$(printf '%s' "$DOC" | python3 "$WB/scripts/doctor_gate.py")"; RC=$?
    if [ "$RC" = 0 ]; then ok "$R"; else fail "$R"; fi
  else
    fail "hyperframes doctor not run (CLI not installed). Fix: bash setup.sh"
  fi
  echo
  if [ "$FAILS" = 0 ]; then echo "Everything is in place. Self-check: bash tests/run.sh"; exit 0; fi
  echo "$FAILS problem(s). Fix: bash setup.sh (it asks before downloading anything)."
  exit 1
fi

# ---------------------------------------------------------------- what will be downloaded
PLAN=""
[ "$NEED_NPM" = 1 ]     && PLAN="$PLAN    HyperFrames CLI $PIN and its dependencies (about 128 MB, npm)\n"
[ "$NEED_CHROME" = 1 ]  && PLAN="$PLAN    the Chrome build HyperFrames renders with (about 195 MB, skipped if cached)\n"
[ "$NEED_VENDOR" = 1 ]  && PLAN="$PLAN    HyperFrames agent skills at $TAG (a few MB, git sparse clone of skills/)\n"
[ "$NEED_PIP" = 1 ]     && PLAN="$PLAN    Python packages into .venv, mostly torch for the speech model (about 339 MB)\n"
[ "$NEED_WHISPER" = 1 ] && PLAN="$PLAN    the whisper small.en speech model for QA (484 MB, into ${WHISPER_PT%/*})\n"
if [ -n "$PLAN" ]; then
  echo "Downloads"
  printf "%b" "$PLAN"
  if [ "$YES" != 1 ]; then
    if [ -t 0 ]; then
      printf "  Download and install these? [y/N] "
      read -r ans
      case "$ans" in y|Y|yes|YES) ;; *) echo "  Nothing installed."; exit 1 ;; esac
    else
      echo "  Not a terminal: run again with --yes to approve these downloads."
      exit 1
    fi
  fi
fi

echo "Install"
# 2. node packages
t0="$(now)"
if [ "$NEED_NPM" = 0 ]; then ok "HyperFrames CLI $PIN"
else
  if [ -f package-lock.json ]; then npm ci --no-audit --no-fund >>"$LOG" 2>&1 || npm install --no-audit --no-fund >>"$LOG" 2>&1
  else npm install --no-audit --no-fund >>"$LOG" 2>&1; fi
  if [ "$(hf_installed)" = "$PIN" ]; then fixed "HyperFrames CLI $PIN installed ($(took "$t0"))"
  else fail "npm install failed. Fix: read $LOG, check your network, then bash setup.sh"; fi
fi

# 3. rendering Chrome
t0="$(now)"
if [ ! -x "$HF_BIN" ]; then fail "rendering Chrome: needs the HyperFrames CLI first. Fix: the npm step above"
elif chrome_path >/dev/null; then ok "rendering Chrome"
elif "$HF_BIN" browser ensure >>"$LOG" 2>&1 && chrome_path >/dev/null; then fixed "rendering Chrome ready ($(took "$t0"))"
else fail "hyperframes browser ensure failed. Fix: read $LOG, then npx hyperframes browser ensure --force"; fi

# 4. HyperFrames skills, from the same release tag as the CLI
t0="$(now)"
if [ "$NEED_VENDOR" = 0 ]; then ok "HyperFrames skills $TAG"
else
  rm -rf vendor/hyperframes
  mkdir -p vendor
  if git clone --quiet --depth 1 --branch "$TAG" --filter=blob:none --no-checkout \
       https://github.com/heygen-com/hyperframes vendor/hyperframes >>"$LOG" 2>&1 \
     && git -C vendor/hyperframes sparse-checkout set --no-cone '/skills/' >>"$LOG" 2>&1 \
     && git -C vendor/hyperframes checkout --quiet >>"$LOG" 2>&1 \
     && [ "$(vendor_tag)" = "$TAG" ]; then
    fixed "HyperFrames skills $TAG ($(ls -d vendor/hyperframes/skills/*/ 2>/dev/null | wc -l | tr -d ' ') skills, $(took "$t0"))"
  else fail "could not clone heygen-com/hyperframes at $TAG. Fix: check your network and GitHub access, read $LOG, then bash setup.sh"; fi
fi

# 5. Python environment
t0="$(now)"
if venv_ok; then ok "Python environment .venv ($(.venv/bin/python -c 'import platform; print(platform.python_version())'))"
else
  rm -rf .venv
  if python3 -m venv .venv >>"$LOG" 2>&1 && venv_ok; then fixed "Python environment .venv created"
  else fail "python3 -m venv failed. Fix: read $LOG (on Debian or Ubuntu: sudo apt install python3-venv)"; fi
fi
t0="$(now)"
if ! venv_ok; then fail "Python packages: needs .venv first"
elif [ "$NEED_PIP" = 0 ]; then ok "Python packages (requirements.txt)"
else
  .venv/bin/python -m pip install --quiet --disable-pip-version-check --upgrade pip >>"$LOG" 2>&1
  if [ "$OS" = Linux ] && ! .venv/bin/python -c 'import torch' 2>/dev/null; then
    # The default Linux torch wheel bundles CUDA (gigabytes). The QA only needs the CPU build.
    .venv/bin/python -m pip install --quiet --disable-pip-version-check torch --index-url https://download.pytorch.org/whl/cpu >>"$LOG" 2>&1
  fi
  if .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt >>"$LOG" 2>&1 \
     && .venv/bin/python -c 'import numpy, PIL, yaml, fontTools, brotli, whisper' >>"$LOG" 2>&1; then
    echo "$REQ_HASH" > .venv/.requirements.sha256
    fixed "Python packages installed ($(took "$t0"))"
  else fail "pip install -r requirements.txt failed. Fix: read $LOG, then bash setup.sh"; fi
fi

# 6. speech model (verified by checksum, downloaded only when missing or corrupt)
t0="$(now)"
if ! pip_ok; then fail "speech model small.en: needs the Python packages first"
else
  HAD=0; whisper_ok && HAD=1
  if .venv/bin/python - >>"$LOG" 2>&1 <<'PY'
import os, whisper
root = os.path.join(os.getenv("XDG_CACHE_HOME", os.path.join(os.path.expanduser("~"), ".cache")), "whisper")
whisper._download(whisper._MODELS["small.en"], root, False)
PY
  then
    if [ "$HAD" = 1 ]; then ok "speech model small.en (checksum verified, $(took "$t0"))"; else fixed "speech model small.en downloaded ($(took "$t0"))"; fi
  else fail "could not download the whisper small.en model. Fix: check your network, read $LOG, then bash setup.sh"; fi
fi

# 7. .env (created from the example; the key is pasted by the user, never by a script or the agent)
if [ -f .env ]; then ok ".env exists"
elif cp .env.example .env && chmod 600 .env; then fixed ".env created from .env.example (mode 600)"
else fail "could not create .env. Fix: cp .env.example .env"; fi
if [ -f .env ]; then
  KEY="$("$WB/bin/pvs-py" -c 'import pvs; print("set" if pvs.env_value("ELEVENLABS_API_KEY") else "empty")' 2>/dev/null)"
  if [ "$KEY" = set ]; then ok "ElevenLabs key is set in .env"
  else warn "ElevenLabs key is empty. Open .env in your editor and paste it after ELEVENLABS_API_KEY= (never in the chat). Without it, voice.provider: say works"; fi
fi

# 8. skill links
if R="$(bash scripts/link-skills.sh 2>>"$LOG")"; then
  case "$R" in *"(0 new, 0 removed"*) ok "$R" ;; *) fixed "$R" ;; esac
else fail "scripts/link-skills.sh failed. Fix: read $LOG, then bash scripts/link-skills.sh"; fi

# 9. hyperframes doctor
t0="$(now)"
if [ -x "$HF_BIN" ]; then
  R="$("$HF_BIN" doctor --json 2>>"$LOG" | python3 "$WB/scripts/doctor_gate.py")"; RC=$?
  if [ "$RC" = 0 ]; then ok "$R ($(took "$t0"))"; else fail "$R"; fi
else fail "hyperframes doctor: the CLI is not installed. Fix: the npm step above"; fi

if [ "$FAILS" -gt 0 ]; then
  echo
  echo "$FAILS step(s) failed. Fix the FAIL lines above, then run bash setup.sh again. Log: $LOG"
  exit 1
fi

# 10. self-check
echo "Self-check"
t0="$(now)"
TOUT="$(bash tests/run.sh 2>&1)"; RC=$?
LAST="$(printf '%s\n' "$TOUT" | tail -1)"
if [ "$RC" = 0 ]; then ok "tests/run.sh: $LAST ($(took "$t0"))"
else
  printf '%s\n' "$TOUT" | grep -E '^ *FAIL' | head -20
  fail "tests/run.sh: $LAST. Fix: read the failing tests above (bash tests/run.sh shows the details)"
fi

# 11. the example video, end to end: voice (macOS say), build, render, QA, delivery, in a temp folder
EXAMPLE_MP4=""
if [ "$EXAMPLE" = 0 ]; then ok "example video: skipped (--no-example)"
elif [ "$FAILS" -gt 0 ]; then warn "example video: skipped because the self-check failed"
elif ! command -v say >/dev/null 2>&1; then warn "example video: skipped (needs macOS say for the free voice). Fix: run on macOS, or bash setup.sh --no-example"
else
  echo "Example video"
  t0="$(now)"
  EOUT="$(bash scripts/example-chain.sh 2>&1)"; RC=$?
  if [ "$RC" = 0 ]; then
    EXAMPLE_MP4="$(printf '%s\n' "$EOUT" | sed -n 's/^mp4 //p' | tail -1)"
    ok "examples/acme tour rendered, qa passed ($(took "$t0"))"
  else
    printf '%s\n' "$EOUT" | tail -25
    fail "example video: the chain failed. Fix: read the step above, then bash scripts/example-chain.sh"
  fi
fi

echo
if [ "$FAILS" -gt 0 ]; then echo "Setup finished with $FAILS failure(s). Log: $LOG"; exit 1; fi
python3 - "$PIN" "$(vendor_tag)" "$(took "$T_START")" <<'PY'
import json, sys, time
json.dump({"hyperframes": sys.argv[1], "vendor_tag": sys.argv[2], "took": sys.argv[3],
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, open(".venv/pvs-setup.json", "w"), indent=1)
PY
rm -f "$LOG"
echo "Setup done in $(took "$T_START"). $LAST"
if [ -n "$EXAMPLE_MP4" ]; then
  echo "Example video: $EXAMPLE_MP4"
  echo "qa passed"
fi
echo "Next: /product-new <slug> to bring your product (or open examples/acme to see the example)."
