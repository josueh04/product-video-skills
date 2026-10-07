"""Show or record the reviewer's sign-off on COVERAGE.md and CLAIMS.md.

    bin/pvs-py skills/video-new/scripts/sign.py <video_dir>                        # status only
    bin/pvs-py skills/video-new/scripts/sign.py <video_dir> --coverage "Name" [--claims "Name"]
    bin/pvs-py skills/video-new/scripts/sign.py <video_dir> --clear

Run it only when the reviewer has said, in their own words, that they read the sheet and sign
it under that name. It refuses to sign an empty matrix or a sheet without a positioning line,
because a signature on an empty sheet is the failure the sign-off exists to prevent.
"""
import argparse
import re
from pathlib import Path
from typing import List

import pvs

COMMENT = re.compile(r"<!--.*?-->", re.S)


def coverage_rows(text: str) -> List[List[str]]:
    rows = []
    for line in COMMENT.sub("", text).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.strip().startswith("|") or len(cells) < 2:
            continue
        if not cells[0] or cells[0].lower() == "feature" or set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def section(text: str, heading: str) -> str:
    m = re.search(r"^##\s+" + re.escape(heading) + r"[^\n]*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return COMMENT.sub("", m.group(1)).strip() if m else ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Reviewer sign-off on the coverage matrix and claims sheet.")
    ap.add_argument("video_dir")
    ap.add_argument("--coverage", help="reviewer name signing COVERAGE.md")
    ap.add_argument("--claims", help="reviewer name signing CLAIMS.md")
    ap.add_argument("--clear", action="store_true", help="empty both signatures (sheets changed)")
    a = ap.parse_args()

    vdir = Path(a.video_dir).resolve()
    brief = vdir / "BRIEF.md"
    if not brief.exists():
        pvs.die(f"sign: no BRIEF.md in {vdir}")
    text = brief.read_text(encoding="utf-8")
    m = pvs.FRONT.match(text)
    if not m:
        pvs.die("sign: BRIEF.md has no frontmatter")
    meta = pvs.load_yaml_text(m.group(1))

    cov_text = (vdir / "COVERAGE.md").read_text(encoding="utf-8") if (vdir / "COVERAGE.md").exists() else ""
    claims_text = (vdir / "CLAIMS.md").read_text(encoding="utf-8") if (vdir / "CLAIMS.md").exists() else ""
    rows = coverage_rows(cov_text)
    must = [r for r in rows if len(r) > 1 and r[1].lower().startswith("y")]
    positioning = section(claims_text, "Positioning")

    if a.coverage:
        if not must:
            pvs.die("sign: COVERAGE.md has no feature marked 'yes' to explain on screen; fill it first")
        missing = [r[0] for r in must if len(r) < 4 or not r[2] or not r[3]]
        if missing:
            pvs.die("sign: these features have no chapter or proof yet: " + ", ".join(missing))
        meta["coverage_signed_by"] = a.coverage.strip()
    if a.claims:
        if not positioning:
            pvs.die("sign: CLAIMS.md has no positioning line; fill it first")
        meta["claims_signed_by"] = a.claims.strip()
    if a.clear:
        meta["coverage_signed_by"] = ""
        meta["claims_signed_by"] = ""
    if a.coverage or a.claims or a.clear:
        dumped = pvs.yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100)
        brief.write_text("---\n" + dumped + "---\n" + text[m.end():], encoding="utf-8")

    cov = meta.get("coverage_signed_by") or ""
    cla = meta.get("claims_signed_by") or ""
    print(f"{vdir.name}: coverage {len(must)} of {len(rows)} features to explain, signed by: {cov or '(unsigned)'}")
    print(f"{vdir.name}: claims, signed by: {cla or '(unsigned)'}")
    print("ready to build" if cov and cla else "not ready: the reviewer signs both sheets before /video-build")


if __name__ == "__main__":
    main()
