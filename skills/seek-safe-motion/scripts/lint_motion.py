"""Static seek-safety lint for a HyperFrames video folder.

    bin/pvs-py skills/seek-safe-motion/scripts/lint_motion.py <video_dir>/video [--strict] [--json] [--summary]

Reads video/index.html, video/src/*.tpl and the *.js files in video/ and video/src/
(inline scripts only; minified vendor files are skipped). It finds the timeline patterns
that render fine in the preview and in single snapshots but drop or flicker elements when
three render workers seek the timeline out of order. Every rule is explained, with the
incident behind it, in skills/seek-safe-motion/SKILL.md.

Errors exit 1. Warnings exit 0 unless --strict. The last line is always a one-line summary.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONTROL_KEYS = {
    "duration", "ease", "delay", "immediateRender", "overwrite", "stagger", "repeat", "yoyo",
    "repeatDelay", "repeatRefresh", "onStart", "onUpdate", "onComplete", "onRepeat", "onReverseComplete",
    "onStartParams", "onUpdateParams", "onCompleteParams", "callbackScope", "paused", "id", "lazy",
    "data", "runBackwards", "startAt", "keyframes", "inherit", "reversed", "yoyoEase", "easeEach",
}
ALIASES = {"autoAlpha": "opacity"}
LAYOUT_KEYS = {"left", "top", "right", "bottom", "width", "height"}
LAYOUT_PREFIX = ("margin", "padding")
NOT_TWEENERS = re.compile(r"^(?:[A-Z]\w*Array|Array|Object|Buffer|Promise|Map|Set|Reflect|JSON)$")

RULES = {
    "SS001": ("error", "fromTo sets {keys} in fromVars but not in toVars: a worker whose frame lands on the tween "
                       "start reverts them and never re-applies them, so the element vanishes on every third frame",
              "repeat those keys in toVars with their end value, or use tl.set() then tl.to()"),
    "SS002": ("error", "to() startAt sets {keys} that the tween does not end on: same failure as SS001",
              "use fromTo with the keys in both vars, or tl.set() then tl.to()"),
    "SS003": ("warn", "fromTo after the start of the timeline without immediateRender: false: it writes its "
                      "start values at build time and fights earlier tweens on the same element after a seek",
              "add immediateRender: false to toVars"),
    "SS004": ("warn", "from() tween: its end state is whatever the element was at build time, which differs "
                      "between workers once earlier tweens have run",
              "use fromTo with explicit start and end, plus immediateRender: false"),
    "SS005": ("error", "tween animates {keys}: display cannot be interpolated and visibility flips at an "
                       "arbitrary point, so workers disagree about when the element exists",
              "change display or visibility with a zero-duration tl.set() at an explicit time; fade with opacity or autoAlpha"),
    "SS006": ("error", "{what} makes a frame depend on wall-clock time or chance, not on the timeline time, so "
                       "two workers render the same frame differently",
              "derive it from the timeline time (tl.time() in onUpdate) or use a seeded PRNG"),
    "SS007": ("error", "the timeline is played or autoplays: render-critical motion must be seeked by the renderer, never played",
              "create it with gsap.timeline({ paused: true }) and remove the play() call"),
    "SS008": ("warn", "repeat: -1 is infinite: only safe under a finite root data-duration, and it hides the true end of the timeline",
              "use a finite count: Math.max(0, Math.floor(span / period) - 1)"),
    "SS009": ("warn", "tween animates layout ({keys}): it reflows every frame and the check flags it as non-transform motion",
              "animate x, y, scale or clip-path instead; keep layout static"),
    "SS010": ("error", "tween targets a .clip element: HyperFrames owns a clip's visibility through data-start and data-duration",
              "animate a wrapper inside the clip"),
    "SS011": ("warn", "gsap.timeline() without paused: true",
              "create every timeline paused; the renderer seeks it"),
    "SS012": ("error", "a GSAP timeline is built but never registered on window.__timelines, so the renderer cannot seek it",
              "end the build with window.__timelines[\"<composition id>\"] = tl"),
}


# ------------------------------------------------------------------ scanning


def mask(text: str, html: bool) -> str:
    """Same length as text: comments blanked (newlines kept), and for HTML every byte outside
    an inline <script> blanked, so offsets still map to the original lines."""
    if html:
        keep = [False] * len(text)
        for m in re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", text, re.S | re.I):
            if re.search(r"\bsrc\s*=", m.group(1)):
                continue
            for i in range(m.start(2), m.end(2)):
                keep[i] = True
        text = "".join(c if keep[i] or c == "\n" else " " for i, c in enumerate(text))
    out = list(text)
    i, n = 0, len(text)
    state = None
    while i < n:
        c = text[i]
        nx = text[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nx == "/":
                state = "line"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if c == "/" and nx == "*":
                state = "block"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if c in "'\"`":
                state = c
        elif state == "line":
            if c == "\n":
                state = None
            else:
                out[i] = " "
        elif state == "block":
            if c == "*" and nx == "/":
                out[i] = out[i + 1] = " "
                state = None
                i += 2
                continue
            if c != "\n":
                out[i] = " "
        else:  # inside a string
            if c == "\\":
                i += 2
                continue
            if c == state or (c == "\n" and state != "`"):
                state = None
        i += 1
    return "".join(out)


def call_args(code: str, open_paren: int) -> Tuple[List[Tuple[str, int]], int]:
    """Top-level arguments of the call whose '(' is at open_paren: [(text, offset)], end."""
    depth, i, n = 0, open_paren, len(code)
    args, start, q = [], open_paren + 1, None
    while i < n:
        c = code[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append((code[start:i], start))
                return [(t, o) for t, o in args if t.strip()], i
        elif c == "," and depth == 1:
            args.append((code[start:i], start))
            start = i + 1
        i += 1
    return [], n


def split_top(s: str) -> List[str]:
    parts, depth, q, cur = [], 0, None, []
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == "\\" and i + 1 < len(s):
                cur.append(s[i + 1])
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
            cur.append(c)
        elif c in "([{":
            depth += 1
            cur.append(c)
        elif c in ")]}":
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


def obj_keys(arg: str) -> Optional[Dict[str, str]]:
    """Top-level keys of an object literal -> raw value text; None when not a plain literal."""
    s = arg.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    keys: Dict[str, str] = {}
    for item in split_top(s[1:-1]):
        it = item.strip()
        if not it:
            continue
        if it.startswith("..."):
            return None  # spread: the real keys are not visible statically
        depth, q, colon = 0, None, -1
        for i, c in enumerate(it):
            if q:
                if c == q:
                    q = None
            elif c in "'\"`":
                q = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == ":" and depth == 0:
                colon = i
                break
        if colon < 0:
            name = it.split("(")[0].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                keys[name] = name
            continue
        k = it[:colon].strip().strip("'\"")
        keys[k] = it[colon + 1:].strip()
    return keys


def norm_keys(keys: Dict[str, str]) -> set:
    return {ALIASES.get(k, k) for k in keys if k not in CONTROL_KEYS}


def is_zero(arg: Optional[str]) -> bool:
    return arg is not None and arg.strip().strip("'\"") in ("0", "0.0")


# ------------------------------------------------------------------ rules


def lint_text(path: Path, text: str) -> Tuple[List[Dict], Dict[str, int]]:
    html = path.suffix.lower() in (".html", ".htm", ".tpl")
    code = mask(text, html)
    findings: List[Dict] = []
    stats = {"tweens": 0, "unchecked": 0, "timelines": 0, "registered": 0}

    def line_of(off: int) -> int:
        return text.count("\n", 0, off) + 1

    def add(rule: str, off: int, snippet: str, **fmt):
        sev, msg, fix = RULES[rule]
        findings.append({"file": str(path), "line": line_of(off), "rule": rule, "severity": sev,
                         "message": msg.format(**fmt), "fix": fix, "snippet": " ".join(snippet.split())[:140]})

    for m in re.finditer(r"([\w$\]\)]+)\s*\.\s*(fromTo|from|to)\s*\(", code):
        recv, kind = m.group(1), m.group(2)
        if NOT_TWEENERS.match(recv):
            continue
        args, end = call_args(code, m.end() - 1)
        if len(args) < 2:
            continue
        snippet = text[m.start():min(end + 1, m.start() + 220)]
        target = args[0][0].strip()
        if kind == "fromTo":
            if len(args) < 3:
                continue
            fv, tv = obj_keys(args[1][0]), obj_keys(args[2][0])
            pos = args[3][0] if len(args) > 3 else None
            vars_list = [v for v in (fv, tv) if v is not None]
        else:
            fv, tv = None, obj_keys(args[1][0])
            pos = args[2][0] if len(args) > 2 else None
            vars_list = [tv] if tv is not None else []
        if not vars_list and not any(a[0].strip().startswith("{") for a in args[1:]):
            # Not a tween at all (e.g. a helper called to()), or fully computed vars.
            if kind == "fromTo":
                stats["unchecked"] += 1
            continue
        stats["tweens"] += 1
        if kind == "fromTo":
            if fv is None or tv is None:
                stats["unchecked"] += 1
            else:
                missing = sorted(norm_keys(fv) - norm_keys(tv))
                if missing:
                    add("SS001", m.start(), snippet, keys=", ".join(missing))
                if tv.get("immediateRender", "").strip() != "false" and not is_zero(pos):
                    add("SS003", m.start(), snippet)
        if kind == "from" and tv is not None and tv.get("immediateRender", "").strip() != "false":
            add("SS004", m.start(), snippet)
        if kind == "to" and tv is not None and "startAt" in tv:
            sa = obj_keys(tv["startAt"])
            if sa is not None:
                missing = sorted(norm_keys(sa) - norm_keys(tv))
                if missing:
                    add("SS002", m.start(), snippet, keys=", ".join(missing))
        allkeys = set()
        for v in vars_list:
            allkeys |= set(v)
        bad = sorted(k for k in allkeys if k in ("display", "visibility"))
        if bad:
            add("SS005", m.start(), snippet, keys=", ".join(bad))
        layout = sorted(k for k in allkeys if k in LAYOUT_KEYS or k.startswith(LAYOUT_PREFIX))
        if layout:
            add("SS009", m.start(), snippet, keys=", ".join(layout))
        if re.search(r"""^["'`][^"'`]*\.clip(?![\w-])""", target):
            add("SS010", m.start(), snippet)
        for v in vars_list:
            if v.get("repeat", "").strip() == "-1":
                add("SS008", m.start(), snippet)
                break

    for m in re.finditer(r"\bMath\s*\.\s*random\s*\(|\bDate\s*\.\s*now\s*\(|\bnew\s+Date\b|\bperformance\s*\.\s*now\s*\(|"
                         r"\bset(?:Timeout|Interval)\s*\(|\brequestAnimationFrame\s*\(", code):
        what = " ".join(m.group(0).rstrip("(").split())
        add("SS006", m.start(), text[m.start():m.start() + 80], what=what)
    for m in re.finditer(r"\b(?:tl|timeline|TL|\w*[Tt]imeline\w*)\s*\.\s*play\s*\(|\bautoplay\s*:\s*true", code):
        add("SS007", m.start(), text[m.start():m.start() + 80])
    for m in re.finditer(r"\bgsap\s*\.\s*timeline\s*\(", code):
        stats["timelines"] += 1
        args, end = call_args(code, m.end() - 1)
        k = obj_keys(args[0][0]) if args else None
        if k is None and args:
            continue  # computed options
        if not k or k.get("paused", "").strip() != "true":
            add("SS011", m.start(), text[m.start():min(end + 1, m.start() + 120)])
    stats["registered"] = len(re.findall(r"__timelines\s*\[", code))
    return findings, stats


def collect(vdir: Path) -> List[Path]:
    files = []
    if (vdir / "index.html").exists():
        files.append(vdir / "index.html")
    for d in (vdir / "src", vdir):
        if d.is_dir():
            files += sorted(d.glob("*.tpl")) if d == vdir / "src" else []
            files += sorted(f for f in d.glob("*.js") if not f.name.endswith(".min.js"))
    seen, out = set(), []
    for f in files:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            out.append(f)
    return out


def lint_dir(vdir: Path) -> Tuple[List[Dict], Dict[str, int], List[Path]]:
    files = collect(vdir)
    findings: List[Dict] = []
    tot = {"tweens": 0, "unchecked": 0, "timelines": 0, "registered": 0}
    for f in files:
        fs, st = lint_text(f, f.read_text(encoding="utf-8", errors="replace"))
        findings += fs
        for k in tot:
            tot[k] += st[k]
    if tot["timelines"] and not tot["registered"]:
        sev, msg, fix = RULES["SS012"]
        findings.append({"file": str(files[0]) if files else str(vdir), "line": 1, "rule": "SS012", "severity": sev,
                         "message": msg, "fix": fix, "snippet": ""})
    # index.html is generated from src/template.tpl: report each finding once.
    uniq: Dict[Tuple[str, str], Dict] = {}
    for f in findings:
        key = (f["rule"], f["snippet"])
        if key in uniq:
            uniq[key].setdefault("also", []).append(f"{Path(f['file']).name}:{f['line']}")
        else:
            uniq[key] = f
    return list(uniq.values()), tot, files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Static seek-safety lint for a HyperFrames video folder.")
    ap.add_argument("video_dir", help="the video/ folder (holding index.html and src/)")
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--summary", action="store_true", help="print only the summary line")
    a = ap.parse_args(argv)
    vdir = Path(a.video_dir)
    if vdir.is_dir() and not (vdir / "index.html").exists() and (vdir / "video").is_dir():
        vdir = vdir / "video"  # accept the video folder's parent too
    if not vdir.is_dir():
        print(f"{vdir}: not a folder", file=sys.stderr)
        return 2
    findings, tot, files = lint_dir(vdir)
    findings.sort(key=lambda f: (f["severity"] != "error", f["file"], f["line"]))
    errors = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warn"]
    if a.json:
        print(json.dumps({"files": [str(f) for f in files], "stats": tot, "findings": findings}, indent=1))
    elif not a.summary:
        for f in findings:
            also = f" (also {', '.join(f['also'][:3])})" if f.get("also") else ""
            print(f"{f['file']}:{f['line']}: {f['severity']} {f['rule']}: {f['message']}{also}")
            if f["snippet"]:
                print(f"    {f['snippet']}")
            print(f"    fix: {f['fix']}")
    fail = bool(errors) or (a.strict and bool(warns))
    print(f"motion lint: {len(errors)} error(s), {len(warns)} warning(s) in {len(files)} file(s); "
          f"{tot['tweens']} tweens checked, {tot['unchecked']} fromTo with computed vars not checkable")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
