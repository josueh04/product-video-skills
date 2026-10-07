"""Extract design tokens from a product's pinned sources into kit/tokens.css, resolved and cited.

    bin/pvs-py skills/ui-spec-from-code/scripts/resolve_tokens.py <product_dir>
        [--role frontend] [--files PATH ...] [--theme-selector SEL] [--all-scopes]
        [--out kit/tokens.css | --stdout]

Reads sources/<role>/ (the read-only export pinned in sources.lock):
- CSS custom properties (--name: value) in .css and .scss files, by scope. :root, html, :host,
  body and Tailwind v4 @theme are the base scope; theme-like scopes (.dark, html.app-dark,
  [data-theme=dark], prefers-color-scheme media) get their own block. Component-scoped
  properties are skipped unless --all-scopes.
- SCSS variables ($name: value) at the top level or marked !global, emitted as --scss-<name>.
- Tailwind v3 theme values (colors, fontFamily, fontSize, spacing, borderRadius, boxShadow)
  read statically from tailwind.config.*, emitted as --tw-<group>-<path>. Static reading cannot
  run imported presets or functions; those keys are reported, not guessed.

Every var() and $variable is resolved to its literal value. An undefined var() takes its
fallback, or stays as var() and is marked UNDEFINED, so it can be fixed as a production glitch.
Each output line ends with /* <role>/<path>:<line>@<sha> */ and, when resolved through other
tokens, the chain it followed. --theme-selector merges that scope over the base scope into one
:root block (the theme the video renders, e.g. app_canvas.theme dark).
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pvs

SKIP_DIRS = {"node_modules", "dist", "build", ".next", ".angular", "coverage", "vendor", ".git", ".git-cache"}
BASE_SELECTORS = {":root", "html", ":host", "body", "@theme", "*", ":root,:host", "html,body"}
THEMEISH = re.compile(r"dark|light|theme|mode|scheme", re.I)
SASS_FUNCS = re.compile(r"\b(lighten|darken|mix|map-get|map\.get|math\.|color\.|adjust-hue|saturate|desaturate|scale-color|transparentize|opacify|percentage|tint|shade)\s*\(")
LOCAL_AT = ("@mixin", "@function", "@include", "@each", "@for", "@while", "@if", "@else")

Def = Tuple[str, str, int]  # value, relative file, line


def strip_comments(text: str, line_comments: bool) -> str:
    """Blank out comments (keeping newlines and offsets) without touching strings or url()."""
    out, i, n = list(text), 0, len(text)
    quote, url_depth = None, 0
    while i < n:
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'`":
            quote = c
            i += 1
            continue
        if text.startswith("url(", i) or text.startswith("URL(", i):
            url_depth = 1
            i += 4
            while i < n and url_depth:
                if text[i] == "(":
                    url_depth += 1
                elif text[i] == ")":
                    url_depth -= 1
                i += 1
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if line_comments and text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def walk_declarations(text: str):
    """Yield (selector_stack, declaration_text, line) for every declaration in CSS/SCSS."""
    stack: List[str] = []
    buf_start, i, n = 0, 0, len(text)
    quote = None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'":
            quote = c
        elif text.startswith("#{", i):  # Sass interpolation: not a block
            depth, i = 1, i + 2
            while i < n and depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            continue
        elif c == "(":  # Sass maps and function args can hold ';' or ':'
            depth, j = 1, i + 1
            while j < n and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            i = j
            continue
        elif c in "{};":
            chunk = text[buf_start:i]
            lead = len(chunk) - len(chunk.lstrip())
            line = text.count("\n", 0, buf_start + lead) + 1
            body = chunk.strip()
            if c == "{":
                stack.append(re.sub(r"\s+", " ", body))
            else:
                if body:
                    yield list(stack), body, line
                if c == "}" and stack:
                    stack.pop()
            buf_start = i + 1
        i += 1


def scope_of(stack: List[str], all_scopes: bool) -> Optional[str]:
    if any(s.startswith(LOCAL_AT) for s in stack):
        return None
    sel = [s for s in stack if not s.startswith("@media") and not s.startswith("@supports") and not s.startswith("@layer")]
    media = [s for s in stack if s.startswith("@media")]
    if not sel:
        if media and THEMEISH.search(" ".join(media)):
            return " ".join(media)
        return ":root" if not media else None
    inner = sel[-1].replace(" ", "")
    if inner in BASE_SELECTORS or all(p.strip() in BASE_SELECTORS for p in inner.split(",")):
        if media:
            return " ".join(media) if THEMEISH.search(" ".join(media)) else None
        return ":root"
    if THEMEISH.search(inner) or re.match(r"^(html|:root|body)[.\[]", inner):
        return " ".join(media) + " { " + sel[-1] if media else sel[-1]
    return sel[-1] if all_scopes else None


def find_call(s: str, name: str, start: int = 0) -> Optional[Tuple[int, int, str]]:
    """(start, end, inner) of the first name( ... ) with balanced parentheses."""
    i = s.find(name + "(", start)
    if i < 0:
        return None
    depth, j = 0, i + len(name)
    while j < len(s):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return i, j + 1, s[i + len(name) + 1:j]
        j += 1
    return None


def split_fallback(inner: str) -> Tuple[str, Optional[str]]:
    depth = 0
    for k, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            return inner[:k].strip(), inner[k + 1:].strip()
    return inner.strip(), None


def hex_to_rgb(h: str) -> Optional[Tuple[int, int, int]]:
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h[:3])
    if len(h) in (6, 8) and re.fullmatch(r"[0-9a-fA-F]+", h):
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return None


def tidy(v: str) -> str:
    v = re.sub(r"\s*!(default|global|important)\b", "", v).strip()

    def rgba(m):
        rgb = hex_to_rgb(m.group(2))
        return f"{m.group(1)}({rgb[0]}, {rgb[1]}, {rgb[2]}, {m.group(3).strip()})" if rgb else m.group(0)
    return re.sub(r"\b(rgba?)\(\s*(#[0-9a-fA-F]{3,8})\s*,\s*([^)]+)\)", rgba, v)


class Resolver:
    def __init__(self, role: str, pin: str):
        self.role, self.pin = role, pin
        self.scss: Dict[str, Def] = {}
        self.scss_default: Dict[str, Def] = {}
        self.css: Dict[str, Dict[str, Def]] = {}
        self.conflicts: List[str] = []

    def cite(self, f: str, line: int) -> str:
        return f"{self.role}/{f}:{line}@{self.pin}"

    def scss_lookup(self, name: str) -> Optional[Def]:
        return self.scss.get(name) or self.scss_default.get(name)

    def resolve_scss(self, value: str, chain: List[str], depth: int = 0) -> str:
        if depth > 20:
            return value

        def sub(m):
            d = self.scss_lookup(m.group(1))
            if d is None:
                chain.append(f"${m.group(1)} UNDEFINED")
                return m.group(0)
            chain.append(f"${m.group(1)} ({self.cite(d[1], d[2])})")
            return self.resolve_scss(tidy(d[0]), chain, depth + 1)
        value = re.sub(r"#\{\s*\$([A-Za-z_][\w-]*)\s*\}", sub, value)
        return re.sub(r"\$([A-Za-z_][\w-]*)", sub, value)

    def resolve_css(self, value: str, scopes: List[str], chain: List[str], seen: Tuple[str, ...] = ()) -> str:
        value = self.resolve_scss(value, chain)
        out, pos = "", 0
        while True:
            call = find_call(value, "var", pos)
            if call is None:
                out += value[pos:]
                break
            a, b, inner = call
            out += value[pos:a]
            name, fallback = split_fallback(inner)
            d = None
            for sc in scopes:
                d = self.css.get(sc, {}).get(name)
                if d:
                    break
            if d and name not in seen:
                chain.append(f"{name} ({self.cite(d[1], d[2])})")
                out += self.resolve_css(tidy(d[0]), scopes, chain, seen + (name,))
            elif fallback is not None:
                chain.append(f"{name} undefined, fallback used")
                out += self.resolve_css(fallback, scopes, chain, seen)
            else:
                chain.append(f"{name} UNDEFINED")
                out += value[a:b]
            pos = b
        return out


def read_tailwind(text: str):
    """Static read of the theme object in a Tailwind v3 config: [(path, value, offset)], notes."""
    s = strip_comments(text, True)
    notes: List[str] = []
    m = re.search(r"\btheme\s*:\s*\{", s)
    if not m:
        return [], ["no theme object found"]
    i = m.end() - 1
    leaves: List[Tuple[List[str], str, int]] = []

    def ws(j):
        while j < len(s) and s[j] in " \t\r\n":
            j += 1
        return j

    def raw_expr(j):
        depth, k = 0, j
        while k < len(s):
            ch = s[k]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif ch == "," and depth == 0:
                break
            k += 1
        return s[j:k].strip(), k

    def string(j):
        q, k = s[j], j + 1
        while k < len(s) and s[k] != q:
            k += 2 if s[k] == "\\" else 1
        return s[j + 1:k], k + 1

    def value(j, path):
        j = ws(j)
        if j >= len(s):
            return j
        ch = s[j]
        if ch == "{":
            return obj(j, path)
        if ch == "[":
            items, k, start = [], j + 1, j
            while True:
                k = ws(k)
                if k >= len(s) or s[k] == "]":
                    break
                if s[k] in "\"'`":
                    v, k = string(k)
                    items.append(v)
                else:
                    v, k = raw_expr(k)
                    items.append(None if v.startswith("{") else v)
                k = ws(k)
                if k < len(s) and s[k] == ",":
                    k += 1
            vals = [x for x in items if x is not None]
            if vals:
                leaves.append((path, ", ".join(f'"{x}"' if " " in x and not x.startswith('"') else x for x in vals), start))
            return k + 1
        if ch in "\"'`":
            v, k = string(j)
            leaves.append((path, v, j))
            return k
        v, k = raw_expr(j)
        if re.fullmatch(r"-?\d+(\.\d+)?", v):
            leaves.append((path, v, j))
        elif v:
            notes.append(f"{'.'.join(path)}: {v[:40]} is code, not a literal (skipped)")
        return k

    def obj(j, path):
        k = j + 1
        while True:
            k = ws(k)
            if k >= len(s):
                return k
            if s[k] == "}":
                return k + 1
            if s.startswith("...", k):
                v, k = raw_expr(k)
                notes.append(f"{'.'.join(path) or 'theme'}: spread {v[:40]} not read")
            else:
                if s[k] in "\"'`":
                    key, k = string(k)
                else:
                    mk = re.match(r"[A-Za-z0-9_$-]+", s[k:])
                    if not mk:
                        v, k = raw_expr(k)
                        notes.append(f"{'.'.join(path)}: could not read {v[:40]}")
                        k = ws(k)
                        if k < len(s) and s[k] == ",":
                            k += 1
                        continue
                    key, k = mk.group(0), k + mk.end()
                k = ws(k)
                if k < len(s) and s[k] == ":":
                    k = value(k + 1, path + [key])
                elif k < len(s) and s[k] == "(":
                    v, k = raw_expr(k)
                    notes.append(f"{'.'.join(path + [key])}: function, not read")
            k = ws(k)
            if k < len(s) and s[k] == ",":
                k += 1
    obj(i, [])
    return leaves, notes


TW_GROUPS = {"colors": "color", "fontFamily": "font", "fontSize": "text", "spacing": "spacing",
             "borderRadius": "radius", "boxShadow": "shadow"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir")
    ap.add_argument("--role", default="frontend")
    ap.add_argument("--files", nargs="*", help="only these paths, relative to sources/<role>/")
    ap.add_argument("--theme-selector", help="merge this scope over :root into one block")
    ap.add_argument("--all-scopes", action="store_true", help="also emit component-scoped custom properties")
    ap.add_argument("--out", help="output file (default <product_dir>/kit/tokens.css)")
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()

    product = pvs.product_dir(Path(a.product_dir))
    cfg = pvs.load_product(product)
    lock = pvs.read_json(product / "sources.lock", {}) or {}
    entry = lock.get(a.role)
    if not entry:
        pvs.die(f"{a.role} is not in sources.lock: run source-recon's fetch_sources.py first")
    pin = (entry.get("commit") or entry.get("tree_sha256") or "")[:7]
    root = product / "sources" / a.role
    if not root.is_dir():
        pvs.die(f"{root} is missing: run fetch_sources.py")
    app_dir = entry.get("app_dir") or next((s.get("app_dir", "") for s in cfg.get("sources", []) if s.get("role") == a.role), "")

    if a.files:
        files = [root / f for f in a.files]
        missing = [str(f) for f in files if not f.is_file()]
        if missing:
            pvs.die("not found in the export: " + ", ".join(missing))
    else:
        base = root / app_dir if app_dir and (root / app_dir).is_dir() else root
        files = []
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix in (".css", ".scss") and not (set(p.relative_to(root).parts) & SKIP_DIRS):
                files.append(p)
        files += sorted(p for p in root.glob("tailwind.config.*") if p.is_file())
        if base != root:
            files += sorted(p for p in base.glob("tailwind.config.*") if p.is_file())

    R = Resolver(a.role, pin)
    order: Dict[str, List[str]] = {}
    tw_rows: List[Tuple[str, str, str, int]] = []
    notes: List[str] = []
    skipped_component = 0
    for f in files:
        rel = f.relative_to(root).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        if f.name.startswith("tailwind.config."):
            leaves, tw_notes = read_tailwind(text)
            notes += [f"{rel}: {n}" for n in tw_notes]
            for path, val, off in leaves:
                keys = path[1:] if path and path[0] == "extend" else path
                if not keys or keys[0] not in TW_GROUPS:
                    continue
                parts = [k for k in keys[1:] if k != "DEFAULT"]
                name = "--tw-" + "-".join([TW_GROUPS[keys[0]]] + parts)
                tw_rows.append((name, val, rel, text.count("\n", 0, off) + 1))
            continue
        clean = strip_comments(text, f.suffix == ".scss")
        for stack, decl, line in walk_declarations(clean):
            m = re.match(r"^(--[A-Za-z0-9_-]+)\s*:\s*(.*)$", decl, re.S)
            if m:
                sc = scope_of(stack, a.all_scopes)
                if sc is None:
                    skipped_component += 1
                    continue
                name, val = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
                bucket = R.css.setdefault(sc, {})
                if name in bucket and bucket[name][0] != val:
                    R.conflicts.append(f"{name} in {sc}: {R.cite(bucket[name][1], bucket[name][2])} and {R.cite(rel, line)} (kept the later)")
                bucket[name] = (val, rel, line)
                order.setdefault(sc, [])
                if name not in order[sc]:
                    order[sc].append(name)
                continue
            m = re.match(r"^\$([A-Za-z_][\w-]*)\s*:\s*(.*)$", decl, re.S)
            if m and (not stack or "!global" in m.group(2)):
                name, val = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
                target = R.scss_default if "!default" in val else R.scss
                if name in target and target[name][0] != val:
                    R.conflicts.append(f"${name}: {R.cite(target[name][1], target[name][2])} and {R.cite(rel, line)} (kept the later)")
                target[name] = (val, rel, line)
                order.setdefault("$scss", [])
                if name not in order["$scss"]:
                    order["$scss"].append(name)

    def line_for(name: str, d: Def, scopes: List[str]) -> Tuple[str, bool]:
        chain: List[str] = []
        val = tidy(R.resolve_css(tidy(d[0]), scopes, chain))
        flags = []
        undefined = any("UNDEFINED" in c for c in chain)
        if undefined:
            flags.append("UNDEFINED reference")
        if SASS_FUNCS.search(val):
            flags.append("needs a Sass compile")
        if val.lstrip().startswith("("):
            flags.append("Sass map")
        via = f" via {', '.join(chain)}" if chain else ""
        flag = f" [{'; '.join(flags)}]" if flags else ""
        return f"  {name}: {val}; /* {R.cite(d[1], d[2])}{via}{flag} */", bool(flags)

    out: List[str] = [
        "/* Design tokens resolved to literal values by resolve_tokens.py from "
        f"{a.role}@{pin}. Regenerate instead of editing.",
        "   Each value cites where it is defined; 'via' lists the tokens it was resolved through. */",
    ]
    flagged = 0
    count = 0
    theme_scopes = [s for s in order if s not in (":root", "$scss")]
    if a.theme_selector:
        want = a.theme_selector.replace(" ", "")
        match = next((s for s in theme_scopes if s.replace(" ", "") == want), None)
        if match is None:
            pvs.die(f"scope {a.theme_selector} not found; scopes: {', '.join(theme_scopes) or 'none'}")
        merged = list(order.get(":root", [])) + [n for n in order[match] if n not in order.get(":root", [])]
        out.append(f"/* :root with {match} merged over it */")
        out.append(":root {")
        for name in merged:
            d = R.css.get(match, {}).get(name) or R.css[":root"][name]
            text, f = line_for(name, d, [match, ":root"])
            out.append(text)
            flagged += f
            count += 1
        out.append("}")
    else:
        for sc in ([":root"] if ":root" in order else []) + theme_scopes:
            sel = sc if not sc.startswith("@media") or "{" in sc else sc + " { :root"
            out.append(f"/* scope: {sc.replace(' { ', ' ')} */")
            out.append(f"{sel} {{")
            for name in order[sc]:
                text, f = line_for(name, R.css[sc][name], [sc, ":root"])
                out.append(text)
                flagged += f
                count += 1
            out.append("}" + (" }" if sc.startswith("@media") else ""))
    if order.get("$scss"):
        out.append("/* SCSS variables, as --scss-<name> */")
        out.append(":root {")
        for name in order["$scss"]:
            d = R.scss_lookup(name)
            chain: List[str] = []
            val = tidy(R.resolve_scss(tidy(d[0]), chain))
            flags = []
            if SASS_FUNCS.search(val):
                flags.append("needs a Sass compile")
            if val.startswith("("):
                flags.append("Sass map")
            if any("UNDEFINED" in c for c in chain):
                flags.append("UNDEFINED reference")
            flagged += bool(flags)
            via = f" via {', '.join(chain)}" if chain else ""
            flag = f" [{'; '.join(flags)}]" if flags else ""
            out.append(f"  --scss-{name}: {val}; /* {R.cite(d[1], d[2])}{via}{flag} */")
            count += 1
        out.append("}")
    if tw_rows:
        out.append("/* Tailwind theme, read statically from the config (verify presets and plugins by hand) */")
        out.append(":root {")
        seen = set()
        for name, val, rel, line in tw_rows:
            if name in seen:
                continue
            seen.add(name)
            out.append(f"  {name}: {val}; /* {R.cite(rel, line)} */")
            count += 1
        out.append("}")
    text = "\n".join(out) + "\n"
    if a.stdout:
        sys.stdout.write(text)
    else:
        dest = Path(a.out) if a.out else product / "kit" / "tokens.css"
        if not dest.is_absolute():
            dest = product / dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    for c in R.conflicts:
        notes.append("conflict: " + c)
    if skipped_component:
        notes.append(f"{skipped_component} component-scoped custom properties skipped (use --all-scopes)")
    for n in notes:
        print("  note: " + n, file=sys.stderr)
    where = "stdout" if a.stdout else str((Path(a.out) if a.out else Path("kit/tokens.css")))
    print(f"{count} token(s) from {len(files)} file(s) -> {where}; {flagged} flagged (UNDEFINED, Sass functions or maps)",
          file=sys.stderr if a.stdout else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
