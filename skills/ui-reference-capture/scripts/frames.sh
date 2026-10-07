#!/usr/bin/env bash
# Extract frames from a screen recording in two sizes: small thumbs to detect changes, and
# frames at the app's logical width for OCR, measurement and parity.
#
#   frames.sh <recording> <out_dir> [--fps 10] [--logical-width W] [--thumb-width 377]
#             [--start SECONDS] [--end SECONDS]
#
# Writes <out_dir>/thumb/%05d.jpg, <out_dir>/logical/%05d.jpg and <out_dir>/probe.json.
# Frame n is at start + (n - 1) / fps seconds. A retina recording is 2x: pass
# --logical-width <pixel width / 2> so one frame pixel is one CSS px of the app.
set -euo pipefail

usage() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -ge 2 ] || usage
rec="$1"; out="$2"; shift 2
fps=10; lw=""; tw=377; start=""; end=""
while [ $# -gt 0 ]; do
  case "$1" in
    --fps) fps="$2"; shift 2 ;;
    --logical-width) lw="$2"; shift 2 ;;
    --thumb-width) tw="$2"; shift 2 ;;
    --start) start="$2"; shift 2 ;;
    --end) end="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown option $1" >&2; usage ;;
  esac
done
command -v ffmpeg >/dev/null || { echo "ffmpeg not found (brew install ffmpeg)" >&2; exit 1; }
[ -f "$rec" ] || { echo "no such file: $rec (macOS recording names contain a narrow no-break space before AM/PM: use a glob)" >&2; exit 1; }

mkdir -p "$out/thumb" "$out/logical"
ffprobe -v error -print_format json -show_format -show_streams "$rec" > "$out/probe.json"
read -r w h dur < <(python3 - "$out/probe.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
v = next(s for s in d["streams"] if s.get("codec_type") == "video")
print(v["width"], v["height"], d["format"].get("duration", "0"))
PY
)
if [ -z "$lw" ]; then
  lw="$w"
  echo "note: no --logical-width, using the pixel width $w (a retina recording needs $((w / 2)))" >&2
fi
range=()
[ -n "$start" ] && range+=(-ss "$start")
[ -n "$end" ] && range+=(-to "$end")
ffmpeg -v error -y ${range[@]+"${range[@]}"} -i "$rec" -vf "fps=$fps,scale=$tw:-2" -q:v 3 "$out/thumb/%05d.jpg"
ffmpeg -v error -y ${range[@]+"${range[@]}"} -i "$rec" -vf "fps=$fps,scale=$lw:-2" -q:v 4 "$out/logical/%05d.jpg"
n=$(ls "$out/logical" | wc -l | tr -d ' ')
cat > "$out/frames.json" <<JSON
{"recording": "$(basename "$rec")", "pixel_size": [$w, $h], "duration_s": $dur, "fps": $fps, "logical_width": $lw, "start_s": ${start:-0}, "frames": $n}
JSON
echo "$n frames at $fps fps (${w}x${h}, ${dur}s) -> $out/logical (width $lw) and $out/thumb (width $tw)"
