"""Open the next version of a video: back up the current sources, bump BRIEF version, add a changelog stub.

    bin/pvs-py skills/video-review/scripts/bump_version.py <video_dir> [--note "reviewer words"]... [--force]

Backups (never overwritten): audio/lines-v<N>.tsv, audio/timings-v<N>.json, video/_v<N>-src/.
The previous render video/renders/<video>-v<N>.mp4 is kept as is: it is the reference for the
parity check, and a file the reviewer may already have shared must never be replaced. Refuses
when v<N> was never rendered (bumping twice would skip a version), unless --force.
"""
import argparse
import datetime as dt
import re
import shutil
from pathlib import Path

import pvs


def main() -> None:
    ap = argparse.ArgumentParser(description="Start the next version of a video.")
    ap.add_argument("video_dir")
    ap.add_argument("--note", action="append", default=[], help="the reviewer's words, verbatim (repeatable)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    vdir = pvs.video_dir(Path(a.video_dir))
    brief = vdir / "BRIEF.md"
    text = brief.read_text(encoding="utf-8")
    m = pvs.FRONT.match(text)
    if not m:
        pvs.die("bump_version: BRIEF.md has no frontmatter")
    meta = pvs.load_yaml_text(m.group(1))
    video = str(meta.get("video") or vdir.name)
    n = int(meta.get("version") or 1)
    prev_mp4 = vdir / "video" / "renders" / f"{video}-v{n}.mp4"
    if not prev_mp4.exists() and not a.force:
        pvs.die(f"bump_version: {prev_mp4.relative_to(vdir)} does not exist, so v{n} is still open. "
                "Fix v{n} in place, or pass --force".replace("{n}", str(n)))

    backups = []
    pairs = [(vdir / "audio" / "lines.tsv", vdir / "audio" / f"lines-v{n}.tsv"),
             (vdir / "audio" / "timings.json", vdir / "audio" / f"timings-v{n}.json")]
    for src, dst in pairs:
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            backups.append(dst.relative_to(vdir))
    src_dir, dst_dir = vdir / "video" / "src", vdir / "video" / f"_v{n}-src"
    if src_dir.is_dir() and not dst_dir.exists():
        shutil.copytree(src_dir, dst_dir)
        backups.append(dst_dir.relative_to(vdir))
    build = vdir / "video" / "build.py"
    if build.exists() and dst_dir.exists() and not (dst_dir / "build.py").exists():
        shutil.copy2(build, dst_dir / "build.py")

    meta["version"] = n + 1
    body = text[m.end():]
    quotes = "\n".join(f'> "{q.strip()}"' for q in a.note) or "> (paste the reviewer's words)"
    stub = (f"\n### v{n + 1} ({dt.date.today().isoformat()})\n\nFeedback:\n\n{quotes}\n\n"
            f"Changes: (filled by the fix)\n\nParity vs v{n}: (filled after the parity check)\n")
    if re.search(r"^## Changelog\s*$", body, re.M):
        body = body.rstrip() + "\n" + stub
    else:
        body = body.rstrip() + "\n\n## Changelog\n" + stub
    dumped = pvs.yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100)
    brief.write_text("---\n" + dumped + "---\n" + body, encoding="utf-8")

    print(f"{video}: v{n} to v{n + 1}")
    print("  backups: " + (", ".join(map(str, backups)) or "none needed"))
    print(f"  parity reference: {prev_mp4.relative_to(vdir)}" + ("" if prev_mp4.exists() else " (missing)"))


if __name__ == "__main__":
    main()
