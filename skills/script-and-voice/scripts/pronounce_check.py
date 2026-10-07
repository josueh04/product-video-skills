"""Check that brand words are heard right in the voiced clips.

    bin/pvs-py skills/script-and-voice/scripts/pronounce_check.py <video_dir> [--only N1,N3] [--model small.en]

For every clip in audio/clips/ it transcribes the audio with whisper (no prompt, so the ASR is
not nudged toward the right answer) and flags:

  brand      a word from product.pronounce, product.names, the product name or the fictional
             company that the line contains but the transcript does not (fuzzy, spacing and
             case ignored)
  cast       a cast person's name (full, or first name alone) that the line contains but the
             transcript does not have word for word: "Maya" heard as "Mya" is close enough for
             the fuzzy match and still a different name to the viewer
  legacy     a legacy name from product.names heard in the clip
  vowel      a pronounce entry with `vowel:` whose first vowel, measured from formants, is
             closer to the confusable vowel than to the expected one
  match      (warning only) the transcript matches the line text below 0.80

A flag means "listen to this clip", not "the clip is wrong": ASRs mishear brand words that
were said correctly (see references/casting-and-pronunciation.md for known false positives).
Exits 1 when any brand, cast, legacy or vowel flag is raised.

Vowel check entry in product.yaml:

    pronounce:
      Acme: {say: AK-mee, vowel: ae, confusable: ey}

Optional explicit limits override the reference table: f1_min, f1_max, f2_min, f2_max (Hz).
"""
import argparse
import difflib
import math
import os
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvs  # noqa: E402
import voicelib as vl  # noqa: E402

# Average first and second formants (Hz) of American English vowels, adult male and female
# speakers, rounded from Hillenbrand et al. (1995). Labels are ARPAbet.
VOWELS = {
    "iy": ((342, 2322), (437, 2761)),   # beet
    "ih": ((427, 2034), (483, 2365)),   # bit
    "ey": ((476, 2089), (536, 2530)),   # bait
    "eh": ((580, 1799), (731, 2058)),   # bet
    "ae": ((588, 1952), (669, 2349)),   # bat
    "ah": ((623, 1200), (753, 1426)),   # but
    "aa": ((768, 1333), (936, 1551)),   # hot
    "ao": ((652, 997), (781, 1136)),    # bought
    "ow": ((497, 910), (555, 1035)),    # boat
    "uh": ((469, 1122), (519, 1225)),   # book
    "uw": ((378, 997), (459, 1105)),    # boot
    "er": ((474, 1379), (523, 1588)),   # bird
}


# ---------------------------------------------------------------- formants (pure numpy)

def _read(path: Path):
    import numpy as np
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
        return x, w.getframerate()


def _formants(seg, sr: int, order: int = 12) -> List[float]:
    """Formant frequencies of one frame from the roots of an LPC polynomial (Levinson-Durbin)."""
    import numpy as np
    seg = np.append(seg[0], seg[1:] - 0.97 * seg[:-1]) * np.hamming(len(seg))
    r = np.correlate(seg, seg, "full")[len(seg) - 1:len(seg) + order]
    a = np.zeros(order + 1)
    a[0] = 1
    e = r[0]
    if e <= 0:
        return []
    for i in range(1, order + 1):
        k = -(r[i] + np.dot(a[1:i], r[i - 1:0:-1])) / e
        a[1:i + 1] = a[1:i + 1] + k * a[i - 1::-1][:i]
        e *= 1 - k * k
        if e <= 0:
            return []
    f = sorted((np.angle(z) * sr / (2 * np.pi), -sr / np.pi * np.log(abs(z))) for z in np.roots(a) if z.imag > 0)
    return [fr for fr, bw in f if fr > 150 and bw < 400]


