# Tests for skills/ui-demo-composer: the signature gate of build.py, draft stamping, the beat
# helpers w()/end(), the camera clamp, and `hyperframes check` on the built template.
# Fast: no network except the guarded check (skipped when npx or the cached CLI is unavailable).

_uc_fixture() {  # a fictional product with one video copied from _template/video
  P="$TEST_TMP/acme"; V="$P/videos/demo"
  mkdir -p "$P/kit/logos" "$P/kit/fonts" "$P/videos"
  cat > "$P/product.yaml" <<'EOF'
product: {name: Acme Tasks, slug: acme, positioning: "The to-do list that plans your day."}
app_canvas: {logical: [1440, 810], theme: light}
brand: {accent: "#4F46E5", font: Inter, logo_light: kit/logos/logo-light.svg, logo_dark: kit/logos/logo-dark.svg, app_tile: kit/logos/app-tile.svg}
video: {fps: 30, max_zoom: 1.35}
EOF
  echo ':root { --acme-accent: #4F46E5; }' > "$P/kit/tokens.css"
  for f in logo-light logo-dark app-tile; do
    echo '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40"><rect width="40" height="40" rx="10" fill="#4F46E5"/></svg>' > "$P/kit/logos/$f.svg"
  done
  local fonts="$HOME/.claude/skills/hyperframes-creative/frame-presets/code-editorial/fonts"
  if [ -f "$fonts/Inter-400.woff2" ]; then
    cp "$fonts/Inter-400.woff2" "$fonts/Inter-700.woff2" "$P/kit/fonts/"
    printf '@font-face { font-family: "Inter"; font-weight: 400; src: url("Inter-400.woff2") format("woff2"); }\n@font-face { font-family: "Inter"; font-weight: 500 700; src: url("Inter-700.woff2") format("woff2"); }\n' > "$P/kit/fonts/fonts.css"
  fi
  cp -R "$PVS_HOME/_template/video" "$V"
  "$PVS_PY" - "$V" <<'PY'
import json, sys, wave
from pathlib import Path
v = Path(sys.argv[1])
for f in ["BRIEF.md", "COVERAGE.md", "CLAIMS.md", "SOURCES.md", "TRUTH.md"]:
    p = v / f
    s = p.read_text()
    for k, x in {"{{TITLE}}": "Acme demo", "{{VIDEO}}": "demo", "{{FORMAT}}": "pitch", "{{PRODUCT_NAME}}": "Acme Tasks"}.items():
        s = s.replace(k, x)
    p.write_text(s)
lines = {"N1": ("Every morning, your plan for the day is ready before you open the app.", 4.0),
         "N2": ("Type a task, and it lands in the right slot.", 2.8)}
tim = {}
(v / "audio/clips").mkdir(parents=True, exist_ok=True)
for k, (txt, dur) in lines.items():
    ws = txt.split(); step = (dur - 0.4) / len(ws)
    tim[k] = {"dur": dur, "words": [{"w": x, "s": round(0.1 + i * step, 3), "e": round(0.1 + i * step + step * 0.8, 3)} for i, x in enumerate(ws)]}
    with wave.open(str(v / "audio/clips" / (k + ".wav")), "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(48000); wv.writeframes(b"\0\0" * int(48000 * dur))
(v / "audio/timings.json").write_text(json.dumps(tim))
PY
}

_uc_sign() { "$PVS_PY" - "$V/BRIEF.md" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
s = s.replace('coverage_signed_by: ""', 'coverage_signed_by: "Maya Lindqvist"').replace('claims_signed_by: ""', 'claims_signed_by: "Maya Lindqvist"')
open(p, "w").write(s)
PY
}

test_build_refuses_unsigned_brief() {
  _uc_fixture
  out="$("$PVS_PY" "$V/video/build.py" 2>&1)"; rc=$?
  assert_eq "$rc" "2" "exit code of an unsigned build"
  assert_contains "$out" "not signed"
  assert_contains "$out" "--draft"
  assert_no_file "$V/video/index.html"
}

test_build_draft_stamps_meta() {
  _uc_fixture
  out="$("$PVS_PY" "$V/video/build.py" --draft --quiet 2>&1)" || fail "draft build failed: $out"
  assert_contains "$out" "DRAFT"
  html="$(cat "$V/video/index.html")"
  assert_contains "$html" '<meta name="pvs-draft" content="1">'
  assert_not_contains "$html" "{{"
  assert_contains "$html" 'data-composition-id="main"'
  assert_contains "$html" 'id="vo-N1" src="audio/clips/N1.wav"'
  assert_file "$V/video/audio/clips/N2.wav"
  assert_contains "$out" "--quality draft"
}

test_build_signed_has_no_draft_meta() {
  _uc_fixture; _uc_sign
  out="$("$PVS_PY" "$V/video/build.py" --quiet 2>&1)" || fail "signed build failed: $out"
  assert_contains "$out" "(signed)"
  assert_not_contains "$(cat "$V/video/index.html")" "pvs-draft"
  assert_contains "$out" "render . -o renders/demo-v1.mp4 --fps 30 --quality delivery"
}

test_fake_timings_need_draft() {
  _uc_fixture; _uc_sign
  out="$("$PVS_PY" "$V/video/build.py" --fake-timings 2>&1)" && fail "--fake-timings without --draft must fail"
  assert_contains "$out" "needs --draft"
  rm "$V/audio/timings.json"
  out="$("$PVS_PY" "$V/video/build.py" --draft --fake-timings --quiet 2>&1)" || fail "fake-timings draft failed: $out"
  assert_contains "$(cat "$V/video/index.html")" 'pvs-fake-timings'
}

test_w_end_and_camera_clamp() {
  _uc_fixture
  out="$(cd "$V/video" && "$PVS_PY" - <<'PY'
import sys
import os
sys.path.insert(0, os.path.join(os.environ["PVS_HOME"], "skills/ui-demo-composer/scripts"))
import buildlib
b = buildlib.Build(os.path.abspath("build.py"), ["--draft"])
T, w, end = b.T, b.w, b.end
assert abs(w("N1", "every") - 0.1) < 1e-9
assert w("N1", "the", 2) > w("N1", "the", 1)          # nth occurrence
assert w("N2", "Lands") == w("N2", "lands")            # case-insensitive, punctuation stripped
assert b.we("N2", "type") > w("N2", "type")
try:
    w("N1", "zebra"); raise SystemExit("missing word did not raise")
except buildlib.BuildError as e:
    assert "no such word" in str(e) and "Every morning" in str(e)
try:
    end("N1"); raise SystemExit("end of an unplaced clip did not raise")
except buildlib.BuildError:
    pass
T["N1"] = 1.0
assert abs(end("N1") - 5.0) < 1e-9
T["typing"] = 2.0
try:
    end("typing"); raise SystemExit("end of a beat without duration did not raise")
except buildlib.BuildError as e:
    assert "b.dur" in str(e)
b.dur("typing", 1.5)
assert end("typing") == 3.5
b.cam(3.0, 2.0, "#list")
assert b.cam_moves[-1]["s"] == 1.35, b.cam_moves
assert any("above video.max_zoom" in x for x in b.warnings), b.warnings
b.cam(3.5, 1.1)
assert any("before the previous one ends" in x for x in b.warnings), b.warnings
print("helpers ok")
PY
)" || fail "helper checks failed: $out"
  assert_contains "$out" "helpers ok"
}

