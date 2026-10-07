#!/usr/bin/env bash
# PreToolUse guard for the workbench and every product folder (hook matcher:
# Write|Edit|MultiEdit|NotebookEdit|Bash|Read|Grep).
#
# Blocks, with exit code 2 and the reason on stderr (Claude Code shows it to the model):
#   - writes into a product's sources/ (read-only exports pinned in sources.lock) or into vendor/
#   - reading .env or any .env.* except .env.example (the key stays out of the transcript)
#   - `hyperframes upgrade`, `skills update`, and installing or running another hyperframes version
# Reads the hook JSON from stdin with python3 (no jq). If the guard itself fails it lets the
# call through and says so on stderr: the settings deny rules still keep .env out.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export PVS_HOME="${PVS_HOME:-$(cd "$here/../.." && pwd)}"
exec python3 - "$@" 3<&0 <<'PY'
import json, os, re, shlex, sys

def block(reason):
    sys.stderr.write("Blocked by the workbench guard: " + reason + "\n")
    sys.exit(2)

try:
    data = json.load(os.fdopen(3))
except Exception:
    sys.exit(0)

tool = data.get("tool_name") or ""
inp = data.get("tool_input") or {}
cwd = data.get("cwd") or os.getcwd()
home = os.environ.get("PVS_HOME", "")

def pinned():
    try:
        with open(os.path.join(home, "package.json"), encoding="utf-8") as f:
            return (json.load(f).get("dependencies") or {}).get("hyperframes", "").lstrip("^~=")
    except Exception:
        return ""

def absp(p):
    p = os.path.expanduser(str(p))
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    return os.path.normpath(p)

def real(p):
    # Resolve symlinks of the longest existing parent, keep the rest as written.
    head, tail = p, []
    while head and not os.path.exists(head) and head != os.path.dirname(head):
        head, t = os.path.split(head)
        tail.insert(0, t)
    return os.path.join(os.path.realpath(head), *tail) if tail else os.path.realpath(head)

def protected(p):
    """A reason string when p is inside a product's sources/ or the vendor/ folder."""
    for cand in {absp(p), real(absp(p))}:
        if re.search(r"(^|/)products/[^/]+/sources(/|$)", cand):
            return "products/<slug>/sources/ is a read-only export pinned in sources.lock. Change the source repo and run fetch_sources.py --refresh instead."
        if home and (cand == os.path.join(home, "vendor") or cand.startswith(os.path.join(home, "vendor") + os.sep)):
            return "vendor/ is the pinned HyperFrames release. Change the pin in package.json in a pull request instead."
        if re.search(r"(^|/)vendor/hyperframes(/|$)", cand):
            return "vendor/hyperframes is the pinned HyperFrames release and is never edited."
        # A product folder anywhere: the nearest folder with product.yaml, then sources/.
        d = os.path.dirname(cand)
        while d and d != os.path.dirname(d):
            if os.path.isfile(os.path.join(d, "product.yaml")):
                rel = os.path.relpath(cand, d)
                if rel == "sources" or rel.startswith("sources" + os.sep):
                    return "sources/ of this product is a read-only export pinned in sources.lock. Refresh it with fetch_sources.py --refresh."
                break
            d = os.path.dirname(d)
    return None

ENV_RE = re.compile(r"(?:^|[\s/'\"=<>:(])(\.env(?:\.[A-Za-z0-9_.-]+)?)(?=$|[\s'\";|&)<>])")

def env_name_blocked(name):
    base = os.path.basename(str(name))
    return bool(re.fullmatch(r"\.env(\..+)?", base)) and base != ".env.example"

ENV_MSG = ("never read .env: it holds the voice API key. Scripts load it through lib/pvs.py env_value. "
           "To set the key, the user pastes it into .env in their own editor.")

if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
    p = inp.get("file_path") or inp.get("notebook_path") or ""
    if p:
        r = protected(p)
        if r:
            block(r)
    sys.exit(0)

if tool in ("Read", "Grep"):
    p = inp.get("file_path") or inp.get("path") or ""
    if p and env_name_blocked(p):
        block(ENV_MSG)
    sys.exit(0)

if tool != "Bash":
    sys.exit(0)

cmd = inp.get("command") or ""

# 1. Toolchain changes.
if re.search(r"\bhyperframes(@\S+)?\s+(--?\S+\s+)*upgrade\b", cmd):
    block("never run `hyperframes upgrade` here. HyperFrames is pinned in package.json; a version change is a pull request that passes tests/run.sh.")
if re.search(r"\bskills\s+update\b", cmd) or re.search(r"\bskills\s+add\s+heygen-com/hyperframes\b", cmd):
    block("never run `skills update`: the HyperFrames skills come from vendor/hyperframes at the pinned tag (bash setup.sh refreshes them).")
pin = pinned()
for m in re.finditer(r"\bhyperframes@([A-Za-z0-9._-]+)", cmd):
    if pin and m.group(1) != pin:
        block("this workbench pins hyperframes@%s. Use `npx --yes hyperframes@%s ...` or the local bin (npm run check / render)." % (pin, pin))
if re.search(r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|update|up|upgrade)\b[^;&|]*\bhyperframes\b(?!@)", cmd) and "hyperframes@" not in cmd:
    block("do not install or update hyperframes by hand. Run `bash setup.sh`, which installs the version pinned in package.json.")

# 2. Reading .env.
for m in ENV_RE.finditer(cmd):
    name = m.group(1)
    if not env_name_blocked(name):
        continue
    # Allowed: creating it from the example, locking its mode, testing that it exists.
    allowed = (re.search(r"\bcp\s+(\S*/)?\.env\.example\s+\S*\.env\b", cmd)
               or re.search(r"\bchmod\s+[0-7]{3}\s+\S*\.env\b", cmd)
               or re.search(r"(\btest|\[)\s+-[efs]\s+\S*\.env\b", cmd)
               or re.search(r"\bls\b[^;&|]*\.env\b", cmd))
    if not allowed:
        block(ENV_MSG)

# 3. Shell writes into protected folders: redirections, and the destination of common writers.
targets = [m.group(2) for m in re.finditer(r"(>>?|\btee\s+(?:-a\s+)?)\s*(['\"]?[^\s;&|'\"]+)", cmd)]
for seg in re.split(r"&&|\|\||;|\|", cmd):
    try:
        words = shlex.split(seg)
    except ValueError:
        continue
    if not words:
        continue
    verb = os.path.basename(words[0])
    args = [w for w in words[1:] if not w.startswith("-")]
    if verb in ("rm", "rmdir", "touch", "truncate", "chmod", "chown", "mkdir", "unlink", "ln"):
        targets += args
    elif verb in ("cp", "mv", "rsync", "install") and args:
        targets.append(args[-1])
    elif verb in ("sed", "perl") and any(w == "-i" or w.startswith("-i") for w in words[1:]):
        targets += args[1:]
for t in targets:
    t = t.strip("'\"")
    if not t or t.startswith("/dev/"):
        continue
    r = protected(t)
    if r:
        block(r)
sys.exit(0)
PY
