# Tests for skills/render-qa. Sourced by tests/run.sh; each test_* runs in a subshell.
# Fast: a 3 s synthetic MP4 made with ffmpeg lavfi. Speech to text only under PVS_FULL=1.

_rqa_py() { "$PVS_HOME/bin/pvs-py" "$@"; }
_rqa_s() { echo "$PVS_HOME/skills/render-qa/scripts/$1"; }

# A product with one video, a signed BRIEF and a tiny render. Prints the product dir.
_rqa_fixture() {
  local root p v
  root="${TEST_TMP:-$(mktemp -d)}/fx-$RANDOM"
  p="$root/acme"
  v="$p/videos/pitch"
  mkdir -p "$v/audio" "$v/video/renders"
  cat > "$p/product.yaml" <<'YAML'
product:
  name: Acme Tasks
  slug: acme
  never_say: ["the last app you will ever need"]
  names:
    Acme Tasks: ["AcmeTodo"]
  banned_terms: ["Globex"]
video:
  size: [320, 180]
  fps: 30
  max_zoom: 1.35
  lang: en
review:
  naming: "{product} {video} v{version}.mp4"
YAML
  cat > "$v/BRIEF.md" <<'MD'
---
title: Acme Tasks in 60 seconds
video: pitch
format: pitch
lang: en
version: 1
coverage_signed_by: "Maya Lindqvist"
claims_signed_by: "Maya Lindqvist"
---
Test brief.
MD
  printf 'id\trole\tspeed\ttext\nN1\tnarrator\t1.0\tAcme Tasks plans your day.\n' > "$v/audio/lines.tsv"
  cat > "$v/video/index.html" <<'HTML'
<!doctype html><html><body>
<div data-composition-id="main" data-width="320" data-height="180" data-duration="3">
  <h1>Acme Tasks</h1>
  <audio id="vo-N1" src="../audio/clips/N1.wav" data-start="0.5" data-duration="2.0" data-track-index="10"></audio>
</div>
<script>
const tl = gsap.timeline({ paused: true });
tl.fromTo("#t", { yPercent: 110, opacity: 1 }, { yPercent: 0, opacity: 1, duration: 0.7, immediateRender: false }, 0.4);
cam(1.0, 1.2, 100, 100);
window.__timelines["main"] = tl;
</script>
</body></html>
HTML
  ffmpeg -v error -y -f lavfi -i "color=c=0x334455:s=320x180:d=3:r=30" -f lavfi -i "sine=f=440:d=3:sample_rate=48000" \
    -af "volume=-20dB" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$v/video/renders/pitch-v1.mp4"
  echo "$p"
}

_rqa_sha() { shasum -a 256 "$1" | cut -d' ' -f1; }

# A REPORT.json for an mp4: passed and draft as given, sha256 as given (default: the real one).
_rqa_report() {
  local v="$1" mp4="$2" passed="$3" draft="$4" sha="${5:-$(_rqa_sha "$2")}"
  mkdir -p "$v/qa"
  cat > "$v/qa/REPORT.json" <<JSON
{"mp4": "video/renders/$(basename "$mp4")", "sha256": "$sha", "created": "2026-01-01T00:00:00Z",
 "draft": $draft, "checks": [{"name": "black_frames", "passed": $passed, "detail": "test"}], "passed": $passed}
JSON
}

test_banned_terms_hit() {
  local p; p="$(_rqa_fixture)"
  ! _rqa_py "$(_rqa_s banned_terms.py)" --product "$p" --text "Try AcmeTodo today" >/dev/null || return 1
  # the spoken form of a camel-case legacy name, as speech to text writes it
  ! _rqa_py "$(_rqa_s banned_terms.py)" --product "$p" --text "try acme todo today" >/dev/null || return 1
  echo "We beat globex." > "$p/videos/pitch/note.md"
  out="$(_rqa_py "$(_rqa_s banned_terms.py)" "$p/videos/pitch/note.md")" && return 1
  echo "$out" | grep -q "note.md:1: banned: 'Globex'"
}

