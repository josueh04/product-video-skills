"""Create products/<slug>/ from the product template (or an example) and the interview answers.

    bin/pvs-py skills/product-new/scripts/new_product.py <slug> [--from <dir>] [--answers answers.json]
                                                          [--dest <dir>] [--no-git] [--no-link]

The product lands in <dest>/<slug> (default dest: the workbench's products/). --from copies a
folder (e.g. examples/acme) over the template, so any file it lacks comes from the template.

answers.json has the same shape as product.yaml (any subset of it, see
skills/product-new/references/answers.example.json). It is merged into product.yaml line by
line, so the comments that explain each key survive. The script refuses an existing product, an invalid slug, credentials inside a
source URL, and cast contact data that is not obviously fictional. It never reads .env and never
asks for a token: sources are fetched later by source-recon with the git access the machine has.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pvs

SLUG = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
RESERVED = {"template", "examples", "products", "skills", "vendor", "tests", "docs", "lib", "bin"}
FRAMEWORKS = {"angular-primeng", "react", "vue", "svelte", "html", "other"}
FICTIONAL_EMAIL = re.compile(r"@([a-z0-9-]+\.)*(example|test|invalid|localhost)$|@example\.(com|org|net)$", re.I)
CRED_URL = re.compile(r"^[a-z+]+://[^/@\s]+@", re.I)
SKIP_DIRS = {".git", "sources", "node_modules", "renders", "deliveries", "__pycache__"}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt", ".gitignore", ""}

GITIGNORE = """sources/
*.mp4
renders/
qa/sheets/
qa/strips/
audio/raw/
node_modules/
.env
"""

CLAUDE_MD = """# {name} videos

This folder is a product of the Product Video Skills workbench at `{home}`.
The workbench rules apply here: read `{home}/CLAUDE.md` and `kit/RULES.md` before any work.

