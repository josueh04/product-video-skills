"""Find banned terms, never-say phrases and legacy product names in text or files.

    bin/pvs-py skills/render-qa/scripts/banned_terms.py [--product DIR] [--text TEXT] [FILE|DIR ...]

The terms come from product.yaml:
  product.banned_terms   anything that must never be seen or heard (kind "banned")
  product.never_say      positioning phrases to avoid (kind "never_say")
  product.names          canonical name -> legacy strings (kind "legacy_name")

Matching is case-insensitive and word-boundary aware ("Acme" does not hit "Acmeville"),
and whitespace inside a term matches any run of whitespace. A legacy name written as one
camel-case word ("AcmeTodo") also matches its spoken form ("Acme Todo"), because speech to
text never writes the joined spelling.

Exit 1 when anything is found, 0 when clean. Other scripts import find_banned().
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

TEXT_EXT = {".html", ".htm", ".tpl", ".js", ".mjs", ".css", ".md", ".txt", ".tsv", ".json",
            ".yaml", ".yml", ".py", ".svg", ".srt", ".vtt"}
SKIP_DIRS = {".git", "node_modules", "renders", "raw", "sources", "vendor", ".venv", "__pycache__"}


def _product_section(product: Dict[str, Any]) -> Dict[str, Any]:
    """Accept the full load_product() dict or only its 'product' section."""
    if isinstance(product.get("product"), dict):
        return product["product"]
    return product


def terms_of(product: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(term, kind) pairs from a product config, without blanks or duplicates."""
    p = _product_section(product or {})
    out: List[Tuple[str, str]] = []
    for t in p.get("banned_terms") or []:
        out.append((str(t), "banned"))
    for t in p.get("never_say") or []:
        out.append((str(t), "never_say"))
    for _canonical, legacy in (p.get("names") or {}).items():
        if isinstance(legacy, str):
            legacy = [legacy]
        for t in legacy or []:
            out.append((str(t), "legacy_name"))
    seen = set()
    uniq = []
    for t, k in out:
        key = t.strip().lower()
        if key and key not in seen:
            seen.add(key)
            uniq.append((t.strip(), k))
    return uniq


def _variants(term: str) -> List[str]:
    v = [term]
    split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", term)  # AcmeTodo -> Acme Todo
    if split != term:
        v.append(split)
    return v


def _pattern(term: str) -> "re.Pattern[str]":
    parts = [re.escape(w) for w in term.split()]
    body = r"\s+".join(parts)
    return re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])", re.I)


def find_banned(text: str, product: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Every (term, kind) of the product found in text, in order of first appearance."""
    hits = []
    for term, kind in terms_of(product):
        pos = None
        for v in _variants(term):
            m = _pattern(v).search(text or "")
            if m and (pos is None or m.start() < pos):
                pos = m.start()
        if pos is not None:
            hits.append((pos, term, kind))
    hits.sort()
    return [(t, k) for _, t, k in hits]


def find_banned_lines(text: str, product: Dict[str, Any]) -> List[Tuple[int, str, str, str]]:
    """(line number, term, kind, line text) for every line with a hit."""
    out = []
    for n, line in enumerate((text or "").splitlines(), 1):
        for term, kind in find_banned(line, product):
            out.append((n, term, kind, line.strip()))
    return out


def iter_files(paths: Iterable[str]) -> Iterable[Path]:
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in TEXT_EXT and not (set(f.relative_to(p).parts[:-1]) & SKIP_DIRS):
                    yield f
        elif p.is_file():
            yield p


def load_product_for(start: Path) -> Dict[str, Any]:
    import pvs  # lib/pvs.py, on PYTHONPATH through bin/pvs-py
    d = pvs.find_up(start, "product.yaml")
    if d is None:
        pvs.die(f"No product.yaml above {start}. Pass --product <product_dir>.")
    return pvs.load_product(d)


def main(argv=None) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
    ap = argparse.ArgumentParser(description="Find banned terms, never-say phrases and legacy names.")
    ap.add_argument("paths", nargs="*", help="files or folders to scan")
    ap.add_argument("--product", help="product folder or product.yaml (default: found above the first path or the cwd)")
    ap.add_argument("--text", action="append", default=[], help="text to scan (repeatable)")
    a = ap.parse_args(argv)
    if not a.paths and not a.text:
        ap.error("give at least one path or --text")
    start = Path(a.product) if a.product else Path(a.paths[0] if a.paths else ".")
    product = load_product_for(start)
    if not terms_of(product):
        print("banned terms: product.yaml lists no banned terms, never_say phrases or legacy names")
        return 0
    found = 0
    for i, t in enumerate(a.text, 1):
        for term, kind in find_banned(t, product):
            print(f"text#{i}: {kind}: {term!r}")
            found += 1
    for f in iter_files(a.paths):
        try:
            body = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, term, kind, line in find_banned_lines(body, product):
            print(f"{f}:{n}: {kind}: {term!r}: {line[:160]}")
            found += 1
    print(f"banned terms: {found} hit(s)" if found else "banned terms: clean")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
