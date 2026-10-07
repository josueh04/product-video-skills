"""Fast check of a rendered MP4: worker-pattern flicker, black frames and loudness.

    bin/pvs-py skills/render-qa/scripts/scan_render.py <video.mp4> [--json]

Run it right after every render, before the full QA. A run of one-frame outliers that all
share the same frame index mod 3 means one of the three parallel render workers lost an
element's state: a seek-safety bug in the timeline (see the seek-safe-motion skill).
Isolated outliers during scrolls or blur racks are usually fine but worth a strip.

Exit 1 on a worker pattern or a black frame outside the first 1 s and the last 2 s.
"""
import argparse
import json
import sys
from pathlib import Path

import qalib


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mp4")
    ap.add_argument("--json", action="store_true", help="print the numbers as JSON")
    a = ap.parse_args(argv)
    mp4 = Path(a.mp4)
    info = qalib.probe(mp4)
    st = qalib.frame_stats(mp4)
    out = qalib.outlier_runs(st, info["fps"])
    bl = qalib.black_frames(st, info["fps"], info["duration"])
    ld = qalib.loudness(mp4) if info["audio"] else {"I": None, "TP": None, "LRA": None}
    worker = [r for r in out["runs"] if r["worker_pattern"]]
    if a.json:
        print(json.dumps({"probe": info, "outliers": out, "black": bl, "loudness": ld}, indent=1))
    else:
        print(f"{mp4.name}: {info['width']}x{info['height']} {info['fps']:g} fps {info['duration']:.2f} s")
        print(f"frames {out['frames']}, outlier frames {out['outliers']} in {len(out['runs'])} runs")
        for r in out["runs"]:
            flag = "  <-- WORKER PATTERN (seek-safety bug)" if r["worker_pattern"] else ""
            print(f"  t={r['t0']:7.2f}-{r['t1']:7.2f}s  n={r['n']:3d}  mod3={r['mod3']}  max={r['max']:.2f}{flag}")
        print(f"black frames: {bl['total']} total, {bl['mid']} outside the first {qalib.BLACK_HEAD_S:g} s "
              f"and last {qalib.BLACK_TAIL_S:g} s" + (f" at {bl['spans'][:5]}" if bl["spans"] else ""))
        print(f"loudness I={ld['I']} LUFS, true peak={ld['TP']} dBFS" if info["audio"] else "audio: none")
    return 1 if worker or bl["mid"] else 0


if __name__ == "__main__":
    sys.exit(main())
