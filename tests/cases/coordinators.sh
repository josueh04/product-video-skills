# Tests for the user-invoked coordinators: product-new, video-new, video-build, video-review.
# Products are created in $TEST_TMP/products (new_product.py --dest), so products/ of the real
# workbench is never touched. Fast: no network, no render.

_bench() {  # the real workbench; products go to $TEST_TMP/products through new_product.py --dest
  B="$PVS_HOME"
  PRODUCTS="$TEST_TMP/products"
  export GIT_AUTHOR_NAME="Test Runner" GIT_AUTHOR_EMAIL="runner@example.test"
  export GIT_COMMITTER_NAME="Test Runner" GIT_COMMITTER_EMAIL="runner@example.test"
  PY="$PVS_PY"
  ANS="$PVS_HOME/skills/product-new/references/answers.example.json"
}

_np() { "$PY" "$B/skills/product-new/scripts/new_product.py" "$@" --dest "$PRODUCTS"; }

_product() {  # a product named northwind in the bench
  _bench
  _np northwind --answers "$ANS" >/dev/null 2>&1 \
    || fail "new_product.py failed"
  P="$PRODUCTS/northwind"
}

_signable_sheets() {  # fill COVERAGE.md and CLAIMS.md of video $1 so sign.py accepts them
  local v="$P/videos/$1"
  cat > "$v/COVERAGE.md" <<'MD'
| Feature | Must explain on screen? | Chapter | Proof |
|---|---|---|---|
| Plan my day | yes | 2 | Tasks reorder by due time |
| Integrations | no | End | Listed |
MD
  printf '# Claims\n\n## Positioning\n\nNorthwind Orders takes bakery orders.\n\n## Phrases to avoid\n' > "$v/CLAIMS.md"
}

test_new_product_creates_valid_folder() {
  _product
  assert_file "$P/product.yaml"
  assert_file "$P/CLAUDE.md"
  assert_file "$P/.gitignore"
  out="$(cd "$P" && "$PY" -c '
import pvs
c = pvs.load_product()
print(c["product"]["name"], c["product"]["slug"], len(c["sources"]), c["sources"][0]["framework"],
      c["cast"]["people"][0]["name"], c["review"]["reviewer"])')"
  assert_eq "$out" "Northwind Orders northwind 2 react Maya Lindqvist Priya Raman"
  assert_not_contains "$(cat "$P/product.yaml")" "{{PRODUCT_"
  assert_file "$P/.git"
  assert_eq "$(git -C "$P" rev-list --count HEAD)" "1" "one first commit"
  if [ -f "$B/scripts/link-skills.sh" ]; then
    assert_file "$P/.claude/skills"
  else
    echo "link-skills.sh not present yet: link check skipped"
  fi
}

test_new_product_keeps_comments_and_layers_from() {
  _product
  y="$(cat "$P/product.yaml")"
  assert_contains "$y" "# the canonical name, exactly as it must appear on screen" "template comments survive the answers"
  assert_contains "$y" "reviewer: Priya Raman"
  assert_contains "$y" "#  - role: frontend" "the commented sources example survives"
  # a --from folder with only product.yaml: everything else comes from the template
  mkdir -p "$TEST_TMP/bare"
  cp "$PVS_HOME/examples/acme/product.yaml" "$TEST_TMP/bare/"
  _np lean --from "$TEST_TMP/bare" --no-git --no-link >/dev/null || fail "new_product --from failed"
  assert_file "$PRODUCTS/lean/kit/RULES.md"
  assert_file "$PRODUCTS/lean/CLAUDE.md"
  y="$(cat "$PRODUCTS/lean/product.yaml")"
  assert_contains "$y" "# The example product of the Product Video Skills workbench"
  assert_contains "$y" "slug: lean"
  assert_contains "$y" "name: Acme Tasks"
}

test_new_product_refuses_existing_slug() {
  _product
  echo "keep" > "$P/marker.txt"
  out="$(_np northwind --answers "$ANS" 2>&1)" && fail "should refuse"
  assert_contains "$out" "already exists"
  assert_file "$P/marker.txt"
}

test_new_product_refuses_invalid_slugs() {
  _bench
  for s in Bad_Slug x 9lives "has space" skills; do
    out="$(_np "$s" 2>&1)" && fail "should refuse '$s'"
    case "$out" in *invalid*|*reserved*) ;; *) fail "unexpected message for '$s': $out" ;; esac
  done
  assert_no_file "$PRODUCTS/Bad_Slug"
}

