#!/usr/bin/env python3
"""Gate on `hyperframes doctor --json`, read from stdin. Prints one line, exits 1 on a blocking failure.

The raw `ok` is false on any failed check, and some checks always fail here on purpose:
the Version check (the workbench pins an older release than the latest on npm) and the optional
local fallbacks. Those are listed and ignored; every other failed check blocks.
"""
import json
import sys

NON_BLOCKING = {
    "Version": "pinned on purpose",
    "TTS (Kokoro)": "optional",
    "BGM (MusicGen)": "optional",
    "whisper-cpp": "optional",
    "Docker": "only for render --docker",
    "Docker running": "only for render --docker",
    "onnxruntime-node": "installs on first use",
    "@google/genai": "installs on first use",
}

try:
    data = json.load(sys.stdin)
except Exception:
    print("hyperframes doctor printed no JSON. Fix: run npx hyperframes doctor and read its output")
    sys.exit(1)

failed = [c for c in data.get("checks", []) if not c.get("ok")]
blocking = [c for c in failed if c.get("name") not in NON_BLOCKING]
ignored = ["%s (%s)" % (c["name"], NON_BLOCKING[c["name"]]) for c in failed if c.get("name") in NON_BLOCKING]
if data.get("ok") or not blocking:
    msg = "hyperframes doctor: ok"
    if ignored:
        msg += ", ignored: " + ", ".join(ignored)
    print(msg)
    sys.exit(0)
parts = []
for c in blocking:
    fix = c.get("hint") or "see npx hyperframes doctor"
    if c.get("name") == "Chrome":
        fix = "npx hyperframes browser ensure"
    parts.append("%s: %s. Fix: %s" % (c.get("name"), c.get("detail", "failed"), fix))
print("hyperframes doctor: " + "; ".join(parts))
sys.exit(1)
