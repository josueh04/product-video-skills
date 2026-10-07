"""Pure helpers shared by the script-and-voice scripts (no network, no audio I/O).

- pronounce map from product.yaml and the respelling of a line for the TTS
- alignment of provider word timings to the text that was sent
- mapping of those timings back to the canonical (on-screen) words
- ElevenLabs character alignment to word timings
- the content hash used to skip unchanged lines
"""
import difflib
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

Word = Dict[str, Any]

TOKEN = re.compile(r"\S+")


def norm(word: str) -> str:
    """Lowercase, letters and digits only: how words are compared across spellings."""
    return re.sub(r"[^0-9a-z]", "", word.lower())


# ---------------------------------------------------------------- pronounce

def pronounce_entries(product: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """product.pronounce as {canonical: {"say": str, ...checks}}.

    Accepts both forms:
        Acme: AK-mee
        Acme: {say: AK-mee, vowel: ae, confusable: ey}
    """
    raw = (product.get("product") or {}).get("pronounce") or {}
    out: Dict[str, Dict[str, Any]] = {}
    for canon, val in raw.items():
        if isinstance(val, dict):
            entry = dict(val)
            entry.setdefault("say", canon)
        else:
            entry = {"say": str(val)}
        out[str(canon)] = entry
    return out


def pronounce_map(product: Dict[str, Any]) -> Dict[str, str]:
    return {k: v["say"] for k, v in pronounce_entries(product).items()}


def _pattern(canon: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![0-9A-Za-z])" + re.escape(canon) + r"(?![0-9A-Za-z])")


def respell(text: str, pmap: Dict[str, str]) -> Tuple[str, List[Tuple[int, int, int, int]]]:
    """Apply the pronounce map to `text`.

    Returns (spoken_text, spans) where each span is (canon_start, canon_end, spoken_start,
    spoken_end) for one replacement. Longer keys win, so "Acme Tasks" beats "Acme".
    Matching is case-sensitive: the canonical spelling is exact by definition.
    """
    hits: List[Tuple[int, int, str]] = []
    taken = [False] * len(text)
    for canon in sorted(pmap, key=len, reverse=True):
        for m in _pattern(canon).finditer(text):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            hits.append((m.start(), m.end(), pmap[canon]))
    hits.sort()
    out, spans, pos = [], [], 0
    olen = 0
    for cs, ce, say in hits:
        out.append(text[pos:cs])
        olen += cs - pos
        spans.append((cs, ce, olen, olen + len(say)))
        out.append(say)
        olen += len(say)
        pos = ce
    out.append(text[pos:])
    return "".join(out), spans


def tokens(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(text)]


# ---------------------------------------------------------------- alignment

def align_words(timed: List[Word], text: str) -> List[Word]:
    """Give every whitespace token of `text` a start and end from `timed` (provider words).

    `timed` may differ from `text` (an ASR hears "10" for "ten", splits or joins words).
    Matching tokens take the provider times; the rest are spread over the gap between their
    matched neighbours in proportion to their length, so every token gets a time.
    """
    toks = tokens(text)
    if not toks:
        return []
    if not timed:
        raise ValueError("no word timings to align")
    a = [norm(w["w"]) for w in timed]
    b = [norm(t[0]) for t in toks]
    res: List[Optional[Tuple[float, float]]] = [None] * len(toks)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                res[j1 + k] = (timed[i1 + k]["s"], timed[i1 + k]["e"])
        elif tag == "replace":
            # Same span on both sides: take the provider block and split it by token length.
            s, e = timed[i1]["s"], timed[i2 - 1]["e"]
            _spread(res, toks, j1, j2, s, e)
    # Tokens with no counterpart (inserted in text): spread over the gap between neighbours.
    j = 0
    n = len(toks)
    while j < n:
        if res[j] is not None:
            j += 1
            continue
        k = j
        while k < n and res[k] is None:
            k += 1
        s = res[j - 1][1] if j > 0 else (timed[0]["s"] if k >= n else min(timed[0]["s"], res[k][0]))
        e = res[k][0] if k < n else max(timed[-1]["e"], s)
        if e < s:
            e = s
        _spread(res, toks, j, k, s, e)
        j = k
    return [{"w": t[0], "s": round(r[0], 3), "e": round(r[1], 3)} for t, r in zip(toks, res)]


def _spread(res, toks, j1, j2, s, e):
    lens = [max(1, len(norm(toks[j][0]))) for j in range(j1, j2)]
    total = float(sum(lens))
    t = s
    for j, ln in zip(range(j1, j2), lens):
        d = (e - s) * ln / total
        res[j] = (t, t + d)
        t += d


def to_canonical(spoken_words: List[Word], canon_text: str, spoken_text: str,
                 spans: List[Tuple[int, int, int, int]]) -> List[Word]:
    """Map timings of the spoken tokens back to the tokens of the canonical text.

    Outside a replacement the two texts are identical, so tokens pair one to one. Inside a
    replacement (e.g. "Acme" -> "AK-mee", "AI Notes" -> "A.I. Notes") the spoken
    tokens of that span cover the canonical tokens of that span: paired one to one when the
    counts match, else the span's time is split by token length. A canonical word whose
    spelling differs from what was spoken carries "say".
    """
    ctoks = tokens(canon_text)
    stoks = tokens(spoken_text)
    if len(stoks) != len(spoken_words):
        raise ValueError("spoken_words must be align_words() output for spoken_text")

    def s_to_c(pos: int) -> Tuple[int, Optional[int]]:
        """Canonical offset for a spoken offset, plus the replacement index it falls in."""
        delta = 0
        for idx, (cs, ce, ss, se) in enumerate(spans):
            if pos < ss:
                break
            if pos < se:
                return cs, idx
            delta = ce - se
        return pos + delta, None

    groups: Dict[Any, List[int]] = {}
    order: List[Any] = []
    for i, (_, st, _) in enumerate(stoks):
        cpos, rep = s_to_c(st)
        if rep is not None:
            key = ("rep", rep)
        else:
            key = ("tok", next((j for j, (_, a, b) in enumerate(ctoks) if a <= cpos < b), None))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(i)

    out: List[Optional[Word]] = [None] * len(ctoks)
    for key in order:
        idxs = groups[key]
        s = spoken_words[idxs[0]]["s"]
        e = spoken_words[idxs[-1]]["e"]
        if key[0] == "tok":
            j = key[1]
            if j is None:
                continue
            if out[j] is None:
                out[j] = {"w": ctoks[j][0], "s": s, "e": e, "_say": [stoks[i][0] for i in idxs]}
            else:  # several spoken tokens inside one canonical token (respelling with a space)
                out[j]["e"] = e
                out[j]["_say"] += [stoks[i][0] for i in idxs]
        else:
            cs, ce, _, _ = spans[key[1]]
            cj = [j for j, (_, a, b) in enumerate(ctoks) if a < ce and b > cs]
            if len(cj) == len(idxs):
                for j, i in zip(cj, idxs):
                    w = spoken_words[i]
                    _merge_into(out, j, ctoks[j][0], w["s"], w["e"], [stoks[i][0]])
            else:
                lens = [max(1, len(norm(ctoks[j][0]))) for j in cj]
                total = float(sum(lens))
                t = s
                for j, ln in zip(cj, lens):
                    d = (e - s) * ln / total
                    _merge_into(out, j, ctoks[j][0], t, t + d, [stoks[i][0] for i in idxs])
                    t += d
    res = []
    prev_e = 0.0
    for j, w in enumerate(out):
        if w is None:  # canonical token that produced no spoken token (should not happen)
            w = {"w": ctoks[j][0], "s": prev_e, "e": prev_e, "_say": []}
        say = " ".join(w.pop("_say"))
        w["s"], w["e"] = round(w["s"], 3), round(w["e"], 3)
        if say and say != w["w"]:
            w["say"] = say
        prev_e = w["e"]
        res.append(w)
    return res


def _merge_into(out, j, w, s, e, say):
    if out[j] is None:
        out[j] = {"w": w, "s": s, "e": e, "_say": list(say)}
    else:
        out[j]["s"] = min(out[j]["s"], s)
        out[j]["e"] = max(out[j]["e"], e)
        for x in say:
            if x not in out[j]["_say"]:
                out[j]["_say"].append(x)


def char_alignment_words(alignment: Dict[str, List[Any]]) -> List[Word]:
    """ElevenLabs /with-timestamps alignment (characters + start/end times) to words."""
    words: List[Word] = []
    cur, start, end = "", None, None
    for ch, s, e in zip(alignment.get("characters", []),
                        alignment.get("character_start_times_seconds", []),
                        alignment.get("character_end_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append({"w": cur, "s": start, "e": end})
            cur, start = "", None
            continue
        if start is None:
            start = s
        cur, end = cur + ch, e
    if cur:
        words.append({"w": cur, "s": start, "e": end})
    return words


def shift_words(words: List[Word], offset: float, dur: float) -> List[Word]:
    """Move word times by -offset (after trimming the head) and clamp them into the clip."""
    out = []
    for w in words:
        x = dict(w)
        x["s"] = round(min(max(0.0, w["s"] - offset), dur), 3)
        x["e"] = round(min(max(x["s"], w["e"] - offset), dur), 3)
        out.append(x)
    return out


def canonical_timings(timed: List[Word], canon_text: str, pmap: Dict[str, str]) -> List[Word]:
    """Provider word timings (for the respelled text) to canonical words, in one call."""
    spoken, spans = respell(canon_text, pmap)
    return to_canonical(align_words(timed, spoken), canon_text, spoken, spans)


# ---------------------------------------------------------------- cache

def content_hash(parts: Dict[str, Any]) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


# ---------------------------------------------------------------- roles

PLACEHOLDER = re.compile(r"^<.*>$")


def role_config(product: Dict[str, Any], role: str) -> Dict[str, Any]:
    roles = (product.get("voice") or {}).get("roles") or {}
    if role not in roles:
        raise KeyError(role)
    return dict(roles[role] or {})


def neighbours(rows: List[Dict[str, Any]], i: int) -> Tuple[Optional[str], Optional[str]]:
    """Previous and next line of the same role, sent as context so a line is read as part of
    an explanation instead of as a standalone announcement."""
    role = rows[i]["role"]
    prev = next((r["text"] for r in reversed(rows[:i]) if r["role"] == role), None)
    nxt = next((r["text"] for r in rows[i + 1:] if r["role"] == role), None)
    return prev, nxt
