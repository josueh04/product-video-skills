"""Narration edges in the final mix: the level just before and after each voice clip.

    bin/pvs-py skills/render-qa/scripts/edges.py <video.mp4> <index.html | video_dir> [--window 0.12]

A click shows up as a spike in the "pre" or "post" window of the mix. A cut word shows up in
the clip itself: speech still sounding in its last 40 ms ("tail"), right up to its real end
(the last sample above -50 dBFS, "gap" is the silence after it). Use it to pick which edges to
listen to; it does not pass or fail anything. Reads the <audio> tags that the build writes into
index.html, and the clip files they point to.

Why the tail is measured that way: a clean clip ends in its natural decay plus a short fade, so
a wide window over the clip end (or over the mix, where an effect may overlap) reads the decay
as "still loud" and flags every line. tts.py fades the last 80 ms, so a word cut by the trim is
still at half level or more in the last 40 ms, while a clean ending is 45 dB or more down there.
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

import qalib

SR = 48000
TAIL_WINDOW = 0.04   # shorter than the 80 ms fade-out that tts.py applies to every clip
TAIL_LOUD_DB = -35.0  # clean endings measured -46 to -51 dBFS here, cut words -10 to -27
POST_LOUD_DB = -40.0  # a spike after the clip must be audible, not noise-floor jitter
FLOOR_DB = -50.0      # "real end": the last sample above this


def clip_end(path: Path, dur: float) -> Optional[Tuple[float, float]]:
    """(tail peak dB over the last TAIL_WINDOW before dur, silence after the real end), or None.

    dur is the length the build plays (data-duration), which can be shorter than the file."""
    if not path.is_file():
        return None
    r = subprocess.run([qalib.FFMPEG, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode != 0:
        return None
    x = np.frombuffer(r.stdout, dtype=np.float32)[:int(round(dur * SR))]
    if not len(x):
        return None
    loud = np.nonzero(np.abs(x) > 10 ** (FLOOR_DB / 20))[0]
    real_end = (loud[-1] + 1) / SR if len(loud) else 0.0
    return qalib.peak_db(x[-int(TAIL_WINDOW * SR):]), len(x) / SR - real_end


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Level around each narration clip edge.")
    ap.add_argument("mp4")
    ap.add_argument("where", help="video/index.html or the video folder")
    ap.add_argument("--window", type=float, default=0.12, help="pre and post window in the mix, seconds")
    a = ap.parse_args(argv)
    p = Path(a.where)
    vdir = p.parent.parent if p.is_file() else p
    if p.is_file() and p.parent.name != "video":
        # a loose index.html: read it through a temporary layout
        vdir = None
    lines = qalib.load_lines(vdir) if vdir else []
    if vdir:
        clips = qalib.audio_clips(vdir, {r["id"] for r in lines})
    else:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "video").mkdir()
            (Path(td) / "video" / "index.html").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            clips = qalib.audio_clips(Path(td))
    voice = [c for c in clips if c["kind"] == "voice" and c["dur"]]
    if not voice:
        print("no voice clips found in index.html")
        return 0
    x = qalib.audio_samples(Path(a.mp4), SR).mean(axis=1)
    w = int(a.window * SR)
    tw = int(TAIL_WINDOW * SR)
    flagged = 0
    for c in voice:
        i0, i1 = int(c["start"] * SR), int((c["start"] + c["dur"]) * SR)
        pre = qalib.peak_db(x[max(0, i0 - w):i0])
        head = qalib.peak_db(x[i0:i0 + w])
        post = qalib.peak_db(x[i1:i1 + w])
        own = clip_end(vdir / "video" / c["src"], c["dur"]) if vdir else None
        if own:
            tail, gap = own[0], f"gap {own[1]:5.3f} s"
        else:  # no clip file: the mix, same short window
            tail, gap = qalib.peak_db(x[max(i0, i1 - tw):i1]), "gap     ? "
        why = []
        if tail > TAIL_LOUD_DB:
            why.append("speech at the clip end (cut word?)")
        if post > POST_LOUD_DB and post > tail + 6:
            why.append("sound right after the clip")
        flagged += bool(why)
        flag = ("  <-- listen: " + ", ".join(why)) if why else ""
        print(f"{c['key']:6} start {c['start']:7.2f}  pre {pre:6.1f} dB  head {head:6.1f} dB | "
              f"end {c['start'] + c['dur']:7.2f}  tail {tail:6.1f} dB  {gap}  post {post:6.1f} dB{flag}")
    print(f"{len(voice)} narration clip(s), {flagged} edge(s) to listen to")
    return 0


if __name__ == "__main__":
    sys.exit(main())