test_new_product_refuses_credentials_and_real_contacts() {
  _bench
  echo '{"sources":[{"role":"frontend","url":"https://user:secret@github.com/example/x.git","branch":"main"}]}' > "$TEST_TMP/a1.json"
  out="$(_np credtest --answers "$TEST_TMP/a1.json" 2>&1)" && fail "should refuse credentials"
  assert_contains "$out" "credentials"
  assert_not_contains "$out" "secret"
  echo '{"cast":{"people":[{"name":"A Person","email":"someone@realmail.com","phone":"+1 415 867 5309"}]}}' > "$TEST_TMP/a2.json"
  out="$(_np casttest --answers "$TEST_TMP/a2.json" 2>&1)" && fail "should refuse real contacts"
  assert_contains "$out" "fictional"
  assert_no_file "$PRODUCTS/credtest"
  assert_no_file "$PRODUCTS/casttest"
}

test_new_video_creates_unsigned_brief() {
  _product
  out="$("$PY" "$B/skills/video-new/scripts/new_video.py" "$P" pitch --format pitch --title "Northwind in 90 seconds" 2>&1)" \
    || fail "new_video failed: $out"
  V="$P/videos/pitch"
  assert_file "$V/BRIEF.md"
  assert_file "$V/COVERAGE.md"
  assert_file "$V/CLAIMS.md"
  meta="$("$PY" -c '
import sys, pvs
m = pvs.read_brief(sys.argv[1])
print(m["title"], "|", m["video"], m["format"], m["duration_s"], m["version"], m["reviewer"], "|", repr(m["coverage_signed_by"]), repr(m["claims_signed_by"]), pvs.signed(m))' "$V")"
  assert_eq "$meta" "Northwind in 90 seconds | pitch pitch 90 1 Priya Raman | '' '' False"
  assert_not_contains "$(cat "$V"/*.md)" "{{TITLE}}"
}

test_new_video_tour_format_and_aligned_chapter_tables() {
  _product
  "$PY" "$B/skills/video-new/scripts/new_video.py" "$P" quick --format tour >/dev/null 2>&1 || fail "--format tour refused"
  assert_eq "$("$PY" -c 'import sys,pvs; m=pvs.read_brief(sys.argv[1]); print(m["format"], m["duration_s"])' "$P/videos/quick")" "tour 30"
  grep -q '^## Tour' "$PVS_HOME/skills/script-and-voice/references/script-templates.md" || fail "no Tour script template"
  head="$(grep -m1 '^| t (s) | Chapter |' "$PVS_HOME/_template/video/BRIEF.md")"
  [ -n "$head" ] || fail "no chapter table in _template/video/BRIEF.md"
  grep -qF "$head" "$PVS_HOME/skills/video-new/assets/BRIEF.md" || fail "assets/BRIEF.md chapter columns differ from the template"
  grep -qF "$head" "$PVS_HOME/skills/video-new/references/sheets.md" || fail "sheets.md chapter columns differ from the template"
}

test_new_video_refuses_duplicate_and_bad_id() {
  _product
  "$PY" "$B/skills/video-new/scripts/new_video.py" "$P" pitch >/dev/null 2>&1 || fail "first create failed"
  out="$("$PY" "$B/skills/video-new/scripts/new_video.py" "$P" pitch 2>&1)" && fail "should refuse duplicate"
  assert_contains "$out" "already exists"
  out="$("$PY" "$B/skills/video-new/scripts/new_video.py" "$P" "Bad Id" 2>&1)" && fail "should refuse bad id"
  assert_contains "$out" "invalid video id"
}

test_sign_refuses_empty_sheets_then_signs() {
  _product
  "$PY" "$B/skills/video-new/scripts/new_video.py" "$P" pitch >/dev/null 2>&1 || fail "create failed"
  V="$P/videos/pitch"
  printf '| Feature | Must explain on screen? | Chapter | Proof |\n|---|---|---|---|\n' > "$V/COVERAGE.md"
  out="$("$PY" "$B/skills/video-new/scripts/sign.py" "$V" --coverage "Priya Raman" 2>&1)" && fail "should refuse an empty matrix"
  assert_contains "$out" "no feature marked"
  _signable_sheets pitch
  out="$("$PY" "$B/skills/video-new/scripts/sign.py" "$V" --coverage "Priya Raman" --claims "Priya Raman" 2>&1)" || fail "sign failed: $out"
  assert_contains "$out" "ready to build"
  assert_eq "$("$PY" -c 'import sys,pvs; print(pvs.signed(pvs.read_brief(sys.argv[1])))' "$V")" "True"
}

