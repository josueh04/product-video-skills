"""Flag cast entries in product.yaml that look like real people, numbers or domains.

    bin/pvs-py skills/product-kit/scripts/check_cast.py <product_dir> [--yaml FILE]

Checks `cast:` (company and people), see docs/contracts.md section 2:
- every person has a first name and a surname (agents and bots, role agent, assistant or bot,
  may have one name), and a first name is never used with two different surnames;
- phone numbers are fictional: North American numbers must use the 555 exchange, ideally
  555-0100 to 555-0199 (the only range reserved for fiction; other 555 numbers can be real);
  UK numbers must be in Ofcom's drama ranges (07700 900000 to 900999, 020 7946 0000 to 0999);
  anything else is flagged;
- emails, websites and domains use reserved names only: example.com, example.net,
  example.org, or a .example, .test, .invalid or .localhost domain.
Exits 1 when something must change, 0 when only warnings remain.
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Any, List

import pvs

RESERVED_DOMAINS = ("example.com", "example.net", "example.org")
RESERVED_TLDS = (".example", ".test", ".invalid", ".localhost")
SINGLE_NAME_ROLES = {"agent", "assistant", "bot", "ai", "voice agent"}
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
URLISH = re.compile(r"(?:https?://)?((?:[\w-]+\.)+[a-z]{2,})(?:[/:]\S*)?$", re.I)


def domain_ok(domain: str) -> bool:
    d = domain.lower().rstrip(".")
    return d in RESERVED_DOMAINS or any(d.endswith("." + r) for r in RESERVED_DOMAINS) or d.endswith(RESERVED_TLDS)


def phone_issue(raw: str):
    """(level, message) or None. level is 'error' or 'warn'."""
    digits = re.sub(r"\D", "", raw)
    plus = raw.strip().startswith("+")
    if (plus and digits.startswith("1") and len(digits) == 11) or (not plus and len(digits) == 10) or (not plus and len(digits) == 11 and digits.startswith("1")):
        nanp = digits[-10:]
        exchange, line = nanp[3:6], nanp[6:]
        if exchange != "555":
            return "error", f"{raw}: not a 555 number"
        if not ("0100" <= line <= "0199"):
            return "warn", f"{raw}: 555 but outside 555-0100 to 0199; some 555 numbers are real"
        return None
    if (plus and digits.startswith("44")) or (not plus and digits.startswith("0")):
        uk = "0" + digits[2:] if plus else digits
        if re.fullmatch(r"07700900\d{3}", uk) or re.fullmatch(r"02079460\d{3}", uk):
            return None
        return "error", f"{raw}: not in a fictional range (UK drama numbers: 07700 900000 to 900999)"
    return "error", f"{raw}: cannot confirm it is fictional; use +1 555 01xx"


def walk_strings(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, (str, int)):
        yield path, str(obj)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir", nargs="?", default=".")
    ap.add_argument("--yaml", help="check this YAML file's cast: instead of product.yaml")
    a = ap.parse_args()

    if a.yaml:
        data = pvs.load_yaml(Path(a.yaml))
    else:
        data = pvs.load_yaml(pvs.product_dir(Path(a.product_dir)) / "product.yaml")
    cast = data.get("cast") or {}
    errors: List[str] = []
    warns: List[str] = []
    people = cast.get("people") or []
    if not people:
        warns.append("cast.people is empty: propose a fictional cast for the reviewer to veto")

    firsts = {}
    for i, p in enumerate(people):
        if not isinstance(p, dict):
            errors.append(f"people[{i}]: expected a mapping with role and name")
            continue
        name = str(p.get("name", "")).strip()
        role = str(p.get("role", "")).strip().lower()
        words = name.split()
        if not name:
            errors.append(f"people[{i}] ({role or 'no role'}): no name")
        elif len(words) < 2 and role not in SINGLE_NAME_ROLES:
            errors.append(f"{name} ({role}): missing surname; give every person one full name for all videos")
        if len(words) >= 2:
            first, rest = words[0].lower(), " ".join(words[1:])
            if first in firsts and firsts[first] != rest:
                errors.append(f"{words[0]} has two surnames ({firsts[first]}, {rest}); one surname per person across every video")
            firsts.setdefault(first, rest)

    for path, value in walk_strings(cast):
        key = path.rsplit(".", 1)[-1].split("[")[0].lower()
        for m in EMAIL.finditer(value):
            if not domain_ok(m.group(1)):
                errors.append(f"{path}: {value} uses a real-looking domain; use example.com or a .example/.test domain")
        if key in ("phone", "mobile", "tel", "fax", "whatsapp") or re.fullmatch(r"\+?[\d\s().-]{7,}", value):
            issue = phone_issue(value)
            if issue:
                (errors if issue[0] == "error" else warns).append(f"{path}: {issue[1]}")
        if key in ("domain", "website", "url", "site", "web") and "@" not in value:
            m = URLISH.match(value.strip())
            if m and not domain_ok(m.group(1)):
                errors.append(f"{path}: {value} looks like a real domain; use example.com or a .example/.test domain")

    for w in warns:
        print("  warn: " + w)
    for e in errors:
        print("  FAIL: " + e)
    print(f"cast check: {len(people)} people, {len(errors)} to fix, {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
