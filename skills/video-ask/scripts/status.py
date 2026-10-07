#!/usr/bin/env python3
"""Where am I and what do I type next.

Reports the workbench setup, every product and video with its stage (inferred from files, see
docs/contracts.md), and the next command. Works from any folder: the workbench, a product, a
video, or a folder outside both (then pass the folder as an argument).

usage: status.py [<dir>] [--json] [--short]
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import pvs  # noqa: E402

STAGES = ["brief unsigned", "signed", "sources fetched", "truth", "specs", "voice", "built",
          "rendered", "QA failed", "QA passed", "delivered"]


# ---------- setup ----------

def installed_hyperframes(home: Path) -> Optional[str]:
    pkg = pvs.read_json(home / "node_modules" / "hyperframes" / "package.json", None)
    return pkg.get("version") if isinstance(pkg, dict) else None


def vendor_tag(home: Path) -> Optional[str]:
    v = home / "vendor" / "hyperframes"
    if not (v / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "-C", str(v), "describe", "--tags", "--exact-match"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def setup_state(home: Path) -> Dict[str, Any]:
    try:
        pinned = pvs.hyperframes_version()
    except SystemExit:
        pinned = None
    hf = installed_hyperframes(home)
    tag = vendor_tag(home)
    venv = (home / ".venv" / "bin" / "python").exists()
    stamp = pvs.read_json(home / ".venv" / "pvs-setup.json", None)
    missing = []
    if not pinned or hf != pinned:
        missing.append("HyperFrames CLI")
    if not pinned or tag != "v" + pinned:
        missing.append("HyperFrames skills (vendor/)")
    if not venv:
        missing.append("Python environment (.venv)")
    if pvs.yaml is None:
        missing.append("PyYAML")
    if not stamp:
        missing.append("a passing run of setup.sh")
    return {
        "pinned": pinned, "hyperframes": hf, "vendor_tag": tag, "venv": venv,
        "setup_finished": (stamp or {}).get("finished_at"),
        "env_file": (home / ".env").exists(),
        "voice_key_set": bool(pvs.env_value("ELEVENLABS_API_KEY")),
        "missing": missing, "done": not missing,
    }


# ---------- products and videos ----------

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def newest(pattern: str) -> Optional[Path]:
    files = [Path(p) for p in glob.glob(pattern)]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def product_info(pdir: Path) -> Dict[str, Any]:
    try:
        cfg = pvs._merge(pvs.DEFAULTS, pvs.load_yaml(pdir / "product.yaml"))
    except Exception as e:  # a broken product.yaml should not hide the others
        return {"dir": str(pdir), "slug": pdir.name, "name": pdir.name, "error": str(e), "videos": []}
    info = {"dir": str(pdir), "slug": cfg["product"].get("slug") or pdir.name,
            "example": pdir.parent.name == "examples",
            "name": cfg["product"].get("name") or pdir.name, "videos": []}
    for b in sorted(pdir.glob("videos/*/BRIEF.md")):
        info["videos"].append(video_info(pdir, cfg, b.parent))
    return info


def video_info(pdir: Path, cfg: Dict[str, Any], vdir: Path) -> Dict[str, Any]:
    name = vdir.name
    try:
        meta = pvs.read_brief(vdir)
    except Exception as e:
        return {"dir": str(vdir), "video": name, "stage": "brief unsigned", "error": str(e),
                "next": f"Fix the frontmatter of {vdir / 'BRIEF.md'}"}
    version = meta.get("version", 1)
    signed = pvs.signed(meta)
    v = {"dir": str(vdir), "video": meta.get("video") or name, "version": version, "signed": signed}

    has_sources = bool(cfg.get("sources"))
    reached = {
        "sources fetched": (vdir / "SOURCES.md").exists() and (not has_sources or (pdir / "sources.lock").exists()),
        "truth": (vdir / "TRUTH.md").exists(),
        "specs": bool(list(vdir.glob("specs/*.md"))),
        "voice": (vdir / "audio" / "timings.json").exists() and bool(list(vdir.glob("audio/clips/*.wav"))),
        "built": (vdir / "video" / "index.html").exists(),
    }
    mp4 = newest(str(vdir / "video" / "renders" / "*.mp4"))
    qa = None
    report = pvs.read_json(vdir / "qa" / "REPORT.json", None)
    if mp4 is not None and isinstance(report, dict):
        rp = report.get("mp4") or ""
        target = (vdir / rp) if rp and not os.path.isabs(rp) else Path(rp)
        if target.exists() and target.resolve() == mp4.resolve():
            ok = bool(report.get("passed")) and report.get("sha256") == sha256(mp4)
            qa = {"passed": ok, "draft": bool(report.get("draft"))}
    delivered = False
    naming = cfg["review"].get("naming") or "{product} {video} v{version}.mp4"
    try:
        fname = naming.format(product=cfg["product"].get("name") or pdir.name, video=v["video"], version=version)
        delivered = (pdir / "deliveries" / fname).exists()
    except (KeyError, IndexError, ValueError):
        pass
    if not delivered:
        delivered = bool(glob.glob(str(pdir / "deliveries" / f"*{v['video']}*v{version}*.mp4")))

    stage = "signed" if signed else "brief unsigned"
    for s in ["sources fetched", "truth", "specs", "voice", "built"]:
        if reached[s]:
            stage = s
    if mp4 is not None:
        stage = "rendered"
        if qa is not None:
            stage = "QA passed" if qa["passed"] else "QA failed"
    if signed and delivered:
        stage = "delivered"
    v["stage"] = stage
    v["mp4"] = str(mp4.relative_to(vdir)) if mp4 is not None else None
    v["qa_draft"] = bool(qa and qa["draft"])
    v["next"] = next_for_video(v, signed, qa)
    return v


def next_for_video(v: Dict[str, Any], signed: bool, qa: Optional[Dict[str, Any]]) -> str:
    name, stage = v["video"], v["stage"]
    if not signed:
        draft = f" (a draft build reached: {stage})" if stage != "brief unsigned" else ""
        return (f"The reviewer reads COVERAGE.md and CLAIMS.md and signs them in BRIEF.md "
                f"(coverage_signed_by, claims_signed_by){draft}. Then: /video-build {name}")
    if stage in ("signed", "sources fetched", "truth", "specs", "voice", "built"):
        return f"/video-build {name}"
    if stage == "rendered":
        return f"/video-build {name} (it runs QA: bin/pvs-py skills/render-qa/scripts/qa.py {v['dir']} {v['mp4']})"
    if stage == "QA failed":
        return f"Fix the failing checks in qa/REPORT.md, then /video-build {name} again"
    if stage == "QA passed":
        if qa and qa.get("draft"):
            return f"QA passed on a draft build. Rebuild without --draft: /video-build {name}"
        return f"/video-build {name} (it delivers: bin/pvs-py skills/render-qa/scripts/deliver.py {v['dir']} {v['mp4']})"
    return f"/video-review {name} with the next round of feedback, or /video-new <name> for another video"


# ---------- where am I ----------

def find_products(home: Path, here: Path) -> List[Path]:
    found = sorted(p.parent for p in (home / "products").glob("*/product.yaml"))
    found += sorted(p.parent for p in (home / "examples").glob("*/product.yaml"))
    mine = pvs.find_up(here, "product.yaml")
    if mine is not None and mine.resolve() not in [p.resolve() for p in found]:
        found.append(mine)
    return found


def status(here: Path) -> Dict[str, Any]:
    home = pvs.workbench()
    out: Dict[str, Any] = {"workbench": str(home), "here": str(here), "setup": setup_state(home),
                           "products": [], "product": None, "video": None}
    if pvs.yaml is None:
        out["next"] = "/video-setup"
        return out
    for p in find_products(home, here):
        out["products"].append(product_info(p))
    pdir = pvs.find_up(here, "product.yaml")
    vdir = pvs.find_up(here, "BRIEF.md")
    current = None
    if pdir is not None:
        current = next((p for p in out["products"] if Path(p["dir"]).resolve() == pdir.resolve()), None)
        out["product"] = current["slug"] if current else pdir.name
    video = None
    if current and vdir is not None:
        video = next((v for v in current["videos"] if Path(v["dir"]).resolve() == vdir.resolve()), None)
        out["video"] = video["video"] if video else None
    out["next"] = next_command(out, current, video, home)
    return out


def next_command(out, current, video, home: Path) -> str:
    s = out["setup"]
    if not s["done"]:
        return "/video-setup"
    if video:
        return video["next"]
    if current:
        if current.get("error"):
            return f"Fix {current['dir']}/product.yaml ({current['error']})"
        if not current["videos"]:
            return "/video-new <video> (for example: /video-new pitch)"
        open_videos = [v for v in current["videos"] if v["stage"] != "delivered"]
        if open_videos:
            v = max(open_videos, key=lambda v: os.path.getmtime(v["dir"]))
            return f"cd videos/{Path(v['dir']).name}, then: {v['next']}"
        return "/video-new <video> for another video, or /video-review <video> with new feedback"
    real = [p for p in out["products"] if not p.get("example")]
    if not real:
        return "/product-new <slug> (for example: /product-new acme)"
    p = max(real, key=lambda p: os.path.getmtime(p["dir"]))
    rel = os.path.relpath(p["dir"], out["here"])
    return f"cd {rel} && claude"


# ---------- output ----------

def setup_line(s: Dict[str, Any]) -> str:
    if s["done"]:
        return f"Setup: done (HyperFrames {s['hyperframes']}, skills {s['vendor_tag']}, finished {s['setup_finished']})."
    return "Setup: not done (missing: " + ", ".join(s["missing"]) + ")."


def voice_line(s: Dict[str, Any]) -> str:
    if s["voice_key_set"]:
        return "Voice key: set in .env."
    return "Voice key: not set. Paste it into .env yourself, or use voice.provider: say (no key needed)."


def human(out: Dict[str, Any]) -> str:
    s = out["setup"]
    lines = [f"Workbench: {out['workbench']}", setup_line(s), voice_line(s)]
    if out["products"]:
        lines.append("Products:")
        for p in out["products"]:
            tag = " [example]" if p.get("example") else ""
            lines.append(f"  {p['slug']}{tag} ({p['name']}): {len(p['videos'])} video(s)" + (f"  ERROR {p['error']}" if p.get("error") else ""))
            for v in p["videos"]:
                draft = " (draft QA)" if v.get("qa_draft") else ""
                lines.append(f"    {v['video']} v{v.get('version', 1)}: {v['stage']}{draft}")
    elif s["done"]:
        lines.append("Products: none yet.")
    where = "the workbench" if not out["product"] else f"product {out['product']}" + (f", video {out['video']}" if out["video"] else "")
    lines.append(f"Here: {where}")
    lines.append(f"Next: {out['next']}")
    return "\n".join(lines)


def short(out: Dict[str, Any]) -> str:
    s = out["setup"]
    lines = ["Product Video Skills workbench: " + setup_line(s)]
    if out["product"]:
        cur = next((p for p in out["products"] if p["slug"] == out["product"]), None)
        line = f"Product: {out['product']}"
        if out["video"] and cur:
            v = next((v for v in cur["videos"] if v["video"] == out["video"]), None)
            if v:
                line += f". Video: {v['video']} v{v.get('version', 1)}, stage: {v['stage']}"
        lines.append(line + ".")
    elif s["done"]:
        lines.append(f"Products: {len([p for p in out['products'] if not p.get('example')])}.")
    if s["done"] and not s["voice_key_set"]:
        lines.append(voice_line(s))
    lines.append(f"Next: {out['next']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir", nargs="?", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--short", action="store_true", help="3 to 5 lines, for the session-start hook")
    a = ap.parse_args()
    here = Path(a.dir).resolve()
    if not here.exists():
        pvs.die(f"No such folder: {a.dir}")
    out = status(here)
    if a.json:
        print(json.dumps(out, indent=1))
    elif a.short:
        print(short(out))
    else:
        print(human(out))


if __name__ == "__main__":
    main()
