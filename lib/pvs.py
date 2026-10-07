"""Shared helpers for the workbench scripts.

Find the workbench, find the product and video a path belongs to, and load
product.yaml and BRIEF.md with defaults, so every script reads config the same way.
See docs/contracts.md for the formats.
"""
import copy
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # setup.sh installs PyYAML into .venv
    yaml = None

DEFAULTS: Dict[str, Any] = {
    "product": {
        "name": "", "slug": "", "positioning": "", "never_say": [],
        "names": {}, "pronounce": {}, "banned_terms": [],
    },
    "sources": [],
    "docs": [],
    "app_canvas": {"logical": [1440, 810], "theme": "light", "rem_px": 16},
    "brand": {"accent": "#4F46E5", "font": "Inter", "logo_light": "", "logo_dark": "", "app_tile": ""},
    "cast": {"company": {}, "people": []},
    "voice": {
        "provider": "elevenlabs", "env_key": "ELEVENLABS_API_KEY",
        "roles": {"narrator": {"voice": "", "model": "eleven_multilingual_v2", "say_voice": "Samantha"}},
        "clip_lufs": -18, "mix_lufs": -16,
    },
    "video": {"size": [1920, 1080], "fps": 30, "max_zoom": 1.35, "lang": "en"},
    "review": {"reviewer": "", "report_language": "en", "naming": "{product} {video} v{version}.mp4"},
}


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def workbench() -> Path:
    """The workbench root: PVS_HOME if set, else the folder that holds this lib/."""
    env = os.environ.get("PVS_HOME")
    if env and (Path(env) / "lib" / "pvs.py").exists():
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def _merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        die("PyYAML is missing. Run /video-setup (or bash setup.sh) first.")
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        die(f"{path}: expected a mapping at the top level")
    return data


def find_up(start: Path, name: str) -> Optional[Path]:
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        if (d / name).exists():
            return d
    return None


def product_dir(start: Path = Path.cwd()) -> Path:
    d = find_up(start, "product.yaml")
    if d is None:
        die(f"No product.yaml above {start}. Run /product-new first.")
    return d


def load_product(start: Path = Path.cwd()) -> Dict[str, Any]:
    """product.yaml merged over DEFAULTS, plus '_dir' (the product folder)."""
    d = product_dir(start)
    cfg = _merge(DEFAULTS, load_yaml(d / "product.yaml"))
    cfg["_dir"] = str(d)
    return cfg


def video_dir(start: Path = Path.cwd()) -> Path:
    d = find_up(start, "BRIEF.md")
    if d is None:
        die(f"No BRIEF.md above {start}. Run /video-new first.")
    return d


FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def read_brief(vdir: Path) -> Dict[str, Any]:
    """The BRIEF.md frontmatter as a dict ('' for missing signatures)."""
    text = (Path(vdir) / "BRIEF.md").read_text(encoding="utf-8")
    m = FRONT.match(text)
    meta = load_yaml_text(m.group(1)) if m else {}
    for k in ("coverage_signed_by", "claims_signed_by", "reviewer"):
        meta[k] = (meta.get(k) or "").strip() if isinstance(meta.get(k, ""), str) else str(meta.get(k))
    meta.setdefault("version", 1)
    return meta


def load_yaml_text(text: str) -> Dict[str, Any]:
    if yaml is None:
        die("PyYAML is missing. Run /video-setup (or bash setup.sh) first.")
    data = yaml.safe_load(text) or {}
    return data if isinstance(data, dict) else {}


def signed(meta: Dict[str, Any]) -> bool:
    return bool(meta.get("coverage_signed_by")) and bool(meta.get("claims_signed_by"))


def read_lines_tsv(path: Path):
    """Rows of lines.tsv as dicts with id, role, speed (float) and text."""
    rows = []
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        if parts[0] == "id":
            continue
        if len(parts) < 4:
            die(f"{path}:{n}: expected 4 tab-separated columns (id, role, speed, text)")
        rows.append({"id": parts[0].strip(), "role": parts[1].strip(),
                     "speed": float(parts[2] or 1.0), "text": "\t".join(parts[3:]).strip()})
    return rows


def read_json(path: Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def env_value(key: str) -> Optional[str]:
    """A secret from the environment or PVS_HOME/.env. Callers must never print it."""
    if os.environ.get(key):
        return os.environ[key]
    f = workbench() / ".env"
    if not f.exists():
        return None
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'") or None
    return None


def hyperframes_version() -> str:
    pkg = read_json(workbench() / "package.json", {})
    v = (pkg.get("dependencies") or {}).get("hyperframes") or (pkg.get("devDependencies") or {}).get("hyperframes")
    if not v:
        die("package.json does not pin hyperframes")
    return v.lstrip("^~=")
