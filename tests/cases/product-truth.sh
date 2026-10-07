# Tests for skills/product-truth/scripts/truth_check.py on a fixture product.

_pt_check() { "$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/product-truth/scripts/truth_check.py" "$@"; }

_pt_setup() {
  T="$(mktemp -d)"
  trap 'rm -rf "$T"' EXIT
  P="$T/acme"; V="$P/videos/pitch"
  mkdir -p "$P/sources/frontend/src" "$V/audio"
  echo "product: {name: Acme Tasks, slug: acme}" > "$P/product.yaml"
  for i in 1 2 3 4 5 6 7 8 9 10; do echo "line $i"; done > "$P/sources/frontend/src/plan.ts"
  echo '{"frontend": {"path": "../web", "branch": "main", "commit": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b", "fetched_at": "2026-01-01T00:00:00Z"}}' > "$P/sources.lock"
  printf 'id\trole\tspeed\ttext\nN1\tnarrator\t1.0\tAcme Tasks plans your day.\nN2\tnarrator\t1.0\tOverdue tasks move to tomorrow.\n' > "$V/audio/lines.tsv"
  cat > "$V/TRUTH.md" <<'MD'
# Truth: pitch

| id | sentence | source | visibility | verdict | notes |
|---|---|---|---|---|---|
| N1 | Acme Tasks plans your day. | frontend/src/plan.ts:3@1a2b3c4 | ui | backed | |
| N2 | Overdue tasks move to tomorrow. | frontend/src/plan.ts:5-9@1a2b3c4; https://docs.example.com/rollover | backend | backed | |
| screen:board | Board with three tasks | frontend/src/plan.ts:1@1a2b3c4 | ui | backed | |
| screen:call | Phone call | (designed) | mock | mock | |
MD
}

_pt_sub() { sed -i '' "$1" "$V/TRUTH.md" 2>/dev/null || sed -i "$1" "$V/TRUTH.md"; }

test_truth_check_passes_on_backed_video() {
  _pt_setup
  _pt_check "$V" | grep -q "0 error" || return 1
}

test_truth_check_fails_on_stale_sha() {
  _pt_setup
  _pt_sub 's/plan.ts:3@1a2b3c4/plan.ts:3@9999999/'
  out="$(_pt_check "$V")" && return 1
  echo "$out" | grep -q "locked at 1a2b3c4" || { echo "$out"; return 1; }
}

test_truth_check_fails_on_line_out_of_range_and_missing_file() {
  _pt_setup
  _pt_sub 's/plan.ts:5-9@/plan.ts:5-90@/; s#src/plan.ts:1@#src/nope.ts:1@#'
  out="$(_pt_check "$V")" && return 1
  echo "$out" | grep -q "out of range" || { echo "$out"; return 1; }
  echo "$out" | grep -q "not in sources/frontend" || { echo "$out"; return 1; }
}

test_truth_check_fails_on_changed_line_missing_row_and_cut() {
  _pt_setup
  printf 'N3\tnarrator\t1.0\tIt also books rooms.\n' >> "$V/audio/lines.tsv"
  _pt_sub 's/| Acme Tasks plans your day. |/| Acme Tasks plans your week. |/; s/| backend | backed |/| backend | cut |/'
  out="$(_pt_check "$V")" && return 1
  echo "$out" | grep -q "N3: line in lines.tsv has no row" || { echo "$out"; return 1; }
  echo "$out" | grep -q "N1: the line changed" || { echo "$out"; return 1; }
  echo "$out" | grep -q "N2: verdict cut" || { echo "$out"; return 1; }
}

test_truth_check_fails_without_citation() {
  _pt_setup
  _pt_sub 's#| frontend/src/plan.ts:3@1a2b3c4 | ui#| the team said so | ui#'
  out="$(_pt_check "$V")" && return 1
  echo "$out" | grep -q "N1: no citation" || { echo "$out"; return 1; }
}
