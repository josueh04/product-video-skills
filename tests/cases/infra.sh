#!/usr/bin/env bash
# Infra tests: lib/pvs.py helpers, the guard hook, link-skills.sh, setup.sh --check, status.py.

# ---------- lib/pvs.py

test_pvs_defaults_merge() {
  mkdir -p "$TEST_TMP/p/videos/v"
  cat > "$TEST_TMP/p/product.yaml" <<'EOF'
product: {name: Acme Tasks, slug: acme}
voice:
  roles:
    narrator: {voice: abc}
video: {fps: 60}
EOF
  out="$("$PVS_PY" - "$TEST_TMP/p/videos/v" <<'PY'
import sys, pvs
from pathlib import Path
c = pvs.load_product(Path(sys.argv[1]))
assert c["product"]["name"] == "Acme Tasks"
assert c["product"]["banned_terms"] == []
assert c["video"]["fps"] == 60 and c["video"]["max_zoom"] == 1.35
n = c["voice"]["roles"]["narrator"]
assert n["voice"] == "abc" and n["model"] == "eleven_multilingual_v2", n
assert c["voice"]["clip_lufs"] == -18
assert c["_dir"].endswith("/p")
print("merged")
PY
)" || fail "load_product failed: $out"
  assert_eq "$out" "merged"
}

test_pvs_read_brief_and_signed() {
  mkdir -p "$TEST_TMP/v"
  printf -- '---\ntitle: T\nvideo: pitch\ncoverage_signed_by: ""\nclaims_signed_by: Maya Lindqvist\n---\nbody\n' > "$TEST_TMP/v/BRIEF.md"
  out="$("$PVS_PY" - "$TEST_TMP/v" <<'PY'
import sys, pvs
m = pvs.read_brief(sys.argv[1])
assert m["coverage_signed_by"] == "" and m["claims_signed_by"] == "Maya Lindqvist"
assert m["version"] == 1 and m["reviewer"] == ""
assert not pvs.signed(m)
m["coverage_signed_by"] = "Maya Lindqvist"
assert pvs.signed(m)
print("brief ok")
PY
)" || fail "$out"
  assert_eq "$out" "brief ok"
}

test_pvs_read_lines_tsv() {
  printf 'id\trole\tspeed\ttext\n# a comment\n\nN1\tnarrator\t1.0\tHello there.\nN2\tnarrator\t\tTabs\tinside\n' > "$TEST_TMP/lines.tsv"
  out="$("$PVS_PY" - "$TEST_TMP/lines.tsv" <<'PY'
import sys, pvs
r = pvs.read_lines_tsv(sys.argv[1])
assert [x["id"] for x in r] == ["N1", "N2"], r
assert r[0]["speed"] == 1.0 and r[1]["speed"] == 1.0
assert r[1]["text"] == "Tabs\tinside"
print("tsv ok")
PY
)" || fail "$out"
  assert_eq "$out" "tsv ok"
}

test_pvs_env_value_never_echoes() {
  # A fake workbench whose .env holds a recognizable secret.
  mkdir -p "$TEST_TMP/wb/lib"
  cp "$PVS_HOME/lib/pvs.py" "$TEST_TMP/wb/lib/"
  secret="sk-test-$RANDOM$RANDOM-do-not-print"
  printf '# comment\nOTHER=1\nELEVENLABS_API_KEY="%s"\n' "$secret" > "$TEST_TMP/wb/.env"
  out="$(env -u ELEVENLABS_API_KEY PVS_HOME="$TEST_TMP/wb" PYTHONPATH="$TEST_TMP/wb/lib" python3 - "$secret" 2>&1 <<'PY'
import sys, pvs
v = pvs.env_value("ELEVENLABS_API_KEY")
print("match" if v == sys.argv[1] else "mismatch")
print("missing" if pvs.env_value("NOPE_KEY") is None else "found")
PY
)"
  assert_not_contains "$out" "$secret" "env_value output"
  assert_contains "$out" "match"
  assert_not_contains "$out" "mismatch"
  assert_contains "$out" "missing"
  # The status script reports only whether the key is set.
  out="$(env -u ELEVENLABS_API_KEY PVS_HOME="$TEST_TMP/wb" python3 "$PVS_HOME/skills/video-ask/scripts/status.py" "$TEST_TMP" --json 2>&1)"
  assert_not_contains "$out" "$secret" "status.py output"
}

# ---------- guard hook

guard() { # guard <json> -> prints "rc=<n>" and the reason
  local o rc
  o="$(printf '%s' "$1" | bash "$PVS_HOME/.claude/hooks/guard.sh" 2>&1)"; rc=$?
  echo "rc=$rc $o"
}

