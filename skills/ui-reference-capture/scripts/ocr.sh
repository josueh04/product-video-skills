#!/usr/bin/env bash
# Run OCR over a folder of frames with Apple Vision. Compiles ocr.swift once into a cache folder.
#
#   ocr.sh <frames_dir> <out.jsonl> [lang,lang]
#
# macOS only (needs the Xcode command line tools for swiftc). On other systems it exits 2 with
# "unsupported": use the frames, contact sheets and manual reading instead.
# Cache: $PVS_CACHE, else ${XDG_CACHE_HOME:-~/.cache}/pvs. The binary name carries a hash of the
# source, so an edited ocr.swift is recompiled.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
[ $# -ge 2 ] || { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
if [ "$(uname -s)" != "Darwin" ]; then
  echo "OCR unsupported on $(uname -s): it uses Apple Vision (macOS only)" >&2
  exit 2
fi
command -v swiftc >/dev/null || { echo "swiftc not found: run xcode-select --install" >&2; exit 1; }
cache="${PVS_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/pvs}"
mkdir -p "$cache"
sum="$(shasum -a 256 "$here/ocr.swift" | cut -c1-12)"
bin="$cache/ocr-$sum"
if [ ! -x "$bin" ]; then
  echo "compiling ocr.swift -> $bin" >&2
  swiftc -O "$here/ocr.swift" -o "$bin.tmp" && mv "$bin.tmp" "$bin"
fi
exec "$bin" "$@"
