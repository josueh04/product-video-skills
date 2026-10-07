"""Copy a QA'd render into the product's deliveries/ folder, or refuse.

    bin/pvs-py skills/render-qa/scripts/deliver.py <video_dir> <video.mp4> [--report PATH]
                                                    [--archive-previous] [--dry-run]

Refuses unless qa/REPORT.json (or --report) exists, says "passed": true and "draft": false,
and its sha256 matches the MP4 byte for byte. The gate is code because "the agent said it
was clean" is not evidence: subagents reported renders as clean that had a 0.3 s UI flash
and a clipped modal in them.

The file is named with product.yaml review.naming ({product}, {video}, {version}; version
from BRIEF.md) and lands in <product_dir>/deliveries/ next to a copy of BRIEF.md named
"<same name>.BRIEF.md". Nothing is ever overwritten: the same bytes already delivered is a
no-op, and different bytes under a delivered name bump the version in the file name (bump
BRIEF.md to match). --archive-previous moves older versions of this video into
deliveries/previous/ so the folder holds only the latest one. Exit 1 on refusal.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import qalib

pvs = qalib.pvs


def refuse(msg: str) -> int:
    print(f"REFUSED: {msg}", file=sys.stderr)
    return 1


def clone_copy(src: Path, dst: Path) -> None:
    """APFS clone on macOS (instant, no extra space), plain copy elsewhere."""
    if sys.platform == "darwin":
        r = subprocess.run(["cp", "-c", str(src), str(dst)], capture_output=True)
        if r.returncode == 0:
            return
    shutil.copy2(src, dst)


def render_name(naming: str, product: str, video: str, version: int) -> str:
    name = naming.format(product=product, video=video, version=version)
    name = re.sub(r'[\\/:*?"<>|]', "-", name).strip()
    return name if name.lower().endswith(".mp4") else name + ".mp4"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deliver a QA'd render, or refuse.")
    ap.add_argument("video_dir")
    ap.add_argument("mp4")
    ap.add_argument("--report", help="REPORT.json (default <video_dir>/qa/REPORT.json)")
    ap.add_argument("--archive-previous", action="store_true", help="move older versions of this video to deliveries/previous/")
    ap.add_argument("--dry-run", action="store_true", help="check and print the destination, copy nothing")
    a = ap.parse_args(argv)
    vdir = Path(a.video_dir).resolve()
    mp4 = Path(a.mp4)
    if not mp4.exists() and (vdir / a.mp4).exists():
        mp4 = vdir / a.mp4
    if not mp4.exists():
        return refuse(f"{a.mp4}: no such file")
    report = Path(a.report) if a.report else vdir / "qa" / "REPORT.json"
    if not report.exists():
        return refuse(f"no QA report at {report}. Run qa.py {vdir} {mp4} first.")
    try:
        rep = pvs.read_json(report)
    except ValueError as e:
        return refuse(f"{report} is not valid JSON ({e})")
    if rep.get("passed") is not True:
        failed = [c.get("name") for c in rep.get("checks", []) if not c.get("passed")]
        return refuse(f"the QA report did not pass (failed: {', '.join(map(str, failed)) or 'unknown'}). Fix and re-run qa.py.")
    if rep.get("draft") is not False:
        return refuse(f"the QA report is a draft ({rep.get('draft_reason', 'draft not false')}). Drafts are never delivered: "
                      "get BRIEF.md signed and rebuild without --draft.")
    digest = qalib.sha256(mp4)
    if rep.get("sha256") != digest:
        return refuse(f"sha256 mismatch: the report was made for another file ({str(rep.get('sha256'))[:12]}...), "
                      f"this MP4 is {digest[:12]}.... Re-run qa.py on this exact file.")
    # Signatures are checked again here: a BRIEF edited after QA must not slip through.
    draft, why = qalib.draft_status(vdir)
    if draft:
        return refuse(f"the video is a draft now: {why}")

    pdir = pvs.find_up(vdir, "product.yaml")
    if pdir is None:
        return refuse(f"no product.yaml above {vdir}: cannot find the deliveries folder")
    cfg = pvs.load_product(pdir)
    brief = pvs.read_brief(vdir)
    product = (cfg.get("product") or {}).get("name") or (cfg.get("product") or {}).get("slug") or pdir.name
    video = str(brief.get("video") or vdir.name)
    version = int(brief.get("version") or 1)
    naming = (cfg.get("review") or {}).get("naming") or "{product} {video} v{version}.mp4"
    dest_dir = pdir / "deliveries"

    v = version
    while True:
        name = render_name(naming, product, video, v)
        dst = dest_dir / name
        if not dst.exists():
            break
        if qalib.sha256(dst) == digest:
            print(f"already delivered: {dst} (identical bytes); nothing to do")
            return 0
        if "{version}" not in naming:
            stem = Path(render_name(naming, product, video, version)).stem
            k = 2
            while (dest_dir / f"{stem} ({k}).mp4").exists():
                k += 1
            name = f"{stem} ({k}).mp4"
            dst = dest_dir / name
            break
        v += 1
    if v != version:
        print(f"WARNING: v{version} was already delivered with different content; delivering as v{v}. "
              f"Set version: {v} in BRIEF.md and add a ### v{v} section.")
    brief_dst = dst.with_name(dst.stem + ".BRIEF.md")
    if a.dry_run:
        print(f"would deliver {mp4} -> {dst} (+ {brief_dst.name})")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    if a.archive_previous:
        prev = dest_dir / "previous"
        pat = re.compile(re.escape(render_name(naming, product, video, 999999)).replace("999999", r"\d+")
                         .replace(r"\.mp4", r"(?: \(\d+\))?\.mp4") + "$")
        for f in sorted(dest_dir.glob("*.mp4")):
            if f != dst and pat.match(f.name):
                prev.mkdir(exist_ok=True)
                for g in (f, f.with_name(f.stem + ".BRIEF.md")):
                    if g.exists():
                        target = prev / g.name
                        if target.exists():
                            print(f"kept {g.name}: previous/ already has that name")
                            continue
                        g.rename(target)
                        print(f"moved {g.name} -> previous/")
    clone_copy(mp4, dst)
    if qalib.sha256(dst) != digest:
        dst.unlink()
        return refuse("the copy does not match the source byte for byte; nothing delivered")
    shutil.copy2(vdir / "BRIEF.md", brief_dst)
    print(f"delivered {dst}")
    print(f"brief     {brief_dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
