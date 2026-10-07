"""Generic build library for product demo videos (ui-demo-composer).

Every video's build.py imports this, defines its beats from the narration's
word timings and calls Build.write(). Timing has one source of truth: the
words in audio/timings.json. Regenerate one line of voice and every beat
anchored to it moves with it.

    import buildlib
    b = buildlib.Build(__file__)          # parses --draft / --fake-timings, checks signatures
    T, w, end = b.T, b.w, b.end
    T["N1"] = 0.7                          # a key that is a clip id places that clip
    T["ch1"] = end("N1") + 0.15
    T["open1"] = T["N2"] + w("N2", "open") - 0.2
    b.click(T["open1"])
    b.cam(T["push1"], 1.2, "#list", d=1.2)
    T["DUR"] = round(end("N2") + 2.0, 2)
    b.write(texts={"t1": "Order flour for Saturday"})

See ../references/stage-kit.md for the template placeholders and the JS API.
Python 3.9 compatible.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HF_VERSION = "0.8.134"
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
HERE = Path(__file__).resolve().parent
KIT = HERE.parent / "kit"

# audio tracks (a Studio display lane; `check` warns when two clips overlap on one)
TRACK_VOICE = 10
TRACK_CHARACTER = 11
TRACK_CLICK = 20
TRACK_TYPING = 21
TRACK_POP = 22
TRACK_OTHER = 23


class BuildError(Exception):
    pass


def find_workbench(start: Optional[Path] = None) -> Path:
    """PVS_HOME if it points at a workbench, else the first folder above `start` holding bin/pvs-py."""
    env = os.environ.get("PVS_HOME")
    if env and (Path(env) / "bin" / "pvs-py").exists():
        return Path(env).resolve()
    p = Path(start or HERE).resolve()
    for d in [p, *p.parents]:
        if (d / "bin" / "pvs-py").exists() and (d / "lib" / "pvs.py").exists():
            return d
    raise BuildError("Cannot find the workbench (no bin/pvs-py above %s and PVS_HOME is not set)" % p)


PVS_HOME = find_workbench(HERE)
if str(PVS_HOME / "lib") not in sys.path:
    sys.path.insert(0, str(PVS_HOME / "lib"))
import pvs  # noqa: E402


def hf_version() -> str:
    pkg = pvs.read_json(PVS_HOME / "package.json", {}) or {}
    v = (pkg.get("dependencies") or {}).get("hyperframes") or (pkg.get("devDependencies") or {}).get("hyperframes")
    return v.lstrip("^~=") if v else HF_VERSION


# ---------------------------------------------------------------- small helpers
def norm_word(s: str) -> str:
    return s.lower().strip(".,!?:;\"'()[]{}\u2019\u2018\u201c\u201d")


def svg_clean(s: str) -> str:
    """An SVG ready to inline: no XML header, ids, comments or fixed size; fills follow currentColor."""
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r'\sid="[^"]*"', "", s)
    s = re.sub(r'fill="(black|#000|#000000)"', 'fill="currentColor"', s)

    def root(m):
        tag = re.sub(r'\s(width|height|class)="[^"]*"', "", m.group(0))
        return tag if "fill=" in tag else tag[:-1] + ' fill="currentColor">'

    s = re.sub(r"<svg\b[^>]*>", root, s, count=1)
    return re.sub(r">\s+<", "><", s).strip()


def audio_tag(aid: str, src: str, start: float, dur: Optional[float], vol: float, track: int) -> str:
    a = '<audio id="%s" src="%s" data-start="%.3f"' % (aid, src, start)
    if dur is not None:
        a += ' data-duration="%.3f"' % dur
    return a + ' data-track-index="%d" data-volume="%s"></audio>' % (track, vol)


def replace_placeholders(text: str, values: Dict[str, str]) -> str:
    """Replace {{NAME}} for every NAME in values."""
    for k, v in values.items():
        text = text.replace("{{%s}}" % k, v)
    return text


PH = re.compile(r"\{\{([A-Z][A-Z0-9_]*)(?::([^}]+))?\}\}")


def leftover_placeholders(text: str) -> List[str]:
    return sorted(set(m.group(0) for m in PH.finditer(text)))


def fake_timings(rows: List[Dict[str, Any]], wps: float = 2.6) -> Dict[str, Any]:
    """Placeholder word timings from lines.tsv (draft only): even words at `wps` words per second."""
    out = {}
    for r in rows:
        words, t = [], 0.08
        step = 1.0 / wps / max(0.5, r["speed"])
        for tok in r["text"].split():
            words.append({"w": tok, "s": round(t, 3), "e": round(t + step * 0.8, 3)})
            t += step
        out[r["id"]] = {"dur": round(t + 0.3, 3), "words": words, "fake": True}
    return out


# ---------------------------------------------------------------- the build
class Build:
    def __init__(self, build_file: str, argv: Optional[List[str]] = None):
        ap = argparse.ArgumentParser(description="Build index.html for this video.")
        ap.add_argument("--draft", action="store_true", help="build without reviewer signatures (renders can be checked, never delivered)")
        ap.add_argument("--fake-timings", action="store_true", help="draft only: invent word timings from audio/lines.tsv (no voice yet)")
        ap.add_argument("--quiet", action="store_true", help="do not print the beat table")
        self.args = ap.parse_args(sys.argv[1:] if argv is None else argv)
        self.draft = bool(self.args.draft)
        self.video = Path(build_file).resolve().parent          # <video_dir>/video
        self.vdir = self.video.parent                            # <video_dir> (holds BRIEF.md)
        if not (self.vdir / "BRIEF.md").exists():
            raise SystemExit("build.py must live in <video_dir>/video/ with BRIEF.md one level up (%s)" % self.vdir)
        self.brief = pvs.read_brief(self.vdir)
        self._gate()
        self.cfg = pvs.load_product(self.vdir)
        self.pdir = Path(self.cfg["_dir"])
        self.warnings: List[str] = []
        self.timings = self._load_timings()
        self.D: Dict[str, float] = {k: float(v["dur"]) for k, v in self.timings.items()}
        self.T: Dict[str, Any] = {}
        self.roles = self._roles()
        self.audio: List[Tuple[str, str, float, Optional[float], float, int]] = []  # id, src, start, dur, vol, base track
        self.copies: Dict[str, Path] = {}                       # published path -> source file
        self.cam_moves: List[Dict[str, Any]] = []
        self.snaps: List[Tuple[float, str]] = []
        self._sfx_mod = None
        self._sfx_tried = False
        self._sfx_n = 0
        vid = self.cfg["video"]
        self.max_zoom = float(vid.get("max_zoom", 1.35))
        self.fps = int(vid.get("fps", 30))

    # ---------- gate ----------
    def _gate(self) -> None:
        if self.args.fake_timings and not self.args.draft:
            raise SystemExit("--fake-timings needs --draft: invented timings can never be delivered.")
        if pvs.signed(self.brief) or self.draft:
            return
        missing = [k for k in ("coverage_signed_by", "claims_signed_by") if not self.brief.get(k)]
        msg = ("Refusing to build: BRIEF.md is not signed (%s empty).\n"
               "The reviewer signs coverage_signed_by after reading COVERAGE.md and claims_signed_by after reading CLAIMS.md.\n"
               "Run with --draft for a draft build: it renders and passes QA as a draft, and can never be delivered."
               % ", ".join(missing))
        print(msg, file=sys.stderr)
        raise SystemExit(2)

    # ---------- timings ----------
    def _load_timings(self) -> Dict[str, Any]:
        if self.args.fake_timings:
            lines = self.vdir / "audio" / "lines.tsv"
            if not lines.exists():
                raise SystemExit("--fake-timings needs audio/lines.tsv")
            self.warn("timings are invented from lines.tsv (--fake-timings); voice and motion are not in sync")
            return fake_timings(pvs.read_lines_tsv(lines))
        f = self.vdir / "audio" / "timings.json"
        data = pvs.read_json(f)
        if data is None:
            raise SystemExit("No %s. Run the voice step first, or use --draft --fake-timings for a layout draft." % f)
        for k, v in data.items():
            if "dur" not in v or "words" not in v:
                raise SystemExit("%s: clip %s needs dur and words" % (f, k))
        return data

    def _roles(self) -> Dict[str, str]:
        f = self.vdir / "audio" / "lines.tsv"
        if not f.exists():
            return {}
        return {r["id"]: r["role"] for r in pvs.read_lines_tsv(f)}

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def fail(self, msg: str) -> None:
        """An error in a signed build, a warning in a draft."""
        if self.draft:
            self.warn(msg)
        else:
            raise BuildError(msg)

    # ---------- word anchors ----------
    def _words(self, clip: str) -> List[Dict[str, Any]]:
        if clip not in self.timings:
            raise BuildError("No clip %s in timings.json (clips: %s)" % (clip, ", ".join(self.timings)))
        return self.timings[clip]["words"]

    def _find(self, clip: str, prefix: str, nth: int) -> Dict[str, Any]:
        p = norm_word(prefix)
        hits = [x for x in self._words(clip) if norm_word(x["w"]).startswith(p)]
        if len(hits) < nth:
            words = " ".join(x["w"] for x in self._words(clip))
            raise BuildError("w(%r, %r, nth=%d): no such word in %s: %s" % (clip, prefix, nth, clip, words))
        return hits[nth - 1]

    def w(self, clip: str, prefix: str, nth: int = 1) -> float:
        """Start (s, relative to the clip) of the nth word of `clip` that begins with `prefix`. No silent fallback."""
        return float(self._find(clip, prefix, nth)["s"])

    def we(self, clip: str, prefix: str, nth: int = 1) -> float:
        """End (s, relative to the clip) of that word."""
        return float(self._find(clip, prefix, nth)["e"])

    def lw(self, clip: str) -> float:
        """End of the last spoken word of `clip` (the clip itself may carry a tail of silence)."""
        return float(self._words(clip)[-1]["e"])

    def at(self, clip: str, prefix: str, nth: int = 1) -> float:
        """Absolute time of a word of a clip that is already placed in T."""
        if clip not in self.T:
            raise BuildError("at(%r, ...): place clip %s in T first" % (clip, clip))
        return self.T[clip] + self.w(clip, prefix, nth)

    def dur(self, key: str, d: float) -> None:
        """Give a non-clip beat a duration so end(key) works for it (a typing run, a build animation)."""
        self.D[key] = float(d)

    def end(self, key: str) -> float:
        if key not in self.T:
            raise BuildError("end(%r): %s is not placed in T yet" % (key, key))
        if key not in self.D:
            raise BuildError("end(%r): %s has no duration (it is not a clip; call b.dur(%r, d))" % (key, key, key))
        return self.T[key] + self.D[key]

    # ---------- sound effects ----------
    def _sfx(self):
        if not self._sfx_tried:
            self._sfx_tried = True
            sdir = PVS_HOME / "skills" / "script-and-voice" / "scripts"
            if str(sdir) not in sys.path:
                sys.path.insert(0, str(sdir))
            try:
                import make_sfx  # type: ignore
                self._sfx_mod = make_sfx
            except ImportError:
                self._sfx_mod = None
        if self._sfx_mod is None:
            self.fail("skills/script-and-voice/scripts/make_sfx.py is not available; sound effects skipped")
        return self._sfx_mod

    def cue(self, cue: Dict[str, Any], vol: float, track: int) -> None:
        """Add a cue dict from make_sfx ({id, src, start, dur}); src is relative to the video dir."""
        self._sfx_n += 1
        aid = "sfx-%s-%d" % (re.sub(r"[^a-zA-Z0-9_-]", "", str(cue.get("id", "x"))) or "x", self._sfx_n)
        self._publish(cue["src"])
        self.audio.append((aid, cue["src"], float(cue["start"]), cue.get("dur"), vol, track))

    def _call_sfx(self, what: str, fn, *a, **k) -> Optional[Dict[str, Any]]:
        try:
            return fn(*a, **k)
        except SystemExit as e:        # pvs.die inside make_sfx
            self.fail("%s failed: %s" % (what, e))
        except Exception as e:  # noqa: BLE001 (a draft keeps going without that sound)
            self.fail("%s failed: %s: %s" % (what, type(e).__name__, e))
        return None

    def sfx(self, name: str, t: float, vol: float = 0.3, track: int = TRACK_OTHER) -> None:
        m = self._sfx()
        if m is not None:
            c = self._call_sfx("sfx %s at %.2f s" % (name, t), m.library_sfx, name, t, video_dir=self.vdir)
            if c:
                self.cue(c, vol, track)

    def click(self, t: float, vol: float = 0.35) -> None:
        self.sfx("click", t, vol, TRACK_CLICK)

    def pop(self, t: float, vol: float = 0.18) -> None:
        self.sfx("pop", t, vol, TRACK_POP)

    def typing(self, text: str, t: float, dur: Optional[float] = None, cps: float = 14.0, vol: float = 0.45, seed: Optional[int] = None) -> None:
        m = self._sfx()
        if m is not None:
            c = self._call_sfx("typing at %.2f s" % t, m.typing_track, text, t, cps, dur=dur, seed=seed, video_dir=self.vdir)
            if c:
                self.cue(c, vol, TRACK_TYPING)

    # ---------- camera ----------
    def cam(self, t: float, scale: float, at: Any = None, d: float = 0.9, ease: str = "power2.inOut", label: str = "") -> None:
        """Record a camera move for stage.js (S.camPlan). `at` is a selector or [x, y] in app pixels."""
        if scale > self.max_zoom + 1e-9:
            self.warn("camera %.2fx at %.2f s is above video.max_zoom %.2f: clamped. Full-page 1x is the default; "
                      "raise max_zoom in product.yaml only for a far-out canvas or a narrow column." % (scale, t, self.max_zoom))
            scale = self.max_zoom
        if scale < 1:
            self.warn("camera %.2fx at %.2f s is below 1x: clamped to 1" % (scale, t))
            scale = 1.0
        if self.cam_moves:
            prev = self.cam_moves[-1]
            if t < prev["t"] + prev["d"] - 1e-6:
                self.warn("camera move at %.2f s starts before the previous one ends (%.2f s)" % (t, prev["t"] + prev["d"]))
        self.cam_moves.append({"t": round(t, 3), "s": round(scale, 4), "at": at, "d": round(d, 3), "ease": ease, "label": label})

    def snap(self, t: float, label: str = "") -> None:
        """A setup beat to look at before rendering (printed as one snapshot command)."""
        self.snaps.append((round(t, 3), label))

    # ---------- assets ----------
    def _publish(self, rel: str, src: Optional[Path] = None) -> None:
        """Copy <video_dir>/<rel> (or src) to <video_dir>/video/<rel> at write time."""
        self.copies[rel] = src or (self.vdir / rel)

    def _asset(self, path_in_product: str, placeholder: str) -> str:
        if not path_in_product:
            self.fail("%s: product.yaml has no path for it" % placeholder)
            return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1' height='1'/%3E"
        src = (self.pdir / path_in_product).resolve()
        if not src.exists():
            self.fail("%s: %s does not exist" % (placeholder, src))
            return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1' height='1'/%3E"
        rel = "assets/" + src.name
        self.copies[rel] = src
        return rel

    def _fonts_css(self) -> str:
        f = self.pdir / "kit" / "fonts" / "fonts.css"
        if not f.exists():
            self.warn("no kit/fonts/fonts.css in the product: named fonts will fall back (and check flags font_family_without_font_face)")
            return ""
        css = f.read_text(encoding="utf-8")

        def fix(m):
            url = m.group(2)
            if re.match(r"^(data:|https?:|/)", url):
                return m.group(0)
            src = (f.parent / url).resolve()
            if not src.exists():
                self.fail("fonts.css points at a missing file: %s" % url)
                return m.group(0)
            rel = "assets/fonts/" + src.name
            self.copies[rel] = src
            return 'url("%s")' % rel

        return re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", fix, css)

    def _icons(self) -> Dict[str, str]:
        icons: Dict[str, str] = {}
        for d in [self.pdir / "kit" / "icons", self.video / "src" / "icons"]:
            if d.is_dir():
                for f in sorted(d.glob("*.svg")):
                    icons[f.stem] = svg_clean(f.read_text(encoding="utf-8"))
        return icons

    def _ui_dirs(self) -> List[Path]:
        return [self.video / "src" / "ui", self.pdir / "kit" / "ui"]

    def _ui(self, name: str, depth: int = 0) -> str:
        if depth > 6:
            raise BuildError("{{UI:%s}} nests too deep (a component includes itself?)" % name)
        for d in self._ui_dirs():
            f = d / (name + ".html")
            if f.exists():
                return self._expand_ui(f.read_text(encoding="utf-8"), depth + 1)
        raise BuildError("{{UI:%s}}: no %s.html in %s" % (name, name, " or ".join(str(d) for d in self._ui_dirs())))

    def _expand_ui(self, text: str, depth: int = 0) -> str:
        return re.sub(r"\{\{UI:([A-Za-z0-9_./-]+)\}\}", lambda m: self._ui(m.group(1), depth), text)

    def _ui_css(self) -> str:
        parts = []
        for d in reversed(self._ui_dirs()):        # product components first, the video's overrides after
            if d.is_dir():
                for f in sorted(d.glob("*.css")):
                    parts.append("/* %s */\n%s" % (f.name, f.read_text(encoding="utf-8")))
        return "\n".join(parts)

    def _stage_vars(self) -> Tuple[str, Dict[str, Any]]:
        W, H = [float(x) for x in self.cfg["app_canvas"].get("logical", [1440, 810])]
        K = min(1920.0 / W, 1080.0 / H)
        X, Y = (1920 - W * K) / 2, (1080 - H * K) / 2
        if abs(X) > 0.5 or abs(Y) > 0.5:
            self.warn("app_canvas.logical %dx%d is not 16:9; the app is letterboxed (%.0f px, %.0f px)" % (W, H, X, Y))
        theme = self.cfg["app_canvas"].get("theme", "light")
        brand = self.cfg["brand"]
        font = brand.get("font") or "system-ui"
        lines = [
            "--pvs-app-w: %gpx;" % W, "--pvs-app-h: %gpx;" % H, "--pvs-app-k: %.6f;" % K,
            "--pvs-app-x: %.2fpx;" % X, "--pvs-app-y: %.2fpx;" % Y,
            "--pvs-accent: %s;" % brand.get("accent", "#4F46E5"),
            "--pvs-font: \"%s\", system-ui, sans-serif;" % font,
        ]
        if theme == "light":
            lines += ["--pvs-bg: #ffffff;", "--pvs-veil: rgba(246, 247, 249, 0.72);", "--pvs-title: #111318;",
                      "--pvs-sub: #4a4f59;", "--pvs-muted: #6b7280;", "--pvs-end-bg: rgba(246, 247, 249, 0.55);",
                      "--pvs-card-bg: #ffffff;", "--pvs-card-border: rgba(17, 19, 24, 0.10);"]
        css = ":root {\n  " + "\n  ".join(lines) + "\n}"
        js = {"W": W, "H": H, "K": round(K, 6), "X": round(X, 2), "Y": round(Y, 2), "maxZoom": self.max_zoom, "theme": theme}
        return css, js

    # ---------- audio ----------
    def _voice_audio(self) -> None:
        for k in self.timings:
            if k not in self.T:
                self.warn("clip %s is in timings.json but never placed in T" % k)
                continue
            rel = "audio/clips/%s.wav" % k
            if not (self.vdir / rel).exists():
                self.fail("missing %s (run the voice step)" % rel)
                continue
            self._publish(rel)
            track = TRACK_CHARACTER if self.roles.get(k, "narrator") != "narrator" else TRACK_VOICE
            self.audio.append(("vo-" + k, rel, float(self.T[k]), self.D[k], 1.0, track))
        placed = sorted((self.T[k], k) for k in self.timings if k in self.T and self.roles.get(k, "narrator") == "narrator")
        for (s1, a), (s2, b2) in zip(placed, placed[1:]):
            if s1 + self.D[a] > s2 + 1e-6:
                self.warn("narration %s (ends %.2f s) overlaps %s (starts %.2f s)" % (a, s1 + self.D[a], b2, s2))

    @staticmethod
    def _allocate(clips):
        """A track per clip with no overlap on the same track (base, base+30, base+60, ...)."""
        busy: Dict[int, List[Tuple[float, float]]] = {}
        out = []
        for aid, src, s, d, vol, base in sorted(clips, key=lambda c: (c[5], c[2])):
            e = s + (d if d is not None else 1.0)
            tr = base
            while any(not (e <= a or s >= b) for a, b in busy.get(tr, [])):
                tr += 30
            busy.setdefault(tr, []).append((s, e))
            out.append((aid, src, s, d, vol, tr))
        return sorted(out, key=lambda c: c[2])

    # ---------- write ----------
    def _round(self) -> None:
        for k, v in list(self.T.items()):
            if isinstance(v, float):
                self.T[k] = round(v, 3)

    def write(self, texts: Optional[Dict[str, str]] = None, values: Optional[Dict[str, str]] = None,
              template: str = "src/template.tpl", out: str = "index.html") -> Path:
        T = self.T
        if "DUR" not in T:
            raise BuildError('Set T["DUR"] (the total duration) before write()')
        self._round()
        DUR = float(T["DUR"])
        self._voice_audio()
        for aid, src, s, d, vol, tr in self.audio:
            e = s + (d or 0)
            if s < 0:
                raise BuildError("%s starts before 0 (%.3f s)" % (aid, s))
            if e > DUR + 1e-6:
                raise BuildError("%s ends at %.3f s, past DUR %.3f s: raise T['DUR']" % (aid, e, DUR))
        for k, v in T.items():
            if isinstance(v, (int, float)) and k != "DUR" and v > DUR + 1e-6:
                self.warn("beat %s at %.3f s is past DUR %.3f s" % (k, v, DUR))
        T["W"] = {}
        for k, v in self.timings.items():
            m: Dict[str, float] = {}
            for x in v["words"]:
                m.setdefault(norm_word(x["w"]), float(x["s"]))
            T["W"][k] = m
        T["texts"] = texts or {}
        T["CAM"] = [{k: m[k] for k in ("t", "s", "at", "d", "ease")} for m in self.cam_moves]

        stage_css, stage_js = self._stage_vars()
        tokens = self.pdir / "kit" / "tokens.css"
        if not tokens.exists():
            self.warn("no kit/tokens.css in the product")
        app_css = self.video / "src" / "app.css"
        brand = self.cfg["brand"]
        theme = stage_js["theme"]
        # product-kit naming: logo_light is the variant for light backgrounds, logo_dark for dark ones
        logo_on_veil = brand.get("logo_dark") if theme == "dark" else brand.get("logo_light")
        icons = self._icons()
        audio = self._allocate(self.audio)
        vals = {
            "STAGE_VARS": stage_css,
            "STAGE_CSS": (KIT / "stage.css").read_text(encoding="utf-8"),
            "TITLES_CSS": (KIT / "titles.css").read_text(encoding="utf-8"),
            "FONTS_CSS": self._fonts_css(),
            "TOKENS_CSS": tokens.read_text(encoding="utf-8") if tokens.exists() else "",
            "UI_CSS": self._ui_css(),
            "APP_CSS": app_css.read_text(encoding="utf-8") if app_css.exists() else "",
            "GSAP": '<script src="%s"></script>' % GSAP_URL,
            "STAGE_JS": "window.PVS_STAGE = %s;\n%s" % (json.dumps(stage_js), (KIT / "stage.js").read_text(encoding="utf-8")),
            "T_JSON": json.dumps(T),
            "ICONS_JSON": json.dumps(icons),
            "AUDIO": "\n    ".join(audio_tag(*a) for a in audio),
            "DUR": "%g" % DUR,
            "FPS": str(self.fps),
            "PRODUCT_NAME": html.escape(self.cfg["product"].get("name", "")),
            "POSITIONING": html.escape(self.cfg["product"].get("positioning", "")),
            "LOGO_LIGHT": self._asset(brand.get("logo_light", ""), "{{LOGO_LIGHT}}"),
            "LOGO_DARK": self._asset(brand.get("logo_dark", ""), "{{LOGO_DARK}}"),
            "LOGO_ON_VEIL": self._asset(logo_on_veil or "", "{{LOGO_ON_VEIL}}"),
            "APP_TILE": self._asset(brand.get("app_tile", ""), "{{APP_TILE}}"),
        }
        for k, v in (values or {}).items():
            vals[k] = v
        for k, v in (texts or {}).items():
            vals["TEXT_" + re.sub(r"[^A-Z0-9_]", "_", k.upper())] = html.escape(v)

        tpl_path = self.video / template
        page = self._expand_ui(tpl_path.read_text(encoding="utf-8"))
        page = replace_placeholders(page, vals)

        def icon(m):
            name = m.group(1)
            if name not in icons:
                self.fail("icon %r is not in kit/icons or src/icons (have: %s)" % (name, ", ".join(sorted(icons)) or "none"))
                return m.group(0)
            return '<i data-icon="%s" class="pvs-ic%s">%s</i>' % (name, (" " + m.group(2)) if m.group(2) else "", icons[name])

        page = re.sub(r'<i data-icon="([A-Za-z0-9_.-]+)"(?: class="([^"]*)")?></i>', icon, page)
        left = leftover_placeholders(page)
        if left:
            raise BuildError("unreplaced placeholders in %s: %s" % (template, ", ".join(left)))
        if "\u2014" in page:
            self.warn("the page contains an em dash (U+2014)")
        meta = ['<meta name="pvs-build" content="%s">' % hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()[:12]]
        if self.draft:
            meta.append('<meta name="pvs-draft" content="1">')
        if self.args.fake_timings:
            meta.append('<meta name="pvs-fake-timings" content="1">')
        page, n = re.subn(r"(<head[^>]*>)", lambda m: m.group(1) + "\n    " + "\n    ".join(meta), page, count=1)
        if not n:
            raise BuildError("%s has no <head>" % template)

        for rel, src in self.copies.items():
            dst = self.video / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not src.exists():
                self.fail("missing %s" % src)
                continue
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copyfile(src, dst)
        dst = self.video / out
        dst.write_text(page, encoding="utf-8")
        self._report(dst, audio)
        return dst

    def _report(self, dst: Path, audio) -> None:
        T = self.T
        kind = "DRAFT" if self.draft else "signed"
        print("%s written (%s): duration %s s, %d audio clips, %d camera moves" % (dst.name, kind, T["DUR"], len(audio), len(self.cam_moves)))
        if not self.args.quiet:
            beats = sorted(((v, k) for k, v in T.items() if isinstance(v, (int, float))), key=lambda x: x[0])
            for v, k in beats:
                mark = "  (clip, %.2f s)" % self.D[k] if k in self.timings else ""
                print("  %-12s %8.3f%s" % (k, v, mark))
            for m in self.cam_moves:
                print("  camera  %6.2f s  %.2fx  at %s  over %.2f s  %s" % (m["t"], m["s"], m["at"], m["d"], m["label"]))
        for wmsg in self.warnings:
            print("warning: " + wmsg)
        hv = hf_version()
        if self.snaps:
            ts = ",".join("%g" % t for t, _ in sorted(self.snaps))
            print("snapshot the setup beats: (cd %s && npx --yes hyperframes@%s snapshot . --at %s --no-end --describe false -o snapshots/setup)"
                  % (shlex.quote(str(self.video)), hv, ts))
            # check samples 9 evenly spaced times and audits contrast on 5 of them, which in a
            # video that is racked for titles often land only on blurred moments (text under the
            # veil is skipped, so nothing of the product gets audited). The setup beats are the
            # moments a viewer reads, so audit those too.
            print("check contrast at the setup beats: (cd %s && npx --yes hyperframes@%s check --at %s)"
                  % (shlex.quote(str(self.video)), hv, ts))
        name = "%s-v%s.mp4" % (self.brief.get("video") or self.vdir.name, self.brief.get("version", 1))
        print("render: (cd %s && npx --yes hyperframes@%s render . -o renders/%s --fps %d --quality %s)"
              % (shlex.quote(str(self.video)), hv, name, self.fps, "draft" if self.draft else "delivery"))


def main_guard(fn) -> None:
    """Run a build function and turn BuildError into a short message and exit code 1."""
    try:
        fn()
    except BuildError as e:
        print("build failed: %s" % e, file=sys.stderr)
        sys.exit(1)