test_unreplaced_placeholder_fails() {
  _uc_fixture
  sed -i '' 's|<title>|<title>{{NOT_A_PLACEHOLDER}}|' "$V/video/src/template.tpl" 2>/dev/null \
    || sed -i 's|<title>|<title>{{NOT_A_PLACEHOLDER}}|' "$V/video/src/template.tpl"
  out="$("$PVS_PY" "$V/video/build.py" --draft --quiet 2>&1)" && fail "a leftover placeholder must fail the build"
  assert_contains "$out" "{{NOT_A_PLACEHOLDER}}"
}

test_ui_component_include() {
  _uc_fixture
  mkdir -p "$P/kit/ui"
  echo '<div class="acme-badge" id="badge">New</div>' > "$P/kit/ui/badge.html"
  echo '.acme-badge { color: #4F46E5; }' > "$P/kit/ui/badge.css"
  sed -i '' 's|<main class="main">|<main class="main">{{UI:badge}}|' "$V/video/src/template.tpl" 2>/dev/null \
    || sed -i 's|<main class="main">|<main class="main">{{UI:badge}}|' "$V/video/src/template.tpl"
  "$PVS_PY" "$V/video/build.py" --draft --quiet >/dev/null 2>&1 || fail "build with a UI include failed"
  html="$(cat "$V/video/index.html")"
  assert_contains "$html" '<div class="acme-badge" id="badge">New</div>'
  assert_contains "$html" '.acme-badge { color: #4F46E5; }'
}

test_hyperframes_check_passes_on_template() {
  command -v npx >/dev/null 2>&1 || { echo "SKIP: npx not found"; return 0; }
  ls -d "$HOME"/.npm/_npx/*/node_modules/hyperframes >/dev/null 2>&1 || { echo "SKIP: hyperframes not cached (offline)"; return 0; }
  _uc_fixture
  "$PVS_PY" "$V/video/build.py" --draft --quiet >/dev/null 2>&1 || fail "draft build failed"
  local to=""; command -v timeout >/dev/null 2>&1 && to="timeout 150"
  out="$(cd "$V/video" && $to npx --yes hyperframes@0.8.134 check 2>&1)"; rc=$?
  if [ "$rc" = 124 ]; then echo "SKIP: check timed out"; return 0; fi
  [ "$rc" = 0 ] || fail "hyperframes check failed: $(printf '%s' "$out" | tail -30)"
  assert_contains "$out" "Check passed"
}
