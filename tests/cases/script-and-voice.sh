# Tests for skills/script-and-voice: lines.tsv parsing, pronounce mapping, timing alignment,
# check_script.py, typing tracks, the missing-key error, and a real `say` run when possible.
# Sourced by tests/run.sh, which calls each test_* function in a subshell. No network.

_sv_scripts() { echo "$PVS_HOME/skills/script-and-voice/scripts"; }
_sv_py() { "$PVS_HOME/bin/pvs-py" "$@"; }

# A product with one video. $1: lines.tsv body (printf format).
_sv_setup() {
  T="$(mktemp -d)"
  trap 'rm -rf "$T"' EXIT
  mkdir -p "$T/prod/videos/pitch/audio"
  cat > "$T/prod/product.yaml" <<'YAML'
product:
  name: Acme Tasks
  slug: acme
  never_say: ["the last app you will ever need"]
  names: {Acme Tasks: ["AcmeTodo"]}
  pronounce: {Acme: AK-mee}
  banned_terms: ["Globex"]
cast:
  company: {name: Northwind Bakery}
  people: [{role: owner, name: Maya Lindqvist}]
voice:
  provider: say
  roles:
    narrator: {voice: "<elevenlabs voice id>", model: eleven_multilingual_v2, say_voice: Samantha}
  clip_lufs: -18
YAML
  printf -- '---\ntitle: Test\nvideo: pitch\nformat: pitch\n---\n' > "$T/prod/videos/pitch/BRIEF.md"
  V="$T/prod/videos/pitch"
  printf "${1:-id\trole\tspeed\ttext\nN1\tnarrator\t1.0\tThis is Acme Tasks.\n}" > "$V/audio/lines.tsv"
}

test_sv_lines_tsv_parsing() {
  _sv_setup 'id\trole\tspeed\ttext\n# a comment\n\nN1\tnarrator\t1.0\tFirst line.\nN2\tnarrator\t\tNo speed given.\nbad row\nN3\tnarrator\tfast\tSpeed is not a number.\n'
  _sv_py - "$V/audio/lines.tsv" <<'PY' || return 1
import sys
sys.path.insert(0, __import__("os").environ["PVS_HOME"] + "/skills/script-and-voice/scripts")
import check_script as cs
from pathlib import Path
rows, errors = cs.parse_rows(Path(sys.argv[1]))
assert [r["id"] for r in rows] == ["N1", "N2"], rows
assert rows[1]["speed"] == 1.0, rows[1]
assert len(errors) == 2 and "4 tab-separated" in errors[0] and "not a number" in errors[1], errors
PY
}

test_sv_pronounce_mapping_and_canonical_timings() {
  _sv_py - <<'PY' || return 1
import os, sys
sys.path.insert(0, os.environ["PVS_HOME"] + "/skills/script-and-voice/scripts")
import voicelib as vl
product = {"product": {"pronounce": {"Acme": "AK-mee", "AI Notes": {"say": "A.I. Notes", "vowel": "ae"}}}}
pm = vl.pronounce_map(product)
assert pm == {"Acme": "AK-mee", "AI Notes": "A.I. Notes"}, pm
text = "Meet Acme, and AI Notes. Acmeish stays."
spoken, spans = vl.respell(text, pm)
assert spoken == "Meet AK-mee, and A.I. Notes. Acmeish stays.", spoken
# Provider words for the spoken text, as an ASR would return them (punctuation and case differ).
timed = [{"w": w, "s": i * 0.5, "e": i * 0.5 + 0.4} for i, w in
         enumerate(["meet", "AK-mee", "and", "A.I.", "notes", "acmeish", "stays"])]
words = vl.canonical_timings(timed, text, pm)
assert [w["w"] for w in words] == ["Meet", "Acme,", "and", "AI", "Notes.", "Acmeish", "stays."], words
acme = words[1]
assert acme["say"] == "AK-mee," and (acme["s"], acme["e"]) == (0.5, 0.9), acme
assert "say" not in words[0] and "say" not in words[5]
assert words[3]["say"] == "A.I." and words[3]["s"] == 1.5, words[3]
s = [w["s"] for w in words]
assert s == sorted(s), s
PY
}

