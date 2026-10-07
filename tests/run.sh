#!/usr/bin/env bash
# Self-check of the workbench. Prints "passed N, failed M" last and exits non-zero on any failure.
#
#   bash tests/run.sh               every tests/cases/*.sh
#   bash tests/run.sh infra voice   only the case files whose name contains one of the words
#   PVS_FULL=1 bash tests/run.sh    also the slow tests (full renders) that check $PVS_FULL
#
# A case file defines functions named test_*. Each one runs in its own bash process that sources
# the file, with the current folder at PVS_HOME and a fresh empty folder in $TEST_TMP (removed
# afterwards, read-only files included). Exit status 0 passes. The helpers below are exported to every test: they print
# what went wrong and exit 1, so a test can call them anywhere.
set -u
PVS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
export PVS_HOME
export PVS_PY="$PVS_HOME/bin/pvs-py"
export PYTHONDONTWRITEBYTECODE=1

fail()            { echo "$*" >&2; exit 1; }
assert_eq()       { [ "$1" = "$2" ] || fail "expected [$2], got [$1]${3:+ ($3)}"; }
assert_contains() { case "$1" in *"$2"*) ;; *) fail "expected to contain [$2]${3:+ ($3)}, got: $1" ;; esac; }
assert_not_contains() { case "$1" in *"$2"*) fail "expected NOT to contain [$2]${3:+ ($3)}, got: $1" ;; esac; }
assert_file()     { [ -e "$1" ] || fail "missing file: $1"; }
assert_no_file()  { [ ! -e "$1" ] || fail "file should not exist: $1"; }
export -f fail assert_eq assert_contains assert_not_contains assert_file assert_no_file

PASS=0; FAILED=0; FAILED_NAMES=""
cases=()
for f in "$PVS_HOME"/tests/cases/*.sh; do
  [ -f "$f" ] || continue
  if [ $# -gt 0 ]; then
    keep=0
    for w in "$@"; do case "$(basename "$f")" in *"$w"*) keep=1 ;; esac; done
    [ "$keep" = 1 ] || continue
  fi
  cases+=("$f")
done

for f in "${cases[@]+"${cases[@]}"}"; do
  echo "$(basename "$f" .sh)"
  fns="$(bash -c 'source "$1" >/dev/null 2>&1; declare -F | awk "{print \$3}" | grep "^test_"' _ "$f")"
  if [ -z "$fns" ]; then
    echo "  FAIL (no test_* functions, or the file does not source cleanly)"
    FAILED=$((FAILED+1)); FAILED_NAMES="$FAILED_NAMES $(basename "$f" .sh):load"
    continue
  fi
  for fn in $fns; do
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/pvs-test.XXXXXX")"
    out="$(cd "$PVS_HOME" && TEST_TMP="$tmp" bash -c 'source "$1"; "$2"' _ "$f" "$fn" 2>&1 </dev/null)"
    rc=$?
    chmod -R u+w "$tmp" 2>/dev/null; rm -rf "$tmp"   # sources/ exports are read-only
    if [ "$rc" = 0 ]; then
      PASS=$((PASS+1)); echo "  ok   $fn"
    else
      FAILED=$((FAILED+1)); FAILED_NAMES="$FAILED_NAMES $(basename "$f" .sh):$fn"
      echo "  FAIL $fn (exit $rc)"
      printf '%s\n' "$out" | tail -15 | sed 's/^/       /'
    fi
  done
done

[ "$FAILED" = 0 ] || echo "failed:$FAILED_NAMES"
echo "passed $PASS, failed $FAILED"
[ "$FAILED" = 0 ]
