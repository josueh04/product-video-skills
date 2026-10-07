"""Turn a free-text batch of review notes into one markdown table skeleton per video.

    bin/pvs-py skills/video-review/scripts/feedback_table.py <product_dir> [<notes.txt> | -] [--out FILE]

Each note (a line, a bullet or a paragraph) is kept verbatim and assigned to a video when it
names the video id or its BRIEF title, or when it sits under a heading such as "pitch:" or
"## Onboarding tour". Notes that say "all videos" or "every video" go to a shared section,
because a note that is really a rule must reach every video in the same round. Notes that match
nothing are listed for the coordinator to ask about. The coordinator fills the Meaning and
Acceptance columns; this script only does the sorting.
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pvs

ALL = re.compile(r"\b(all|every|each)\s+(the\s+)?(videos?|pieces?|cuts?)\b|\bacross\s+(all|the)\s+videos\b", re.I)
TIME = re.compile(r"\b(\d{1,2}:\d{2}(?:\.\d+)?)\b|\b(?:at|around|near)\s+(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?)?)?\b", re.I)
HEADING = re.compile(r"^\s*(?:#+\s*|video\s*:\s*|\*\*)?(?P<name>[^:*#]{1,60}?)(?:\*\*)?\s*:?\s*$", re.I)


def videos(pdir: Path) -> Dict[str, Dict[str, str]]:
    out = {}
    root = pdir / "videos"
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if (d / "BRIEF.md").exists():
            meta = pvs.read_brief(d)
            out[d.name] = {"title": str(meta.get("title") or ""), "version": str(meta.get("version") or 1)}
    return out


def aliases(vid: str, info: Dict[str, str]) -> List[str]:
    names = {vid.lower(), vid.replace("-", " ").lower()}
    if info.get("title"):
        names.add(info["title"].lower())
    return sorted((n for n in names if len(n) >= 3), key=len, reverse=True)


def split_notes(text: str) -> List[str]:
    """One note per line or bullet; indented lines continue the previous note. Headings are
    returned with a leading NUL so the caller can switch the current video."""
    notes: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if line[:1] in (" ", "\t") and notes and not notes[-1].startswith("\0") \
                and not re.match(r"^([-*+]|\d+[.)])\s+", s):
            notes[-1] += " " + s
            continue
        s = re.sub(r"^([-*+]|\d+[.)])\s+", "", s)
        if HEADING.match(s) and (s.endswith(":") or s.startswith("#") or s.lower().startswith("video:")):
            notes.append("\0" + s)
        else:
            notes.append(s)
    return notes


def first_mention(text: str, vids: Dict[str, Dict[str, str]]) -> List[str]:
    """Videos named in the note, earliest mention first."""
    low = text.lower()
    found = []
    for vid, info in vids.items():
        pos = [m.start() for name in aliases(vid, info)
               for m in re.finditer(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", low)]
        if pos:
            found.append((min(pos), vid))
    return [v for _, v in sorted(found)]


def where(note: str) -> str:
    found = [m.group(1) or (m.group(2) + " s") for m in TIME.finditer(note)]
    return ", ".join(found)


def cell(s: str) -> str:
    return s.replace("|", "\\|").strip()


def sort_notes(text: str, vids: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, List[str]], List[str], List[str]]:
    per: Dict[str, List[str]] = {v: [] for v in vids}
    shared, unassigned = [], []
    current = None
    for note in split_notes(text):
        if note.startswith("\0"):
            head = note[1:]
            hits = first_mention(head, vids)
            current = "*" if ALL.search(head) else (hits[0] if hits else None)
            continue
        prefix = re.match(r"^([^:]{1,60}):\s+\S", note)
        if prefix and ALL.search(prefix.group(1)):
            shared.append(note)
            continue
        if prefix and first_mention(prefix.group(1), vids):
            per[first_mention(prefix.group(1), vids)[0]].append(note)
            continue
        if ALL.search(note):
            shared.append(note)
            continue
        hits = first_mention(note, vids)
        if hits:
            extra = f" (also mentions {', '.join(hits[1:])})" if len(hits) > 1 else ""
            per[hits[0]].append(note + extra)
        elif current == "*":
            shared.append(note)
        elif current:
            per[current].append(note)
        elif len(vids) == 1:
            per[next(iter(vids))].append(note)
        else:
            unassigned.append(note)
    return per, shared, unassigned


def render(pdir: Path, text: str) -> str:
    vids = videos(pdir)
    if not vids:
        pvs.die(f"feedback_table: no videos with a BRIEF.md under {pdir / 'videos'}")
    per, shared, unassigned = sort_notes(text, vids)
    out = [f"# Review round, {dt.date.today().isoformat()}", "",
           "Fill Meaning (your reading, including what must NOT change) and Acceptance (how the "
           "fixed version will be checked). Mark notes that are really rules for every video.", ""]
    head = ["| # | Reviewer's words (verbatim) | Where | Meaning | Acceptance | Rule for all videos? |",
            "|---|---|---|---|---|---|"]
    for vid, info in vids.items():
        notes = per[vid]
        if not notes and not shared:
            continue
        nxt = int(info["version"]) + 1
        out += [f"## {vid} (v{info['version']} to v{nxt}){': ' + info['title'] if info['title'] else ''}", ""] + head
        for i, n in enumerate(notes, 1):
            out.append(f"| {i} | {cell(n)} | {where(n)} |  |  |  |")
        for j, n in enumerate(shared, len(notes) + 1):
            out.append(f"| {j} | {cell(n)} (shared note) | {where(n)} |  |  | yes |")
        out.append("")
    if unassigned:
        out += ["## Unassigned (ask the reviewer which video)", ""]
        out += [f"- {n}" for n in unassigned] + [""]
    untouched = [v for v in vids if not per[v] and not shared]
    if untouched:
        out += ["## No feedback (stay untouched)", ""] + [f"- {v} v{vids[v]['version']}" for v in untouched] + [""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sort a batch of review notes per video.")
    ap.add_argument("product_dir")
    ap.add_argument("notes", nargs="?", default="-", help="a text file, or - for stdin")
    ap.add_argument("--out", help="write the markdown here instead of stdout")
    a = ap.parse_args()
    pdir = pvs.product_dir(Path(a.product_dir))
    text = sys.stdin.read() if a.notes == "-" else Path(a.notes).read_text(encoding="utf-8")
    if not text.strip():
        pvs.die("feedback_table: the notes are empty")
    md = render(pdir, text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(md + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