test_banned_terms_miss() {
  local p; p="$(_rqa_fixture)"
  _rqa_py "$(_rqa_s banned_terms.py)" --product "$p" --text "Acme Tasks plans your day. Globexia is a town." | grep -q clean
}

test_banned_terms_import() {
  local p; p="$(_rqa_fixture)"
  PYTHONPATH="$PVS_HOME/skills/render-qa/scripts:$PVS_HOME/lib" python3 - "$p" <<'PY'
import sys, pvs
from banned_terms import find_banned
cfg = pvs.load_product(sys.argv[1])
assert find_banned("AcmeTodo and the last app you will ever need, Globex", cfg) == [
    ("AcmeTodo", "legacy_name"), ("the last app you will ever need", "never_say"), ("Globex", "banned")], find_banned
assert find_banned("nothing here", cfg["product"]) == []
PY
}

test_scan_render_flags_worker_pattern() {
  local d; d="${TEST_TMP:-$(mktemp -d)}/flick"; mkdir -p "$d"
  # every third frame from 1 s to 2 s drops to dark: one worker losing an element's state
  ffmpeg -v error -y -f lavfi -i "color=c=gray:s=320x180:d=3:r=30,format=gray,geq=lum='if(eq(mod(N\,3)\,0)*between(N\,30\,60)\,20\,128)'" \
    -c:v libx264 -pix_fmt yuv420p "$d/flicker.mp4"
  out="$(_rqa_py "$(_rqa_s scan_render.py)" "$d/flicker.mp4")" && return 1
  echo "$out" | grep -q "WORKER PATTERN"
}

test_scan_render_clean() {
  local p; p="$(_rqa_fixture)"
  _rqa_py "$(_rqa_s scan_render.py)" "$p/videos/pitch/video/renders/pitch-v1.mp4" | grep -q "outlier frames 0"
}

test_qa_writes_report() {
  local p v mp4; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/pitch-v1.mp4"
  # --no-asr must make the report fail: speech to text is required before delivery
  _rqa_py "$(_rqa_s qa.py)" "$v" "$mp4" --no-asr --no-sheets >/dev/null && return 1
  [ -f "$v/qa/REPORT.json" ] && [ -f "$v/qa/REPORT.md" ] || return 1
  python3 - "$v/qa/REPORT.json" "$(_rqa_sha "$mp4")" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
assert r["sha256"] == sys.argv[2], "sha256"
assert r["draft"] is False, r["draft_reason"]
assert r["mp4"] == "video/renders/pitch-v1.mp4", r["mp4"]
assert r["passed"] is False
c = {x["name"]: x for x in r["checks"]}
assert c["asr"].get("skipped") and not c["asr"]["passed"]
assert c["size"]["passed"] and c["black_frames"]["passed"] and c["worker_pattern"]["passed"]
assert c["voice_overlap"]["passed"] and c["banned_terms_visible"]["passed"]
assert c["camera_zoom"]["passed"] and c["camera_zoom"].get("level") == "info"
PY
}

test_qa_flags_draft_banned_and_zoom() {
  local p v mp4; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/pitch-v1.mp4"
  perl -pi -e 's#<body>#<head><meta name="pvs-draft" content="1"></head><body>#; s#<h1>Acme Tasks</h1>#<h1>Now with Globex sync</h1>#; s#cam\(1.0, 1.2,#cam(1.0, 1.9,#' "$v/video/index.html"
  _rqa_py "$(_rqa_s qa.py)" "$v" "$mp4" --no-asr --no-sheets >/dev/null
  python3 - "$v/qa/REPORT.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
c = {x["name"]: x for x in r["checks"]}
assert r["draft"] is True and "pvs-draft" in r["draft_reason"], r["draft_reason"]
assert not c["banned_terms_visible"]["passed"] and "Globex" in c["banned_terms_visible"]["detail"]
assert c["camera_zoom"]["passed"] and c["camera_zoom"]["level"] == "warn" and "1.9" in c["camera_zoom"]["detail"]
PY
}