def first_vowel(wav: Path, start: float, end: float) -> Tuple[float, float]:
    """Median (F1, F2) over the loud frames of the first ~45% of a word."""
    import numpy as np
    x, sr = _read(wav)
    step = max(1, sr // 12000)
    y, sr2 = x[::step], sr // step
    s = int((start + 0.02) * sr2)
    e = int((start + max(0.08, (end - start) * 0.45)) * sr2)
    hop, win, rows = int(0.008 * sr2), int(0.022 * sr2), []
    for i in range(s, max(s + 1, e - win), hop):
        fr = y[i:i + win]
        if len(fr) < win or np.sqrt((fr ** 2).mean()) < 0.02:
            continue
        f = _formants(fr, sr2)
        if len(f) >= 2:
            rows.append(f[:2])
    return tuple(float(v) for v in np.median(np.array(rows), axis=0)) if rows else (0.0, 0.0)


def vowel_distance(f1: float, f2: float, label: str) -> float:
    """Distance in log-formant space to the nearer (male or female) reference of a vowel."""
    return min(math.hypot(math.log(f1 / r1), math.log(f2 / r2)) for r1, r2 in VOWELS[label])


def vowel_verdict(f1: float, f2: float, entry: Dict[str, Any]) -> Tuple[bool, str]:
    want = entry["vowel"]
    if f1 <= 0 or f2 <= 0:
        return False, "no voiced frames found at the word"
    limits = {k: entry[k] for k in ("f1_min", "f1_max", "f2_min", "f2_max") if k in entry}
    if limits:
        ok = (f1 >= limits.get("f1_min", 0) and f1 <= limits.get("f1_max", 1e9)
              and f2 >= limits.get("f2_min", 0) and f2 <= limits.get("f2_max", 1e9))
        return ok, f"F1 {f1:.0f} F2 {f2:.0f} against {limits}"
    if want not in VOWELS:
        return False, f"unknown vowel '{want}' (use one of {', '.join(VOWELS)})"
    nearest = min(VOWELS, key=lambda v: vowel_distance(f1, f2, v))
    other = entry.get("confusable")
    if other in VOWELS:
        ok = vowel_distance(f1, f2, want) < vowel_distance(f1, f2, other)
        return ok, f"F1 {f1:.0f} F2 {f2:.0f}: closer to /{want if ok else other}/ than /{other if ok else want}/"
    return nearest == want, f"F1 {f1:.0f} F2 {f2:.0f}: nearest /{nearest}/"


# ---------------------------------------------------------------- recognition (pure)

def heard(term: str, transcript: str, threshold: float = 0.8) -> Tuple[bool, str]:
    """Whether `term` appears in `transcript`, ignoring case, punctuation and spacing.
    Returns the closest window of the transcript for the report."""
    t = vl.norm(term)
    words = [vl.norm(w) for w in transcript.split()]
    words = [w for w in words if w]
    if not t:
        return True, ""
    if t in "".join(words):
        return True, term
    n = max(1, len(term.split()))
    best, best_win = 0.0, ""
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(0, max(1, len(words) - size + 1)):
            win = "".join(words[i:i + size])
            r = difflib.SequenceMatcher(a=t, b=win).ratio()
            if r > best:
                best, best_win = r, " ".join(words[i:i + size])
    return best >= threshold, best_win


def heard_exact(term: str, transcript: str) -> bool:
    """Whether every word of `term` appears, in order and adjacent, among the transcript words."""
    t = [vl.norm(w) for w in term.split() if vl.norm(w)]
    words = [vl.norm(w) for w in transcript.split() if vl.norm(w)]
    return not t or any(words[i:i + len(t)] == t for i in range(len(words) - len(t) + 1))


def cast_names(product: Dict[str, Any]) -> List[str]:
    """Full and first names of the cast people (product.yaml cast.people)."""
    out = set()
    for person in (product.get("cast") or {}).get("people") or []:
        name = str((person or {}).get("name") or "").strip()
        if name:
            out.update({name, name.split()[0]})
    return sorted(out, key=len, reverse=True)


def text_match(a: str, b: str) -> float:
    x = [vl.norm(w) for w in a.split() if vl.norm(w)]
    y = [vl.norm(w) for w in b.split() if vl.norm(w)]
    return difflib.SequenceMatcher(a=x, b=y, autojunk=False).ratio() if x or y else 1.0


def brand_terms(product: Dict[str, Any]) -> List[str]:
    p = product.get("product") or {}
    terms = list(vl.pronounce_entries(product)) + list((p.get("names") or {}).keys())
    if p.get("name"):
        terms.append(p["name"])
    cast = product.get("cast") or {}
    if (cast.get("company") or {}).get("name"):
        terms.append(cast["company"]["name"])
    for person in cast.get("people") or []:
        if person.get("name"):
            terms.append(person["name"])
            terms.append(person["name"].split()[0])  # lines often use the first name only
    out: List[str] = []
    for t in sorted(set(terms), key=len, reverse=True):
        out.append(t)
    return out


def legacy_terms(product: Dict[str, Any]) -> List[str]:
    names = (product.get("product") or {}).get("names") or {}
    return [str(x) for v in names.values() for x in (v or [])]


def in_text(term: str, text: str) -> bool:
    return vl._pattern(term).search(text) is not None


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Flag brand words that were not heard right.")
    ap.add_argument("video_dir")
    ap.add_argument("--only")
    ap.add_argument("--model", default=os.environ.get("PVS_WHISPER_MODEL", "small.en"))
    a = ap.parse_args()
    vdir = Path(a.video_dir).resolve()
    audio = vdir / "audio"
    product = pvs.load_product(vdir)
    rows = pvs.read_lines_tsv(audio / "lines.tsv")
    tim = pvs.read_json(audio / "timings.json", {}) or {}
    only = set(a.only.split(",")) if a.only else None
    entries = vl.pronounce_entries(product)
    brands, legacy = brand_terms(product), legacy_terms(product)
    people = set(cast_names(product))
    try:
        import whisper
    except ImportError:
        pvs.die("openai-whisper is not installed; run /video-setup.")
    model = whisper.load_model(a.model)
    lang = "en" if a.model.endswith(".en") else product["video"].get("lang", "en")

    flags = 0
    for r in rows:
        lid = r["id"]
        if only and lid not in only:
            continue
        clip = audio / "clips" / f"{lid}.wav"
        if not clip.exists():
            print(f"{lid:5} MISSING clip; run tts.py first")
            flags += 1
            continue
        res = model.transcribe(str(clip), language=lang, fp16=False, condition_on_previous_text=False)
        said = res.get("text", "").strip()
        notes: List[str] = []
        covered = ""
        for term in brands:
            if in_text(term, r["text"]) and not in_text(term, covered):
                covered += " " + term
                ok, win = heard(term, said)
                if term in people:
                    if not heard_exact(term, said):
                        notes.append(f"cast name '{term}' not heard exactly (heard '{win}')")
                elif not ok:
                    notes.append(f"brand '{term}' not recognized (heard '{win}')")
        for term in legacy:
            if heard(term, said, 0.92)[0] and not in_text(term, r["text"]):
                notes.append(f"legacy name '{term}' heard")
        for canon, entry in entries.items():
            if not entry.get("vowel") or not in_text(canon, r["text"]):
                continue
            first = vl.norm(canon.split()[0])
            word = next((w for w in (tim.get(lid) or {}).get("words", []) if vl.norm(w["w"]).startswith(first)), None)
            if not word:
                notes.append(f"vowel '{canon}': word not in timings.json")
                continue
            f1, f2 = first_vowel(clip, word["s"], word["e"])
            ok, why = vowel_verdict(f1, f2, entry)
            if not ok:
                notes.append(f"vowel '{canon}' expected /{entry['vowel']}/: {why}")
        m = text_match(r["text"], said)
        hard = len(notes)
        if m < 0.8:
            notes.append(f"warning: transcript matches the line at {m:.2f}")
        flags += hard
        status = "FLAG" if hard else "ok"
        print(f"{lid:5} {status:4} {m:4.2f}  heard: {said[:70]}")
        for n in notes:
            print(f"        {n}")
    print(f"{flags} flag(s). Listen to every flagged clip before deciding on a new take.")
    if flags:
        sys.exit(1)


if __name__ == "__main__":
    main()