test_guard_blocks_sources_allows_videos() {
  r="$(guard "{\"tool_name\":\"Write\",\"cwd\":\"$TEST_TMP\",\"tool_input\":{\"file_path\":\"products/x/sources/a\",\"content\":\"x\"}}")"
  assert_contains "$r" "rc=2" "write into sources/"
  assert_contains "$r" "read-only"
  r="$(guard "{\"tool_name\":\"Write\",\"cwd\":\"$TEST_TMP\",\"tool_input\":{\"file_path\":\"products/x/videos/a\",\"content\":\"x\"}}")"
  assert_eq "$r" "rc=0 " "write into videos/"
  # A product anywhere: the folder holding product.yaml defines sources/.
  mkdir -p "$TEST_TMP/elsewhere/sources/frontend"; : > "$TEST_TMP/elsewhere/product.yaml"
  r="$(guard "{\"tool_name\":\"Edit\",\"cwd\":\"/\",\"tool_input\":{\"file_path\":\"$TEST_TMP/elsewhere/sources/frontend/app.ts\"}}")"
  assert_contains "$r" "rc=2" "edit in a product outside products/"
  r="$(guard "{\"tool_name\":\"Bash\",\"cwd\":\"$TEST_TMP\",\"tool_input\":{\"command\":\"echo hi > products/x/sources/a.txt\"}}")"
  assert_contains "$r" "rc=2" "shell redirect into sources/"
  r="$(guard "{\"tool_name\":\"Bash\",\"cwd\":\"$TEST_TMP\",\"tool_input\":{\"command\":\"cp products/x/sources/frontend/logo.svg products/x/kit/logos/\"}}")"
  assert_eq "$r" "rc=0 " "copying out of sources/ is fine"
}

test_guard_blocks_vendor_env_and_upgrades() {
  r="$(guard "{\"tool_name\":\"Write\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"file_path\":\"vendor/hyperframes/skills/x/SKILL.md\"}}")"
  assert_contains "$r" "rc=2" "write into vendor/"
  r="$(guard "{\"tool_name\":\"Read\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"file_path\":\"$PVS_HOME/.env\"}}")"
  assert_contains "$r" "rc=2" "Read .env"
  r="$(guard "{\"tool_name\":\"Read\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"file_path\":\"$PVS_HOME/.env.local\"}}")"
  assert_contains "$r" "rc=2" "Read .env.local"
  r="$(guard "{\"tool_name\":\"Read\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"file_path\":\"$PVS_HOME/.env.example\"}}")"
  assert_eq "$r" "rc=0 " "Read .env.example"
  for c in "cat .env" "grep KEY ../.env" "source .env" "python3 -c \\\"print(open('.env').read())\\\""; do
    r="$(guard "{\"tool_name\":\"Bash\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"command\":\"$c\"}}")"
    assert_contains "$r" "rc=2" "$c"
  done
  for c in "cat .env.example" "cp .env.example .env" "test -f .env" "ls -la"; do
    r="$(guard "{\"tool_name\":\"Bash\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"command\":\"$c\"}}")"
    assert_eq "$r" "rc=0 " "$c"
  done
  for c in "npx hyperframes upgrade" "npx --yes hyperframes@0.8.134 upgrade --yes" "npx hyperframes skills update" \
           "npx --yes hyperframes@0.8.139 render ." "npm install hyperframes@latest" "npm i hyperframes"; do
    r="$(guard "{\"tool_name\":\"Bash\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"command\":\"$c\"}}")"
    assert_contains "$r" "rc=2" "$c"
  done
  r="$(guard "{\"tool_name\":\"Bash\",\"cwd\":\"$PVS_HOME\",\"tool_input\":{\"command\":\"npx --yes hyperframes@0.8.134 render . -o renders/a.mp4\"}}")"
  assert_eq "$r" "rc=0 " "pinned render"
  r="$(guard 'not json')"
  assert_eq "$r" "rc=0 " "bad input lets the call through"
}

# ---------- link-skills.sh

make_fake_workbench() { # a minimal copy with two of our skills and two vendor skills (one clashes)
  local w="$1"
  mkdir -p "$w/scripts" "$w/.claude/hooks" "$w/skills/alpha" "$w/skills/shared" \
           "$w/vendor/hyperframes/skills/shared" "$w/vendor/hyperframes/skills/beta" "$w/skills/not-a-skill"
  cp "$PVS_HOME/scripts/link-skills.sh" "$w/scripts/"
  cp "$PVS_HOME/.claude/settings.json" "$w/.claude/"
  for d in skills/alpha skills/shared vendor/hyperframes/skills/shared vendor/hyperframes/skills/beta; do
    echo "name: $(basename "$d")" > "$w/$d/SKILL.md"
  done
}

