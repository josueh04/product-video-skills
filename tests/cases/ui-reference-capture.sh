# Tests for skills/ui-reference-capture scripts on generated frames and fixture JSONL.

_rc_dir() { echo "$PVS_HOME/skills/ui-reference-capture/scripts"; }
_rc_py() { "$PVS_HOME/bin/pvs-py" "$@"; }
_rc_tmp() { T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT; }

# Solid-color PNG frames with a box, named %05d.png like ffmpeg output.
_rc_frames() {
  _rc_py - "$1" "$2" <<'PY'
import sys
from pathlib import Path
from PIL import Image, ImageDraw
out, n = Path(sys.argv[1]), int(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for i in range(1, n + 1):
    im = Image.new("RGB", (200, 100), (20 * i % 255, 40, 90))
    ImageDraw.Draw(im).rectangle([20, 20, 80, 60], fill=(250, 250, 250))
    im.save(out / f"{i:05d}.png")
PY
}

test_ocr_events_builds_timeline_with_regions_and_gaps() {
  _rc_tmp
  _rc_py - "$T/ocr.jsonl" <<'PY'
import json, sys
rows = []
for n in range(1, 21):
    lines = [{"t": "x", "x": 0.1, "y": 0.1, "w": 0.01, "h": 0.01}]
    if n <= 5 or n >= 12:
        lines.append({"t": "Plan  my day", "x": 0.1, "y": 0.2, "w": 0.2, "h": 0.03})
    if n >= 8:
        lines.append({"t": "Suggested tasks", "x": 0.7, "y": 0.3, "w": 0.2, "h": 0.03})
    if n == 9:
        lines.append({"t": "noise text", "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.03})
    rows.append(json.dumps({"f": f"{n:05d}.jpg", "lines": lines}))
open(sys.argv[1], "w").write("\n".join(rows) + "\n")
PY
  _rc_py "$(_rc_dir)/ocr_events.py" "$T/ocr.jsonl" "$T/timeline.txt" --fps 10 --max-gap 0.3 --region "panel=0.6,0,1,1@0.5" >/dev/null || return 1
  grep -qx "   0.0-   0.4 \[screen\] Plan my day" "$T/timeline.txt" || { cat "$T/timeline.txt"; return 1; }
  grep -qx "   1.1-   1.9 \[screen\] Plan my day" "$T/timeline.txt" || { cat "$T/timeline.txt"; return 1; }
  grep -qx "   0.7-   1.9 \[panel\] Suggested tasks" "$T/timeline.txt" || { cat "$T/timeline.txt"; return 1; }
  grep -q "noise" "$T/timeline.txt" && return 1
  grep -q "\] x$" "$T/timeline.txt" && return 1
  return 0
}

test_pair_stacks_regions_and_reports_diff() {
  _rc_tmp
  _rc_frames "$T/f" 1
  out="$(_rc_py "$(_rc_dir)/pair.py" "$T/f/00001.png" "$T/f/00001.png" 10 10 50 40 "$T/pair.png" --ref-scale 2 --logical-width 100 --render-width 200)" || return 1
  echo "$out" | grep -q "\[0.0, 0.0, 0.0\]" || { echo "$out"; return 1; }
  _rc_py -c "from PIL import Image; im=Image.open('$T/pair.png'); assert im.size==(80,130), im.size" || return 1
  _rc_py "$(_rc_dir)/pair.py" "$T/f/00001.png" "$T/f/00001.png" 0 0 500 40 "$T/bad.png" --logical-width 100 --render-width 200 2>/dev/null && return 1
  return 0
}

test_grid_sheet_splits_and_overlay_draws() {
  _rc_tmp
  _rc_frames "$T/f" 5
  _rc_py "$(_rc_dir)/grid.py" sheet "$T/sheet.png" "$T/f" --cols 2 --width 100 --per-sheet 4 --fps 10 >/dev/null || return 1
  [ -f "$T/sheet-01.png" ] && [ -f "$T/sheet-02.png" ] || return 1
  _rc_py -c "from PIL import Image; im=Image.open('$T/sheet-01.png'); assert im.size==(218,150), im.size" || return 1
  _rc_py "$(_rc_dir)/grid.py" overlay "$T/f/00001.png" "$T/ov.png" --scale 2 --step 10 >/dev/null || return 1
  _rc_py -c "from PIL import Image; im=Image.open('$T/ov.png').convert('RGB'); assert im.getpixel((40,90))!=im.getpixel((41,90))" || return 1
}

test_recover_transcript_images_decodes_and_guards_repo() {
  _rc_tmp
  _rc_frames "$T/f" 1
  _rc_py - "$T/f/00001.png" "$T/session.jsonl" <<'PY'
import base64, json, sys
b64 = base64.b64encode(open(sys.argv[1], "rb").read()).decode()
img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}
lines = [
    {"message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "screenshot", "input": {"page": "board"}}]}},
    {"timestamp": "2026-01-01T00:00:00Z", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": [img]}]}},
    {"message": {"role": "user", "content": [img, {"type": "text", "text": "this looks off"}]}},
    "not json",
]
open(sys.argv[2], "w").write("\n".join(l if isinstance(l, str) else json.dumps(l) for l in lines) + "\n")
PY
  _rc_py "$(_rc_dir)/recover_transcript_images.py" "$T/session.jsonl" "$T/out" >/dev/null || return 1
  [ -f "$T/out/001_L1.png" ] && [ -f "$T/out/002_L2.png" ] || { ls "$T/out"; return 1; }
  cmp -s "$T/out/001_L1.png" "$T/f/00001.png" || return 1
  grep -q "screenshot" "$T/out/index.tsv" && grep -q "pasted" "$T/out/index.tsv" || return 1
  _rc_py "$(_rc_dir)/recover_transcript_images.py" "$T/session.jsonl" "$T/only" --tool screenshot >/dev/null || return 1
  [ "$(ls "$T/only" | grep -c png)" = "1" ] || return 1
  git init -q "$T/repo"
  _rc_py "$(_rc_dir)/recover_transcript_images.py" "$T/session.jsonl" "$T/repo/shots" >/dev/null 2>&1 && return 1
  return 0
}

test_frames_sh_extracts_two_sizes() {
  command -v ffmpeg >/dev/null || { echo "skip: no ffmpeg"; return 0; }
  _rc_tmp
  ffmpeg -v error -f lavfi -i testsrc=size=400x200:rate=30 -t 1 -pix_fmt yuv420p "$T/rec.mp4" || return 1
  bash "$(_rc_dir)/frames.sh" "$T/rec.mp4" "$T/fr" --fps 5 --logical-width 200 --thumb-width 100 >/dev/null 2>&1 || return 1
  [ "$(ls "$T/fr/logical" | wc -l | tr -d ' ')" = "5" ] || return 1
  _rc_py -c "from PIL import Image; assert Image.open('$T/fr/logical/00001.jpg').size==(200,100); assert Image.open('$T/fr/thumb/00001.jpg').size==(100,50)" || return 1
  grep -q '"logical_width": 200' "$T/fr/frames.json" || return 1
}

test_ocr_sh_platform_gate() {
  if [ "$(uname -s)" != "Darwin" ]; then
    bash "$(_rc_dir)/ocr.sh" /nonexistent /dev/null 2>/dev/null; [ $? -eq 2 ] || return 1
    return 0
  fi
  [ "${PVS_FULL:-0}" = "1" ] || { echo "skip: OCR compile runs with PVS_FULL=1"; return 0; }
  _rc_tmp
  _rc_py - "$T/f" <<'PY'
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
out = Path(sys.argv[1]); out.mkdir(parents=True)
im = Image.new("RGB", (800, 200), "white")
ImageDraw.Draw(im).text((40, 70), "Plan my day", fill="black", font=ImageFont.load_default(size=48))
im.save(out / "00001.png")
PY
  PVS_CACHE="$T/cache" bash "$(_rc_dir)/ocr.sh" "$T/f" "$T/ocr.jsonl" >/dev/null 2>&1 || return 1
  grep -q "Plan my day" "$T/ocr.jsonl" || { cat "$T/ocr.jsonl"; return 1; }
}