test_stages_gate_follows_signatures() {
  _product
  "$PY" "$B/skills/video-new/scripts/new_video.py" "$P" pitch >/dev/null 2>&1 || fail "create failed"
  V="$P/videos/pitch"
  out="$("$PY" "$B/skills/video-build/scripts/stages.py" "$V" --require signoff 2>&1)" && fail "unsigned should not pass"
  assert_contains "$out" "| signoff | no |"
  _signable_sheets pitch
  "$PY" "$B/skills/video-new/scripts/sign.py" "$V" --coverage "Priya Raman" --claims "Priya Raman" >/dev/null 2>&1
  out="$("$PY" "$B/skills/video-build/scripts/stages.py" "$V" --require signoff 2>&1)" || fail "signed should pass: $out"
  assert_contains "$out" "| truth | no |"
  "$PY" "$B/skills/video-build/scripts/stages.py" "$V" --json | "$PY" -c 'import json,sys; d=json.load(sys.stdin); assert d["signoff"]["done"] and not d["render"]["done"]'
}

test_feedback_table_sorts_per_video() {
  _product
  for v in pitch tour onboarding; do "$PY" "$B/skills/video-new/scripts/new_video.py" "$P" "$v" >/dev/null 2>&1; done
  cat > "$TEST_TMP/notes.txt" <<'TXT'
something about the colors
pitch: the start is too zoomed in, keep it full page like the tour video at 0:12
Tour:
- at 1:02 the repeat picker is cut off by the edge
- the chapter title flashes
All videos: you never explain that reminders can repeat
TXT
  out="$("$PY" "$B/skills/video-review/scripts/feedback_table.py" "$P" "$TEST_TMP/notes.txt")" || fail "feedback_table failed"
  assert_contains "$out" "## pitch (v1 to v2)"
  assert_contains "$out" "## tour (v1 to v2)"
  assert_contains "$out" "repeat picker is cut off"
  assert_contains "$out" "| 1:02 |"
  assert_contains "$out" "(shared note)"
  assert_contains "$out" "## Unassigned"
  assert_contains "$out" "something about the colors"
  assert_contains "$out" "| 2 | the chapter title flashes |" "heading context keeps tour"
  pitch_part="${out%%## tour*}"
  assert_not_contains "$pitch_part" "repeat picker" "tour note leaked into pitch"
}

test_bump_version_backs_up_and_refuses_unrendered() {
  _product
  "$PY" "$B/skills/video-new/scripts/new_video.py" "$P" pitch >/dev/null 2>&1 || fail "create failed"
  V="$P/videos/pitch"
  mkdir -p "$V/audio" "$V/video/src" "$V/video/renders"
  printf 'id\trole\tspeed\ttext\nN1\tnarrator\t1\tHello.\n' > "$V/audio/lines.tsv"
  echo '{}' > "$V/audio/timings.json"
  echo '<div></div>' > "$V/video/src/template.tpl"
  out="$("$PY" "$B/skills/video-review/scripts/bump_version.py" "$V" 2>&1)" && fail "should refuse without a v1 render"
  assert_contains "$out" "still open"
  echo "fake" > "$V/video/renders/pitch-v1.mp4"
  out="$("$PY" "$B/skills/video-review/scripts/bump_version.py" "$V" --note "too zoomed in" 2>&1)" || fail "bump failed: $out"
  assert_contains "$out" "v1 to v2"
  assert_file "$V/audio/lines-v1.tsv"
  assert_file "$V/audio/timings-v1.json"
  assert_file "$V/video/_v1-src/template.tpl"
  assert_file "$V/video/renders/pitch-v1.mp4"
  assert_eq "$("$PY" -c 'import sys,pvs; print(pvs.read_brief(sys.argv[1])["version"])' "$V")" "2"
  assert_contains "$(cat "$V/BRIEF.md")" '"too zoomed in"'
}

test_coordinator_skills_are_user_invoked() {
  for s in product-new video-new video-build video-review; do
    f="$PVS_HOME/skills/$s/SKILL.md"
    assert_file "$f"
    head -8 "$f" | grep -q '^disable-model-invocation: true' || fail "$s is not user-invoked"
    head -8 "$f" | grep -q '^argument-hint:' || fail "$s has no argument-hint"
    "$PVS_PY" -m json.tool "$PVS_HOME/skills/$s/evals/evals.json" >/dev/null || fail "$s evals.json invalid"
    [ "$(wc -l < "$f")" -lt 500 ] || fail "$s SKILL.md over 500 lines"
  done
}