test_sv_alignment_survives_asr_differences() {
  _sv_py - <<'PY' || return 1
import os, sys
sys.path.insert(0, os.environ["PVS_HOME"] + "/skills/script-and-voice/scripts")
import voicelib as vl
text = "Pick it up at ten a.m. tomorrow."
timed = [{"w": "Pick", "s": 0.0, "e": 0.2}, {"w": "it", "s": 0.25, "e": 0.3}, {"w": "up", "s": 0.35, "e": 0.5},
         {"w": "at", "s": 0.55, "e": 0.6}, {"w": "10am", "s": 0.65, "e": 1.2}, {"w": "tomorrow.", "s": 1.3, "e": 1.9}]
words = vl.align_words(timed, text)
assert [w["w"] for w in words] == text.split(), words
ten, am = words[4], words[5]
assert 0.6 <= ten["s"] < am["s"] <= 1.2 and am["e"] <= 1.2, (ten, am)
assert words[-1]["s"] == 1.3
# ElevenLabs character alignment to words
a = {"characters": list("Hi there"), "character_start_times_seconds": [0, .1, .2, .3, .4, .5, .6, .7],
     "character_end_times_seconds": [.1, .2, .3, .4, .5, .6, .7, .8]}
assert vl.char_alignment_words(a) == [{"w": "Hi", "s": 0, "e": .2}, {"w": "there", "s": .3, "e": .8}]
# head trim shifts and clamps
assert vl.shift_words([{"w": "x", "s": 0.1, "e": 3.0}], 0.2, 2.5) == [{"w": "x", "s": 0.0, "e": 2.5}]
PY
}

test_sv_check_script_errors() {
  _sv_setup 'N1\tnarrator\t1.0\tAcmeTodo is the last app you will ever need.\nN1\thost\t2\tMeet AK-mee at 10.\nN3\tnarrator\t1.0\tGlobex was here.\n'
  out="$(_sv_py "$(_sv_scripts)/check_script.py" "$V" 2>&1)" && { echo "expected failure"; return 1; }
  for want in "legacy name 'AcmeTodo'" "never say" "duplicate id" "role 'host'" "speed 2.0" \
              "TTS respelling of 'Acme'" "banned 'Globex'" "warning: N1 (line 2): digits"; do
    case "$out" in *"$want"*) ;; *) echo "missing: $want"; echo "$out"; return 1 ;; esac
  done
  _sv_setup 'id\trole\tspeed\ttext\nN1\tnarrator\t0.95\tThis is Acme Tasks, the to-do list that plans your day.\n'
  _sv_py "$(_sv_scripts)/check_script.py" "$V" >/dev/null || { echo "clean script failed"; return 1; }
}

test_sv_typing_track_deterministic_and_whoosh_refused() {
  _sv_setup
  _sv_py - "$V" <<'PY' || return 1
import os, sys
sys.path.insert(0, os.environ["PVS_HOME"] + "/skills/script-and-voice/scripts")
import make_sfx as m
try:
    m.library_dir()
except SystemExit:
    print("skip: no SFX library installed"); sys.exit(0)
from pathlib import Path
v = Path(sys.argv[1])
a = m.typing_track("Plan the Saturday orders", 2.0, 14, video_dir=v)
first = (v / a["src"]).read_bytes()
b = m.typing_track("Plan the Saturday orders", 5.0, 14, video_dir=v)
assert a["src"] == b["src"] and (v / b["src"]).read_bytes() == first, "not deterministic"
assert abs(a["dur"] - 24 / 14) < 0.01 and b["start"] == 5.0 and a["strokes"] >= 20, a
c = m.library_sfx("click", 1.0, video_dir=v)
assert (v / c["src"]).exists() and (v / "audio/sfx/CREDITS.md").exists()
try:
    m.library_sfx("whoosh", 1.0, video_dir=v)
    raise AssertionError("whoosh accepted")
except ValueError as e:
    assert "white noise" in str(e)
PY
}

