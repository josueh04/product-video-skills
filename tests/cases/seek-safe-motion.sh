# Tests for skills/seek-safe-motion/scripts/lint_motion.py. Static only, no render.

_ssm_lint() { "$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/seek-safe-motion/scripts/lint_motion.py" "$@"; }

# A video/ folder whose template holds the given script body. Prints the folder.
_ssm_video() {
  local d="${TEST_TMP:-$(mktemp -d)}/v-$RANDOM/video"
  mkdir -p "$d/src"
  {
    echo '<!doctype html><html><body><div data-composition-id="main" data-duration="5"><h1 id="t">Acme Tasks</h1></div>'
    echo '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
    echo '<script>'
    echo 'const tl = gsap.timeline({ paused: true });'
    cat
    echo 'window.__timelines["main"] = tl;'
    echo '</script></body></html>'
  } > "$d/src/template.tpl"
  echo "$d"
}

test_lint_flags_fromvars_missing_in_tovars() {
  local d out
  # the opening-title bug: opacity only in fromVars, so one worker drops the title
  d="$(printf '%s\n' 'tl.fromTo("#t", { yPercent: 110, opacity: 1 }, { yPercent: 0, duration: 0.75, immediateRender: false }, 0.5);' | _ssm_video)"
  out="$(_ssm_lint "$d")" && return 1
  assert_contains "$out" "SS001"
  assert_contains "$out" "opacity"
}

test_lint_passes_good_fromto() {
  local d out
  d="$(printf '%s\n' \
    'tl.fromTo("#t", { yPercent: 110, opacity: 1 }, { yPercent: 0, opacity: 1, duration: 0.75, ease: "expo.out", immediateRender: false }, 0.5);' \
    'tl.set("#t", { display: "none" }, 4.0);' \
    'function rand(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }' \
    '// a comment that mentions Math.random() is fine' \
    | _ssm_video)"
  out="$(_ssm_lint "$d")" || { echo "$out"; return 1; }
  assert_contains "$out" "0 error(s), 0 warning(s)"
}

test_lint_flags_nondeterminism_display_and_play() {
  local d out
  d="$(printf '%s\n' \
    'const jitter = Math.random() * 4;' \
    'tl.to("#t", { display: "block", duration: 0.3 }, 1);' \
    'tl.play();' \
    | _ssm_video)"
  out="$(_ssm_lint "$d")" && return 1
  assert_contains "$out" "SS006"
  assert_contains "$out" "SS005"
  assert_contains "$out" "SS007"
}

test_lint_warnings_and_strict() {
  local d out
  d="$(printf '%s\n' \
    'tl.fromTo("#t", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 2);' \
    'tl.to("#t", { left: 40, duration: 0.3 }, 3);' \
    | _ssm_video)"
  out="$(_ssm_lint "$d")" || return 1
  assert_contains "$out" "SS003"
  assert_contains "$out" "SS009"
  ! _ssm_lint "$d" --strict >/dev/null
}

test_lint_unregistered_timeline() {
  local d out
  d="$(printf '%s\n' 'tl.to("#t", { x: 10, duration: 1 }, 0);' | _ssm_video)"
  perl -pi -e 's/^window\.__timelines.*$//' "$d/src/template.tpl"
  out="$(_ssm_lint "$d")" && return 1
  assert_contains "$out" "SS012"
}
