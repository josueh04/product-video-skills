"""Subset the product's font files to woff2 in kit/fonts/ and regenerate fonts.css and fonts.md.

    bin/pvs-py skills/product-kit/scripts/subset_fonts.py <product_dir> <font file> ...
        [--codepoints U+0020-007E,U+00A0-00FF] [--text "Acme"] [--text-file lines.tsv ...]
        [--all-features] [--source CITATION] [--license NAME] [--family NAME]

Each font (ttf, otf, woff, woff2) is subset with fontTools to the code points given (default:
Latin, Latin-1 and common punctuation) plus every character of --text and --text-file, and
saved as kit/fonts/<family>-<weight>[-italic].woff2. Family, weight and style come from the
font's name and OS/2 tables (--family overrides the family). fonts.css is rebuilt from every
woff2 in kit/fonts with font-display: block, so a render never paints a fallback first.
fonts.md records each file's family, weight, style, glyph count, source and license; the source
is a citation when the font lives in sources/<role>/ or an installed package, else --source.
Layout features default to fontTools' standard set (kerning, ligatures); --all-features keeps
every feature, which icon fonts that work by ligature need.

The license text (OFL.txt, LICENSE, ...) found next to the font, or at the root of the package
that ships it, is copied into kit/fonts/ and named in fonts.md: the OFL and most font licenses
require their text to travel with every copy of the font. The repo root of a source is not
searched, since its LICENSE usually covers the app's code, not the font. A warning names each
font whose license text was not found.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Set

import pvs
import kitlib as K

try:
    from fontTools import subset
    from fontTools.ttLib import TTFont
except ImportError:  # requirements.txt installs fonttools and brotli
    subset = None

DEFAULT_CODEPOINTS = "U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,U+2010-2027,U+2030-203A,U+2044,U+20AC,U+2122,U+2190-2193,U+2212"


def parse_codepoints(spec: str) -> Set[int]:
    out: Set[int] = set()
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        part = part.upper().replace("U+", "")
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a, 16), int(b, 16) + 1))
        else:
            out.add(int(part, 16))
    return out


def font_meta(font) -> dict:
    name = font["name"]
    fam = name.getDebugName(16) or name.getDebugName(1) or "font"
    sub = (name.getDebugName(17) or name.getDebugName(2) or "").lower()
    weight = font["OS/2"].usWeightClass if "OS/2" in font else (700 if "bold" in sub else 400)
    italic = bool("OS/2" in font and font["OS/2"].fsSelection & 1) or "italic" in sub or "oblique" in sub
    glyphs = len(font.getGlyphOrder())
    return {"family": fam, "weight": int(weight), "style": "italic" if italic else "normal", "glyphs": glyphs}


LICENSE_FILE = re.compile(r"^(OFL|UFL|LICEN[CS]E|COPYING)([-_.][\w.-]*)?$", re.I)


def find_license(product: Path, font: Path) -> Optional[Path]:
    """The license text nearest the font: its folder, the one above (a static/ subfolder), its package root."""
    src_root = (product / "sources").resolve()
    dirs = list(font.parents)[:2]
    pkg = K.package_of(font)
    if pkg:
        dirs.append(pkg[1].resolve())
    for d in dirs:
        if d == src_root or d.parent == src_root or d.name == "node_modules":
            break  # a source's repo root: its LICENSE is the app's
        hits = sorted((p for p in d.iterdir() if p.is_file() and LICENSE_FILE.match(p.name)),
                      key=lambda p: (not p.name.upper().startswith("OFL"), p.name))
        if hits:
            return hits[0]
    return None


def copy_license(lic: Path, out_dir: Path, family: str) -> str:
    dst = out_dir / lic.name
    if dst.exists() and dst.read_bytes() != lic.read_bytes():
        dst = out_dir / f"{K.slug(family)}-{lic.name}"
    shutil.copyfile(lic, dst)
    return dst.name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir")
    ap.add_argument("fonts", nargs="+")
    ap.add_argument("--codepoints", default=DEFAULT_CODEPOINTS)
    ap.add_argument("--text", default="")
    ap.add_argument("--text-file", action="append", default=[])
    ap.add_argument("--all-features", action="store_true")
    ap.add_argument("--source", default="", help="citation when the font is not in sources/ or a package")
    ap.add_argument("--license", default="", help="license name when the package does not say (e.g. OFL-1.1)")
    ap.add_argument("--family", help="override the family name")
    a = ap.parse_args()
    if subset is None:
        pvs.die("fontTools is missing. Run /video-setup (or bash setup.sh) first.")

    product = pvs.product_dir(Path(a.product_dir))
    out_dir = product / "kit" / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    text = a.text
    for tf in a.text_file:
        text += Path(tf).read_text(encoding="utf-8")
    cps = parse_codepoints(a.codepoints) | {ord(c) for c in text if not c.isspace() or c == " "}

    md = out_dir / "fonts.md"
    _h, rows = K.read_table(md, "file")
    made: List[str] = []
    no_license: List[str] = []
    for f in a.fonts:
        src = Path(f).expanduser().resolve()
        if not src.is_file():
            pvs.die(f"no such font: {src}")
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        if a.all_features:
            opts.layout_features = ["*"]
        font = subset.load_font(str(src), opts)
        meta = font_meta(font)
        if a.family:
            meta["family"] = a.family
        sub = subset.Subsetter(opts)
        sub.populate([], [], sorted(cps))  # glyphs, gids, code points
        sub.subset(font)
        fname = f"{K.slug(meta['family'])}-{meta['weight']}{'-italic' if meta['style'] == 'italic' else ''}.woff2"
        subset.save_font(font, str(out_dir / fname), opts)
        cite, lic = K.cite_path(product, src)
        if a.source and (cite == str(src)):
            cite = a.source
        kept = len(font.getGlyphOrder())
        lic_path = find_license(product, src)
        lic_file = copy_license(lic_path, out_dir, meta["family"]) if lic_path else ""
        if not lic_file:
            no_license.append(src.name)
        rows[fname] = {"file": fname, "family": meta["family"], "weight": str(meta["weight"]), "style": meta["style"],
                       "glyphs": str(kept), "source": cite, "license": a.license or lic or "unknown: check before use",
                       "license file": lic_file or "missing"}
        made.append(f"{fname} ({kept} glyphs, {(out_dir / fname).stat().st_size} bytes)")

    css = ["/* Generated by subset_fonts.py from kit/fonts/*.woff2. Regenerate instead of editing. */"]
    for w in sorted(out_dir.glob("*.woff2")):
        r = rows.get(w.name)
        if r is None:
            try:
                meta = font_meta(TTFont(str(w)))
            except Exception:
                continue
            r = rows[w.name] = {"file": w.name, "family": meta["family"], "weight": str(meta["weight"]),
                                "style": meta["style"], "glyphs": str(meta["glyphs"]), "source": "unknown", "license": "unknown"}
        css.append("@font-face {\n"
                   f"  font-family: \"{r['family']}\";\n"
                   f"  src: url(\"{w.name}\") format(\"woff2\");\n"
                   f"  font-weight: {r['weight']};\n"
                   f"  font-style: {r['style']};\n"
                   "  font-display: block;\n}")
    (out_dir / "fonts.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    K.write_table(md, "Fonts", "Subsets made by subset_fonts.py. Keep each font's license with the kit.",
                  ["file", "family", "weight", "style", "glyphs", "source", "license", "license file"],
                  [rows[k] for k in sorted(rows) if (out_dir / k).exists()])
    for m in made:
        print("  " + m)
    for n in no_license:
        print(f"  warning: no license text found next to {n}: put it in kit/fonts/ and name it in fonts.md")
    print(f"{len(made)} font(s) -> kit/fonts; fonts.css lists {len(css) - 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
