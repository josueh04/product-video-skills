"""Turn per-frame OCR (ocr.swift output) into a timeline of stable on-screen text.

    python3 ocr_events.py <ocr.jsonl> <out.txt> [--fps 10] [--start 0] [--min-frames 3]
        [--max-gap 1.0] [--min-len 3] [--region NAME=x0,y0,x1,y1[@t0[-t1]]] ...

Each output line is "first-last [region] text", for example
    110.6- 125.0 [panel] Writing the plan...
Frames are named %05d.jpg (or .png) from 1, as ffmpeg writes them, so frame n is at
start + (n - 1) / fps seconds. A text that disappears for more than --max-gap seconds starts a
new span. --region tags text whose box starts inside a normalized rectangle (0 to 1, y from the
top), optionally only between t0 and t1 seconds; the first matching region wins, everything
else is "screen". Text seen in fewer than --min-frames frames is dropped as OCR noise.
"""
import argparse
import json
import re
import sys
from typing import Dict, List, Optional, Tuple


def parse_region(spec: str):
    m = re.fullmatch(r"([\w-]+)=([\d.]+),([\d.]+),([\d.]+),([\d.]+)(?:@([\d.]+)(?:-([\d.]+))?)?", spec)
    if not m:
        raise argparse.ArgumentTypeError(f"bad region {spec!r}: use NAME=x0,y0,x1,y1[@t0[-t1]]")
    g = m.groups()
    return (g[0], float(g[1]), float(g[2]), float(g[3]), float(g[4]),
            float(g[5]) if g[5] else None, float(g[6]) if g[6] else None)


def region_of(regions, t: float, x: float, y: float) -> str:
    for name, x0, y0, x1, y1, t0, t1 in regions:
        if t0 is not None and t < t0:
            continue
        if t1 is not None and t > t1:
            continue
        if x0 <= x <= x1 and y0 <= y <= y1:
            return name
    return "screen"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ocr_jsonl")
    ap.add_argument("out")
    ap.add_argument("--fps", type=float, default=10.0)
    ap.add_argument("--start", type=float, default=0.0, help="seconds of the first frame (frames.sh --start)")
    ap.add_argument("--min-frames", type=int, default=3)
    ap.add_argument("--max-gap", type=float, default=1.0)
    ap.add_argument("--min-len", type=int, default=3)
    ap.add_argument("--region", type=parse_region, action="append", default=[])
    a = ap.parse_args()

    spans: Dict[Tuple[str, str], List[List[float]]] = {}  # key -> [[first, last, count], ...]
    frames = 0
    with open(a.ocr_jsonl, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            r = json.loads(raw)
            m = re.match(r"(\d+)", r["f"])
            if not m:
                continue
            frames += 1
            t = a.start + (int(m.group(1)) - 1) / a.fps
            seen_now = set()
            for line in r.get("lines", []):
                txt = re.sub(r"\s+", " ", line.get("t", "")).strip()
                if len(txt) < a.min_len:
                    continue
                key = (region_of(a.region, t, line.get("x", 0), line.get("y", 0)), txt)
                if key in seen_now:
                    continue
                seen_now.add(key)
                lst = spans.setdefault(key, [])
                if lst and t - lst[-1][1] <= a.max_gap + 1e-9:
                    lst[-1][1] = t
                    lst[-1][2] += 1
                else:
                    lst.append([t, t, 1])
    rows = []
    for (reg, txt), lst in spans.items():
        for first, last, count in lst:
            if count >= a.min_frames:
                rows.append((first, last, reg, txt))
    rows.sort(key=lambda x: (x[0], x[2], x[1]))
    with open(a.out, "w", encoding="utf-8") as f:
        for t0, t1, reg, txt in rows:
            f.write(f"{t0:6.1f}-{t1:6.1f} [{reg}] {txt}\n")
    print(f"{len(rows)} stable text spans from {frames} frames -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