test_link_skills_workbench() {
  w="$TEST_TMP/wb"; make_fake_workbench "$w"
  mkdir -p "$w/.claude/skills/mine"                         # a real folder: left alone
  ln -s ../../skills/gone "$w/.claude/skills/gone"          # dangling link we made: removed
  ln -s /usr/bin "$w/.claude/skills/foreign"                # foreign link: left alone
  out="$(bash "$w/scripts/link-skills.sh" 2>&1)" || fail "link-skills failed: $out"
  assert_eq "$(readlink "$w/.claude/skills/alpha")" "../../skills/alpha"
  assert_eq "$(readlink "$w/.claude/skills/shared")" "../../skills/shared" "our skill wins the clash"
  assert_eq "$(readlink "$w/.claude/skills/beta")" "../../vendor/hyperframes/skills/beta"
  assert_file "$w/.claude/skills/beta/SKILL.md"
  assert_no_file "$w/.claude/skills/not-a-skill"
  [ -L "$w/.claude/skills/gone" ] && fail "dangling link not removed"
  [ -d "$w/.claude/skills/mine" ] && [ ! -L "$w/.claude/skills/mine" ] || fail "real folder touched"
  [ -L "$w/.claude/skills/foreign" ] || fail "foreign link removed"
  out="$(bash "$w/scripts/link-skills.sh" 2>/dev/null)"
  assert_contains "$out" "(0 new, 0 removed" "second run changes nothing"
}

test_link_skills_product() {
  w="$TEST_TMP/wb"; make_fake_workbench "$w"
  bash "$w/scripts/link-skills.sh" >/dev/null 2>&1
  p="$w/products/acme"; mkdir -p "$p"; echo "product: {slug: acme}" > "$p/product.yaml"
  out="$(bash "$w/scripts/link-skills.sh" "$p" 2>&1)" || fail "product link failed: $out"
  assert_file "$p/.claude/skills/alpha/SKILL.md"
  assert_eq "$(readlink "$p/.claude/skills/alpha")" "../../../../skills/alpha"
  assert_file "$p/.claude/hooks"
  assert_eq "$(cd "$p/.claude/hooks" && pwd -P)" "$(cd "$w/.claude/hooks" && pwd -P)"
  cmp -s "$p/.claude/settings.json" "$w/.claude/settings.json" || fail "settings not copied"
  out="$(bash "$w/scripts/link-skills.sh" "$TEST_TMP" 2>&1)" && fail "accepted a folder without product.yaml"
  assert_contains "$out" "no product.yaml"
}

# ---------- setup.sh --check

test_setup_check_installs_nothing() {
  w="$TEST_TMP/wb"; mkdir -p "$w/scripts"
  cp "$PVS_HOME/setup.sh" "$PVS_HOME/package.json" "$PVS_HOME/requirements.txt" "$PVS_HOME/.env.example" "$w/"
  cp "$PVS_HOME/scripts/"*.sh "$PVS_HOME/scripts/"*.py "$w/scripts/"
  before="$(cd "$w" && find . | sort)"
  out="$(bash "$w/setup.sh" --check 2>&1)"; rc=$?
  after="$(cd "$w" && find . | sort)"
  assert_eq "$after" "$before" "setup.sh --check wrote files"
  assert_contains "$out" "report only"
  case "$out" in *" ok "*|*"  ok"*) ;; *) fail "no ok lines: $out" ;; esac
  # Nothing is installed in the copy, so these must be reported, with the fix.
  if printf '%s' "$out" | grep -q '^  FAIL   \(node\|python\|ffmpeg\|git\)'; then
    : # a machine without the prerequisites stops earlier; still nothing was written
  else
    assert_contains "$out" "HyperFrames CLI 0.8.134 not installed"
    assert_contains "$out" "Fix: bash setup.sh"
    [ "$rc" != 0 ] || fail "--check exited 0 with missing pieces"
  fi
  assert_not_contains "$out" "Download and install"
}

# ---------- status.py

