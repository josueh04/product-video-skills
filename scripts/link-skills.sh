#!/usr/bin/env bash
# Link the workbench skills where Claude Code looks for them.
#
#   scripts/link-skills.sh                 link skills/* and vendor/hyperframes/skills/* into .claude/skills/
#   scripts/link-skills.sh <product_dir>   give a product folder the same skills, hooks and settings
#
# Links are relative. Our skills win over a HyperFrames skill with the same name. Dangling links
# this script made (they point into skills/ or vendor/hyperframes/skills/) are removed. A real
# folder or a foreign link in .claude/skills/ is never touched. Safe to run again.
set -euo pipefail

home="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

relpath() { # relpath <target> <from_dir>
  python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$2"
}

# Desired links: name<TAB>absolute target. Vendor first so ours overwrite on a name clash.
desired() {
  local d
  for d in "$home"/vendor/hyperframes/skills/*/ "$home"/skills/*/; do
    [ -f "$d/SKILL.md" ] || continue
    d="${d%/}"
    printf '%s\t%s\n' "$(basename "$d")" "$d"
  done | awk -F'\t' '{t[$1]=$2; if (!($1 in seen)) {order[++n]=$1; seen[$1]=1}} END {for (i=1;i<=n;i++) print order[i] "\t" t[order[i]]}'
}

made_by_us() { # a link whose target points into skills/ or vendor/hyperframes/skills/ of this workbench
  python3 - "$1" "$home" <<'PY'
import os, sys
link, home = sys.argv[1], sys.argv[2]
t = os.readlink(link)
abs_t = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(link)), t))
roots = [os.path.join(home, "skills"), os.path.join(home, "vendor", "hyperframes", "skills")]
sys.exit(0 if any(abs_t.startswith(r + os.sep) for r in roots) else 1)
PY
}

link_into() { # link_into <skills_dir>
  local dir="$1" made=0 kept=0 removed=0 skipped=0 name target rel cur
  mkdir -p "$dir"
  local wanted=" "
  while IFS=$'\t' read -r name target; do
    [ -n "$name" ] || continue
    wanted="$wanted$name "
    rel="$(relpath "$target" "$dir")"
    if [ -L "$dir/$name" ]; then
      cur="$(readlink "$dir/$name")"
      if [ "$cur" = "$rel" ]; then kept=$((kept+1)); continue; fi
      if ! made_by_us "$dir/$name"; then
        echo "  skip   $dir/$name is a link this script did not make" >&2
        skipped=$((skipped+1)); continue
      fi
      rm "$dir/$name"
    elif [ -e "$dir/$name" ]; then
      echo "  skip   $dir/$name is a real folder, left as is" >&2
      skipped=$((skipped+1)); continue
    fi
    ln -s "$rel" "$dir/$name"
    made=$((made+1))
  done < <(desired)
  # Remove dangling links we made, and links we made for skills that no longer exist.
  for l in "$dir"/*; do
    [ -L "$l" ] || continue
    name="$(basename "$l")"
    case "$wanted" in *" $name "*) continue ;; esac
    if made_by_us "$l" && [ ! -e "$l" ]; then rm "$l"; removed=$((removed+1)); fi
  done
  echo "linked $((made+kept)) skills in $dir ($made new, $removed removed, $skipped skipped)"
}

if [ $# -eq 0 ]; then
  link_into "$home/.claude/skills"
  exit 0
fi

product="$(cd "$1" && pwd -P)" || { echo "No such folder: $1" >&2; exit 1; }
[ -f "$product/product.yaml" ] || { echo "$product has no product.yaml" >&2; exit 1; }
mkdir -p "$product/.claude"
link_into "$product/.claude/skills"
# Hooks: one link to the workbench hooks, so settings.json can call $CLAUDE_PROJECT_DIR/.claude/hooks/*.
hooks_rel="$(relpath "$home/.claude/hooks" "$product/.claude")"
if [ -L "$product/.claude/hooks" ] || [ ! -e "$product/.claude/hooks" ]; then
  ln -sfn "$hooks_rel" "$product/.claude/hooks"
else
  echo "  skip   $product/.claude/hooks is a real folder, left as is" >&2
fi
# Claude Code reads project settings from the folder it starts in, so the product needs its own copy.
cp "$home/.claude/settings.json" "$product/.claude/settings.json"
echo "copied settings and linked hooks into $product/.claude"
