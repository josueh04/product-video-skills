"""List the logo files in the product's sources, or copy the chosen ones into kit/logos/ with citations.

    bin/pvs-py skills/product-kit/scripts/collect_logos.py <product_dir>
        [--light FILE] [--dark FILE] [--tile FILE] [--root DIR]

Without --light/--dark/--tile it lists candidates: image files (svg, png, webp) under sources/
(or --root, e.g. a brand folder the user handed over) whose path mentions logo, brand,
wordmark, mark, app-icon, app-tile, apple-touch-icon, favicon or icon-<size>. Pick the variants yourself:
which mark reads on which background is a judgment, not a file-name match.

With them, each file is copied to kit/logos/logo-light.<ext>, logo-dark.<ext> or
app-tile.<ext>, and kit/logos/logos.md gets a row: file, use, source citation (a file in
sources/<role>/ is cited as <role>/<path>@<pin>). FILE is a local path, relative to sources/ (tried
first, so the citation carries the pin), to the product folder, or absolute. A URL is refused: logos come from the product's own files,
never from a website, so nothing here touches the network.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import List

import pvs
import kitlib as K

EXTS = {".svg", ".png", ".webp"}
HINT = re.compile(r"logo|brand|wordmark|(^|[-_/])mark([-_.]|$)|app[-_]?(icon|tile)|apple-touch-icon|favicon|icon[-_]?\d{2,4}", re.I)
SKIP = {"node_modules", ".git", ".git-cache", "dist", "build", "coverage"}
VARIANTS = [("light", "logo-light", "the mark on light backgrounds"),
            ("dark", "logo-dark", "the mark on dark backgrounds"),
            ("tile", "app-tile", "the square app icon")]


def candidates(root: Path) -> List[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        rel = p.relative_to(root)
        if any(part in SKIP for part in rel.parts):
            continue
        if HINT.search(rel.as_posix()):
            out.append(p)
    return out


def resolve(product: Path, value: str) -> Path:
    if re.match(r"^[a-z][a-z0-9+.-]*://", value, re.I):
        pvs.die(f"collect_logos: {value} is a URL. Logos come from the product's own files "
                "(sources/ or a brand folder the user hands over), never from a website.")
    p = Path(value).expanduser()
    if not p.is_absolute():
        for base in (product / "sources", product, Path.cwd()):
            if (base / p).is_file():
                return (base / p).resolve()
    if not p.is_file():
        pvs.die(f"collect_logos: no such file: {value}")
    return p.resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir")
    ap.add_argument("--light", help="the mark for light backgrounds")
    ap.add_argument("--dark", help="the mark for dark backgrounds")
    ap.add_argument("--tile", help="the square app icon")
    ap.add_argument("--root", help="where to look for candidates (default: sources/)")
    a = ap.parse_args()
    product = pvs.product_dir(Path(a.product_dir))

    chosen = [(v, stem, use, getattr(a, v)) for v, stem, use in VARIANTS if getattr(a, v)]
    if not chosen:
        root = Path(a.root).expanduser().resolve() if a.root else product / "sources"
        if not root.is_dir():
            pvs.die(f"collect_logos: {root} does not exist. Fetch the sources first (source-recon).")
        found = candidates(root)
        for p in found:
            cite, _lic = K.cite_path(product, p)
            print(f"  {cite}  ({p.stat().st_size} bytes)")
        print(f"{len(found)} logo candidate(s) under {root}. Copy the chosen ones with --light, --dark and --tile.")
        return 0 if found else 1

    out_dir = product / "kit" / "logos"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "logos.md"
    _h, rows = K.read_table(md, "file")
    for variant, stem, use, value in chosen:
        src = resolve(product, value)
        if src.suffix.lower() not in EXTS:
            pvs.die(f"collect_logos: {src.name} is not an svg, png or webp file")
        fname = stem + src.suffix.lower()
        for old in out_dir.glob(stem + ".*"):  # a new pick replaces the old one, whatever its format
            if old.name != fname:
                old.unlink()
                rows.pop(old.name, None)
        shutil.copyfile(src, out_dir / fname)
        cite, _lic = K.cite_path(product, src)
        rows[fname] = {"file": fname, "use": (rows.get(fname) or {}).get("use") or use, "source": cite}
        key = {"light": "logo_light", "dark": "logo_dark", "tile": "app_tile"}[variant]
        print(f"  kit/logos/{fname} <- {cite}   (product.yaml brand.{key}: kit/logos/{fname})")
    order = {stem: i for i, (_v, stem, _u) in enumerate(VARIANTS)}
    K.write_table(md, "Logos", "Copied from the product's own assets by collect_logos.py, never redrawn. "
                  "Pick the variant by background.", ["file", "use", "source"],
                  sorted(rows.values(), key=lambda r: (order.get(Path(r["file"]).stem, 9), r["file"])))
    print(f"{len(chosen)} logo(s) -> kit/logos; logos.md lists {len(rows)}")
    if any(str(src_cite).startswith("/") for src_cite in (r["source"] for r in rows.values())):
        print("  note: a logo outside sources/ is cited by its path; say in logos.md where the user got it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
