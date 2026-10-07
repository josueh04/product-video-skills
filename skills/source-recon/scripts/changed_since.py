"""List the videos (and kit files) that cite source files changed since sources.lock.

    bin/pvs-py skills/source-recon/scripts/changed_since.py <product_dir> [--offline] [--json]

For each locked source, compare the locked commit with the current head of its branch
(git sources), or the locked copy with the original folder (non-git sources). Then scan every
video's SOURCES.md, TRUTH.md, specs/ and video/src/ files, plus kit/, for citations of the form
<role>/<path>[:<line>[-<line>]][@<sha>] and report each one that points at a changed file.
A citation whose lines fall inside a changed hunk is marked "lines changed".

--offline skips URL sources (they need a network fetch into sources/.git-cache).
Read-only: nothing is exported and the lock is not moved. Run fetch_sources.py --refresh for that,
and run this first: after a refresh the lock is the head, so there is nothing left to compare.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pvs
import srclib as S

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")
SCAN_GLOBS = ["SOURCES.md", "TRUTH.md", "BRIEF.md", "specs/**/*", "video/src/**/*"]
KIT_GLOBS = ["kit/tokens.css", "kit/icons/icons.md", "kit/fonts/*.md", "kit/fonts/fonts.css", "kit/*.md"]
TEXT_EXT = {".md", ".css", ".html", ".tpl", ".js", ".json", ".txt", ".tsv", ".py", ""}


def changes_git(product: Path, role: str, entry: dict, offline: bool) -> Optional[Tuple[str, Dict[str, List[Tuple[int, int]]]]]:
    """(head sha, {path: [(old_start, old_len), ...]}) or None when skipped."""
    locked = entry["commit"]
    branch = entry.get("branch", "")
    if entry.get("url"):
        if offline:
            return None
        gd = S.cache_git_dir(product, role)
        head = S.url_clone_or_fetch(entry["url"], branch, gd, want_sha=locked)
        kw = {"git_dir": gd}
    else:
        repo = (product / entry["path"]).resolve()
        if not S.is_git_repo(repo):
            raise S.SourceError(f"{role}: {repo} is no longer a git repo")
        _ref, head, _w = S.resolve_local_ref(repo, branch)
        kw = {"cwd": repo}
    if head == locked:
        return head, {}
    names = S.git(["diff", "--no-renames", "--name-only", locked, head], **kw).splitlines()
    hunks: Dict[str, List[Tuple[int, int]]] = {n: [] for n in names if n}
    cur, header = None, False
    for line in S.git(["diff", "--no-renames", "-U0", "--no-color", locked, head], **kw).splitlines():
        if line.startswith("diff --git "):
            cur, header = None, True
        elif header and line.startswith("--- "):
            cur = line[6:] if line.startswith("--- a/") else None
        elif header and line.startswith("+++ "):
            if cur is None and line.startswith("+++ b/"):
                cur = line[6:]  # added file: no old lines
        else:
            if line.startswith("@@"):
                header = False
            m = HUNK.match(line)
            if m and cur in hunks:
                start, length = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
                hunks[cur].append((start, length))
    return head, hunks


def changes_copy(product: Path, role: str, entry: dict) -> Tuple[str, Dict[str, List[Tuple[int, int]]]]:
    orig = (product / entry["path"]).resolve()
    if not orig.exists():
        raise S.SourceError(f"{role}: {orig} does not exist any more")
    now_h = S.tree_hashes(orig)
    then_h = S.tree_hashes(product / "sources" / role)
    changed = {p: [] for p in set(now_h) | set(then_h) if now_h.get(p) != then_h.get(p)}
    digest = S.tree_sha256(orig)
    return digest, changed


def cite_re(roles: List[str]):
    alt = "|".join(re.escape(r) for r in sorted(roles, key=len, reverse=True))
    return re.compile(r"(?<![\w./-])(" + alt + r")/([A-Za-z0-9_.\-/+~\[\]]+?)(?::(\d+)(?:-(\d+))?)?(?:@([0-9a-f]{6,64}))?(?=[^A-Za-z0-9_.\-/+~\[\]]|$)")


def scan_files(base: Path, globs: List[str]) -> List[Path]:
    out = []
    for g in globs:
        for p in sorted(base.glob(g)):
            if p.is_file() and p.suffix.lower() in TEXT_EXT and p not in out:
                out.append(p)
    return out


def touched(hunks: List[Tuple[int, int]], a: Optional[int], b: Optional[int]) -> bool:
    if a is None:
        return False
    b = b or a
    for start, length in hunks:
        lo, hi = start, start + max(length, 1) - 1
        if length == 0:  # pure insertion after line `start`
            lo, hi = start, start + 1
        if lo <= b and a <= hi:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir")
    ap.add_argument("--offline", action="store_true", help="skip URL sources")
    ap.add_argument("--json", action="store_true", help="print a JSON report instead of text")
    a = ap.parse_args()

    product = pvs.product_dir(Path(a.product_dir))
    lock = pvs.read_json(product / "sources.lock", {}) or {}
    if not lock:
        pvs.die("no sources.lock: run fetch_sources.py first")

    changed: Dict[str, Dict[str, List[Tuple[int, int]]]] = {}
    report = {"sources": {}, "videos": {}, "kit": []}
    for role, entry in sorted(lock.items()):
        try:
            if entry.get("commit"):
                res = changes_git(product, role, entry, a.offline)
                if res is None:
                    report["sources"][role] = {"skipped": "url source, --offline"}
                    continue
                head, hunks = res
                report["sources"][role] = {"locked": S.short(entry["commit"]), "head": S.short(head), "files": sorted(hunks)}
            else:
                head, hunks = changes_copy(product, role, entry)
                report["sources"][role] = {"locked": S.short(entry.get("tree_sha256", "")), "head": S.short(head), "files": sorted(hunks)}
            changed[role] = hunks
        except S.SourceError as e:
            report["sources"][role] = {"error": str(e)}

    rx = cite_re(list(lock))

    def hits_in(files: List[Path], base: Path) -> List[dict]:
        hits = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except (ValueError, OSError):  # undecodable text or unreadable file
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for m in rx.finditer(line):
                    role, path = m.group(1), m.group(2).rstrip(".")
                    hunks = changed.get(role)
                    if not hunks:
                        continue
                    a0 = int(m.group(3)) if m.group(3) else None
                    b0 = int(m.group(4)) if m.group(4) else None
                    match = [c for c in hunks if c == path or c.startswith(path.rstrip("/") + "/")]
                    if not match:
                        continue
                    hit = any(touched(hunks[c], a0, b0) for c in match if c == path)
                    hits.append({"file": f.relative_to(base).as_posix(), "line": n, "cite": m.group(0),
                                 "status": "lines changed" if hit else ("file changed" if path in hunks else "folder changed")})
        return hits

    for v in sorted((product / "videos").glob("*/")) if (product / "videos").exists() else []:
        h = hits_in(scan_files(v, SCAN_GLOBS), v)
        if h:
            report["videos"][v.name] = h
    report["kit"] = hits_in(scan_files(product, KIT_GLOBS), product)

    if a.json:
        print(json.dumps(report, indent=1))
        return 0
    for role, r in report["sources"].items():
        if "error" in r:
            print(f"{role:10} ERROR: {r['error']}")
        elif "skipped" in r:
            print(f"{role:10} skipped ({r['skipped']})")
        elif not r["files"]:
            print(f"{role:10} {r['locked']} is still the head: no changes")
        else:
            print(f"{role:10} {r['locked']} -> {r['head']}: {len(r['files'])} file(s) changed")
    for name, hits in report["videos"].items():
        print(f"videos/{name}: {len(hits)} citation(s) of changed files")
        for h in hits:
            print(f"  {h['file']}:{h['line']}  {h['cite']}  ({h['status']})")
    if report["kit"]:
        print(f"kit: {len(report['kit'])} citation(s) of changed files")
        for h in report["kit"]:
            print(f"  {h['file']}:{h['line']}  {h['cite']}  ({h['status']})")
    compared = [r for r in report["sources"].values() if "files" in r]
    if compared and all(r["locked"] == r["head"] for r in compared):
        print("hint: every lock equals its head. If fetch_sources.py --refresh just ran, the changes it pulled "
              "are no longer visible here: run changed_since.py before --refresh next time, or diff the "
              "previous commit by hand (git diff <old sha> <new sha>).")
    total = len(list((product / 'videos').glob('*/'))) if (product / 'videos').exists() else 0
    print(f"{len(report['videos'])} of {total} video(s) cite changed files"
          + (": " + ", ".join(report["videos"]) if report["videos"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
