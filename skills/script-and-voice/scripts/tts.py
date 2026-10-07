"""Voice every line of audio/lines.tsv and write clips plus word timings.

    bin/pvs-py skills/script-and-voice/scripts/tts.py <video_dir> [--only N1,N3] [--provider elevenlabs|say]
                                                      [--force] [--restore]

For each line: the role column picks voice.roles[role] in product.yaml, the pronounce map
respells brand words in what is sent to the TTS (never in lines.tsv or on screen), and the
take is archived untouched in audio/raw/ before anything is done to it. Then the clip is
trimmed, resampled to 48 kHz mono, given its role's treatment (phone or room, optional),
normalized to voice.clip_lufs (ffmpeg loudnorm, two
passes), faded at both edges, and written to audio/clips/<id>.wav. Word timings are mapped
back to the canonical words and merged into audio/timings.json.

Providers:
  elevenlabs  POST /v1/text-to-speech/{voice}/with-timestamps, key from voice.env_key
              (environment or PVS_HOME/.env, never printed). Character alignment -> words.
  say         macOS `say -v <say_voice>`, word timings from whisper. Free; for drafts and tests.

A line whose text, voice and settings are unchanged since its last take is skipped (hash in
audio/raw/cache.json) unless --force. If only clip_lufs or the processing changed, the clip is
rebuilt from the archived raw take without calling the provider.
--restore (with --only) swaps the current raw take with the previous one in audio/raw/prev/
and rebuilds the clip, for when a new take came out worse.

Exits non-zero naming every line that failed.
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvs  # noqa: E402
import voicelib as vl  # noqa: E402

SR = 48000
PROC_VERSION = 1           # bump when the trim/normalize chain changes, so clips are rebuilt
TRUE_PEAK = -1.5           # dBTP after normalization (the renderer limits the mix at -1 on its own)
HEAD_PAD = 0.04            # silence kept before the first sound
TAIL_PAD = 0.18            # silence kept after the last sound
TAIL_MAX_AFTER_WORD = 0.6  # never keep more than this after the last word: cuts trailing clicks and breaths
FADE_IN = 0.005
FADE_OUT = 0.08
API = "https://api.elevenlabs.io"
# Per-role treatment, applied before normalization: a voice on a phone call or in a recorded
# meeting should sound like it, not like a studio narrator.
TREATMENTS = {
    "phone": "highpass=f=320,lowpass=f=3600,acompressor=threshold=-18dB:ratio=3:attack=5:release=80",
    "room": "highpass=f=140,lowpass=f=7200,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120",
}
ELEVEN_DEFAULTS = {
    "eleven_v3": {"stability": 0.5, "similarity_boost": 0.8},
    "_": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True},
}


class LineError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        pvs.die("ffmpeg not found. Install it (brew install ffmpeg) or run /video-setup.")
    return exe


def run(cmd: List[str], what: str) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise LineError(f"{what} failed: {p.stderr.strip()[-400:]}")
    return p


def decode(path: Path):
    """Any audio file to a float32 numpy array at 48 kHz mono."""
    import numpy as np
    p = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    if p.returncode != 0:
        raise LineError(f"cannot decode {path.name}: {p.stderr.decode()[-300:]}")
    return np.frombuffer(p.stdout, dtype=np.float32)


def sound_bounds(x, thr_db: float = -45.0) -> Tuple[float, float]:
    """First and last time the 10 ms RMS envelope rises above thr_db relative to its peak."""
    import numpy as np
    hop = int(SR * 0.01)
    n = len(x) // hop
    if n == 0:
        return 0.0, len(x) / SR
    env = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    ref = env.max()
    loud = np.where(20 * np.log10(env / ref + 1e-12) > thr_db)[0]
    if len(loud) == 0:
        return 0.0, len(x) / SR
    return loud[0] * hop / SR, (loud[-1] + 1) * hop / SR


def measure_loudnorm(path: Path, lufs: float) -> Optional[Dict[str, str]]:
    af = f"loudnorm=I={lufs}:TP={TRUE_PEAK}:LRA=11:print_format=json"
    p = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    err = p.stderr
    i = err.rfind("{")
    if p.returncode != 0 or i < 0:
        return None
    try:
        m = json.loads(err[i:err.rfind("}") + 1])
    except ValueError:
        return None
    if "inf" in m.get("input_i", "inf"):
        return None
    return m


def integrated_lufs(path: Path) -> Optional[float]:
    p = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = p.stderr[p.stderr.rfind("Summary:"):]
    try:
        return float(s.split("I:")[1].split("LUFS")[0])
    except (IndexError, ValueError):
        return None


def wav_dur(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------- providers

class ElevenLabs:
    def __init__(self, env_key: str):
        self.env_key = env_key
        self._key: Optional[str] = None

    def key(self) -> str:
        if self._key is None:
            k = pvs.env_value(self.env_key)
            if not k:
                pvs.die(f"{self.env_key} is not set. Add the line {self.env_key}=... to "
                        f"{pvs.workbench() / '.env'} yourself (never paste it into the chat), "
                        "or set `voice.provider: say` in product.yaml (or pass --provider say) "
                        "for a free local draft voice.")
            self._key = k
        return self._key

    def request(self, voice: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API}/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128"
        data = json.dumps(body).encode()
        for attempt in range(6):
            req = urllib.request.Request(url, data=data, method="POST", headers={
                "xi-api-key": self.key(), "Content-Type": "application/json", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if (e.code == 429 or e.code >= 500) and attempt < 5:
                    wait = 4 * 2 ** attempt
                    print(f"  HTTP {e.code}, retrying in {wait}s", file=sys.stderr)
                    time.sleep(wait)
                    continue
                if e.code == 401:
                    raise LineError(f"HTTP 401: the key in {self.env_key} was rejected")
                raise LineError(f"HTTP {e.code}: {detail}")
            except urllib.error.URLError as e:
                if attempt < 5:
                    time.sleep(4 * 2 ** attempt)
                    continue
                raise LineError(f"network error: {e.reason}")
        raise LineError("gave up after retries")

    @staticmethod
    def settings(cfg: Dict[str, Any], speed: float) -> Dict[str, Any]:
        model = cfg.get("model") or "eleven_multilingual_v2"
        s = dict(ELEVEN_DEFAULTS.get(model, ELEVEN_DEFAULTS["_"]))
        s.update(cfg.get("settings") or {})
        s["speed"] = speed
        return s

    def synth(self, line: Dict[str, Any], cfg: Dict[str, Any], spoken: str, ctx: Tuple[Optional[str], Optional[str]],
              raw_audio: Path) -> List[Dict[str, Any]]:
        voice = (cfg.get("voice") or "").strip()
        if not voice or vl.PLACEHOLDER.match(voice):
            raise LineError(f"role '{line['role']}' has no ElevenLabs voice id in product.yaml voice.roles")
        model = cfg.get("model") or "eleven_multilingual_v2"
        body: Dict[str, Any] = {"text": spoken, "model_id": model, "voice_settings": self.settings(cfg, line["speed"])}
        # Neighbouring lines as context make a line sound like part of one explanation.
        # Not sent to eleven_v3 models, which do not take request context.
        if cfg.get("context", not model.startswith("eleven_v3")):
            if ctx[0]:
                body["previous_text"] = ctx[0]
            if ctx[1]:
                body["next_text"] = ctx[1]
        r = self.request(voice, body)
        if "audio_base64" not in r:
            raise LineError("response has no audio")
        raw_audio.write_bytes(base64.b64decode(r["audio_base64"]))
        # `alignment` follows the characters we sent; `normalized_alignment` may expand numbers.
        a = r.get("alignment") or r.get("normalized_alignment") or {}
        words = vl.char_alignment_words(a)
        if not words:
            raise LineError("response has no character alignment")
        return words


class Say:
    def __init__(self, lang: str):
        self.lang = lang
        self._model = None

    def model(self):
        if self._model is None:
            try:
                import whisper
            except ImportError:
                pvs.die("openai-whisper is not installed; run /video-setup. It gives the say provider its word timings.")
            name = os.environ.get("PVS_WHISPER_MODEL", "small.en")
            self._model = whisper.load_model(name)
        return self._model

    def synth(self, line, cfg, spoken, ctx, raw_audio: Path):
        if not shutil.which("say"):
            pvs.die("The say provider needs macOS `say`. Use provider elevenlabs on this machine.")
        voice = cfg.get("say_voice") or "Samantha"
        rate = int(round(float(cfg.get("say_rate", 180)) * line["speed"]))
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(spoken)
            txt = f.name
        try:
            run(["say", "-v", voice, "-r", str(rate), "-o", str(raw_audio), "-f", txt], f"say -v {voice}")
        finally:
            os.unlink(txt)
        lang = self.lang if self.lang and not os.environ.get("PVS_WHISPER_MODEL", "small.en").endswith(".en") else "en"
        r = self.model().transcribe(str(raw_audio), word_timestamps=True, language=lang,
                                    initial_prompt=spoken, fp16=False, condition_on_previous_text=False)
        words = [{"w": w["word"].strip(), "s": float(w["start"]), "e": float(w["end"])}
                 for seg in r.get("segments", []) for w in seg.get("words", [])]
        if not words:
            raise LineError("whisper heard no words in the take")
        return words


# ---------------------------------------------------------------- processing

def process(raw_audio: Path, raw_words: List[Dict[str, Any]], line: Dict[str, Any], pmap: Dict[str, str],
            lufs: float, out_wav: Path, treatment: str = "") -> Dict[str, Any]:
    """Trim, normalize and fade one archived take; return its timings.json entry."""
    import numpy as np
    x = decode(raw_audio)
    if len(x) < SR * 0.1:
        raise LineError("take is shorter than 0.1 s")
    words = vl.canonical_timings(raw_words, line["text"], pmap)
    a, b = sound_bounds(x)
    last_e = max(w["e"] for w in words)
    start = max(0.0, a - HEAD_PAD)
    end = min(len(x) / SR, b + TAIL_PAD, max(last_e + TAIL_MAX_AFTER_WORD, a + 0.2))
    end = max(end, min(len(x) / SR, last_e + 0.12))
    seg = x[int(start * SR):int(end * SR)]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "trim.wav"
        pcm = (np.clip(seg, -1, 1) * 32767).astype(np.int16)
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        dur = len(seg) / SR
        if treatment:
            treated = Path(td) / "treated.wav"
            run([ffmpeg(), "-v", "error", "-y", "-i", str(tmp), "-af", TREATMENTS[treatment], "-ar", str(SR),
                 "-ac", "1", "-c:a", "pcm_s16le", str(treated)], f"treatment {treatment}")
            tmp = treated
        fades = f"afade=t=in:st=0:d={FADE_IN},afade=t=out:st={max(0.0, dur - FADE_OUT):.3f}:d={FADE_OUT}"
        m = measure_loudnorm(tmp, lufs)
        if m:
            norm = (f"loudnorm=I={lufs}:TP={TRUE_PEAK}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
                    f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
                    ":linear=true")
        else:  # too short for an integrated measurement: plain peak-safe gain
            norm = "volume=0dB"
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        run([ffmpeg(), "-v", "error", "-y", "-i", str(tmp), "-af", f"{norm},{fades}", "-ar", str(SR), "-ac", "1",
             "-c:a", "pcm_s16le", str(out_wav)], "normalize")
        # loudnorm falls back to dynamic mode when a linear gain would break the true-peak
        # ceiling, and on short clips that can land 1 to 2 LU off. Then use a plain gain into
        # a limiter, measured from the same trimmed take.
        got = integrated_lufs(out_wav)
        if m and got is not None and abs(got - lufs) > 0.5:
            gain = lufs - float(m["input_i"])
            limit = 10 ** (TRUE_PEAK / 20)
            run([ffmpeg(), "-v", "error", "-y", "-i", str(tmp), "-af",
                 f"volume={gain:.2f}dB,alimiter=limit={limit:.3f}:attack=5:release=50:level=false,{fades}",
                 "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)], "normalize (gain)")
    dur = round(wav_dur(out_wav), 3)
    return {"dur": dur, "words": vl.shift_words(words, start, dur)}


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video_dir")
    ap.add_argument("--only", help="comma-separated line ids")
    ap.add_argument("--provider", choices=["elevenlabs", "say"])
    ap.add_argument("--force", action="store_true", help="new take even if the line is unchanged")
    ap.add_argument("--restore", action="store_true", help="bring back the previous take of --only lines")
    args = ap.parse_args()

    vdir = Path(args.video_dir).resolve()
    audio = vdir / "audio"
    tsv = audio / "lines.tsv"
    if not tsv.exists():
        pvs.die(f"{tsv} not found. Write the script first (see the script-and-voice skill).")
    product = pvs.load_product(vdir)
    voice = product["voice"]
    provider = args.provider or voice.get("provider") or "elevenlabs"
    if provider not in ("elevenlabs", "say"):
        pvs.die(f"unknown voice.provider '{provider}' (elevenlabs | say)")
    lufs = float(voice.get("clip_lufs", -18))
    pmap = vl.pronounce_map(product)
    rows = pvs.read_lines_tsv(tsv)
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        pvs.die("lines.tsv has duplicate ids; run check_script.py")
    only = [x.strip() for x in args.only.split(",") if x.strip()] if args.only else None
    if only:
        missing = [x for x in only if x not in ids]
        if missing:
            pvs.die(f"--only ids not in lines.tsv: {', '.join(missing)}")
    if args.restore and not only:
        pvs.die("--restore needs --only <ids>")

    raw = audio / "raw"
    (raw / "prev").mkdir(parents=True, exist_ok=True)
    cache_f = raw / "cache.json"
    cache = pvs.read_json(cache_f, {}) or {}
    tim_f = audio / "timings.json"
    tim = pvs.read_json(tim_f, {}) or {}
    eng = ElevenLabs(voice.get("env_key") or "ELEVENLABS_API_KEY") if provider == "elevenlabs" else Say(product["video"].get("lang", "en"))
    ext = ".mp3" if provider == "elevenlabs" else ".aiff"

    failed: List[Tuple[str, str]] = []
    done = skipped = takes = 0
    for i, line in enumerate(rows):
        lid = line["id"]
        if only and lid not in only:
            continue
        try:
            try:
                cfg = vl.role_config(product, line["role"])
            except KeyError:
                raise LineError(f"role '{line['role']}' is not in product.yaml voice.roles")
            spoken, _ = vl.respell(line["text"], pmap)
            ctx = tuple(vl.respell(t, pmap)[0] if t else None for t in vl.neighbours(rows, i))
            ident = {"provider": provider, "text": spoken, "speed": line["speed"]}
            if provider == "elevenlabs":
                ident.update(voice=cfg.get("voice"), model=cfg.get("model"), settings=cfg.get("settings"), ctx=ctx)
            else:
                ident.update(voice=cfg.get("say_voice"), rate=cfg.get("say_rate"))
            take_hash = vl.content_hash(ident)
            treatment = cfg.get("treatment") or ""
            if treatment and treatment not in TREATMENTS:
                raise LineError(f"role '{line['role']}' treatment '{treatment}' is not one of {', '.join(TREATMENTS)}")
            proc_hash = vl.content_hash({"lufs": lufs, "v": PROC_VERSION, "canon": line["text"], "pmap": pmap,
                                         "treatment": treatment})
            meta_f = raw / f"{lid}.json"
            meta = pvs.read_json(meta_f, None)
            clip = audio / "clips" / f"{lid}.wav"

            if args.restore:
                pmeta = pvs.read_json(raw / "prev" / meta_f.name, None)
                if not pmeta or not (raw / "prev" / pmeta["file"]).exists():
                    raise LineError("no previous take in audio/raw/prev/")
                if pmeta.get("spoken") != spoken:
                    raise LineError("the previous take was for a different text; put that text back in lines.tsv first")
                swap_takes(raw, meta_f.name, (meta or {}).get("file"), pmeta["file"])
                meta = pmeta
                print(f"{lid:5} restored the previous take (the newer one is now in audio/raw/prev/)")
            else:
                have_take = bool(meta) and meta.get("hash") == take_hash and (raw / meta.get("file", "")).exists()
                c = cache.get(lid, {})
                if have_take and not args.force and c.get("proc") == proc_hash and clip.exists() and lid in tim:
                    skipped += 1
                    continue
                if not have_take or args.force:
                    # Synthesize to a new file first: a failed request must not lose the current take.
                    new_audio = raw / f"{lid}.new{ext}"
                    try:
                        words = eng.synth(line, cfg, spoken, ctx, new_audio)
                    except BaseException:
                        if new_audio.exists():
                            new_audio.unlink()
                        raise
                    if meta and (raw / meta.get("file", "")).exists():  # keep the previous take
                        shutil.move(str(raw / meta["file"]), str(raw / "prev" / meta["file"]))
                        shutil.move(str(meta_f), str(raw / "prev" / meta_f.name))
                    raw_audio = raw / f"{lid}{ext}"
                    new_audio.rename(raw_audio)
                    takes += 1
                    meta = {"hash": take_hash, "provider": provider, "file": raw_audio.name, "spoken": spoken,
                            "words": words, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                    pvs.write_json(meta_f, meta)

            if meta.get("spoken") != spoken:
                raise LineError("archived take does not match the line; rerun with --force")
            entry = process(raw / meta["file"], meta["words"], line, pmap, lufs, clip, treatment)
            tim[lid] = entry
            cache[lid] = {"take": meta["hash"], "proc": proc_hash}
            pvs.write_json(tim_f, _ordered(tim, ids))
            pvs.write_json(cache_f, cache)
            got = integrated_lufs(clip)
            lvl = f"{got:6.1f} LUFS" if got is not None else "   short"
            print(f"{lid:5} {entry['dur']:5.2f}s {lvl}  {line['role']:10} {line['text'][:60]}")
            done += 1
        except LineError as e:
            failed.append((lid, str(e)))
            print(f"{lid:5} FAILED: {e}", file=sys.stderr)

    print(f"{done} built ({takes} new takes from {provider}), {skipped} unchanged, {len(failed)} failed. "
          f"timings: {tim_f}")
    if failed:
        pvs.die("failed lines: " + ", ".join(f"{k} ({m})" for k, m in failed))


def swap_takes(raw: Path, meta_name: str, cur_file: Optional[str], prev_file: str) -> None:
    """Exchange the current take (raw/) with the previous one (raw/prev/)."""
    with tempfile.TemporaryDirectory(dir=str(raw)) as td:
        hold = Path(td)
        for name in filter(None, [meta_name, cur_file]):
            if (raw / name).exists():
                shutil.move(str(raw / name), str(hold / name))
        for name in [meta_name, prev_file]:
            shutil.move(str(raw / "prev" / name), str(raw / name))
        for f in hold.iterdir():
            shutil.move(str(f), str(raw / "prev" / f.name))


def _ordered(tim: Dict[str, Any], ids: List[str]) -> Dict[str, Any]:
    """timings.json in script order; ids no longer in lines.tsv are kept at the end."""
    out = {k: tim[k] for k in ids if k in tim}
    out.update({k: v for k, v in tim.items() if k not in out})
    return out


if __name__ == "__main__":
    main()
