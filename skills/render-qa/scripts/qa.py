"""Run every automatic check on a render and write qa/REPORT.json and qa/REPORT.md.

    bin/pvs-py skills/render-qa/scripts/qa.py <video_dir> <video.mp4> [--out DIR] [--no-asr]
                                               [--asr-model NAME] [--strip name:t0:t1[:fps] ...]

Checks: everything in qa_full.py (frames, black, loudness, true peak, clipping, clicks,
edges, voice overlaps, ASR vs lines.tsv, banned terms heard), plus banned terms and legacy
names in the visible text of video/index.html and in lines.tsv, camera zoom above
product.yaml video.max_zoom (warning), and the seek-safe-motion lint when that skill is
installed. Writes contact sheets to qa/sheets/ and strips to qa/strips/ (one per outlier
run, up to 12, the last 5 s, and each --strip), and the speech transcript to qa/asr.txt.

draft is true when BRIEF.md is missing a signature or video/index.html carries
<meta name="pvs-draft" content="1">. A draft can pass QA but deliver.py refuses it.

Exit 0 when every check passed, 1 otherwise. --no-asr makes the report fail on purpose:
the speech check is required before anything is delivered.
"""
import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import qalib
import qa_full
import sheets as sheets_mod
import strips as strips_mod
from banned_terms import find_banned

check = qa_full.check


def rel(p: Path, base: Path) -> str:
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(p.resolve())


