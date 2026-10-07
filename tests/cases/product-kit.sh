# Tests for skills/product-kit scripts: check_cast.py, collect_icons.py, collect_logos.py, subset_fonts.py.

_pk_py() { "$PVS_HOME/bin/pvs-py" "$@"; }
_pk_s() { echo "$PVS_HOME/skills/product-kit/scripts/$1"; }

_pk_setup() {
  T="$(mktemp -d)"
  trap 'rm -rf "$T"' EXIT
  P="$T/acme"; mkdir -p "$P"
  cat > "$P/product.yaml" <<'YAML'
product: {name: Acme Tasks, slug: acme}
cast:
  company: {name: Northwind Bakery, city: Portland OR, website: northwind.example}
  people:
    - {role: owner, name: Maya Lindqvist, email: maya@northwind.example}
    - {role: customer, name: Omar Haddad, phone: "+1 503 555 0172"}
    - {role: agent, name: Robin}
YAML
}

test_check_cast_passes_fictional_cast() {
  _pk_setup
  _pk_py "$(_pk_s check_cast.py)" "$P" | grep -q "0 to fix" || return 1
}

test_check_cast_flags_real_looking_entries() {
  _pk_setup
  cat > "$T/bad.yaml" <<'YAML'
cast:
  company: {name: Northwind Bakery, website: https://northwindbakery.com}
  people:
    - {role: owner, name: Maya, email: maya@northwindbakery.com}
    - {role: customer, name: Omar Haddad, phone: "+1 503 867 5309"}
    - {role: lead, name: Omar Price, phone: "(503) 555-1212"}
YAML
  out="$(_pk_py "$(_pk_s check_cast.py)" --yaml "$T/bad.yaml")" && { echo "$out"; return 1; }
  echo "$out" | grep -q "Maya (owner): missing surname" || { echo "$out"; return 1; }
  echo "$out" | grep -q "real-looking domain" || { echo "$out"; return 1; }
  echo "$out" | grep -q "not a 555 number" || { echo "$out"; return 1; }
  echo "$out" | grep -q "outside 555-0100" || { echo "$out"; return 1; }
  echo "$out" | grep -q "two surnames" || { echo "$out"; return 1; }
  echo "$out" | grep -q "website: https://northwindbakery.com looks like a real domain" || { echo "$out"; return 1; }
}

test_collect_icons_copies_and_cites() {
  _pk_setup
  pkg="$T/node_modules/demo-icons"
  mkdir -p "$pkg/svg/outline" "$pkg/svg/solid"
  echo '{"name": "demo-icons", "version": "1.2.3", "license": "MIT"}' > "$pkg/package.json"
  printf '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path id="p1" d="M1 1h22"/></svg>\n' > "$pkg/svg/outline/calendar.svg"
  printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M2 2h20"/></svg>\n' > "$pkg/svg/solid/calendar.svg"
  printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg>\n' > "$pkg/svg/outline/check.svg"
  out="$(_pk_py "$(_pk_s collect_icons.py)" "$P" --package "$pkg/svg" --names calendar,check)" && { echo "ambiguity not caught"; return 1; }
  echo "$out" | grep -q "ambiguous: calendar" || { echo "$out"; return 1; }
  _pk_py "$(_pk_s collect_icons.py)" "$P" --package "$pkg/svg" --names calendar,check --variant outline --clean >/dev/null || return 1
  [ -f "$P/kit/icons/demo-icons-calendar.svg" ] || return 1
  grep -q 'width=' "$P/kit/icons/demo-icons-calendar.svg" && { echo "not cleaned"; return 1; }
  grep -q 'id=' "$P/kit/icons/demo-icons-calendar.svg" && return 1
  grep -q "| demo-icons-calendar.svg | calendar | demo-icons | npm:demo-icons@1.2.3/svg/outline/calendar.svg | MIT |" "$P/kit/icons/icons.md" || { cat "$P/kit/icons/icons.md"; return 1; }
  _pk_py "$(_pk_s collect_icons.py)" "$P" --package "$pkg/svg" --names nope >/dev/null && return 1
  grep -q "check.svg" "$P/kit/icons/icons.md" || return 1
}

test_subset_fonts_writes_woff2_and_css() {
  _pk_setup
  _pk_py - "$T/Demo-Regular.ttf" <<'PY' || return 1
import sys
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
fb = FontBuilder(1000, isTTF=True)
names = [".notdef", "space", "A", "B", "C"]
fb.setupGlyphOrder(names)
fb.setupCharacterMap({0x20: "space", 0x41: "A", 0x42: "B", 0x43: "C"})
def box():
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0)); pen.lineTo((100, 700)); pen.lineTo((500, 700)); pen.lineTo((500, 0)); pen.closePath()
    return pen.glyph()
empty = TTGlyphPen(None).glyph()
fb.setupGlyf({".notdef": box(), "space": empty, "A": box(), "B": box(), "C": box()})
fb.setupHorizontalMetrics({n: (600, 100) for n in names})
fb.setupHorizontalHeader(ascent=800, descent=-200)
fb.setupNameTable({"familyName": "Demo Sans", "styleName": "Regular"})
fb.setupOS2(usWeightClass=400)
fb.setupPost()
fb.save(sys.argv[1])
PY
  _pk_py "$(_pk_s subset_fonts.py)" "$P" "$T/Demo-Regular.ttf" --codepoints U+0020 --text "AB" --source "fixture" --license OFL-1.1 >/dev/null || return 1
  f="$P/kit/fonts/demo-sans-400.woff2"
  [ -f "$f" ] || { ls "$P/kit/fonts"; return 1; }
  _pk_py -c "
