"""Frame-by-frame parity between two renders: proves an approved stretch did not change.

    bin/pvs-py skills/render-qa/scripts/parity.py <old.mp4> <new.mp4> [--end T] [--skip A:B ...]
                                                   [--threshold 1.0] [--audio]

Decodes both at 192x108 gray, 30 fps, from 0 to --end (default: the shorter file), and
reports the frames whose mean absolute difference is above the threshold. Encoding noise
stays far below 1.0 (two re-renders of an unchanged video measured a max of 0.06 to 0.09).
--skip A:B excludes a beat that changed on purpose (repeatable). --audio also compares the
mix as 100 ms RMS levels (informational).

Exit 1 when any frame outside the skipped ranges is above the threshold.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

import qalib

W, H, FPS = 192, 108, 30


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Parity between two renders of the same video.")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--end", type=float, help="compare from 0 to this time (s)")
    ap.add_argument("--skip", action="append", default=[], metavar="A:B", help="time range that changed on purpose")
    ap.add_argument("--threshold", type=float, default=1.0)
    ap.add_argument("--audio", action="store_true", help="also compare 100 ms RMS levels of the mix")
    a = ap.parse_args(argv)
    old, new = Path(a.old), Path(a.new)
    end = a.end or min(qalib.probe(old)["duration"], qalib.probe(new)["duration"])
    skips = []
    for s in a.skip:
        x, _, y = s.partition(":")
        skips.append((float(x), float(y)))
    fa = qalib.gray_frames(old, W, H, fps=FPS, t_end=end)
    fb = qalib.gray_frames(new, W, H, fps=FPS, t_end=end)
    n = min(len(fa), len(fb))
    d = np.array([np.abs(fa[i].astype(np.int16) - fb[i].astype(np.int16)).mean() for i in range(n)])
    t = np.arange(n) / FPS
    mask = np.ones(n, bool)
    for x, y in skips:
        mask &= ~((t >= x) & (t <= y))
    if not mask.any():
        print("nothing to compare outside the skipped ranges")
        return 1
    print(f"frames compared {int(mask.sum())} of {n} (0 to {end:.2f} s); mean diff {d[mask].mean():.3f}; "
          f"max {d[mask].max():.3f} at t={t[mask][d[mask].argmax()]:.2f}s")
    bad = np.nonzero(mask & (d > a.threshold))[0]
    runs = []
    for i in bad.tolist():
        if runs and i - runs[-1][-1] <= 3:
            runs[-1].append(i)
        else:
            runs.append([i])
    for r in runs[:20]:
        print(f"  diff>{a.threshold:g}  t={t[r[0]]:.2f}-{t[r[-1]]:.2f}s  max={d[r].max():.2f}")
    for x, y in skips:
        s = (t >= x) & (t <= y)
        if s.any():
            print(f"skipped {x:g}-{y:g}s: max diff {d[s].max():.2f} (changed on purpose)")
    if a.audio:
        sr = 8000
        aa = qalib.audio_samples(old, sr).mean(axis=1)
        ab = qalib.audio_samples(new, sr).mean(axis=1)
        w = sr // 10
        m = int(min(len(aa), len(ab), end * sr) // w)
        if m:
            ra = 20 * np.log10(np.sqrt((aa[:m * w].reshape(m, w) ** 2).mean(axis=1)) + 1e-6)
            rb = 20 * np.log10(np.sqrt((ab[:m * w].reshape(m, w) ** 2).mean(axis=1)) + 1e-6)
            ta = np.arange(m) * 0.1
            am = np.ones(m, bool)
            for x, y in skips:
                am &= ~((ta >= x) & (ta <= y))
            loud = am & ((ra > -50) | (rb > -50))
            if loud.any():
                dd = np.abs(ra - rb)[loud]
                print(f"audio: 100 ms RMS max diff {dd.max():.2f} dB at t={ta[loud][dd.argmax()]:.1f}s, mean {dd.mean():.2f} dB")
    print("parity: OK" if not runs else f"parity: {len(runs)} stretch(es) differ")
    return 1 if runs else 0


if __name__ == "__main__":
    sys.exit(main())