def visible_checks(vdir: Path, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    html = vdir / "video" / "index.html"
    if html.exists():
        text = qalib.visible_text(html.read_text(encoding="utf-8", errors="replace"))
        hits = find_banned(text, cfg)
        out.append(check("banned_terms_visible", not hits,
                         f"{len(hits)} hit(s) in the visible text of video/index.html"
                         + (": " + ", ".join(f"{t} ({k})" for t, k in hits) if hits else "")))
    else:
        out.append(check("banned_terms_visible", True, "no video/index.html to scan", level="warn"))
    lines = qalib.load_lines(vdir)
    if lines:
        hits = []
        for r in lines:
            for t, k in find_banned(r["text"], cfg):
                hits.append(f"{r['id']}: {t} ({k})")
        out.append(check("banned_terms_script", not hits,
                         f"{len(hits)} hit(s) in audio/lines.tsv" + (": " + "; ".join(hits[:10]) if hits else "")))
    return out


def zoom_check(vdir: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    max_zoom = float((cfg.get("video") or {}).get("max_zoom", 1.35))
    seen, over = set(), []
    files = [vdir / "video" / "src" / "template.tpl", vdir / "video" / "index.html"]
    files += sorted((vdir / "video" / "src").glob("*.js")) if (vdir / "video" / "src").is_dir() else []
    for f in files:
        if not f.exists():
            continue
        for line, s, snip in qalib.camera_zooms(f.read_text(encoding="utf-8", errors="replace")):
            if s > max_zoom + 1e-9 and snip not in seen:
                seen.add(snip)
                over.append(f"{f.name}:{line} scale {s:g} ({snip[:70]})")
    return check("camera_zoom", True,
                 (f"{len(over)} camera scale(s) above video.max_zoom {max_zoom:g}: " + "; ".join(over[:8])
                  + ". Full-page and settings screens stay at 1x; only a zoomed-out canvas or a narrow column "
                  "tolerates more. Confirm with the reviewer or lower it.")
                 if over else f"no literal camera scale above {max_zoom:g}",
                 level="warn" if over else "info")


def motion_check(vdir: Path) -> Dict[str, Any]:
    lint = qalib.pvs.workbench() / "skills" / "seek-safe-motion" / "scripts" / "lint_motion.py"
    if not lint.exists():
        lint = Path(__file__).resolve().parents[2] / "seek-safe-motion" / "scripts" / "lint_motion.py"
    if not lint.exists() or not (vdir / "video").is_dir():
        return check("motion_lint", True, "seek-safe-motion lint not available or no video/ folder", level="warn")
    r = subprocess.run([sys.executable, str(lint), str(vdir / "video"), "--summary"], capture_output=True, text=True)
    detail = (r.stdout.strip().splitlines() or ["no output"])[-1]
    return check("motion_lint", r.returncode == 0, detail + ("" if r.returncode == 0 else
                 f"; run lint_motion.py {rel(vdir / 'video', Path.cwd())} for the findings"))


def write_md(path: Path, rep: Dict[str, Any]) -> None:
    L = [f"# QA report: {Path(rep['mp4']).name}", ""]
    status = "PASSED" if rep["passed"] else "FAILED"
    L.append(f"**{status}**, draft: {'yes' if rep['draft'] else 'no'} ({rep['draft_reason']})  ")
    L.append(f"sha256 `{rep['sha256'][:16]}...`, created {rep['created']}  ")
    p = rep["probe"]
    L.append(f"{p['width']}x{p['height']}, {p['fps']:g} fps, {p['duration']:.2f} s")
    L += ["", "| Check | Result | Detail |", "|---|---|---|"]
    for c in rep["checks"]:
        res = "FAIL" if not c["passed"] else ("WARN" if c.get("level") == "warn" else "pass")
        L.append(f"| {c['name']} | {res} | {c['detail'].replace('|', '/')} |")
    L += ["", "## Still to do by eye (the scripts cannot see these)", ""]
    a = rep["artifacts"]
    L.append(f"- [ ] Look at every contact sheet ({len(a['sheets'])} in `{a['sheets_dir']}`). The time label can cover a "
             "title: pull the full frame before calling it cut.")
    L.append(f"- [ ] Look at every strip in `{a['strips_dir']}` ({', '.join(Path(s).stem for s in a['strips']) or 'none'}), "
             "then add strips (`strips.py`) for every modal, scroll, camera move, chapter change and changed beat.")
    L.append("- [ ] Listen to the narration edges (`edges.py <mp4> <video_dir>` says where).")
    L.append("- [ ] If this version edits an approved one, run `parity.py <approved.mp4> <this.mp4> --skip A:B`.")
    asr = next((c for c in rep["checks"] if c["name"] == "asr"), None)
    if asr and asr.get("diffs"):
        L += ["", "## ASR diffs (read each one)", ""] + [f"- {d}" for d in asr["diffs"]]
    o = next((c for c in rep["checks"] if c["name"] == "outliers"), None)
    if o and o.get("runs"):
        L += ["", "## Outlier runs", "", "| t0 | t1 | frames | mod 3 | worker pattern |", "|---|---|---|---|---|"]
        for r in o["runs"]:
            L.append(f"| {r['t0']:.2f} | {r['t1']:.2f} | {r['n']} | {r['mod3']} | {'YES' if r['worker_pattern'] else ''} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="All automatic QA for a render; writes qa/REPORT.json and REPORT.md.")
    ap.add_argument("video_dir")
    ap.add_argument("mp4")
    ap.add_argument("--out", help="QA folder (default <video_dir>/qa)")
    ap.add_argument("--no-asr", action="store_true", help="skip speech to text (the report then fails)")
    ap.add_argument("--asr-model")
    ap.add_argument("--strip", action="append", default=[], metavar="name:t0:t1[:fps]")
    ap.add_argument("--no-sheets", action="store_true", help="skip contact sheets and strips (tests)")
    a = ap.parse_args(argv)
    vdir = Path(a.video_dir).resolve()
    mp4 = Path(a.mp4)
    if not mp4.exists() and (vdir / a.mp4).exists():
        mp4 = vdir / a.mp4
    if not mp4.exists():
        qalib.pvs.die(f"{a.mp4}: no such file")
    mp4 = mp4.resolve()
    out = qalib.ensure_dir(Path(a.out).resolve() if a.out else vdir / "qa")
    cfg = qalib.load_config(vdir)
    brief = qalib.load_brief(vdir) or {}
    draft, why = qalib.draft_status(vdir)
    t_start = dt.datetime.now()
    print(f"QA {mp4.name} for {vdir.name} -> {out}")

    res = qa_full.run_checks(vdir, mp4, out, cfg, not a.no_asr, a.asr_model, lang=brief.get("lang"),
                             log=lambda s="": None)
    checks = res["checks"] + visible_checks(vdir, cfg) + [zoom_check(vdir, cfg), motion_check(vdir)]

    sheet_paths, strip_paths = [], []
    if not a.no_sheets:
        sheet_paths = sheets_mod.make_sheets(mp4, out / "sheets")
        dur = res["probe"]["duration"]
        specs = []
        for k, r in enumerate(sorted(res["outliers"]["runs"], key=lambda r: (not r["worker_pattern"], -r["max"]))[:12]):
            specs.append((f"outlier-{k + 1:02d}-{r['t0']:.1f}s", max(0, r["t0"] - 0.5), min(dur, r["t1"] + 0.5), 10.0))
        if dur > 6:
            specs.append(("end", dur - 5.0, dur - 0.05, 6.0))
        for s in a.strip:
            specs.append(strips_mod.parse_spec(s))
        sdir = qalib.ensure_dir(out / "strips")
        for old in sdir.glob("outlier-*.jpg"):
            old.unlink()
        for name, t0, t1, fps in specs:
            p, _ = strips_mod.make_strip(mp4, sdir, name, t0, t1, fps)
            strip_paths.append(p)

    passed = all(c["passed"] for c in checks)
    rep = {
        "mp4": rel(mp4, vdir),
        "sha256": qalib.sha256(mp4),
        "created": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "draft": draft,
        "draft_reason": why,
        "product": (cfg.get("product") or {}).get("name", ""),
        "video": brief.get("video") or vdir.name,
        "version": brief.get("version", 1),
        "probe": res["probe"],
        "checks": checks,
        "artifacts": {
            "sheets_dir": rel(out / "sheets", vdir), "sheets": [rel(p, vdir) for p in sheet_paths],
            "strips_dir": rel(out / "strips", vdir), "strips": [rel(p, vdir) for p in strip_paths],
            "asr": rel(out / "asr.txt", vdir) if (out / "asr.txt").exists() and res["heard"] else "",
        },
        "seconds": round((dt.datetime.now() - t_start).total_seconds(), 1),
        "passed": passed,
    }
    qalib.pvs.write_json(out / "REPORT.json", rep)
    write_md(out / "REPORT.md", rep)
    for c in checks:
        mark = "FAIL" if not c["passed"] else ("WARN" if c.get("level") == "warn" else "pass")
        if mark != "pass" or c["name"] in ("loudness", "asr"):
            print(f"  [{mark}] {c['name']}: {c['detail'][:200]}")
    nfail = sum(not c["passed"] for c in checks)
    print(f"{'PASSED' if passed else 'FAILED'}: {len(checks) - nfail} passed, {nfail} failed"
          f"{', DRAFT (not deliverable): ' + why if draft else ''}; {rep['seconds']} s")
    print(f"report: {out / 'REPORT.md'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
