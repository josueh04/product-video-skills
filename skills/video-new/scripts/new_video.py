"""Create videos/<video>/ in a product from _template/video, with the BRIEF frontmatter filled.

    bin/pvs-py skills/video-new/scripts/new_video.py <product_dir> <video> [--format pitch|tour|docs|tutorial|loop]
                                                      [--title T] [--duration S]

Both signatures start empty: only the reviewer fills them (see sign.py), and build.py refuses
to build a non-draft while either is empty. COVERAGE.md and CLAIMS.md are seeded from this
skill's assets/ when the template does not ship them.
"""
import argparse
import re
import shutil
from pathlib import Path
from typing import Any, Dict

import pvs

VIDEO_ID = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
# default seconds per format; script-and-voice/references/script-templates.md has one template each
FORMATS = {"pitch": 90, "tour": 30, "docs": 120, "tutorial": 240, "loop": 15}
KEY_ORDER = ["title", "video", "format", "duration_s", "lang", "reviewer", "version",
             "coverage_signed_by", "claims_signed_by"]
SKIP = {"node_modules", "renders", "__pycache__", ".git"}
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def fail(msg: str) -> None:
    pvs.die(f"new_video: {msg}")


def dump_front(meta: Dict[str, Any]) -> str:
    ordered = {k: meta[k] for k in KEY_ORDER if k in meta}
    ordered.update({k: v for k, v in meta.items() if k not in ordered})
    return "---\n" + pvs.yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=100) + "---\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Create a video folder inside a product.")
    ap.add_argument("product_dir")
    ap.add_argument("video")
    ap.add_argument("--format", default="pitch", choices=sorted(FORMATS))
    ap.add_argument("--title")
    ap.add_argument("--duration", type=int, help="target length in seconds")
    a = ap.parse_args()

    if not VIDEO_ID.match(a.video):
        fail(f"invalid video id '{a.video}': lowercase letters, digits and dashes, starting with a letter")
    pdir = Path(a.product_dir).resolve()
    if not (pdir / "product.yaml").exists():
        fail(f"{pdir} has no product.yaml. Run /product-new first")
    cfg = pvs.load_product(pdir)
    dest = pdir / "videos" / a.video
    if dest.exists():
        fail(f"{dest} already exists. Pick another id, or run /video-review to make its next version")
    tpl = pvs.workbench() / "_template" / "video"
    if not tpl.is_dir():
        fail(f"template not found: {tpl} (run /video-setup)")

    shutil.copytree(tpl, dest, ignore=lambda d, names: [n for n in names if n in SKIP or n.endswith(".mp4")])
    name = cfg["product"]["name"] or cfg["product"]["slug"] or pdir.name
    title = a.title or f"{name} {a.video}"
    for f in ("BRIEF.md", "COVERAGE.md", "CLAIMS.md"):
        if not (dest / f).exists():
            shutil.copy(ASSETS / f, dest / f)

    values = {"PRODUCT_NAME": name, "VIDEO": a.video, "FORMAT": a.format, "TITLE": title}
    for f in dest.rglob("*.md"):  # never *.tpl: the composer's own placeholders live there
        text = f.read_text(encoding="utf-8")
        new = text
        for k, v in values.items():
            new = new.replace("{{" + k + "}}", v)
        if new != text:
            f.write_text(new, encoding="utf-8")

    brief = dest / "BRIEF.md"
    text = brief.read_text(encoding="utf-8")
    m = pvs.FRONT.match(text)
    meta = pvs.load_yaml_text(m.group(1)) if m else {}
    body = text[m.end():] if m else text
    meta.update({
        "title": title, "video": a.video, "format": a.format,
        "duration_s": a.duration or FORMATS[a.format],
        "lang": cfg["video"].get("lang") or "en",
        "reviewer": cfg["review"].get("reviewer") or "",
        "version": 1, "coverage_signed_by": "", "claims_signed_by": "",
    })
    brief.write_text(dump_front(meta) + body, encoding="utf-8")

    print(f"Created {dest}")
    print(f"  {title} | format {a.format} | {meta['duration_s']} s | reviewer: {meta['reviewer'] or '(not set)'}")
    print("  signatures: coverage and claims empty (the reviewer signs, then /video-build)")


if __name__ == "__main__":
    main()