- `product.yaml` is the single source of product config (positioning, names, cast, voice).
- `sources/` is a read-only export of the product code, pinned in `sources.lock`. Never edit it.
- Each video lives in `videos/<video>/`. Start one with `/video-new <video>`.
- Fictional data only. Never print a secret.
"""


def fail(msg: str) -> None:
    pvs.die(f"new_product: {msg}")


def check_slug(slug: str) -> None:
    if not SLUG.match(slug):
        fail(f"invalid slug '{slug}': use 2 to 40 lowercase letters, digits or dashes, starting with a letter")
    if slug in RESERVED:
        fail(f"'{slug}' is reserved, pick another slug")


def validate(cfg: Dict[str, Any]) -> List[str]:
    """Problems that make the config unusable or unsafe. Empty list means valid."""
    errs = []
    prod = cfg.get("product") or {}
    if not prod.get("name"):
        errs.append("product.name is empty")
    for key in ("never_say", "banned_terms"):
        if not isinstance(prod.get(key, []), list):
            errs.append(f"product.{key} must be a list")
    for key in ("names", "pronounce"):
        if not isinstance(prod.get(key, {}), dict):
            errs.append(f"product.{key} must be a mapping")
    roles = set()
    for i, src in enumerate(cfg.get("sources") or []):
        where = f"sources[{i}]"
        if not isinstance(src, dict):
            errs.append(f"{where} must be a mapping")
            continue
        role = str(src.get("role") or "")
        if not re.match(r"^[a-z][a-z0-9_-]*$", role):
            errs.append(f"{where}.role '{role}' must be a short lowercase id")
        if role in roles:
            errs.append(f"{where}.role '{role}' is repeated")
        roles.add(role)
        if bool(src.get("url")) == bool(src.get("path")):
            errs.append(f"{where} needs exactly one of url or path")
        if src.get("url") and not is_placeholder(src["url"]) and CRED_URL.match(str(src["url"])):
            errs.append(f"{where}.url contains credentials: remove them, the machine's own git access is used")
        fw = src.get("framework")
        if fw and not is_placeholder(fw) and fw not in FRAMEWORKS:
            errs.append(f"{where}.framework '{fw}' is not one of {sorted(FRAMEWORKS)}")
    cast = cfg.get("cast") or {}
    for i, person in enumerate(cast.get("people") or []):
        if not isinstance(person, dict):
            errs.append(f"cast.people[{i}] must be a mapping")
            continue
        email = person.get("email")
        if email and not is_placeholder(email) and not FICTIONAL_EMAIL.search(str(email)):
            errs.append(f"cast.people[{i}].email '{email}' is not on an example/.test domain (fictional data only)")
        phone = person.get("phone")
        if phone and not is_placeholder(phone) and "555" not in re.sub(r"\D", "", str(phone)):
            errs.append(f"cast.people[{i}].phone '{phone}' is not a 555 number (fictional data only)")
    video = cfg.get("video") or {}
    if video.get("size") and (not isinstance(video["size"], list) or len(video["size"]) != 2):
        errs.append("video.size must be [width, height]")
    return errs


def is_placeholder(v: Any) -> bool:
    return isinstance(v, str) and v.strip().startswith("<") and v.strip().endswith(">")


def placeholders(node: Any, path: str = "") -> List[str]:
    """Dotted paths of values still shaped like "<...>" (left for the interview to fill)."""
    if isinstance(node, dict):
        return [p for k, v in node.items() for p in placeholders(v, f"{path}.{k}" if path else str(k))]
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in placeholders(v, f"{path}[{i}]")]
    return [path] if is_placeholder(node) else []


def substitute(root: Path, values: Dict[str, str]) -> None:
    for f in root.rglob("*"):
        if not f.is_file() or ".git" in f.parts:
            continue
        if f.suffix not in TEXT_SUFFIXES and f.name != ".gitignore":
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for k, v in values.items():
            new = new.replace("{{" + k + "}}", v)
        if new != text:
            f.write_text(new, encoding="utf-8")


# ---------- product.yaml edits that keep comments ----------
# PyYAML drops every comment on a dump, and the template's comments are the only documentation a
# user sees when they open product.yaml. So answers are written as targeted line edits: a key's
# value is replaced in place (its trailing comment kept), a mapping is merged key by key, and a
# missing key is appended to its parent block. The result is parsed back and compared with a plain
# merge; if they ever differ, the file is dumped without comments instead of being wrong.
KEY_LINE = re.compile(r"""^(\s*)("[^"]*"|'[^']*'|[^\s#'"\-{\[][^:#]*?)\s*:(?:\s+(.*))?$""")
INLINE_MAX = 100


def dump_inline(value: Any) -> str:
    text = pvs.yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10 ** 9, sort_keys=False)
    lines = text.strip().splitlines()
    if lines and lines[-1] == "...":
        lines = lines[:-1]
    return " ".join(x.strip() for x in lines)


def split_comment(rest: str) -> Tuple[str, str]:
    """'value   # note' -> ('value', '# note'), ignoring # inside quotes."""
    quote = ""
    for i, ch in enumerate(rest):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or rest[i - 1] in " \t"):
            return rest[:i].rstrip(), rest[i:]
    return rest.rstrip(), ""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _content(line: str) -> bool:
    return bool(line.strip()) and not line.lstrip().startswith("#")


def _key_at(line: str, indent: int) -> Optional[Tuple[str, str]]:
    m = KEY_LINE.match(line)
    if not m or len(m.group(1)) != indent:
        return None
    key = m.group(2)
    if key[:1] in "\"'":
        key = key[1:-1]
    return key, m.group(3) or ""


def _block_end(lines: List[str], i: int, indent: int) -> int:
    j = i + 1
    while j < len(lines) and (not _content(lines[j]) or _indent(lines[j]) > indent):
        j += 1
    return j


def _last_content(lines: List[str], start: int, end: int) -> int:
    last = start - 1
    for j in range(start, end):
        if _content(lines[j]):
            last = j
    return last