from fontTools.ttLib import TTFont
t = TTFont('$f'); cmap = t.getBestCmap()
assert 0x41 in cmap and 0x42 in cmap and 0x43 not in cmap, cmap
assert t.flavor == 'woff2'" || return 1
  grep -q 'font-family: "Demo Sans";' "$P/kit/fonts/fonts.css" || return 1
  grep -q 'font-display: block' "$P/kit/fonts/fonts.css" || return 1
  grep -q "| demo-sans-400.woff2 | Demo Sans | 400 | normal |" "$P/kit/fonts/fonts.md" || { cat "$P/kit/fonts/fonts.md"; return 1; }
  grep -q "| fixture | OFL-1.1 | missing |" "$P/kit/fonts/fonts.md" || { cat "$P/kit/fonts/fonts.md"; return 1; }
  # with a license text next to the font, it travels into kit/fonts
  echo "SIL Open Font License 1.1 (fixture)" > "$T/OFL.txt"
  out="$(_pk_py "$(_pk_s subset_fonts.py)" "$P" "$T/Demo-Regular.ttf" --codepoints U+0020 --text "AB" --source "fixture" --license OFL-1.1)" || return 1
  echo "$out" | grep -q "warning: no license" && { echo "$out"; return 1; }
  [ -f "$P/kit/fonts/OFL.txt" ] || { ls "$P/kit/fonts"; return 1; }
  grep -q "| fixture | OFL-1.1 | OFL.txt |" "$P/kit/fonts/fonts.md" || { cat "$P/kit/fonts/fonts.md"; return 1; }
}

test_subset_fonts_warns_without_license_text() {
  _pk_setup
  mkdir -p "$T/f"
  _pk_py -c "
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
fb = FontBuilder(1000, isTTF=True); fb.setupGlyphOrder(['.notdef', 'A']); fb.setupCharacterMap({0x41: 'A'})
fb.setupGlyf({'.notdef': TTGlyphPen(None).glyph(), 'A': TTGlyphPen(None).glyph()})
fb.setupHorizontalMetrics({'.notdef': (600, 0), 'A': (600, 0)}); fb.setupHorizontalHeader(ascent=800, descent=-200)
fb.setupNameTable({'familyName': 'Lone Sans', 'styleName': 'Regular'}); fb.setupOS2(usWeightClass=400); fb.setupPost()
fb.save('$T/f/Lone.ttf')" || return 1
  out="$(_pk_py "$(_pk_s subset_fonts.py)" "$P" "$T/f/Lone.ttf" --text A)" || { echo "$out"; return 1; }
  echo "$out" | grep -q "warning: no license text found next to Lone.ttf" || { echo "$out"; return 1; }
}

test_collect_logos_lists_copies_and_refuses_urls() {
  _pk_setup
  mkdir -p "$P/sources/frontend/assets" "$P/sources/frontend/public" "$P/sources/frontend/node_modules/x"
  echo '{"frontend": {"path": "../web", "tree_sha256": "abcdef1234567890", "pinned": false}}' > "$P/sources.lock"
  echo '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>' > "$P/sources/frontend/assets/logo.svg"
  echo '<svg xmlns="http://www.w3.org/2000/svg"><circle/></svg>' > "$P/sources/frontend/assets/logo-white.svg"
  printf 'PNG' > "$P/sources/frontend/public/icon-512.png"
  echo '<svg/>' > "$P/sources/frontend/node_modules/x/logo.svg"
  echo '<svg/>' > "$P/sources/frontend/assets/chevron.svg"
  out="$(_pk_py "$(_pk_s collect_logos.py)" "$P")" || { echo "$out"; return 1; }
  echo "$out" | grep -q "3 logo candidate" || { echo "$out"; return 1; }
  echo "$out" | grep -q "frontend/assets/logo-white.svg@abcdef1" || { echo "$out"; return 1; }
  echo "$out" | grep -q "node_modules\|chevron" && { echo "$out"; return 1; }
  _pk_py "$(_pk_s collect_logos.py)" "$P" --light frontend/assets/logo.svg --dark frontend/assets/logo-white.svg \
    --tile frontend/public/icon-512.png >/dev/null || return 1
  [ -f "$P/kit/logos/logo-light.svg" ] && [ -f "$P/kit/logos/logo-dark.svg" ] && [ -f "$P/kit/logos/app-tile.png" ] || { ls "$P/kit/logos"; return 1; }
  grep -q "| app-tile.png | the square app icon | frontend/public/icon-512.png@abcdef1 |" "$P/kit/logos/logos.md" || { cat "$P/kit/logos/logos.md"; return 1; }
  out="$(_pk_py "$(_pk_s collect_logos.py)" "$P" --light https://example.com/logo.svg 2>&1)" && return 1
  echo "$out" | grep -q "is a URL" || { echo "$out"; return 1; }
}