test_sv_missing_key_is_clear_and_keeps_take() {
  _sv_setup
  sed -i '' 's/<elevenlabs voice id>/test-voice-id/' "$T/prod/product.yaml" 2>/dev/null \
    || sed -i 's/<elevenlabs voice id>/test-voice-id/' "$T/prod/product.yaml"
  # A workbench copy without .env, so no real key can be found and nothing reaches the network.
  mkdir -p "$T/home/lib" && cp "$PVS_HOME/lib/pvs.py" "$T/home/lib/"
  mkdir -p "$V/audio/raw" && echo '{"hash": "x", "file": "N1.mp3", "spoken": "x", "words": []}' > "$V/audio/raw/N1.json"
  echo keep > "$V/audio/raw/N1.mp3"
  out="$(env -u ELEVENLABS_API_KEY PVS_HOME="$T/home" PYTHONPATH="$T/home/lib" \
         python3 "$(_sv_scripts)/tts.py" "$V" --provider elevenlabs --force 2>&1)" && { echo "expected failure"; return 1; }
  case "$out" in *".env"*"voice.provider: say"*) ;; *) echo "unclear message: $out"; return 1 ;; esac
  [ "$(cat "$V/audio/raw/N1.mp3")" = keep ] || { echo "current take was moved or lost"; return 1; }
}

test_sv_say_end_to_end() {
  command -v say >/dev/null || { echo "skip: no macOS say"; return 0; }
  python3 -c "import whisper" 2>/dev/null || [ -x "$PVS_HOME/.venv/bin/python" ] || { echo "skip: no whisper"; return 0; }
  model=""
  for m in tiny.en base.en tiny base; do [ -f "$HOME/.cache/whisper/$m.pt" ] && { model="$m"; break; }; done
  if [ -z "$model" ]; then
    [ "${PVS_FULL:-}" = 1 ] || { echo "skip: no small whisper model cached (PVS_FULL=1 downloads base.en)"; return 0; }
    model=base.en
  fi
  _sv_setup 'id\trole\tspeed\ttext\nN1\tnarrator\t1.0\tThis is Acme Tasks.\nN2\tnarrator\t1.1\tMaya plans her day.\n'
  out="$(PVS_WHISPER_MODEL=$model _sv_py "$(_sv_scripts)/tts.py" "$V" 2>&1)" || { echo "$out"; return 1; }
  _sv_py - "$V" <<'PY' || return 1
import json, sys, wave, subprocess
from pathlib import Path
v = Path(sys.argv[1]) / "audio"
tim = json.loads((v / "timings.json").read_text())
assert list(tim) == ["N1", "N2"], tim
for k, n in (("N1", 4), ("N2", 4)):
    e = tim[k]
    with wave.open(str(v / "clips" / f"{k}.wav")) as w:
        assert w.getframerate() == 48000 and w.getnchannels() == 1
        assert abs(w.getnframes() / 48000 - e["dur"]) < 0.01
    assert len(e["words"]) == n and all(0 <= x["s"] <= x["e"] <= e["dur"] for x in e["words"]), e
acme = tim["N1"]["words"][2]
assert acme["w"] == "Acme" and acme["say"] == "AK-mee", acme
err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(v / "clips/N1.wav"), "-af", "ebur128",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
lufs = float(err[err.rfind("Summary:"):].split("I:")[1].split("LUFS")[0])
assert abs(lufs + 18) <= 1.0, lufs
assert (v / "raw" / "N1.aiff").exists() and (v / "raw" / "cache.json").exists()
PY
  again="$(PVS_WHISPER_MODEL=$model _sv_py "$(_sv_scripts)/tts.py" "$V" 2>&1)" || return 1
  case "$again" in *"0 built (0 new takes from say), 2 unchanged"*) ;; *) echo "cache miss: $again"; return 1 ;; esac
}

test_sv_pronounce_check_cast_names_need_exact_hearing() {
  # "Mya" passes the fuzzy brand match for "Maya" (ratio 0.86) but is another name on screen.
  "$PVS_HOME/bin/pvs-py" - "$PVS_HOME/skills/script-and-voice/scripts" <<'PY' || fail "cast name check"
import sys
sys.path.insert(0, sys.argv[1])
import pronounce_check as pc
product = {"cast": {"people": [{"name": "Maya Lindqvist"}, {"name": "Omar Haddad"}]}}
names = pc.cast_names(product)
assert names[:2] == ["Maya Lindqvist", "Omar Haddad"] and "Maya" in names and "Omar" in names, names
assert pc.heard("Maya", "Mya runs Northwind Bakery.")[0], "fuzzy match should accept Mya"
assert not pc.heard_exact("Maya", "Mya runs Northwind Bakery."), "Mya must not count as Maya"
assert pc.heard_exact("Maya", "maya, runs Northwind Bakery.")
assert pc.heard_exact("Omar Haddad", "a call from Omar Haddad today")
assert not pc.heard_exact("Omar Haddad", "a call from Omar Hadad today")
PY
}