def _render(key: Any, value: Any, indent: int, comment: str = "", col: int = 0) -> List[str]:
    pad = " " * indent
    head = pad + dump_inline(key) + ":"
    inline = dump_inline(value)
    nested = isinstance(value, list) and any(isinstance(v, (dict, list)) for v in value)
    def with_comment(first: str) -> str:
        if not comment:
            return first
        return first.ljust(col - 1) + comment if len(first) < col - 2 else first + "  " + comment

    if not nested and not (isinstance(value, dict) and len(inline) > INLINE_MAX):
        return [with_comment(head + " " + inline)]
    out = [with_comment(head)]
    if isinstance(value, dict):
        for k, v in value.items():
            out += _render(k, v, indent + 2)
        return out
    block = any(isinstance(item, dict) and len(dump_inline(item)) > INLINE_MAX for item in value)
    for item in value:
        flow = dump_inline(item)
        if not isinstance(item, dict) or not block:
            out.append(pad + "  - " + flow)
        else:
            sub = [x for k, v in item.items() for x in _render(k, v, indent + 4)]
            sub[0] = pad + "  - " + sub[0].lstrip()
            out += sub
    return out


def _apply(lines: List[str], start: int, end: int, indent: int, key: str, value: Any) -> None:
    """Set key (at this indent, inside lines[start:end]) to value, merging mappings like pvs._merge."""
    i = next((j for j in range(start, end) if _content(lines[j]) and _key_at(lines[j], indent)
              and _key_at(lines[j], indent)[0] == key), None)
    if i is None:
        at = _last_content(lines, start, end) + 1
        lines[at:at] = _render(key, value, indent)
        return
    rest = _key_at(lines[i], indent)[1]
    val, comment = split_comment(rest)
    bend = _block_end(lines, i, indent)
    kids = [j for j in range(i + 1, bend) if _content(lines[j])]
    if isinstance(value, dict):
        if val == "" and kids and not lines[kids[0]].lstrip().startswith("- "):
            child = _indent(lines[kids[0]])
            for k, v in value.items():
                _apply(lines, i + 1, _block_end(lines, i, indent), child, str(k), v)
            return
        if val.startswith("{"):
            merged = pvs._merge(pvs.yaml.safe_load(val) or {}, value)
            lines[i:i + 1] = _render(key, merged, indent, comment, lines[i].find(comment) + 1 if comment else 0)
            return
    col = lines[i].find(comment) + 1 if comment else 0
    keep = [lines[j] for j in range(i + 1, bend) if not _content(lines[j]) and lines[j].strip()]
    lines[i:bend] = _render(key, value, indent, comment, col) + keep


def edit_yaml(text: str, answers: Dict[str, Any]) -> str:
    lines = text.splitlines()
    for k, v in answers.items():
        _apply(lines, 0, len(lines), 0, str(k), v)
    return "\n".join(lines) + "\n"


