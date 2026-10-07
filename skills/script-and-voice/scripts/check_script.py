"""Lint audio/lines.tsv before any voice is generated.

    bin/pvs-py skills/script-and-voice/scripts/check_script.py <video_dir>

Errors (exit 1):
  - malformed rows, empty text, duplicate or badly formed ids
  - a role that is not in product.yaml voice.roles
  - speed outside 0.7 to 1.2 (the range TTS providers accept without artifacts)
  - a clip over 40 words (one clip per sentence keeps a changed line cheap and re-timeable)
  - a banned term, a never_say phrase or a legacy name (render-qa's matcher when present)
  - a pronounce respelling written into the script (lines.tsv keeps the on-screen spelling)

Warnings:
  - over 25 words or more than two sentences in one clip
  - digits (write numbers and times as words: "ten a.m.", so the TTS and the QA agree)
  - dashes inside a sentence (TTS pauses on them unpredictably)
  - ids in timings.json that are no longer in lines.tsv
"""
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvs  # noqa: E402
import voicelib as vl  # noqa: E402

ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
MAX_WORDS, WARN_WORDS = 40, 25
COST: Dict[str, int] = {}


def _find_banned():
    """render-qa's matcher if that skill is installed, else None."""
    qa = pvs.workbench() / "skills" / "render-qa" / "scripts"
    if (qa / "banned_terms.py").exists():
        sys.path.insert(0, str(qa))
        try:
            from banned_terms import find_banned  # type: ignore
            return find_banned
        except Exception:
            return None
    return None


def inline_banned(text: str, product: Dict[str, Any]) -> List[Tuple[str, str]]:
    p = product.get("product") or product
    groups = [("banned", p.get("banned_terms") or []), ("never_say", p.get("never_say") or []),
              ("legacy_name", [x for v in (p.get("names") or {}).values() for x in (v or [])])]
    hits, seen = [], set()
    for kind, terms in groups:
        for t in terms:
            if not t or t.lower() in seen:
                continue
            if re.search(r"(?<![0-9A-Za-z])" + re.escape(str(t)) + r"(?![0-9A-Za-z])", text, re.I):
                hits.append((str(t), kind))
                seen.add(t.lower())
    return hits


def parse_rows(tsv: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows, errors = [], []
    for n, raw in enumerate(tsv.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        if parts[0] == "id":
            continue
        if len(parts) < 4:
            errors.append(f"line {n}: expected 4 tab-separated columns (id, role, speed, text), got {len(parts)}")
            continue
        try:
            speed = float(parts[2] or 1.0)
        except ValueError:
            errors.append(f"line {n}: speed '{parts[2]}' is not a number")
            continue
        rows.append({"n": n, "id": parts[0].strip(), "role": parts[1].strip(), "speed": speed,
                     "text": "\t".join(parts[3:]).strip()})
    return rows, errors


def lint(vdir: Path) -> Tuple[List[str], List[str]]:
    audio = vdir / "audio"
    tsv = audio / "lines.tsv"
    if not tsv.exists():
        return [f"{tsv} not found"], []
    product = pvs.load_product(vdir)
    roles = (product.get("voice") or {}).get("roles") or {}
    pmap = vl.pronounce_map(product)
    find_banned = _find_banned() or inline_banned
    rows, errors = parse_rows(tsv)
    warnings: List[str] = []
    seen: Dict[str, int] = {}
    for r in rows:
        at = f"{r['id'] or '?'} (line {r['n']})"
        t = r["text"]
        if not ID.match(r["id"]):
            errors.append(f"{at}: id must start with a letter and use letters, digits, - or _")
        if r["id"] in seen:
            errors.append(f"{at}: duplicate id, first used on line {seen[r['id']]}")
        seen.setdefault(r["id"], r["n"])
        if r["role"] not in roles:
            errors.append(f"{at}: role '{r['role']}' is not in product.yaml voice.roles ({', '.join(roles) or 'none'})")
        if not 0.7 <= r["speed"] <= 1.2:
            errors.append(f"{at}: speed {r['speed']} is outside 0.7 to 1.2")
        if not t:
            errors.append(f"{at}: empty text")
            continue
        words = len(t.split())
        if words > MAX_WORDS:
            errors.append(f"{at}: {words} words; split it into one clip per sentence")
        elif words > WARN_WORDS:
            warnings.append(f"{at}: {words} words; consider splitting")
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]
        if len(sentences) > 2:
            warnings.append(f"{at}: {len(sentences)} sentences in one clip")
        for term, kind in find_banned(t, product):
            errors.append(f"{at}: {kind.replace('_', ' ')} '{term}'")
        for canon, say in pmap.items():
            if say != canon and re.search(r"(?<![0-9A-Za-z])" + re.escape(say) + r"(?![0-9A-Za-z])", t):
                errors.append(f"{at}: '{say}' is the TTS respelling of '{canon}'; write '{canon}' in the script")
        if re.search(r"\d", t):
            warnings.append(f"{at}: digits; write numbers and times as words")
        if re.search("\\s[\u2013\u2014-]\\s|\u2014|\u2013", t):
            warnings.append(f"{at}: a dash inside the sentence; use a comma or a period")
    # What a full run will cost the provider: characters of the respelled text, and how many of
    # them belong to lines whose archived take no longer matches.
    total = changed = 0
    for r in rows:
        spoken = vl.respell(r["text"], pmap)[0]
        total += len(spoken)
        meta = pvs.read_json(audio / "raw" / f"{r['id']}.json", None)
        if not meta or meta.get("spoken") != spoken:
            changed += len(spoken)
    COST.update(total=total, changed=changed)
    tim = pvs.read_json(audio / "timings.json", {}) or {}
    stale = [k for k in tim if k not in seen]
    if stale:
        warnings.append(f"timings.json has ids no longer in lines.tsv: {', '.join(stale)}")
    if not rows and not errors:
        fmt = ""
        if (vdir / "BRIEF.md").exists():
            fmt = str(pvs.read_brief(vdir).get("format") or "")
        if fmt != "loop":  # a silent loop has no narration; every other format does
            errors.append("lines.tsv has no lines")
    return errors, warnings


def main() -> None:
    if len(sys.argv) != 2:
        pvs.die("usage: check_script.py <video_dir>")
    vdir = Path(sys.argv[1]).resolve()
    errors, warnings = lint(vdir)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    if COST:
        print(f"{COST['changed']} characters to voice in new or changed lines ({COST['total']} for the whole script)")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