test_deliver_refuses_missing_report() {
  local p v; p="$(_rqa_fixture)"; v="$p/videos/pitch"
  ! _rqa_py "$(_rqa_s deliver.py)" "$v" "$v/video/renders/pitch-v1.mp4" 2>/dev/null && [ ! -d "$p/deliveries" ]
}

test_deliver_refuses_failed_report() {
  local p v mp4; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/pitch-v1.mp4"
  _rqa_report "$v" "$mp4" false false
  ! _rqa_py "$(_rqa_s deliver.py)" "$v" "$mp4" 2>/dev/null && [ ! -d "$p/deliveries" ]
}

test_deliver_refuses_draft_and_mismatch() {
  local p v mp4; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/pitch-v1.mp4"
  _rqa_report "$v" "$mp4" true true
  _rqa_py "$(_rqa_s deliver.py)" "$v" "$mp4" 2>/dev/null && return 1
  _rqa_report "$v" "$mp4" true false "0000000000000000000000000000000000000000000000000000000000000000"
  _rqa_py "$(_rqa_s deliver.py)" "$v" "$mp4" 2>/dev/null && return 1
  # a passing report but a BRIEF that lost its signature after QA
  _rqa_report "$v" "$mp4" true false
  perl -pi -e 's/^claims_signed_by: .*/claims_signed_by: ""/' "$v/BRIEF.md"
  _rqa_py "$(_rqa_s deliver.py)" "$v" "$mp4" 2>/dev/null && return 1
  [ ! -d "$p/deliveries" ]
}

test_deliver_accepts_passing_and_never_overwrites() {
  local p v mp4; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/pitch-v1.mp4"
  _rqa_report "$v" "$mp4" true false
  _rqa_py "$(_rqa_s deliver.py)" "$v" "$mp4" >/dev/null || return 1
  [ -f "$p/deliveries/Acme Tasks pitch v1.mp4" ] && [ -f "$p/deliveries/Acme Tasks pitch v1.BRIEF.md" ] || return 1
  cmp -s "$mp4" "$p/deliveries/Acme Tasks pitch v1.mp4" || return 1
  # same bytes again: a no-op
  _rqa_py "$(_rqa_s deliver.py)" "$v" "$mp4" | grep -q "already delivered" || return 1
  # different bytes under the same version: bumped, the delivered v1 untouched
  ffmpeg -v error -y -f lavfi -i "color=c=0x445566:s=320x180:d=3:r=30" -c:v libx264 -pix_fmt yuv420p "$v/video/renders/pitch-v1b.mp4"
  _rqa_report "$v" "$v/video/renders/pitch-v1b.mp4" true false
  _rqa_py "$(_rqa_s deliver.py)" "$v" "$v/video/renders/pitch-v1b.mp4" --archive-previous >/dev/null || return 1
  [ -f "$p/deliveries/Acme Tasks pitch v2.mp4" ] && [ -f "$p/deliveries/previous/Acme Tasks pitch v1.mp4" ] || return 1
  cmp -s "$mp4" "$p/deliveries/previous/Acme Tasks pitch v1.mp4"
}

test_strips_sheets_parity() {
  local p v mp4 d; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/pitch-v1.mp4"; d="$p/out"; mkdir -p "$d"
  _rqa_py "$(_rqa_s strips.py)" "$mp4" "$d" end:1.0:2.0:6 >/dev/null && [ -f "$d/end.jpg" ] || return 1
  _rqa_py "$(_rqa_s sheets.py)" "$mp4" "$d" >/dev/null && [ -f "$d/sheet-01.jpg" ] || return 1
  _rqa_py "$(_rqa_s parity.py)" "$mp4" "$mp4" | grep -q "parity: OK" || return 1
  ffmpeg -v error -y -f lavfi -i "color=c=white:s=320x180:d=3:r=30" -c:v libx264 -pix_fmt yuv420p "$d/other.mp4"
  ! _rqa_py "$(_rqa_s parity.py)" "$mp4" "$d/other.mp4" >/dev/null || return 1
  _rqa_py "$(_rqa_s parity.py)" "$mp4" "$d/other.mp4" --skip 0:3 --end 2.9 | grep -q "nothing to compare"
}

