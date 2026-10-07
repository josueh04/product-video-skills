"""Full automatic QA of a rendered product video: every frame and the whole mix.

    bin/pvs-py skills/render-qa/scripts/qa_full.py <video_dir> <video.mp4> [--out DIR] [--no-asr]
                                                    [--asr-model NAME] [--json]

video_dir holds audio/lines.tsv, audio/timings.json and video/index.html. Usually you run
qa.py, which calls these same checks and writes qa/REPORT.json; run this one alone when you
only want the numbers (it writes REPORT.txt and asr.txt into --out, default <video_dir>/qa).

Video   probe vs product.yaml video.size and fps, one-frame outliers with the worker pattern,
        black frames outside the intended fades.
Audio   integrated loudness vs voice.mix_lufs, true peak, clipped samples on the real
        channels, impulsive clicks classified (inside SFX, inside voice, outside any clip),
        abrupt ends and starts, spoken-word overlaps between voice clips.
Speech  whisper (small.en for English, multilingual small otherwise) diffed against
        lines.tsv in playback order, plus banned terms and legacy names in what was heard.

Exit 1 when any check fails.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import qalib
from banned_terms import find_banned

LOUDNESS_TOL = 1.0     # LU around voice.mix_lufs; delivered finals measured -16.8 to -15.3 for -16
TRUE_PEAK_MAX = -1.0   # dBFS
ASR_MIN = 0.93         # word match ratio; delivered finals measured 0.953 to 0.988


def check(name: str, passed: bool, detail: str, level: str = "error", **extra) -> Dict[str, Any]:
    c = {"name": name, "passed": bool(passed), "detail": detail}
    if level != "error":
        c["level"] = level
    c.update(extra)
    return c


def run_checks(video_dir: Path, mp4: Path, out: Path, cfg: Dict[str, Any], do_asr: bool = True,
               asr_model: Optional[str] = None, asr_min: float = ASR_MIN, lang: Optional[str] = None,
               log=print) -> Dict[str, Any]:
    """All measurements as check records plus the raw numbers other steps need."""
    out = qalib.ensure_dir(out)
    checks: List[Dict[str, Any]] = []
    info = qalib.probe(mp4)
    want_w, want_h = (cfg.get("video") or {}).get("size", [1920, 1080])
    want_fps = float((cfg.get("video") or {}).get("fps", 30))
    lang = lang or (cfg.get("video") or {}).get("lang", "en")
    au = info["audio"]
    log(f"VIDEO {mp4.name}: {info['width']}x{info['height']} {info['fps']:g} fps {info['duration']:.2f} s, "
        f"audio: " + (f"{au['codec']} {au['sample_rate']} Hz {au['channels']} ch" if au else "none"))
    checks.append(check("size", (info["width"], info["height"]) == (want_w, want_h),
                        f"{info['width']}x{info['height']} (product.yaml video.size {want_w}x{want_h})"))
    checks.append(check("fps", True, f"{info['fps']:g} fps (product.yaml video.fps {want_fps:g})"
                        + ("" if abs(info["fps"] - want_fps) < 0.01 else ": differs, confirm it was intended"),
                        level="info" if abs(info["fps"] - want_fps) < 0.01 else "warn"))

    # ---- frames
    st = qalib.frame_stats(mp4)
    o = qalib.outlier_runs(st, info["fps"])
    worker = [r for r in o["runs"] if r["worker_pattern"]]
    log(f"FRAMES {o['frames']}: {o['outliers']} outlier frames in {len(o['runs'])} runs")
    for r in o["runs"]:
        log(f"  t={r['t0']:7.2f}-{r['t1']:7.2f}s n={r['n']:3d} mod3={r['mod3']} max={r['max']:.2f}"
            + ("  <-- WORKER PATTERN" if r["worker_pattern"] else ""))
    checks.append(check("worker_pattern", not worker,
                        f"{len(worker)} run(s) on one frame index mod 3"
                        + (": " + ", ".join(f"{r['t0']:.2f}-{r['t1']:.2f}s" for r in worker[:8]) if worker else "")))
    checks.append(check("outliers", True,
                        f"{o['outliers']} outlier frames in {len(o['runs'])} runs; look at a strip of each"
                        if o["runs"] else "0 outlier frames", level="warn" if o["runs"] else "info",
                        runs=o["runs"][:40]))
    bl = qalib.black_frames(st, info["fps"], info["duration"])
    log(f"black frames: {bl['total']} total, {bl['mid']} mid-video" + (f" at {bl['spans'][:5]}" if bl["spans"] else ""))
    checks.append(check("black_frames", bl["mid"] == 0,
                        f"{bl['mid']} outside the first {qalib.BLACK_HEAD_S:g} s and last {qalib.BLACK_TAIL_S:g} s"
                        + (f", spans {bl['spans'][:5]}" if bl["spans"] else "")))

    # ---- composition map
    lines = qalib.load_lines(video_dir)
    timings = qalib.load_timings(video_dir)
    clips = qalib.audio_clips(video_dir, {r["id"] for r in lines})
    voice = [c for c in clips if c["kind"] == "voice"]
    ov = qalib.voice_overlaps(clips, timings)
    log(f"COMPOSITION {len(clips)} audio tags, {len(voice)} voice clips, {len(ov)} spoken overlaps")
    checks.append(check("voice_overlap", not ov,
                        f"{len(ov)} pair(s) of voice clips whose spoken words overlap (of {len(voice)} clips)"
                        + ("".join(f"; {x} overlaps {y} by {s}s" for x, y, s in ov[:6]) if ov else "")))

    # ---- audio
    heard = ""
    if not au:
        checks.append(check("audio", not lines, "no audio track" + (" but lines.tsv has narration" if lines else ""),
                            level="error" if lines else "info"))
    else:
        mix_lufs = float((cfg.get("voice") or {}).get("mix_lufs", -16))
        ld = qalib.loudness(mp4)
        log(f"AUDIO I={ld['I']} LUFS, true peak={ld['TP']} dBFS, LRA={ld['LRA']} LU")
        ok_i = ld["I"] is not None and abs(ld["I"] - mix_lufs) <= LOUDNESS_TOL
        checks.append(check("loudness", ok_i, f"{ld['I']} LUFS integrated (target {mix_lufs:g} +/- {LOUDNESS_TOL:g})"))
        checks.append(check("true_peak", ld["TP"] is not None and ld["TP"] <= TRUE_PEAK_MAX,
                            f"{ld['TP']} dBFS (max {TRUE_PEAK_MAX:g})"))
        sr = 48000
        ach = qalib.audio_samples(mp4, sr)
        clipped = int((abs(ach) >= qalib.CLIP_SAMPLE).sum())
        checks.append(check("clipping", clipped == 0,
                            f"{clipped} samples at |x| >= {qalib.CLIP_SAMPLE} on the real channels; "
                            f"sample peak {qalib.peak_db(ach):.2f} dBFS"))
        a = ach.mean(axis=1)
        sfx = [(c["start"], c["start"] + (c["dur"] or 0.5)) for c in clips if c["kind"] == "sfx"]
        snd = [(c["start"], c["start"] + c["dur"]) for c in clips if c["kind"] != "sfx" and c["dur"]]
        inside = lambda t, spans: any(x0 - 0.02 <= t <= x1 + 0.02 for x0, x1 in spans)
        cl = qalib.clicks(a, sr)
        c_sfx = [t for t in cl if inside(t, sfx)]
        c_vox = [t for t in cl if not inside(t, sfx) and inside(t, snd)]
        c_out = [t for t in cl if not inside(t, sfx) and not inside(t, snd)]
        mapped = bool(clips)
        log(f"clicks: {len(cl)} total, {len(c_sfx)} inside SFX, {len(c_vox)} inside voice/music, {len(c_out)} outside")
        checks.append(check("clicks_outside_clips", (not c_out) or not mapped,
                            f"{len(c_out)} outside any clip"
                            + (": " + ", ".join(f"{t:.2f}s" for t in c_out[:12]) if c_out else "")
                            + f" ({len(c_sfx)} inside SFX, expected; {len(c_vox)} inside voice, usually consonants"
                            + (": " + ", ".join(f"{t:.2f}s" for t in c_vox[:8]) if c_vox else "") + ")"
                            + ("" if mapped else "; no audio tags in index.html, so clicks cannot be classified"),
                            level="error" if mapped else "warn"))
        ends, starts = qalib.abrupt_edges(a, sr)
        sfx_on = [c["start"] for c in clips if c["kind"] == "sfx"]
        e_bad = [t for t in ends if not inside(t, sfx)]
        s_bad = [t for t in starts if not any(abs(t - s0) <= 0.03 for s0 in sfx_on)]
        checks.append(check("abrupt_edges", True,
                            f"{len(e_bad)} abrupt ends and {len(s_bad)} abrupt starts outside SFX"
                            + ("; listen at " + ", ".join(f"{t:.2f}s" for t in (e_bad + s_bad)[:12]) if e_bad or s_bad else ""),
                            level="warn" if (e_bad or s_bad) else "info"))

        # ---- speech
        if not lines:
            checks.append(check("asr", True, "no audio/lines.tsv: nothing to compare", level="info"))
        elif not do_asr:
            checks.append(check("asr", False, "skipped (--no-asr); run the full QA before delivery", skipped=True))
        else:
            try:
                heard, model = qalib.asr(mp4, lang, asr_model)
            except Exception as ex:  # whisper missing or a model not cached
                checks.append(check("asr", False, f"could not run: {ex}", skipped=True))
                model = None
            if model:
                (out / "asr.txt").write_text(heard + "\n", encoding="utf-8")
                script = qalib.script_in_playback_order(lines, clips)
                ratio, diffs = qalib.diff_words(script, heard)
                log(f"ASR ({model}) vs lines.tsv: word match {ratio:.3f}")
                for d in diffs:
                    log("  " + d)
                checks.append(check("asr", ratio >= asr_min,
                                    f"{model}: word match {ratio:.3f} (min {asr_min:g}), {len(diffs)} multi-word diffs; "
                                    "read every diff (spelling-only diffs are fine)", ratio=round(ratio, 4), diffs=diffs[:60]))
        if heard:
            hits = find_banned(heard, cfg)
            checks.append(check("banned_terms_heard", not hits,
                                f"{len(hits)} hit(s) in the ASR text" + (": " + ", ".join(f"{t} ({k})" for t, k in hits) if hits else "")))
    return {"probe": info, "checks": checks, "outliers": o, "clips": clips, "heard": heard}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Full automatic QA of a rendered video.")
    ap.add_argument("video_dir")
    ap.add_argument("mp4")
    ap.add_argument("--out", help="folder for REPORT.txt and asr.txt (default <video_dir>/qa)")
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--asr-model", help="whisper model name (default small.en for en, small otherwise)")
    ap.add_argument("--json", action="store_true", help="print the checks as JSON")
    a = ap.parse_args(argv)
    vdir, mp4 = Path(a.video_dir), Path(a.mp4)
    out = Path(a.out) if a.out else vdir / "qa"
    cfg = qalib.load_config(vdir)
    brief = qalib.load_brief(vdir) or {}
    lines_out: List[str] = []

    def log(s=""):
        lines_out.append(s)
        if not a.json:
            print(s)

    res = run_checks(vdir, mp4, out, cfg, not a.no_asr, a.asr_model, lang=brief.get("lang"), log=log)
    failed = [c for c in res["checks"] if not c["passed"]]
    log("")
    for c in res["checks"]:
        mark = "PASS" if c["passed"] else "FAIL"
        if c["passed"] and c.get("level") == "warn":
            mark = "WARN"
        log(f"[{mark}] {c['name']}: {c['detail']}")
    log(f"\n{len(res['checks']) - len(failed)} passed, {len(failed)} failed")
    (out / "REPORT.txt").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    if a.json:
        print(json.dumps(res["checks"], indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
