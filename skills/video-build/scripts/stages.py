"""Which build stages of a video have their output files (docs/contracts.md sections 2 and 3).

    bin/pvs-py skills/video-build/scripts/stages.py <video_dir>                 # table of every stage
    bin/pvs-py skills/video-build/scripts/stages.py <video_dir> --require truth # exit 1 unless done
    bin/pvs-py skills/video-build/scripts/stages.py <video_dir> --json

The coordinator runs it before dispatching each stage and after each subagent reports, so a
stage is "done" because its files exist, not because a subagent said so.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pvs

ORDER = ["signoff", "sources", "recon", "truth", "specs", "voice", "compose", "render", "qa", "deliver"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table_rows(p: Path) -> int:
    if not p.exists():
        return 0
    n = 0
    text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", s) and s.strip("| \t"):
            n += 1
    return max(n - 1, 0)  # minus the header row


def check(vdir: Path) -> Dict[str, Tuple[bool, str]]:
    pdir = pvs.product_dir(vdir)
    meta = pvs.read_brief(vdir)
    video = str(meta.get("video") or vdir.name)
    version = int(meta.get("version") or 1)
    out: Dict[str, Tuple[bool, str]] = {}

    cov, cla = meta.get("coverage_signed_by"), meta.get("claims_signed_by")
    out["signoff"] = (bool(cov and cla), f"coverage: {cov or '-'}, claims: {cla or '-'}")

    lock = pvs.read_json(pdir / "sources.lock", {}) or {}
    out["sources"] = (bool(lock), f"sources.lock roles: {', '.join(sorted(lock)) or 'none'}")

    out["recon"] = (table_rows(vdir / "SOURCES.md") > 0, f"SOURCES.md rows: {table_rows(vdir / 'SOURCES.md')}")
    out["truth"] = (table_rows(vdir / "TRUTH.md") > 0, f"TRUTH.md rows: {table_rows(vdir / 'TRUTH.md')}")

    specs = sorted((vdir / "specs").glob("*.md")) if (vdir / "specs").is_dir() else []
    out["specs"] = (bool(specs), f"specs: {', '.join(s.stem for s in specs) or 'none'}")

    audio = vdir / "audio"
    lines: List[dict] = pvs.read_lines_tsv(audio / "lines.tsv") if (audio / "lines.tsv").exists() else []
    timings = pvs.read_json(audio / "timings.json", {}) or {}
    clips = {c.stem for c in (audio / "clips").glob("*.wav")} if (audio / "clips").is_dir() else set()
    ids = [r["id"] for r in lines]
    missing = [i for i in ids if i not in clips or i not in timings]
    out["voice"] = (bool(ids) and not missing,
                    f"lines {len(ids)}, clips {len(clips)}, timings {len(timings)}"
                    + (f", missing {','.join(missing[:6])}" if missing else ""))

    v = vdir / "video"
    need = ["build.py", "src/template.tpl", "src/app.css", "index.html"]
    absent = [n for n in need if not (v / n).exists()]
    out["compose"] = (not absent, "all present" if not absent else "missing " + ", ".join(absent))

    mp4 = v / "renders" / f"{video}-v{version}.mp4"
    out["render"] = (mp4.exists(), str(mp4.relative_to(vdir)) + ("" if mp4.exists() else " (not found)"))

    rep = pvs.read_json(vdir / "qa" / "REPORT.json", None)
    if not rep:
        out["qa"] = (False, "qa/REPORT.json not found")
    else:
        same = mp4.exists() and rep.get("sha256") == sha256(mp4)
        ok = bool(rep.get("passed")) and not rep.get("draft") and same
        failed = [c.get("name") for c in rep.get("checks", []) if not c.get("passed")]
        detail = f"passed={rep.get('passed')} draft={rep.get('draft')} sha matches v{version}={same}"
        if failed:
            detail += " failed: " + ", ".join(map(str, failed[:6]))
        out["qa"] = (ok, detail)

    deliv = pdir / "deliveries"
    briefs = sorted(deliv.glob("*.BRIEF.md")) if deliv.is_dir() else []
    ver = re.compile(rf"v{version}(?!\d)")
    shipped = [b for b in briefs if ver.search(b.name) and video.lower() in b.name.lower()]
    out["deliver"] = (bool(shipped), shipped[0].name if shipped else f"no v{version} delivery found")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage status of one video.")
    ap.add_argument("video_dir")
    ap.add_argument("--require", choices=ORDER, action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    vdir = pvs.video_dir(Path(a.video_dir))
    res = check(vdir)
    if a.json:
        print(json.dumps({k: {"done": d, "detail": t} for k, (d, t) in res.items()}, indent=1))
    else:
        print(f"| stage | done | detail |  ({vdir})")
        print("|---|---|---|")
        for k in ORDER:
            d, t = res[k]
            print(f"| {k} | {'yes' if d else 'no'} | {t} |")
    missing = [s for s in a.require if not res[s][0]]
    if missing:
        pvs.die("not done: " + ", ".join(f"{s} ({res[s][1]})" for s in missing))


if __name__ == "__main__":
    main()
