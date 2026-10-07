"""Copy named SVG icons from the product's own icon package into kit/icons/, with citations.

    bin/pvs-py skills/product-kit/scripts/collect_icons.py <product_dir> --package DIR --names a,b,c
        [--set NAME] [--variant SUBSTR] [--prefix STR] [--clean]

DIR is a folder of SVG files inside sources/<role>/ or in an installed package (for example
<repo>/node_modules/lucide-static/icons, node_modules/heroicons/24/outline or
node_modules/boxicons/svg; React icon packages ship components, so use their SVG sibling
package). For each name it looks for <prefix><name>.svg
anywhere under DIR. When several files match (sizes, styles), --variant keeps the ones whose
path contains SUBSTR; identical files count as one. The icon is copied to
kit/icons/<set>-<name>.svg and kit/icons/icons.md gets a row: file, name, source citation,
license. --clean drops the root width and height (so CSS sizes it) and every id attribute.
Exits 1 if any name is missing or ambiguous: never substitute a look-alike from another set.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, List

import pvs
import kitlib as K


def clean_svg(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\s+id=\"[^\"]*\"", "", text)

    def root(m):
        tag = re.sub(r"\s(width|height)=\"[^\"]*\"", "", m.group(0))
        return tag
    return re.sub(r"<svg\b[^>]*>", root, text, count=1).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir")
    ap.add_argument("--package", required=True, help="folder that holds the SVG files")
    ap.add_argument("--names", required=True, help="comma-separated icon names")
    ap.add_argument("--set", help="short set name used in file names (default: the package name)")
    ap.add_argument("--variant", help="keep only matches whose path contains this")
    ap.add_argument("--prefix", default="", help="file name prefix, e.g. bx- for Boxicons")
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()

    product = pvs.product_dir(Path(a.product_dir))
    pkg_dir = Path(a.package).expanduser()
    if not pkg_dir.is_absolute():
        pkg_dir = (product / pkg_dir) if (product / pkg_dir).exists() else pkg_dir.resolve()
    if not pkg_dir.is_dir():
        pvs.die(f"no such folder: {pkg_dir}")
    index: Dict[str, List[Path]] = {}
    for p in pkg_dir.rglob("*.svg"):
        index.setdefault(p.stem, []).append(p)
    meta = K.package_of(pkg_dir / "x")
    set_name = a.set or K.slug((meta[0].get("name") if meta else pkg_dir.name).split("/")[-1])

    out_dir = product / "kit" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "icons.md"
    _h, rows = K.read_table(md, "file")
    missing, ambiguous, copied = [], [], 0
    for name in [n.strip() for n in a.names.split(",") if n.strip()]:
        cands = index.get(a.prefix + name, [])
        if a.variant:
            cands = [c for c in cands if a.variant in c.relative_to(pkg_dir).as_posix()]
        uniq: Dict[str, Path] = {}
        for c in sorted(cands):
            uniq.setdefault(hashlib.sha256(c.read_bytes()).hexdigest(), c)
        if not uniq:
            missing.append(name)
            continue
        if len(uniq) > 1:
            ambiguous.append(f"{name}: " + ", ".join(p.relative_to(pkg_dir).as_posix() for p in uniq.values()))
            continue
        src = next(iter(uniq.values()))
        text = src.read_text(encoding="utf-8")
        if a.clean:
            text = clean_svg(text)
        fname = f"{set_name}-{K.slug(name)}.svg"
        (out_dir / fname).write_text(text, encoding="utf-8")
        cite, lic = K.cite_path(product, src)
        rows[fname] = {"file": fname, "name": name, "set": set_name, "source": cite, "license": lic}
        copied += 1
    header = ["file", "name", "set", "source", "license"]
    K.write_table(md, "Icons", "Copied from the product's own icon packages by collect_icons.py. "
                  "Never draw an icon or take one from another set.", header,
                  [rows[k] for k in sorted(rows)])
    for m in missing:
        print(f"  missing: {m} (no {a.prefix}{m}.svg under {pkg_dir})")
    for m in ambiguous:
        print(f"  ambiguous: {m} (narrow it with --variant)")
    print(f"{copied} icon(s) -> kit/icons ({set_name}); {len(missing)} missing, {len(ambiguous)} ambiguous")
    return 1 if missing or ambiguous else 0


if __name__ == "__main__":
    sys.exit(main())
