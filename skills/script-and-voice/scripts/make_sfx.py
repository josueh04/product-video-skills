"""Sound effects for a video: typing tracks made of real keystrokes, and named library sounds.

    bin/pvs-py skills/script-and-voice/scripts/make_sfx.py <video_dir> [--lib DIR] [--list]

The CLI reads <video_dir>/audio/sfx.tsv (optional; lines starting with # are comments):

    id      kind     value                                   cps
    type1   typing   Plan the Saturday orders for Northwind  14
    click   library  click
    pop     library  pop

and writes every sound to audio/sfx/ (typing as <id>.wav, library sounds as <name>.mp3), plus
audio/sfx/manifest.json ({id: {src, dur, kind}}) and audio/sfx/CREDITS.md. Without sfx.tsv, or
with --list, it prints the library. Placement in time belongs to build.py, which imports:

    from make_sfx import typing_track, library_sfx
    cue = typing_track("Plan the Saturday orders", start=T["N4"] + w("N4", "plan"), cps=14)
    cue = library_sfx("click", start=T["tClick"])

Each returns {"id", "src" (relative to the video dir), "start", "dur", "kind"} and writes the
file and CREDITS.md as a side effect. The library is the recorded Pixabay set that ships with
the HyperFrames media-use skill: vendor/hyperframes/skills/media-use/audio/assets/sfx, else
~/.claude/skills/media-use/audio/assets/sfx, or PVS_SFX_LIB / --lib.

Whoosh and riser sounds are refused (they read as white noise over a UI demo), and nothing
called music or bed is placed unless allow=True, because a video has no music unless its
brief asks for it.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvs  # noqa: E402

SR = 48000
MAX_STROKES_PER_S = 15.0  # faster than this reads as a machine gun, not a person typing
REFUSED = ("whoosh", "riser")
NO_MUSIC = ("music", "bed", "loop")
RARELY = ("glitch", "impact")
TYPING_SRC = ("typing.mp3", "key-press.mp3")


# ---------------------------------------------------------------- locations

def library_dir(override: Optional[str] = None) -> Path:
    cands = [override, os.environ.get("PVS_SFX_LIB"),
             str(pvs.workbench() / "vendor/hyperframes/skills/media-use/audio/assets/sfx"),
             str(Path.home() / ".claude/skills/media-use/audio/assets/sfx")]
    for c in cands:
        if c and (Path(c) / "manifest.json").exists():
            return Path(c)
    for c in cands:
        if c and Path(c).is_dir():
            return Path(c)
    pvs.die("No SFX library found. Run /video-setup (it installs the HyperFrames media-use skill), "
            "or point PVS_SFX_LIB at a folder of recorded sounds with a CREDITS.md.")
    raise SystemExit(1)


def _video_dir(video_dir: Optional[Path]) -> Path:
    if video_dir:
        return Path(video_dir).resolve()
    for start in (Path(sys.argv[0] or "."), Path.cwd()):
        d = pvs.find_up(start, "BRIEF.md")
        if d:
            return d
    pvs.die("Cannot tell which video this is: pass video_dir=")
    raise SystemExit(1)


# ---------------------------------------------------------------- audio

def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        pvs.die("ffmpeg not found. Install it (brew install ffmpeg) or run /video-setup.")
    return exe


def _decode(path: Path):
    import numpy as np
    p = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    if p.returncode != 0:
        pvs.die(f"cannot decode {path}: {p.stderr.decode()[-300:]}")
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def _write(path: Path, x) -> None:
    import numpy as np
    x = np.clip(x, -1, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def _onsets(x, thr_ratio=0.18, min_gap=0.045) -> List[float]:
    """Keystroke onsets: rises of a 2 ms RMS envelope above a share of its peak."""
    import numpy as np
    hop, win = int(SR * 0.002), int(SR * 0.004)
    n = (len(x) - win) // hop
    if n <= 1:
        return []
    idx = np.arange(n)[:, None] * hop + np.arange(win)[None, :]
    env = np.sqrt((x[idx] ** 2).mean(axis=1))
    thr = max(env.max() * thr_ratio, 0.01)
    out: List[float] = []
    last = -1
    for i in range(1, n):
        if env[i] > thr and env[i - 1] <= thr and (last < 0 or (i - last) * 0.002 > min_gap):
            out.append(i * 0.002)
            last = i
    return out


def _slice(x, t0, t1, fade_out=0.012):
    import numpy as np
    s = x[max(0, int(t0 * SR)):int(t1 * SR)].copy()
    n = min(len(s), int(fade_out * SR))
    k = min(len(s), 48)
    s[:k] *= np.linspace(0, 1, k)
    if n:
        s[-n:] *= np.linspace(1, 0, n)
    return s / (np.sqrt((s ** 2).mean()) + 1e-9)  # unit RMS, so every stroke starts equal


_STROKES: Dict[str, Any] = {}


def _strokes(lib: Path):
    """Single keystrokes cut from the recorded typing sound, plus a heavier one for spaces."""
    key = str(lib)
    if key not in _STROKES:
        for f in TYPING_SRC:
            if not (lib / f).exists():
                pvs.die(f"{lib / f} is missing: typing tracks are cut from {', '.join(TYPING_SRC)}")
        typ = _decode(lib / "typing.mp3")
        on = _onsets(typ)
        if len(on) < 3:
            pvs.die(f"found only {len(on)} keystrokes in {lib / 'typing.mp3'}")
        keys = [_slice(typ, t - 0.003, min((on[i + 1] - 0.003) if i + 1 < len(on) else 9.0, t + 0.095))
                for i, t in enumerate(on)]
        kp = _decode(lib / "key-press.mp3")
        k0 = (_onsets(kp) or [0.0])[0]
        space = _slice(kp, k0 - 0.003, k0 + 0.16, fade_out=0.04)
        _STROKES[key] = (keys, space)
    return _STROKES[key]


def stroke_times(n_chars: int, dur: float, cps: float, seed: int) -> List[float]:
    """Keystroke times across `dur` seconds: one per character up to MAX_STROKES_PER_S, with a
    seeded human rhythm (each gap 0.7 to 1.3 of the mean), so the same text always sounds the same."""
    import numpy as np
    rng = np.random.default_rng(seed)
    n = max(2, min(n_chars, int(round(dur * MAX_STROKES_PER_S))))
    base = dur / n
    t, times = 0.0, []
    while t < dur - 0.02 and len(times) < n:
        times.append(round(t, 4))
        t += max(0.045, base * rng.uniform(0.7, 1.3))
    return times


def render_typing(text: str, dur: float, cps: float, seed: int, lib: Path):
    import numpy as np
    keys, space = _strokes(lib)
    times = stroke_times(len(text), dur, cps, seed)
    rng = np.random.default_rng(seed + 7)
    buf = np.zeros(int((dur + 0.3) * SR), dtype=np.float32)
    for k, tt in enumerate(times):
        ch = text[min(len(text) - 1, int(k * len(text) / len(times)))]
        if ch == " ":
            s, g = space, 0.9 * rng.uniform(0.85, 1.0)
        else:
            s, g = keys[int(rng.integers(len(keys)))], rng.uniform(0.75, 1.0)
        i = int(tt * SR)
        seg = s[:len(buf) - i]
        buf[i:i + len(seg)] += seg * g
    buf *= 0.55 / (np.abs(buf).max() + 1e-9)
    return buf, len(times)


# ---------------------------------------------------------------- credits and manifest

def _manifest(lib: Path) -> Dict[str, Any]:
    f = lib / "manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _record(vdir: Path, lib: Path, cue_id: str, cue: Dict[str, Any], sources: List[str]) -> None:
    sfx = vdir / "audio" / "sfx"
    man_f = sfx / "manifest.json"
    man = pvs.read_json(man_f, {}) or {}
    entry = {k: cue[k] for k in ("src", "dur", "kind")}
    entry["from"] = sources
    man[cue_id] = entry
    pvs.write_json(man_f, man)
    used = sorted({s for e in man.values() for s in e.get("from", [])})
    lines = ["# Sound effects used in this video", "",
             f"Recorded sounds from the library at `{lib.name}` (the HyperFrames media-use set). "
             "Typing tracks are cut from its `typing.mp3` and `key-press.mp3`.", "",
             "Library files used:", ""] + [f"- `{u}`" for u in used] + [""]
    src = lib / "CREDITS.md"
    if src.exists():
        lines += ["## Library credits (copied verbatim)", "", src.read_text(encoding="utf-8").strip(), ""]
    (sfx / "CREDITS.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- API for build.py

def typing_track(text: str, start: float, cps: float = 14.0, *, dur: Optional[float] = None,
                 seed: Optional[int] = None, video_dir: Optional[Path] = None, lib: Optional[str] = None,
                 cue_id: Optional[str] = None) -> Dict[str, Any]:
    """Write a typing track for `text` and return its cue. dur defaults to len(text)/cps; pass
    dur to make the track last exactly as long as the beat that shows the text appearing."""
    if not text:
        raise ValueError("typing_track needs the text being typed")
    vdir = _video_dir(video_dir)
    ldir = library_dir(lib)
    d = float(dur) if dur else len(text) / float(cps)
    if seed is None:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    h = hashlib.sha256(json.dumps([text, round(d, 3), seed]).encode()).hexdigest()[:10]
    cue_id = cue_id or f"typing-{h}"
    out = vdir / "audio" / "sfx" / f"{cue_id}.wav"
    buf, n = render_typing(text, d, cps, seed, ldir)
    _write(out, buf)
    cue = {"id": cue_id, "src": f"audio/sfx/{out.name}", "start": round(float(start), 3), "dur": round(d, 3),
           "kind": "typing", "strokes": n}
    _record(vdir, ldir, cue_id, cue, list(TYPING_SRC))
    return cue


def check_name(name: str, allow: bool = False) -> Optional[str]:
    """None if the sound may be used, else why not. A warning for rarely fitting sounds is printed."""
    low = name.lower()
    if not allow and any(low.startswith(r) for r in REFUSED):
        return f"'{name}' is refused: whooshes and risers read as white noise over a UI demo (allow=True to override)"
    if not allow and any(m in low for m in NO_MUSIC):
        return f"'{name}' looks like music: a video has no music unless its brief asks (allow=True to override)"
    if any(low.startswith(r) for r in RARELY):
        print(f"note: '{name}' rarely fits a product demo; prefer click, pop or key-press", file=sys.stderr)
    return None


def library_sfx(name: str, start: float, *, video_dir: Optional[Path] = None, lib: Optional[str] = None,
                allow: bool = False) -> Dict[str, Any]:
    """Copy a named library sound into audio/sfx/ and return its cue."""
    why = check_name(name, allow)
    if why:
        raise ValueError(why)
    vdir = _video_dir(video_dir)
    ldir = library_dir(lib)
    man = _manifest(ldir)
    fname = (man.get(name) or {}).get("file") or f"{name}.mp3"
    src = ldir / fname
    if not src.exists():
        names = ", ".join(sorted(k for k in man if check_name(k, True) is None)) or "see the folder"
        raise ValueError(f"no sound '{name}' in {ldir} (available: {names})")
    out = vdir / "audio" / "sfx" / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.stat().st_size != src.stat().st_size:
        shutil.copyfile(src, out)
    dur = (man.get(name) or {}).get("duration")
    if dur is None:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True)
        dur = float(p.stdout.strip() or 0)
    cue = {"id": name, "src": f"audio/sfx/{fname}", "start": round(float(start), 3), "dur": round(float(dur), 3),
           "kind": "library"}
    _record(vdir, ldir, name, cue, [fname])
    return cue


# ---------------------------------------------------------------- CLI

def read_sfx_tsv(path: Path) -> List[Dict[str, str]]:
    rows = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        if parts[0] == "id":
            continue
        if len(parts) < 3:
            pvs.die(f"{path}:{n}: expected id, kind, value[, cps] separated by tabs")
        rows.append({"id": parts[0].strip(), "kind": parts[1].strip(), "value": parts[2].strip(),
                     "cps": (parts[3].strip() if len(parts) > 3 else "")})
    return rows


def print_library(ldir: Path) -> None:
    man = _manifest(ldir)
    print(f"SFX library: {ldir}")
    for k in sorted(man):
        mark = "refused" if check_name(k) else "ok"
        print(f"  {k:18} {man[k].get('duration', 0):5.2f}s  {mark:7}  {man[k].get('description', '')[:70]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the sound effects of a video.")
    ap.add_argument("video_dir")
    ap.add_argument("--lib")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    vdir = Path(a.video_dir).resolve()
    ldir = library_dir(a.lib)
    tsv = vdir / "audio" / "sfx.tsv"
    if a.list or not tsv.exists():
        print_library(ldir)
        if not tsv.exists():
            print(f"No {tsv}; nothing built. build.py can also call typing_track() and library_sfx() directly.")
        return
    errors = []
    for r in read_sfx_tsv(tsv):
        try:
            if r["kind"] == "typing":
                cps = float(r["cps"] or 14)
                cue = typing_track(r["value"], 0.0, cps, video_dir=vdir, lib=str(ldir), cue_id=r["id"])
                print(f"{r['id']:10} typing   {cue['dur']:5.2f}s  {cue['strokes']} strokes")
            elif r["kind"] == "library":
                cue = library_sfx(r["value"], 0.0, video_dir=vdir, lib=str(ldir))
                print(f"{r['id']:10} library  {cue['dur']:5.2f}s  {cue['src']}")
            else:
                errors.append(f"{r['id']}: unknown kind '{r['kind']}' (typing | library)")
        except ValueError as e:
            errors.append(f"{r['id']}: {e}")
    print(f"wrote {vdir / 'audio/sfx'} (manifest.json, CREDITS.md)")
    if errors:
        pvs.die("\n".join(errors))


if __name__ == "__main__":
    main()
