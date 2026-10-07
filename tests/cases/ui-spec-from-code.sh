# Tests for skills/ui-spec-from-code/scripts/resolve_tokens.py on fixture CSS, SCSS and a Tailwind config.

_ut_resolve() { "$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/ui-spec-from-code/scripts/resolve_tokens.py" "$@"; }

_ut_setup() {
  T="$(mktemp -d)"
  trap 'rm -rf "$T"' EXIT
  S="$T/sources/frontend"
  mkdir -p "$S/src/styles"
  echo "product: {name: Acme Tasks, slug: acme}" > "$T/product.yaml"
  echo '{"frontend": {"path": "../web", "branch": "main", "commit": "1a2b3c4d5e6f7a8b", "app_dir": "src"}}' > "$T/sources.lock"
  cat > "$S/src/styles/_vars.scss" <<'EOF'
// palette
$indigo-600: #4F46E5;
$ink: #111827 !default;
$shadow-color: rgba($ink, .12);
$hover: lighten($indigo-600, 10%);
@mixin btn { $local: 3px; padding: $local; }
.logo { background: url(//cdn.example.com/logo.png); }
EOF
  cat > "$S/src/styles/tokens.css" <<'EOF'
/* base */
:root, :host {
  --surface-0: #ffffff;
  --text: var(--ink-900, #111111);
  --accent: var(--brand);
  --brand: #4f46e5;
  --border: var(--surface-border);
}
html.app-dark {
  --surface-0: #222222;
}
.card { --card-pad: 12px; }
EOF
  printf ':root {\n  --shadow: 0 1px 2px #{$shadow-color};\n}\n' > "$S/src/app.scss"
  cat > "$S/tailwind.config.js" <<'EOF'
module.exports = {
  theme: { extend: { colors: { brand: { DEFAULT: '#4F46E5', 50: '#EEF2FF' } }, borderRadius: { lg: '0.5rem' } } },
}
EOF
}

test_resolve_tokens_resolves_and_cites() {
  _ut_setup
  _ut_resolve "$T" >/dev/null 2>&1 || return 1
  f="$T/kit/tokens.css"
  grep -q -- '--accent: #4f46e5; /\* frontend/src/styles/tokens.css:5@1a2b3c4 via --brand (frontend/src/styles/tokens.css:6@1a2b3c4)' "$f" || { cat "$f"; return 1; }
  grep -q -- '--text: #111111;.*fallback used' "$f" || return 1
  grep -q -- '--border: var(--surface-border);.*UNDEFINED' "$f" || return 1
  grep -q -- '--shadow: 0 1px 2px rgba(17, 24, 39, .12);' "$f" || return 1
  grep -q -- '--scss-hover: lighten(#4F46E5, 10%);.*needs a Sass compile' "$f" || return 1
  grep -q -- '--scss-local' "$f" && { echo "mixin-local variable leaked"; return 1; }
  grep -q -- '--card-pad' "$f" && { echo "component scope leaked"; return 1; }
  grep -q -- '--tw-color-brand-50: #EEF2FF; /\* frontend/tailwind.config.js:2@1a2b3c4 \*/' "$f" || return 1
  grep -q -- '--tw-radius-lg: 0.5rem' "$f" || return 1
  grep -q '^html.app-dark {' "$f" || return 1
}

test_resolve_tokens_theme_selector_merges() {
  _ut_setup
  out="$(_ut_resolve "$T" --theme-selector html.app-dark --stdout 2>/dev/null)" || return 1
  echo "$out" | grep -q -- '--surface-0: #222222; /\* frontend/src/styles/tokens.css:10@1a2b3c4' || { echo "$out"; return 1; }
  echo "$out" | grep -q -- '--surface-0: #ffffff' && return 1
  return 0
}

test_resolve_tokens_needs_lock() {
  _ut_setup
  echo '{}' > "$T/sources.lock"
  _ut_resolve "$T" >/dev/null 2>&1 && return 1
  return 0
}
