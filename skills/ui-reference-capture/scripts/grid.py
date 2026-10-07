"""Frame grids: contact sheets of many frames, or a measurement grid over one frame.

    python3 grid.py sheet <out.png> <image|dir> ... [--cols 4] [--width 480] [--every 1]
        [--labels time|name|none] [--fps 10] [--start 0] [--per-sheet 32]
    python3 grid.py overlay <frame.png> <out.png> [--scale 2] [--step 10] [--major 5]

sheet: tiles frames in order (folders are expanded to their .jpg and .png files, sorted), with
each frame's time (from its %05d number, fps and start) or file name under it. More frames than
--per-sheet write <out>-01.png, <out>-02.png and so on. Use it to read a whole recording at a
glance, or to review a phase at 10 fps.
overlay: draws a grid every --step logical px over a frame that has --scale image px per
logical px (2 for a retina capture), labeled every --major lines, to measure positions and
sizes in the app's own units.
"""
import argparse
import re
import sys
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

EXTS = {".jpg", ".jpeg", ".png"}


def expand(paths: List[str]) -> List[Path]:
    out: List[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(q for q in p.iterdir() if q.suffix.lower() in EXTS)
        elif p.is_file():
            out.append(p)
        else:
            raise SystemExit(f"not found: {p}")
    return out


def label_for(p: Path, mode: str, fps: float, start: float) -> str:
    if mode == "none":
        return ""
    if mode == "time":
        m = re.match(r"(\d+)", p.stem)
        if m:
            return f"{start + (int(m.group(1)) - 1) / fps:.1f}s"
    return p.name


def sheet(a) -> int:
    files = expand(a.inputs)[:: max(1, a.every)]
    if not files:
        print("no frames", file=sys.stderr)
        return 1
    font = ImageFont.load_default()
    pad, lab = 6, (16 if a.labels != "none" else 0)
    out = Path(a.out)
    chunks = [files[i:i + a.per_sheet] for i in range(0, len(files), a.per_sheet)]
    written = []
    for n, chunk in enumerate(chunks, 1):
        first = Image.open(chunk[0])
        th = round(first.height * a.width / first.width)
        cols = min(a.cols, len(chunk))
        rows = (len(chunk) + cols - 1) // cols
        im = Image.new("RGB", (cols * (a.width + pad) + pad, rows * (th + lab + pad) + pad), (24, 24, 27))
        d = ImageDraw.Draw(im)
        for i, p in enumerate(chunk):
            x, y = pad + (i % cols) * (a.width + pad), pad + (i // cols) * (th + lab + pad)
            im.paste(Image.open(p).convert("RGB").resize((a.width, th)), (x, y))
            text = label_for(p, a.labels, a.fps, a.start)
            if text:
                d.text((x + 2, y + th + 2), text, fill=(230, 230, 230), font=font)
        dest = out if len(chunks) == 1 else out.with_name(f"{out.stem}-{n:02d}{out.suffix}")
        im.save(dest)
        written.append(dest)
    print(f"{len(files)} frames -> {', '.join(str(w) for w in written)}")
    return 0


def overlay(a) -> int:
    im = Image.open(a.frame).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    font = ImageFont.load_default()
    px = a.step * a.scale
    if px < 2:
        print("step too small for this scale", file=sys.stderr)
        return 2
    i = 0
    while i * px <= im.width:
        x = round(i * px)
        major = i % a.major == 0
        d.line([(x, 0), (x, im.height)], fill=(255, 0, 255, 160 if major else 60), width=1)
        if major:
            d.text((x + 2, 2), str(i * a.step), fill=(255, 0, 255, 255), font=font)
        i += 1
    i = 0
    while i * px <= im.height:
        y = round(i * px)
        major = i % a.major == 0
        d.line([(0, y), (im.width, y)], fill=(0, 200, 255, 160 if major else 60), width=1)
        if major and i:
            d.text((2, y + 2), str(i * a.step), fill=(0, 200, 255, 255), font=font)
        i += 1
    im.save(a.out)
    print(f"{a.out}: grid every {a.step} logical px ({px:g} image px)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("out")
    s.add_argument("inputs", nargs="+")
    s.add_argument("--cols", type=int, default=4)
    s.add_argument("--width", type=int, default=480)
    s.add_argument("--every", type=int, default=1, help="keep one frame in N")
    s.add_argument("--labels", choices=["time", "name", "none"], default="time")
    s.add_argument("--fps", type=float, default=10.0)
    s.add_argument("--start", type=float, default=0.0)
    s.add_argument("--per-sheet", type=int, default=32)
    o = sub.add_parser("overlay")
    o.add_argument("frame")
    o.add_argument("out")
    o.add_argument("--scale", type=float, default=1.0, help="image px per logical px")
    o.add_argument("--step", type=float, default=10.0)
    o.add_argument("--major", type=int, default=5)
    a = ap.parse_args()
    return sheet(a) if a.mode == "sheet" else overlay(a)


if __name__ == "__main__":
    sys.exit(main())
