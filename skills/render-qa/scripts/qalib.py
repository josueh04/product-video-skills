"""Shared measurement code for the render-qa scripts.

Everything here reads an MP4 or a video folder and returns plain data; the scripts decide
what passes. Nothing writes outside the folder it is given.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import pvs  # noqa: E402

import numpy as np  # noqa: E402

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

# Thresholds, calibrated on the production these skills come from (see references/triage.md).
OUTLIER_SCORE = 0.6        # mean gray levels a frame differs from both neighbours beyond their own diff
RUN_GAP = 6                # outlier frames closer than this join one run
WORKER_RUN_MIN = 4         # a run this long, all on one frame index mod 3, is the worker bug
WORKERS = 3                # HyperFrames 0.8.x renders with 3 interleaved workers
BLACK_LUMA = 3.0           # mean luma under this is a black frame
BLACK_HEAD_S, BLACK_TAIL_S = 1.0, 2.0   # intended fades from and to black
CLIP_SAMPLE = 0.995
CLICK_RATIO = 40.0
OVERLAP_S = 0.02


def run(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ config


def load_config(video_dir: Path) -> Dict[str, Any]:
    """product.yaml above the video folder merged over defaults, or the defaults alone."""
    d = pvs.find_up(video_dir, "product.yaml")
    if d is None:
        cfg = pvs._merge(pvs.DEFAULTS, {})
        cfg["_dir"] = ""
        return cfg
    return pvs.load_product(d)


def load_brief(video_dir: Path) -> Optional[Dict[str, Any]]:
    if not (Path(video_dir) / "BRIEF.md").exists():
        return None
    return pvs.read_brief(video_dir)


DRAFT_META = re.compile(r"<meta\s+[^>]*name=[\"']pvs-draft[\"'][^>]*content=[\"']1[\"']|"
                        r"<meta\s+[^>]*content=[\"']1[\"'][^>]*name=[\"']pvs-draft[\"']", re.I)


def draft_status(video_dir: Path) -> Tuple[bool, str]:
    """(draft, why). Draft when a signature is missing or the build left its draft marker."""
    brief = load_brief(video_dir)
    why = []
    if brief is None:
        why.append("no BRIEF.md, signatures cannot be checked")
    elif not pvs.signed(brief):
        missing = [k for k in ("coverage_signed_by", "claims_signed_by") if not brief.get(k)]
        why.append("BRIEF.md not signed: " + ", ".join(missing))
    html = Path(video_dir) / "video" / "index.html"
    if html.exists() and DRAFT_META.search(html.read_text(encoding="utf-8", errors="replace")):
        why.append('index.html carries <meta name="pvs-draft" content="1"> (built with --draft)')
    return (bool(why), "; ".join(why) if why else "signed, not a draft build")


# ------------------------------------------------------------------ probe


def probe(mp4: Path) -> Dict[str, Any]:
    r = run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)])
    if r.returncode != 0:
        pvs.die(f"ffprobe could not read {mp4}: {r.stderr.strip()[:200]}")
    pr = json.loads(r.stdout)
    vs = next((s for s in pr["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    if vs is None:
        pvs.die(f"{mp4} has no video stream")
    num, _, den = vs["r_frame_rate"].partition("/")
    return {
        "width": int(vs["width"]), "height": int(vs["height"]),
        "fps": float(num) / float(den or 1), "duration": float(pr["format"].get("duration", 0.0)),
        "vcodec": vs.get("codec_name"), "pix_fmt": vs.get("pix_fmt"),
        "audio": ({"codec": au.get("codec_name"), "sample_rate": int(au.get("sample_rate", 0)),
                   "channels": int(au.get("channels", 0))} if au else None),
    }


# ------------------------------------------------------------------ frames


def gray_frames(mp4: Path, w: int = 192, h: int = 108, fps: Optional[float] = None,
                t_end: Optional[float] = None) -> np.ndarray:
    """Every frame (or resampled to fps) as uint8 gray, shape (n, h, w)."""
    vf = (f"fps={fps}," if fps else "") + f"scale={w}:{h}:flags=area,format=gray"
    cmd = [FFMPEG, "-v", "error", "-y"]
    if t_end:
        cmd += ["-t", f"{t_end:.3f}"]
    cmd += ["-i", str(mp4), "-vf", vf, "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w)


def frame_stats(mp4: Path, w: int = 192, h: int = 108, chunk: int = 600) -> Dict[str, np.ndarray]:
    """Streamed per-frame numbers, so a long 60 fps render never sits in memory at once.

    d1[k] = mean |f[k] - f[k-1]|, d2[k] = mean |f[k] - f[k-2]| (nan where undefined),
    luma[k] = mean gray level. Area scaling keeps the mean, so a small element that
    flickers moves these numbers as much as it would at full size."""
    cmd = [FFMPEG, "-v", "error", "-i", str(mp4), "-vf", f"scale={w}:{h}:flags=area,format=gray",
           "-f", "rawvideo", "-"]
    fsz = w * h
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    hist = np.zeros((0, h, w), dtype=np.int16)
    d1, d2, luma = [], [], []
    while True:
        buf = proc.stdout.read(fsz * chunk)
        if not buf:
            break
        n = len(buf) // fsz
        cur = np.frombuffer(buf[:n * fsz], dtype=np.uint8).reshape(n, h, w).astype(np.int16)
        allf = np.concatenate([hist, cur])
        off = len(hist)
        luma.append(cur.reshape(n, -1).mean(axis=1))
        k = np.arange(off, len(allf))
        a1 = np.full(n, np.nan, dtype=np.float32)
        a2 = np.full(n, np.nan, dtype=np.float32)
        m1 = k >= 1
        m2 = k >= 2
        if m1.any():
            a1[m1] = np.abs(allf[k[m1]] - allf[k[m1] - 1]).mean(axis=(1, 2))
        if m2.any():
            a2[m2] = np.abs(allf[k[m2]] - allf[k[m2] - 2]).mean(axis=(1, 2))
        d1.append(a1)
        d2.append(a2)
        hist = allf[-2:]
    proc.wait()
    if proc.returncode not in (0, None):
        pvs.die(f"ffmpeg could not decode {mp4}")
    cat = lambda xs: np.concatenate(xs) if xs else np.zeros(0, dtype=np.float32)
    return {"d1": cat(d1), "d2": cat(d2), "luma": cat(luma)}


def outlier_runs(st: Dict[str, np.ndarray], fps: float) -> Dict[str, Any]:
    """One-frame glitches: frames unlike both neighbours while the neighbours agree.

    score(i) = min(d(i, i-1), d(i, i+1)) - d(i-1, i+1); above OUTLIER_SCORE is an outlier."""
    d1, d2 = st["d1"], st["d2"]
    n = len(d1)
    if n < 3:
        return {"frames": int(n), "outliers": 0, "runs": []}
    i = np.arange(1, n - 1)
    score = np.minimum(d1[i], d1[i + 1]) - d2[i + 1]
    idx = i[score > OUTLIER_SCORE]
    runs: List[List[int]] = []
    for k in idx.tolist():
        if runs and k - runs[-1][-1] <= RUN_GAP:
            runs[-1].append(k)
        else:
            runs.append([k])
    out = []
    for r in runs:
        mods = np.bincount(np.array(r) % WORKERS, minlength=WORKERS).tolist()
        out.append({
            "t0": round(r[0] / fps, 3), "t1": round(r[-1] / fps, 3), "n": len(r), "mod3": mods,
            "max": round(float(score[np.array(r) - 1].max()), 2),
            "worker_pattern": len(r) >= WORKER_RUN_MIN and max(mods) == len(r),
        })
    return {"frames": int(n), "outliers": int(len(idx)), "runs": out}


def black_frames(st: Dict[str, np.ndarray], fps: float, dur: float) -> Dict[str, Any]:
    luma = st["luma"]
    black = np.nonzero(luma < BLACK_LUMA)[0]
    mid = [int(i) for i in black if BLACK_HEAD_S < i / fps < dur - BLACK_TAIL_S]
    spans: List[List[float]] = []
    for i in mid:
        t = i / fps
        if spans and t - spans[-1][1] <= 1.5 / fps:
            spans[-1][1] = t
        else:
            spans.append([t, t])
    return {"total": int(len(black)), "mid": len(mid), "spans": [[round(a, 2), round(b, 2)] for a, b in spans]}


def frame_at(mp4: Path, t: float, out: Path, scale: Optional[Tuple[int, int]] = None) -> Path:
    vf = ["-vf", f"scale={scale[0]}:{scale[1]}"] if scale else []
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(mp4),
                    "-frames:v", "1", *vf, str(out)], check=True)
    return out


# ------------------------------------------------------------------ composition


class _AudioTags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: List[Dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "audio":
            self.tags.append({k: (v or "") for k, v in attrs})

    handle_startendtag = handle_starttag


def audio_clips(video_dir: Path, voice_ids: Optional[set] = None) -> List[Dict[str, Any]]:
    """<audio> tags of video/index.html as {id, key, src, start, dur, kind}, sorted by start.

    kind is "sfx" (src under sfx/ or id starting with sfx), "voice" (id vo-*, src under
    clips/, or a lines.tsv id) or "other" (music, ambience)."""
    html = Path(video_dir) / "video" / "index.html"
    if not html.exists():
        return []
    p = _AudioTags()
    p.feed(html.read_text(encoding="utf-8", errors="replace"))
    out = []
    for a in p.tags:
        src = a.get("src", "")
        if not src or "data-start" not in a:
            continue
        cid = a.get("id", "")
        key = cid[3:] if cid.startswith("vo-") else Path(src).stem
        try:
            start = float(a["data-start"])
            dur = float(a["data-duration"]) if a.get("data-duration") else None
        except ValueError:
            continue
        low = src.lower()
        if "/sfx/" in low or low.startswith("sfx/") or cid.lower().startswith("sfx"):
            kind = "sfx"
        elif cid.startswith("vo-") or "/clips/" in low or (voice_ids and key in voice_ids):
            kind = "voice"
        else:
            kind = "other"
        out.append({"id": cid, "key": key, "src": src, "start": start, "dur": dur, "kind": kind})
    out.sort(key=lambda c: c["start"])
    return out


def load_timings(video_dir: Path) -> Dict[str, Any]:
    return pvs.read_json(Path(video_dir) / "audio" / "timings.json", {}) or {}


def load_lines(video_dir: Path) -> List[Dict[str, Any]]:
    p = Path(video_dir) / "audio" / "lines.tsv"
    return pvs.read_lines_tsv(p) if p.exists() else []


def speech_span(clip: Dict[str, Any], timings: Dict[str, Any]) -> Tuple[float, float]:
    """Clip start and end narrowed to the spoken words when word timings exist."""
    st, du = clip["start"], clip["dur"] or 0.0
    words = (timings.get(clip["key"]) or {}).get("words") or []
    if words:
        return st + float(words[0]["s"]), st + float(words[-1].get("e", words[-1]["s"] + 0.4))
    return st, st + du


def voice_overlaps(clips: List[Dict[str, Any]], timings: Dict[str, Any]) -> List[Tuple[str, str, float]]:
    voice = [c for c in clips if c["kind"] == "voice" and c["dur"]]
    ov = []
    for i in range(len(voice)):
        a0, a1 = speech_span(voice[i], timings)
        for j in range(i + 1, len(voice)):
            b0, b1 = speech_span(voice[j], timings)
            if b0 < a1 - OVERLAP_S and a0 < b1:
                ov.append((voice[i]["key"], voice[j]["key"], round(a1 - b0, 2)))
    return ov


class _VisibleText(HTMLParser):
    """Text a viewer can read: body text, alt/title/aria-label/placeholder/value attributes,
    and string literals inside inline scripts (typed text, streamed replies, toasts)."""
    ATTRS = ("alt", "title", "aria-label", "placeholder", "value", "data-text")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._in = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._in = tag
        for k, v in attrs:
            if k in self.ATTRS and v:
                self.parts.append(v)

    def handle_endtag(self, tag):
        if tag == self._in:
            self._in = None

    def handle_data(self, data):
        if self._in == "style":
            return
        if self._in == "script":
            for m in re.finditer(r"\"((?:[^\"\\\n]|\\.)*)\"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`", data):
                s = next(g for g in m.groups() if g is not None)
                if re.search(r"[A-Za-z]{2,}\s+[A-Za-z]", s) or re.fullmatch(r"[A-Z][A-Za-z0-9 .'-]{2,}", s):
                    self.parts.append(s)
            return
        if data.strip():
            self.parts.append(data.strip())


def visible_text(html: str) -> str:
    p = _VisibleText()
    p.feed(html)
    return "\n".join(p.parts)


# Camera zoom: literal scale values on a camera element or passed to a cam*() helper.
_CAM_CALL = re.compile(r"\bcam\w*\s*\(\s*[^,()]+,\s*([0-9]*\.?[0-9]+)\s*[,)]")
_CAM_TWEEN = re.compile(r"\.(?:to|set|fromTo|from)\s*\(\s*([\"'`][^\"'`]*cam[^\"'`]*[\"'`])\s*,", re.I)
_SCALE = re.compile(r"\bscale\s*:\s*([0-9]*\.?[0-9]+)")
_CSS_CAM = re.compile(r"#?[\w-]*cam[\w-]*\s*\{[^}]*transform\s*:[^;}]*scale\(\s*([0-9]*\.?[0-9]+)", re.I)


def camera_zooms(text: str) -> List[Tuple[int, float, str]]:
    """(line, scale, snippet) for every literal camera scale found."""
    found = []

    def line_of(pos):
        return text.count("\n", 0, pos) + 1

    for m in _CAM_CALL.finditer(text):
        head = text[max(0, m.start() - 9):m.start()]
        if "function" in head:  # the helper's own definition
            continue
        found.append((line_of(m.start()), float(m.group(1)), m.group(0).strip()))
    for m in _CAM_TWEEN.finditer(text):
        seg = text[m.end():m.end() + 400]
        end = seg.find(")")
        seg = seg[:end if end >= 0 else len(seg)]
        for s in _SCALE.finditer(seg):
            found.append((line_of(m.start()), float(s.group(1)), (m.group(0) + seg[:s.end()]).strip()[:120]))
    for m in _CSS_CAM.finditer(text):
        found.append((line_of(m.start()), float(m.group(1)), m.group(0).strip()[:120]))
    return found


# ------------------------------------------------------------------ audio


def audio_samples(mp4: Path, sr: int = 48000) -> np.ndarray:
    """All audio channels as float32, shape (n, channels)."""
    info = probe(mp4)["audio"]
    ch = info["channels"] if info else 1
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(mp4), "-vn", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, ch)


def loudness(mp4: Path) -> Dict[str, Optional[float]]:
    eb = run([FFMPEG, "-hide_banner", "-nostats", "-i", str(mp4), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    summ = eb[eb.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summ)
    tp = re.search(r"True peak:\s*\n?\s*Peak:\s+(-?[\d.]+|-inf) dBFS", summ) or re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summ)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", summ)

    def f(m):
        if not m:
            return None
        return float("-inf") if m.group(1) == "-inf" else float(m.group(1))

    return {"I": f(i), "TP": f(tp), "LRA": f(lra)}


def clicks(a: np.ndarray, sr: int) -> List[float]:
    """Impulsive clicks: 1 ms windows far louder than their 30 ms neighbourhood, merged within 50 ms."""
    w1, w30 = int(sr * 0.001), int(sr * 0.030)
    e = a.astype(np.float64) ** 2
    c = np.concatenate([[0.0], np.cumsum(e)])
    i = np.arange(w30, len(a) - w30, w1)
    if len(i) == 0:
        return []
    s1 = (c[i + w1] - c[i]) / w1
    ctx = (c[i + w30] - c[i - w30] - (c[i + w1] - c[i])) / (2 * w30 - w1)
    hit = i[(s1 > 1e-5) & (s1 > CLICK_RATIO * (ctx + 1e-12))] / sr
    merged: List[float] = []
    for t in hit.tolist():
        if not merged or t - merged[-1] > 0.05:
            merged.append(t)
    return merged


def abrupt_edges(a: np.ndarray, sr: int) -> Tuple[List[float], List[float]]:
    """(ends, starts) on a 5 ms RMS envelope: a fall from > -30 dB to < -75 dB, or the reverse."""
    w5 = int(sr * 0.005)
    m = len(a) // w5
    if m < 2:
        return [], []
    db = 20 * np.log10(np.sqrt((a[:m * w5].reshape(m, w5).astype(np.float64) ** 2).mean(axis=1)) + 1e-9)
    k = np.arange(1, m)
    ends = (k[(db[:-1] > -30) & (db[1:] < -75)] * 0.005).tolist()
    starts = (k[(db[:-1] < -75) & (db[1:] > -25)] * 0.005).tolist()
    return ends, starts


def peak_db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.abs(x).max() + 1e-9)) if len(x) else -180.0


# ------------------------------------------------------------------ ASR


def asr(mp4: Path, lang: str, model_name: Optional[str] = None) -> Tuple[str, str]:
    """(text, model) from openai-whisper. small.en for English, multilingual small otherwise."""
    import whisper  # imported late: heavy, and optional for the fast tests
    name = model_name or ("small.en" if (lang or "en").lower().startswith("en") else "small")
    model = whisper.load_model(name)
    kw = {"fp16": False}
    if not name.endswith(".en"):
        kw["language"] = lang
    else:
        kw["language"] = "en"
    res = model.transcribe(str(mp4), **kw)
    return res.get("text", "").strip(), name


def norm_words(s: str) -> List[str]:
    return re.sub(r"[^\w' ]", " ", (s or "").lower()).split()


def script_in_playback_order(lines: List[Dict[str, Any]], clips: List[Dict[str, Any]]) -> str:
    text = {r["id"]: r["text"] for r in lines}
    order = [(c["start"], c["key"]) for c in clips if c["kind"] == "voice" and c["key"] in text]
    if not order:  # no composition: fall back to lines.tsv order
        return " ".join(r["text"] for r in lines)
    return " ".join(text[k] for _, k in sorted(order))


def diff_words(script: str, heard: str) -> Tuple[float, List[str]]:
    import difflib
    a, b = norm_words(script), norm_words(heard)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op != "equal" and (a1 - a0 > 1 or b1 - b0 > 1):
            diffs.append(f"{op}: script '{' '.join(a[a0:a1])}' / heard '{' '.join(b[b0:b1])}'")
    return sm.ratio(), diffs


def tmpdir() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="pvs-qa-")


def ensure_dir(p: Path) -> Path:
    os.makedirs(p, exist_ok=True)
    return Path(p)
