# Tests for examples/acme, the fictional example product: it builds as a draft in a temp folder
# (fast), it stays small and free of renders, voice clips and real names, and with PVS_FULL=1
# the whole chain (voice with say, build, render, QA, delivery) passes.
# The chain itself is scripts/example-chain.sh, the same one setup.sh runs.

test_example_draft_builds_in_temp_dir() {
  local d="$TEST_TMP/run"
  out="$(bash "$PVS_HOME/scripts/example-chain.sh" --draft --keep --dir "$d" 2>&1)" || fail "draft chain failed: $out"
  assert_contains "$out" "draft built"
  assert_file "$d/acme/sources.lock"
  assert_file "$d/acme/videos/tour/video/index.html"
  grep -q 'name="pvs-draft"' "$d/acme/videos/tour/video/index.html" || fail "draft build is not stamped as a draft"
  [ ! -e "$PVS_HOME/examples/acme/sources" ] || fail "the chain wrote into examples/acme"
}

test_example_truth_citations_match_the_frontend() {
  # The tour's TRUTH.md, specs and kit cite frontend@<hash of examples/acme/frontend>. Editing the
  # frontend without re-citing breaks this test: re-run fetch_sources and update the citations.
  local d="$TEST_TMP/acme"
  "$PVS_PY" "$PVS_HOME/skills/product-new/scripts/new_product.py" acme --from examples/acme --dest "$TEST_TMP" --no-git --no-link >/dev/null \
    || fail "new_product --from examples/acme failed"
  "$PVS_PY" "$PVS_HOME/skills/source-recon/scripts/fetch_sources.py" "$d" >/dev/null || fail "fetch_sources failed"
  pin="$("$PVS_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["frontend"]["tree_sha256"][:7])' "$d/sources.lock")"
  out="$("$PVS_PY" "$PVS_HOME/skills/product-truth/scripts/truth_check.py" "$d/videos/tour" 2>&1)" || fail "truth_check failed: $out"
  assert_contains "$out" "0 error(s)"
  grep -q "@$pin" "$PVS_HOME/examples/acme/kit/tokens.css" || fail "kit/tokens.css does not cite frontend@$pin: regenerate it with resolve_tokens.py"
}

test_example_is_small_and_fictional() {
  local e="$PVS_HOME/examples/acme"
  kb="$(du -sk "$e" | awk '{print $1}')"
  [ "$kb" -lt 2048 ] || fail "examples/acme is ${kb} KB, keep it under 2 MB"
  found="$(find "$e" \( -name '*.mp4' -o -name '*.wav' -o -name '*.aiff' -o -name '*.mp3' -o -name index.html -path '*/video/*' -o -name sources -o -name sources.lock \) -print)"
  [ -z "$found" ] || fail "generated files committed in the example: $found"
  if LC_ALL=C grep -rlI $'\xe2\x80\x94' "$e" >/dev/null; then fail "em dash in: $(LC_ALL=C grep -rlI $'\xe2\x80\x94' "$e")"; fi
  out="$("$PVS_PY" "$PVS_HOME/skills/product-kit/scripts/check_cast.py" "$e" 2>&1)" || fail "check_cast: $out"
  out="$("$PVS_PY" "$PVS_HOME/skills/script-and-voice/scripts/check_script.py" "$e/videos/tour" 2>&1)" || fail "check_script: $out"
  grep -q 'coverage_signed_by: Example Reviewer' "$e/videos/tour/BRIEF.md" || fail "the example BRIEF must stay signed by Example Reviewer"
}

test_example_full_chain_passes_qa() {
  if [ "${PVS_FULL:-0}" != 1 ]; then echo "SKIP: set PVS_FULL=1 (voice, render and QA, about 40 s)"; return 0; fi
  command -v say >/dev/null 2>&1 || { echo "SKIP: no macOS say"; return 0; }
  local d="$TEST_TMP/full"
  out="$(bash "$PVS_HOME/scripts/example-chain.sh" --dir "$d" 2>&1)" || fail "full chain failed: $out"
  assert_contains "$out" "qa passed"
  "$PVS_PY" - "$d/acme/videos/tour/qa/REPORT.json" <<'PY' || fail "REPORT.json did not pass"
import json, sys
r = json.load(open(sys.argv[1]))
assert r["passed"] is True and r["draft"] is False, r
assert {c["name"] for c in r["checks"]} >= {"asr", "loudness", "worker_pattern", "black_frames", "banned_terms_visible"}
PY
  assert_file "$d/acme/deliveries/Acme Tasks tour v1.mp4"
}
