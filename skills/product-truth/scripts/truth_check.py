"""Check that every narrated line and every screen of a video is backed in TRUTH.md.

    bin/pvs-py skills/product-truth/scripts/truth_check.py <video_dir>

Reads audio/lines.tsv and TRUTH.md (a markdown table with at least the columns
id | sentence | source | visibility | verdict, see the product-truth SKILL.md) and fails when:
- a line id of lines.tsv has no row, or its row's sentence no longer matches the line text;
- a line's verdict is not "backed" or "approved" (cut, rewrite, needs-approval, unbacked);
- a row has no citation, or a citation <role>/<path>:<line>@<sha> names a role that is not in
  sources.lock, a sha that is not the locked one, a file missing from sources/<role>/, or a
  line past the end of that file;
- a visibility is not one of ui, backend, docs, mock, or a screen row is backend-only.
URLs (http, https) and docs:/mcp: references count as citations but cannot be checked offline.
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

import pvs

CITE = re.compile(r"(?<![\w./-])([A-Za-z0-9_-]+)/([A-Za-z0-9_.\-/+~\[\]]+?):(\d+)(?:-(\d+))?@([0-9a-f]{6,64})")
URL = re.compile(r"\bhttps?://\S+|\b(?:docs|mcp):\S+")
VIS = {"ui", "backend", "docs", "mock"}
LINE_OK = {"backed", "approved"}
VERDICTS = {"backed", "approved", "needs-approval", "rewrite", "cut", "unbacked", "mock"}
ALIASES = {"sentence": ["sentence", "claim", "text", "line"], "source": ["source", "sources", "citation", "citations"],
           "visibility": ["visibility", "visible", "seen"], "verdict": ["verdict", "status"], "id": ["id"]}


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("\\|", "|").strip().strip('"').strip()
    return re.sub(r"\s+", " ", s).lower()


def parse_tables(text: str) -> List[Dict[str, str]]:
    rows, header = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip("|"))]
        if header is None:
            low = [c.lower() for c in cells]
            mapping = {}
            for key, names in ALIASES.items():
                for i, c in enumerate(low):
                    if c in names and key not in mapping:
                        mapping[key] = i
            header = mapping if {"id", "source", "verdict"} <= set(mapping) else {}
            continue
        if not header or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        row = {k: (cells[i] if i < len(cells) else "") for k, i in header.items()}
        row["id"] = row["id"].strip("` ")
        if row["id"]:
            rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video_dir")
    a = ap.parse_args()

    vdir = Path(a.video_dir).resolve()
    product = pvs.product_dir(vdir)
    truth_p, lines_p = vdir / "TRUTH.md", vdir / "audio" / "lines.tsv"
    if not truth_p.exists():
        pvs.die(f"{truth_p} is missing: run the product-truth skill first")
    if not lines_p.exists():
        pvs.die(f"{lines_p} is missing: nothing to check")
    lines = {r["id"]: r["text"] for r in pvs.read_lines_tsv(lines_p)}
    rows = parse_tables(truth_p.read_text(encoding="utf-8"))
    lock = pvs.read_json(product / "sources.lock", {}) or {}
    errors: List[str] = []
    warns: List[str] = []
    by_id: Dict[str, Dict[str, str]] = {}
    line_count_cache: Dict[Path, int] = {}

    def check_source(rid: str, src: str) -> None:
        cites = list(CITE.finditer(src))
        urls = URL.findall(src)
        if not cites and not urls:
            errors.append(f"{rid}: no citation (role/path:line@sha or a docs URL)")
            return
        for m in cites:
            role, path, l0, l1, sha = m.group(1), m.group(2), int(m.group(3)), m.group(4), m.group(5)
            entry = lock.get(role)
            if entry is None:
                errors.append(f"{rid}: {m.group(0)} cites role {role}, which is not in sources.lock")
                continue
            pin = entry.get("commit") or entry.get("tree_sha256") or ""
            if not pin.startswith(sha):
                errors.append(f"{rid}: {m.group(0)} cites {sha[:7]} but {role} is locked at {pin[:7]}: re-verify against the lock")
                continue
            f = product / "sources" / role / path
            if not f.is_file():
                errors.append(f"{rid}: {m.group(0)}: {role}/{path} is not in sources/{role} at {pin[:7]}")
                continue
            if f not in line_count_cache:
                try:
                    line_count_cache[f] = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
                except OSError:
                    line_count_cache[f] = 0
            last = int(l1) if l1 else l0
            if l0 < 1 or last > line_count_cache[f] or last < l0:
                errors.append(f"{rid}: {m.group(0)}: line out of range ({role}/{path} has {line_count_cache[f]} lines)")

    for r in rows:
        rid = r["id"]
        if rid in by_id:
            errors.append(f"{rid}: two rows in TRUTH.md")
        by_id[rid] = r
        vis = r.get("visibility", "").lower().split(" ")[0].strip("`,;()")
        verdict = r.get("verdict", "").lower().split(" ")[0].strip("`,;()")
        if vis and vis not in VIS:
            errors.append(f"{rid}: visibility '{r.get('visibility')}' is not one of {', '.join(sorted(VIS))}")
        if verdict not in VERDICTS:
            errors.append(f"{rid}: verdict '{r.get('verdict')}' is not one of {', '.join(sorted(VERDICTS))}")
        is_screen = rid.startswith("screen:")
        if is_screen and vis == "backend":
            errors.append(f"{rid}: a screen cannot be backend-only; it has no UI to rebuild")
        if verdict == "mock" and vis != "mock":
            errors.append(f"{rid}: verdict mock needs visibility mock")
        if vis == "mock" and verdict == "mock":
            warns.append(f"{rid}: designed piece, not product UI (say so in the BRIEF)")
            continue
        if verdict in ("cut",):
            continue
        check_source(rid, r.get("source", ""))

    for lid, text in lines.items():
        r = by_id.get(lid)
        if r is None:
            errors.append(f"{lid}: line in lines.tsv has no row in TRUTH.md")
            continue
        verdict = r.get("verdict", "").lower().split(" ")[0].strip("`,;()")
        if "sentence" in r and norm(r["sentence"]) != norm(text):
            errors.append(f"{lid}: the line changed since TRUTH.md was written; verify the new text")
        if verdict == "cut":
            errors.append(f"{lid}: verdict cut, but the line is still in lines.tsv")
        elif verdict not in LINE_OK:
            errors.append(f"{lid}: verdict {verdict or '(empty)'}; a narrated line must be backed or approved")
    for rid in by_id:
        if not rid.startswith("screen:") and rid not in lines:
            warns.append(f"{rid}: row has no line in lines.tsv (cut or renamed?)")

    screens = [r for r in by_id if r.startswith("screen:")]
    for w in warns:
        print("  warn: " + w)
    for e in errors:
        print("  FAIL: " + e)
    print(f"truth check: {len(lines)} line(s), {len(screens)} screen(s), {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