test_qa_full_asr() {
  [ "${PVS_FULL:-0}" = 1 ] || { echo "skipped (set PVS_FULL=1)"; return 0; }
  command -v say >/dev/null || { echo "skipped (no say)"; return 0; }
  local p v mp4; p="$(_rqa_fixture)"; v="$p/videos/pitch"; mp4="$v/video/renders/speech.mp4"
  say -o "$v/n1.aiff" "Acme Tasks plans your day."
  ffmpeg -v error -y -f lavfi -i "color=c=0x334455:s=320x180:d=3:r=30" -i "$v/n1.aiff" \
    -af "adelay=500|500,apad" -c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 -t 3 "$mp4"
  _rqa_py "$(_rqa_s qa.py)" "$v" "$mp4" --no-sheets >/dev/null
  python3 - "$v/qa/REPORT.json" <<'PY'
import json, sys
c = {x["name"]: x for x in json.load(open(sys.argv[1]))["checks"]}
assert c["asr"]["passed"], c["asr"]["detail"]
PY
}

test_edges_flags_cut_word_not_clean_padded_clip() {
  # A clean clip ends in a decay plus padded silence; a cut one is still sounding when the
  # 80 ms fade-out of tts.py pulls it down. Only the cut one may be flagged.
  local v="$TEST_TMP/edges"
  mkdir -p "$v/video/audio/clips" "$v/audio"
  _rqa_py - "$v/video/audio/clips" <<'PY' || fail "could not write the fixture clips"
import sys, wave
import numpy as np
sr = 48000
def tone(sec):
    t = np.arange(int(sec * sr)) / sr
    return 0.5 * (np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 660 * t)) / 1.3
def fade_out(x):
    f = int(0.08 * sr); x[-f:] *= np.linspace(1, 0, f); return x
def save(name, x):
    with wave.open(sys.argv[1] + "/" + name, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
clean = tone(0.8); d = int(0.15 * sr); clean[-d:] *= np.exp(-np.linspace(0, 9, d))
save("N1.wav", fade_out(np.concatenate([clean, np.zeros(int(0.18 * sr))])))
save("N2.wav", fade_out(tone(1.0)))
PY
  cat > "$v/video/index.html" <<'HTML'
<div data-composition-id="main" data-duration="3">
  <audio id="vo-N1" src="audio/clips/N1.wav" data-start="0.2" data-duration="0.98" data-track-index="10"></audio>
  <audio id="vo-N2" src="audio/clips/N2.wav" data-start="1.6" data-duration="1.0" data-track-index="10"></audio>
</div>
HTML
  ffmpeg -v error -y -f lavfi -i "color=c=black:s=160x90:d=3:r=30" -f lavfi -i "anullsrc=r=48000:cl=mono" -t 3 \
    -c:v libx264 -pix_fmt yuv420p -c:a aac "$v/mix.mp4" || fail "ffmpeg fixture failed"
  out="$(_rqa_py "$(_rqa_s edges.py)" "$v/mix.mp4" "$v" 2>&1)" || fail "edges.py failed: $out"
  n1="$(echo "$out" | grep '^N1 ')"; n2="$(echo "$out" | grep '^N2 ')"
  assert_not_contains "$n1" "listen" "clean padded clip flagged"
  assert_contains "$n2" "cut word" "cut clip not flagged"
  assert_contains "$out" "1 edge(s) to listen to"
}
