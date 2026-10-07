"""Contact sheets: one labelled frame per second, 4x4 per sheet, for a human pass over every scene.

    bin/pvs-py skills/render-qa/scripts/sheets.py <video.mp4> <outdir> [--fps 1] [--cols 4] [--rows 4]

Look at every sheet. The time label sits in the top-left corner and can cover a title:
pull the full frame (ffmpeg -ss <t> -frames:v 1) before calling a title cut.
"""
import argparse
import sys
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw

import qalib

TW, TH = 480, 270


def make_sheets(mp4: Path, outdir: Path, fps: float = 1.0, cols: int = 4, rows: int = 4) -> List[Path]:
    outdir = qalib.ensure_dir(outdir)
    for old in outdir.glob("sheet-*.jpg"):
        old.unlink()
    per = cols * rows
    paths = []
    with qalib.tmpdir() as td:
        qalib.run([qalib.FFMPEG, "-v", "error", "-y", "-i", str(mp4), "-vf",
                   f"fps={fps},scale={TW}:{TH}", str(Path(td) / "f%05d.png")], check=True)
        frames = sorted(Path(td).glob("f*.png"))
        for s in range(0, len(frames), per):
            batch = frames[s:s + per]
            nrows = (len(batch) + cols - 1) // cols
            sheet = Image.new("RGB", (TW * cols, TH * nrows), "black")
            for k, f in enumerate(batch):
                im = Image.open(f).convert("RGB")
                d = ImageDraw.Draw(im)
                t = (s + k + 0.5) / fps  # the fps filter picks the frame nearest each period's middle
                d.rectangle([0, 0, 66, 18], fill="black")
                d.text((4, 3), f"{t:6.1f}s", fill="yellow")
                sheet.paste(im, ((k % cols) * TW, (k // cols) * TH))
            p = outdir / f"sheet-{s // per + 1:02d}.jpg"
            sheet.save(p, quality=86)
            paths.append(p)
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="1 fps contact sheets of a render.")
    ap.add_argument("mp4")
    ap.add_argument("outdir")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=4)
    a = ap.parse_args(argv)
    paths = make_sheets(Path(a.mp4), Path(a.outdir), a.fps, a.cols, a.rows)
    print(f"{len(paths)} contact sheet(s) in {a.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
