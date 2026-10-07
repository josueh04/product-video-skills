# Tests for skills/source-recon: fetch_sources.py and changed_since.py on throwaway git repos.
# Sourced by tests/run.sh, which calls each test_* function in a subshell.

_sr_py() { "$PVS_HOME/bin/pvs-py" "$@"; }
_sr_fetch() { _sr_py "$PVS_HOME/skills/source-recon/scripts/fetch_sources.py" "$@"; }
_sr_changed() { _sr_py "$PVS_HOME/skills/source-recon/scripts/changed_since.py" "$@"; }

_sr_git() { git -c user.name=Test -c user.email=test@example.com -c commit.gpgsign=false "$@"; }

# A frontend repo with one commit, a non-git design folder, and a product that points at both.
_sr_setup() {
  T="$TEST_TMP"   # run.sh removes it afterwards, read-only sources/ included
  mkdir -p "$T/web/src" "$T/design" "$T/prod"
  for i in 1 2 3 4 5 6 7 8; do echo ".row$i { padding: ${i}px; }"; done > "$T/web/src/app.css"
  echo "export const title = 'Today';" > "$T/web/src/other.ts"
  _sr_git -C "$T/web" init -q -b main
  _sr_git -C "$T/web" add -A && _sr_git -C "$T/web" commit -q -m one
  C1="$(git -C "$T/web" rev-parse HEAD)"
  echo "brand: indigo" > "$T/design/notes.txt"
  cat > "$T/prod/product.yaml" <<'YAML'
product: {name: Acme Tasks, slug: acme}
sources:
  - {role: frontend, path: ../web, branch: main, app_dir: src, framework: html}
  - {role: design, path: ../design}
YAML
}

_sr_lock() { python3 -c "import json,sys;d=json.load(open('$T/prod/sources.lock'));print(d$1)"; }

test_fetch_writes_lock_and_read_only_export() {
  _sr_setup
  _sr_fetch "$T/prod" >/dev/null || return 1
  [ "$(_sr_lock "['frontend']['commit']")" = "$C1" ] || { echo "lock commit mismatch"; return 1; }
  [ -f "$T/prod/sources/frontend/src/app.css" ] || { echo "export missing"; return 1; }
  [ ! -w "$T/prod/sources/frontend/src/app.css" ] || { echo "export is writable"; return 1; }
  ( echo x > "$T/prod/sources/frontend/src/new.txt" ) 2>/dev/null && { echo "could write into export"; return 1; }
  [ -z "$(git -C "$T/web" status --porcelain)" ] || { echo "user working tree touched"; return 1; }
  [ ! -e "$T/prod/sources/frontend/.git" ] || { echo "export has .git"; return 1; }
  return 0
}

test_non_git_copy_is_pinned_false() {
  _sr_setup
  _sr_fetch "$T/prod" --role design >/dev/null || return 1
  [ "$(_sr_lock "['design']['pinned']")" = "False" ] || return 1
  [ "$(_sr_lock "['design']['tree_sha256']" | wc -c | tr -d ' ')" = "65" ] || { echo "no tree hash"; return 1; }
  [ -f "$T/prod/sources/design/notes.txt" ] || return 1
}

test_refresh_moves_lock_and_changed_since_lists_citing_video() {
  _sr_setup
  _sr_fetch "$T/prod" >/dev/null || return 1
  S1="${C1:0:7}"
  mkdir -p "$T/prod/videos/pitch" "$T/prod/videos/docs"
  printf '| screen | route | components | citation |\n|---|---|---|---|\n| board | /board | rows | frontend/src/app.css:3@%s |\n' "$S1" > "$T/prod/videos/pitch/SOURCES.md"
  printf '| title | frontend/src/other.ts:1@%s |\n' "$S1" > "$T/prod/videos/docs/SOURCES.md"
  sed -i '' 's/padding: 3px/padding: 30px/' "$T/web/src/app.css" 2>/dev/null || sed -i 's/padding: 3px/padding: 30px/' "$T/web/src/app.css"
  _sr_git -C "$T/web" commit -q -am two
  C2="$(git -C "$T/web" rev-parse HEAD)"
  out="$(_sr_changed "$T/prod")" || return 1
  echo "$out" | grep -q "videos/pitch" || { echo "pitch not listed: $out"; return 1; }
  echo "$out" | grep -q "lines changed" || { echo "hunk not detected: $out"; return 1; }
  echo "$out" | grep -q "videos/docs" && { echo "docs listed wrongly: $out"; return 1; }
  # without --refresh the lock stays put
  _sr_fetch "$T/prod" >/dev/null || return 1
  [ "$(_sr_lock "['frontend']['commit']")" = "$C1" ] || { echo "lock moved without --refresh"; return 1; }
  _sr_fetch "$T/prod" --refresh >/dev/null || return 1
  [ "$(_sr_lock "['frontend']['commit']")" = "$C2" ] || { echo "refresh did not pick the new commit"; return 1; }
  grep -q "padding: 30px" "$T/prod/sources/frontend/src/app.css" || return 1
  [ ! -w "$T/prod/sources/frontend/src/app.css" ] || return 1
  out="$(_sr_changed "$T/prod")"
  echo "$out" | grep -q "0 of 2 video" || { echo "$out"; return 1; }
  echo "$out" | grep -q "run changed_since.py before --refresh" || { echo "no lock == head hint: $out"; return 1; }
}

test_stale_local_branch_exports_origin() {
  _sr_setup
  _sr_git clone -q "$T/web" "$T/checkout"
  echo "export const n = 2;" >> "$T/web/src/other.ts"
  _sr_git -C "$T/web" commit -q -am newer
  NEW="$(git -C "$T/web" rev-parse HEAD)"
  git -C "$T/checkout" fetch -q origin
  sed -i '' 's#path: ../web#path: ../checkout#' "$T/prod/product.yaml" 2>/dev/null || sed -i 's#path: ../web#path: ../checkout#' "$T/prod/product.yaml"
  out="$(_sr_fetch "$T/prod" --role frontend)" || return 1
  [ "$(_sr_lock "['frontend']['commit']")" = "$NEW" ] || { echo "did not export origin/main"; return 1; }
  echo "$out" | grep -q "behind origin/main" || { echo "no stale warning: $out"; return 1; }
  [ "$(git -C "$T/checkout" rev-parse main)" = "$C1" ] || { echo "user branch moved"; return 1; }
}

test_url_source_shallow_clone() {
  _sr_setup
  cat > "$T/prod/product.yaml" <<YAML
product: {name: Acme Tasks, slug: acme}
sources:
  - {role: frontend, url: "file://$T/web", branch: main, app_dir: src}
YAML
  _sr_fetch "$T/prod" >/dev/null || return 1
  [ "$(_sr_lock "['frontend']['commit']")" = "$C1" ] || return 1
  [ "$(_sr_lock "['frontend']['url']")" = "file://$T/web" ] || return 1
  [ -f "$T/prod/sources/frontend/src/app.css" ] || return 1
}

test_missing_export_is_restored_at_locked_commit() {
  _sr_setup
  _sr_fetch "$T/prod" --role frontend >/dev/null || return 1
  echo "// later" >> "$T/web/src/other.ts"; _sr_git -C "$T/web" commit -q -am later
  chmod -R u+w "$T/prod/sources"; rm -rf "$T/prod/sources/frontend"
  _sr_fetch "$T/prod" --role frontend | grep -q restored || return 1
  [ "$(_sr_lock "['frontend']['commit']")" = "$C1" ] || return 1
  grep -q later "$T/prod/sources/frontend/src/other.ts" && return 1
  return 0
}
