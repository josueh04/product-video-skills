"""Labelled frame strips around transitions: 5 to 6 fps catches what 1 fps contact sheets miss.

    bin/pvs-py skills/render-qa/scripts/strips.py <video.mp4> <outdir> name:t0:t1[:fps] [...]

Example: strips.py renders/pitch-v2.mp4 qa/strips lockup:57.5:60 modal:21:23.4:8
Each window becomes one 4-column sheet with the time stamped on every frame. Make one for
every modal open and close, scroll, camera move, chapter change, beat changed in this
version, and the end screen to lockup handoff. A 1 fps pass once missed a 0.3 s UI flash
before a lockup and a clipped modal; a strip at 6 fps showed both.
"""
import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw

import qalib

TW, TH = 640, 360


def parse_spec(spec: str) -> Tuple[str, float, float, float]:
    parts = spec.split(":")
    if len(parts) not in (3, 4):
        raise ValueError(f"bad strip spec {spec!r}: expected name:t0:t1[:fps]")
    name, t0, t1 = parts[0], float(parts[1]), float(parts[2])
    fps = float(parts[3]) if len(parts) == 4 else 6.0
    if t1 <= t0 or fps <= 0:
        raise ValueError(f"bad strip spec {spec!r}: need t1 > t0 and fps > 0")
    return name, t0, t1, fps


def make_strip(mp4: Path, outdir: Path, name: str, t0: float, t1: float, fps: float = 6.0,
               cols: int = 4, max_frames: int = 48) -> Tuple[Path, int]:
    outdir = qalib.ensure_dir(outdir)
    t0 = max(0.0, t0)
    with qalib.tmpdir() as td:
        # One decode per window; -ss before -i is frame-accurate when re-encoding.
        qalib.run([qalib.FFMPEG, "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0 + 0.5 / fps:.3f}",
                   "-i", str(mp4), "-vf", f"fps={fps}:start_time=0,scale={TW}:{TH}",
                   str(Path(td) / "f%04d.png")], check=True)
        files = sorted(Path(td).glob("f*.png"))[:max_frames]
        frames: List[Image.Image] = []
        for i, f in enumerate(files):
            im = Image.open(f).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 90, 20], fill="black")
            d.text((4, 4), f"{t0 + i / fps:7.3f}s", fill="yellow")
            frames.append(im)
    rows = max(1, (len(frames) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * TW, rows * TH), "black")
    for k, im in enumerate(frames):
        sheet.paste(im, ((k % cols) * TW, (k // cols) * TH))
    p = outdir / f"{name}.jpg"
    sheet.save(p, quality=85)
    return p, len(frames)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Frame strips around transitions.")
    ap.add_argument("mp4")
    ap.add_argument("outdir")
    ap.add_argument("specs", nargs="+", metavar="name:t0:t1[:fps]")
    a = ap.parse_args(argv)
    for spec in a.specs:
        try:
            name, t0, t1, fps = parse_spec(spec)
        except ValueError as e:
            ap.error(str(e))
        p, n = make_strip(Path(a.mp4), Path(a.outdir), name, t0, t1, fps)
        print(f"{p}  {n} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