def git(dest: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(dest), *args], capture_output=True, text=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Create a product folder for the workbench.")
    ap.add_argument("slug")
    ap.add_argument("--from", dest="src", help="copy this folder over _template/product (e.g. examples/acme)")
    ap.add_argument("--dest", help="folder that receives <slug>/ (default: the workbench's products/)")
    ap.add_argument("--answers", help="interview answers as JSON, same shape as product.yaml")
    ap.add_argument("--no-git", action="store_true", help="do not git init the product")
    ap.add_argument("--no-link", action="store_true", help="do not run scripts/link-skills.sh")
    a = ap.parse_args()

    check_slug(a.slug)
    home = pvs.workbench()
    dest = (Path(a.dest).expanduser().resolve() if a.dest else home / "products") / a.slug
    if dest.exists():
        fail(f"{dest} already exists. Pick another slug, or edit that product's product.yaml instead")

    template = home / "_template" / "product"
    src = Path(a.src) if a.src else template
    if not src.is_absolute():
        src = (home / src) if (home / src).exists() else src.resolve()
    if not src.is_dir():
        fail(f"template folder not found: {src} (run /video-setup, or pass --from <dir>)")

    answers: Dict[str, Any] = {}
    if a.answers:
        try:
            answers = json.loads(Path(a.answers).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            fail(f"cannot read answers {a.answers}: {e}")
        if not isinstance(answers, dict):
            fail("answers must be a JSON object shaped like product.yaml")

    name_guess = ((answers.get("product") or {}).get("name") or a.slug.replace("-", " ").title())
    yaml_src = next((d / "product.yaml" for d in (src, template) if (d / "product.yaml").exists()), None)
    raw = yaml_src.read_text(encoding="utf-8") if yaml_src else ""
    base = pvs.load_yaml_text(raw)
    fixed: Dict[str, Any] = {"slug": a.slug}
    name_now = str((pvs._merge(base, answers).get("product") or {}).get("name") or "")
    if not name_now or is_placeholder(name_now) or "{{" in name_now:
        fixed["name"] = name_guess
    edits = pvs._merge(answers, {"product": fixed})
    cfg = pvs._merge(base, edits)
    errs = validate(pvs._merge(pvs.DEFAULTS, cfg))
    if errs:
        fail("product.yaml would be invalid:\n  - " + "\n  - ".join(errs))

    dest.parent.mkdir(parents=True, exist_ok=True)
    skip = lambda d, names: [n for n in names if n in SKIP_DIRS or n.endswith(".mp4")  # noqa: E731
                             or (n == "skills" and Path(d).name == ".claude")]
    # the template first, then the --from folder over it: an example without kit/RULES.md still gets one
    for layer in ([template] if template.is_dir() and src.resolve() != template.resolve() else []) + [src]:
        shutil.copytree(layer, dest, ignore=skip, dirs_exist_ok=True)
    name = cfg["product"]["name"]
    substitute(dest, {"PRODUCT_NAME": name, "PRODUCT_SLUG": a.slug, "PVS_HOME": str(home)})
    text = edit_yaml(raw, edits).replace("{{PRODUCT_NAME}}", name).replace("{{PRODUCT_SLUG}}", a.slug) if raw.strip() else ""
    if not text or pvs.load_yaml_text(text) != cfg:
        text = ("# Product config for the workbench. Schema: docs/contracts.md section 2.\n"
                + pvs.yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, width=100))
        if raw.strip():
            print("  note: product.yaml could not be edited in place, written without its comments")
    (dest / "product.yaml").write_text(text, encoding="utf-8")
    if not (dest / ".gitignore").exists():
        (dest / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    if not (dest / "CLAUDE.md").exists():
        (dest / "CLAUDE.md").write_text(CLAUDE_MD.format(name=name, home=home), encoding="utf-8")
    for sub in ("kit", "references", "videos", "deliveries"):
        (dest / sub).mkdir(exist_ok=True)

    notes = []
    link = home / "scripts" / "link-skills.sh"
    if a.no_link:
        notes.append("skills link: skipped (--no-link)")
    elif link.exists():
        r = subprocess.run(["bash", str(link), str(dest)], capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"link-skills.sh failed: {(r.stderr or r.stdout).strip()[-400:]}")
        notes.append("skills link: .claude/skills linked")
    else:
        notes.append("skills link: skipped (scripts/link-skills.sh not found, run /video-setup)")

    if a.no_git:
        notes.append("git: skipped (--no-git)")
    else:
        r = git(dest, "init", "-q")
        if r.returncode != 0:
            fail(f"git init failed: {r.stderr.strip()}")
        git(dest, "add", "-A")
        r = git(dest, "commit", "-q", "-m", f"New product {name}")
        notes.append("git: initialized with a first commit" if r.returncode == 0
                     else "git: initialized, first commit skipped (set git user.name and user.email)")

    print(f"Created {dest}")
    print(f"  product: {name} ({a.slug}), from {src}")
    print(f"  sources: {len(cfg.get('sources') or [])}, cast people: {len((cfg.get('cast') or {}).get('people') or [])}")
    for n in notes:
        print("  " + n)
    todo = placeholders(cfg)
    if todo:
        print(f"  still to fill in product.yaml ({len(todo)}): " + ", ".join(todo[:12]))
    print("Next: fetch sources (source-recon), then build the kit (product-kit).")


if __name__ == "__main__":
    main()
