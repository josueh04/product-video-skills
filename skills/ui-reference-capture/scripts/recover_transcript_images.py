"""Recover the images a past Claude Code session saw, from its transcript JSONL.

    python3 recover_transcript_images.py <session.jsonl> [<out_dir>] [--from-line N] [--to-line N]
        [--tool NAME] [--no-pasted] [--allow-in-repo]

Screenshots returned by tools (browser captures, window captures, images read from disk) and
images pasted into the chat are stored in the session JSONL as base64 blocks. This decodes each
one to <out_dir>/NNN_L<line>.<ext> and writes index.tsv (file, timestamp, source, tool name,
first 300 characters of the tool input), so the captures of a live app can be reused without
going back to the app.

The images can contain real customer data, internal ids and personal accounts. So the default
out_dir is a fresh folder under the system temp dir, and the script refuses an out_dir inside a
git work tree unless --allow-in-repo. Review them there; copy only what is cleared, and only into
references/ after any real data is cropped out.
Session transcripts live in ~/.claude/projects/<project-folder>/<session-id>.jsonl (subagent
transcripts in a subagents/ folder next to it).
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def inside_git(path: Path) -> bool:
    p = path
    while not p.exists():
        p = p.parent
    r = subprocess.run(["git", "-C", str(p), "rev-parse", "--is-inside-work-tree"],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("jsonl")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--from-line", type=int, default=0, help="skip lines before this one")
    ap.add_argument("--to-line", type=int, default=0, help="stop after this line (0: to the end)")
    ap.add_argument("--tool", action="append", help="only images returned by this tool (substring, repeatable)")
    ap.add_argument("--no-pasted", action="store_true", help="skip images pasted by the user")
    ap.add_argument("--allow-in-repo", action="store_true")
    a = ap.parse_args()

    out = Path(a.out_dir) if a.out_dir else Path(tempfile.mkdtemp(prefix="pvs-recovered-"))
    if inside_git(out.resolve()) and not a.allow_in_repo:
        print(f"refusing {out}: it is inside a git work tree and recovered images may hold real data. "
              "Use a temp folder (omit out_dir) or pass --allow-in-repo.", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    calls, idx, n = {}, [], 0

    def save(block, line_no, ts, source, name, inp):
        nonlocal n
        src = block.get("source") or {}
        data = src.get("data")
        if not data or src.get("type", "base64") != "base64":
            return
        mt = src.get("media_type", "")
        ext = "png" if "png" in mt else "webp" if "webp" in mt else "gif" if "gif" in mt else "jpg"
        n += 1
        fn = f"{n:03d}_L{line_no}.{ext}"
        (out / fn).write_bytes(base64.b64decode(data))
        idx.append("\t".join([fn, str(ts or ""), source, name or "", (inp or "").replace("\t", " ").replace("\n", " ")]))

    with open(a.jsonl, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < a.from_line:
                continue
            if a.to_line and i > a.to_line:
                break
            try:
                d = json.loads(line)
            except ValueError:
                continue
            msg = d.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                kind = c.get("type")
                if kind == "tool_use":
                    calls[c.get("id")] = (c.get("name"), json.dumps(c.get("input"))[:300])
                elif kind == "tool_result" and isinstance(c.get("content"), list):
                    name, inp = calls.get(c.get("tool_use_id"), ("?", ""))
                    if a.tool and not any(t in (name or "") for t in a.tool):
                        continue
                    for s in c["content"]:
                        if isinstance(s, dict) and s.get("type") == "image":
                            save(s, i, d.get("timestamp"), "tool", name, inp)
                elif kind == "image" and msg.get("role") == "user" and not a.no_pasted and not a.tool:
                    save(c, i, d.get("timestamp"), "pasted", "", "")
    (out / "index.tsv").write_text("file\ttimestamp\tsource\ttool\tinput\n" + "\n".join(idx) + ("\n" if idx else ""), encoding="utf-8")
    print(f"{n} images -> {out} (index.tsv lists each one). They may contain real data: keep them out of the repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