test_status_stages() {
  w="$TEST_TMP/wb"; mkdir -p "$w/lib" "$w/products/acme/videos/pitch" "$w/products/acme/videos/docs"
  cp "$PVS_HOME/lib/pvs.py" "$w/lib/"; cp "$PVS_HOME/package.json" "$w/"
  printf 'product: {name: Acme Tasks, slug: acme}\n' > "$w/products/acme/product.yaml"
  v="$w/products/acme/videos/pitch"
  printf -- '---\nvideo: pitch\nversion: 2\ncoverage_signed_by: ""\nclaims_signed_by: ""\n---\n' > "$v/BRIEF.md"
  printf -- '---\nvideo: docs\ncoverage_signed_by: Maya\nclaims_signed_by: Maya\n---\n' > "$w/products/acme/videos/docs/BRIEF.md"
  st() { PVS_HOME="$w" python3 "$PVS_HOME/skills/video-ask/scripts/status.py" "$@" --json | python3 -c "$PYQ"; }
  PYQ='import json,sys; d=json.load(sys.stdin); print("|".join([d["next"]]+[v["video"]+"="+v["stage"] for p in d["products"] for v in p["videos"]]))'
  out="$(st "$w")"
  assert_contains "$out" "/video-setup" "setup is not done in the fake workbench"
  assert_contains "$out" "pitch=brief unsigned"
  assert_contains "$out" "docs=signed"
  # Pretend setup finished, then walk the pitch video through its stages.
  mkdir -p "$w/.venv/bin" "$w/node_modules/hyperframes" "$w/vendor/hyperframes"
  ln -s "$(command -v python3)" "$w/.venv/bin/python"
  echo '{"version": "0.8.134"}' > "$w/node_modules/hyperframes/package.json"
  echo '{"finished_at": "now"}' > "$w/.venv/pvs-setup.json"
  git -C "$w/vendor/hyperframes" init -q && git -C "$w/vendor/hyperframes" -c user.email=t@example.test -c user.name=t commit -q --allow-empty -m t \
    && git -C "$w/vendor/hyperframes" tag v0.8.134
  out="$(st "$v")"
  assert_contains "$out" "The reviewer reads COVERAGE.md"
  sed -i.bak 's/coverage_signed_by: ""/coverage_signed_by: Maya/; s/claims_signed_by: ""/claims_signed_by: Maya/' "$v/BRIEF.md"
  out="$(st "$v")"; assert_contains "$out" "/video-build pitch"; assert_contains "$out" "pitch=signed"
  : > "$v/SOURCES.md"; : > "$v/TRUTH.md"; mkdir -p "$v/specs" "$v/audio/clips" "$v/video/renders" "$v/qa"
  : > "$v/specs/home.md"; echo '{}' > "$v/audio/timings.json"; : > "$v/audio/clips/N1.wav"
  out="$(st "$v")"; assert_contains "$out" "pitch=voice"
  : > "$v/video/index.html"; out="$(st "$v")"; assert_contains "$out" "pitch=built"
  echo fake > "$v/video/renders/pitch-v2.mp4"; out="$(st "$v")"; assert_contains "$out" "pitch=rendered"; assert_contains "$out" "qa.py"
  sha="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$v/video/renders/pitch-v2.mp4")"
  echo "{\"mp4\": \"video/renders/pitch-v2.mp4\", \"sha256\": \"$sha\", \"draft\": false, \"passed\": false}" > "$v/qa/REPORT.json"
  out="$(st "$v")"; assert_contains "$out" "pitch=QA failed"
  echo "{\"mp4\": \"video/renders/pitch-v2.mp4\", \"sha256\": \"$sha\", \"draft\": false, \"passed\": true}" > "$v/qa/REPORT.json"
  out="$(st "$v")"; assert_contains "$out" "pitch=QA passed"; assert_contains "$out" "deliver.py"
  echo changed > "$v/video/renders/pitch-v2.mp4"; out="$(st "$v")"; assert_contains "$out" "pitch=QA failed" "sha mismatch"
  mkdir -p "$w/products/acme/deliveries"; : > "$w/products/acme/deliveries/Acme Tasks pitch v2.mp4"
  out="$(st "$v")"; assert_contains "$out" "pitch=delivered"; assert_contains "$out" "/video-review pitch"
  out="$(PVS_HOME="$w" python3 "$PVS_HOME/skills/video-ask/scripts/status.py" "$v" --short)"
  n="$(printf '%s\n' "$out" | wc -l | tr -d ' ')"
  [ "$n" -ge 2 ] && [ "$n" -le 5 ] || fail "--short printed $n lines: $out"
}

test_session_start_hook() {
  envf="$TEST_TMP/env"
  out="$(echo "{\"cwd\":\"$TEST_TMP\",\"source\":\"startup\"}" | CLAUDE_ENV_FILE="$envf" bash "$PVS_HOME/.claude/hooks/session-start.sh")" \
    || fail "hook exited non-zero"
  assert_contains "$out" "Next:"
  assert_contains "$(cat "$envf")" "export PVS_HOME="
  n="$(printf '%s\n' "$out" | wc -l | tr -d ' ')"
  [ "$n" -ge 3 ] && [ "$n" -le 6 ] || fail "hook printed $n lines: $out"
}

test_skill_docs_keep_command_and_path_apart() {
  # QA="$PVS_HOME/bin/pvs-py $PVS_HOME/..." then $QA/qa.py is not split by zsh and breaks in bash
  # on a path with spaces. Skills keep the interpreter and the script folder in separate quoted
  # variables ("$PY" "$S/qa.py").
  bad="$(grep -rnE '^[[:space:]]*[A-Za-z_]+="[^"]*pvs-py[[:space:]][^"]*"' "$PVS_HOME/skills" "$PVS_HOME/_template" --include='*.md' || true)"
  [ -z "$bad" ] || fail "a variable holds a command plus a path: $bad"
}
