"""Stack the same logical region of a reference capture and of our render, to check 1:1 parity.

    python3 pair.py <ours.png> <reference.png> x0 y0 x1 y1 <out.png>
        [--ref-scale 2] [--logical-width 1440] [--render-width 1920] [--dy 0] [--scale 1]

Coordinates are logical app px (CSS px of the rebuilt app, product.yaml app_canvas.logical).
The reference is a frame of a recording or a capture (--ref-scale 2 for a retina recording);
ours is a HyperFrames snapshot taken with the camera at scale 1, so the app sits at
render_width / logical_width px per logical px. The output puts the reference on top and ours
below with a magenta divider, plus the mean absolute difference per channel, which drops as the
rebuild gets closer. --dy shifts our crop when the layouts differ vertically.
"""
import argparse
import sys

from PIL import Image, ImageChops, ImageStat


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ours")
    ap.add_argument("reference")
    ap.add_argument("box", nargs=4, type=float, metavar=("x0", "y0", "x1", "y1"))
    ap.add_argument("out")
    ap.add_argument("--ref-scale", type=float, default=2.0, help="reference px per logical px")
    ap.add_argument("--logical-width", type=float, default=1440.0, help="logical app width")
    ap.add_argument("--render-width", type=float, default=1920.0, help="width the app is rendered at in ours")
    ap.add_argument("--dy", type=float, default=0.0)
    ap.add_argument("--scale", type=float, default=1.0, help="resize the final image")
    a = ap.parse_args()

    x0, y0, x1, y1 = a.box
    if x1 <= x0 or y1 <= y0:
        print("box must have x1 > x0 and y1 > y0", file=sys.stderr)
        return 2
    k, r = a.render_width / a.logical_width, a.ref_scale
    ref = Image.open(a.reference).convert("RGB")
    ours = Image.open(a.ours).convert("RGB")
    rbox = (round(x0 * r), round(y0 * r), round(x1 * r), round(y1 * r))
    obox = (round(x0 * k), round((y0 + a.dy) * k), round(x1 * k), round((y1 + a.dy) * k))
    for name, im, box in (("reference", ref, rbox), ("ours", ours, obox)):
        if box[2] > im.width or box[3] > im.height:
            print(f"box falls outside {name} ({im.width}x{im.height}); check --ref-scale or --logical-width", file=sys.stderr)
            return 2
    a_crop = ref.crop(rbox)
    b_crop = ours.crop(obox).resize(a_crop.size, Image.LANCZOS)
    diff = [round(v, 2) for v in ImageStat.Stat(ImageChops.difference(a_crop, b_crop)).mean]
    im = Image.new("RGB", (a_crop.width, a_crop.height * 2 + 10), (255, 0, 255))
    im.paste(a_crop, (0, 0))
    im.paste(b_crop, (0, a_crop.height + 10))
    if a.scale != 1:
        im = im.resize((max(1, int(im.width * a.scale)), max(1, int(im.height * a.scale))), Image.LANCZOS)
    im.save(a.out)
    print(f"{a.out}: reference on top, ours below; mean abs diff per channel {diff}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
