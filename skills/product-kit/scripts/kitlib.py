"""Helpers shared by the product-kit scripts: citations for kit files and small markdown tables."""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pvs


def cite_path(product: Path, path: Path) -> Tuple[str, str]:
    """(citation, license) for a file inside sources/<role>/ or an installed package.

    sources/<role>/x.svg          -> "<role>/x.svg@<sha>"
    .../node_modules/pkg/x.svg    -> "npm:pkg@<version>/x.svg" with the package's license
    anything else                 -> the absolute path, license unknown
    """
    path = Path(path).resolve()
    src = (product / "sources").resolve()
    lock = pvs.read_json(product / "sources.lock", {}) or {}
    try:
        rel = path.relative_to(src)
        role = rel.parts[0]
        entry = lock.get(role, {})
        pin = (entry.get("commit") or entry.get("tree_sha256") or "")[:7]
        cite = f"{role}/{Path(*rel.parts[1:]).as_posix()}@{pin}" if pin else f"{role}/{Path(*rel.parts[1:]).as_posix()}"
    except ValueError:
        cite = None
    pkg = package_of(path)
    lic = ""
    if pkg:
        meta, root = pkg
        lic = license_of(meta)
        if cite is None:
            cite = f"npm:{meta.get('name', root.name)}@{meta.get('version', '?')}/{path.relative_to(root).as_posix()}"
    return cite or str(path), lic


def package_of(path: Path) -> Optional[Tuple[dict, Path]]:
    for d in [path.parent, *path.parents]:
        pj = d / "package.json"
        if pj.is_file():
            try:
                meta = json.loads(pj.read_text(encoding="utf-8"))
            except ValueError:
                return None
            if meta.get("name"):
                return meta, d
        if d.name in ("node_modules", "sources"):
            return None
    return None


def license_of(meta: dict) -> str:
    lic = meta.get("license") or ""
    if isinstance(lic, dict):
        lic = lic.get("type", "")
    if not lic and isinstance(meta.get("licenses"), list) and meta["licenses"]:
        lic = meta["licenses"][0].get("type", "")
    return str(lic)


def read_table(md: Path, key: str) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Header and rows (keyed by column `key`) of the first table in a markdown file."""
    if not md.exists():
        return [], {}
    header: List[str] = []
    rows: Dict[str, Dict[str, str]] = {}
    for line in md.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not header:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        if row.get(key):
            rows[row[key]] = row
    return header, rows


def write_table(md: Path, title: str, intro: str, header: List[str], rows: List[Dict[str, str]]) -> None:
    out = [f"# {title}", "", intro, "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(h, "")).replace("|", "/") for h in header) + " |")
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out) + "\n", encoding="utf-8")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
