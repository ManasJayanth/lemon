#!/bin/sh
# Validate the Homebrew packaging end-to-end WITHOUT a published release:
# build the distribution + bottle, install a local tap by placement with a
# file:// formula, pour the bottle through `brew install`, and run the
# installed `lemon`.
#
# usage (from the repository root, inside the esy sandbox):
#   sh packaging/homebrew/local-test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

PY=${PYTHON_CMD:-$(command -v python3 || command -v python)}
VERSION=$($PY -c 'import json; print(json.load(open("esy.json"))["version"])')

# 1. distribution + bottle for THIS machine
sh packaging/make-dist.sh >/dev/null
PLATFORM=$(uname -s)
case "$PLATFORM" in
  Darwin) ;;
  *) echo "local-test.sh: bottles are a macOS artifact; nothing to test here" ;;
esac
STAGING=$(echo dist/staging/lemon-$VERSION-macos-*)
TAG=$(brew ruby -e 'print Hardware::CPU.intel? ? MacOS.version.to_sym.to_s : "arm64_" + MacOS.version.to_sym.to_s')
sh packaging/make-bottle.sh "$STAGING" "$TAG" >/dev/null
# brew derives the local bottle filename from root_url with a single dash
ln -sf "lemon--$VERSION.$TAG.bottle.tar.gz" "dist/lemon-$VERSION.$TAG.bottle.tar.gz"

# 2. local tap with a file:// formula (source tarball must exist for brew)
if [ ! -f "dist/lemon-source-$VERSION.tar.gz" ]; then
  $PY packaging/make-src-dist.py "$ROOT" dist >/dev/null
fi
$PY packaging/homebrew/local-formula.py /tmp/lemon-local-formula.rb "$ROOT" >/dev/null
TAPDEST="$(brew --repository lemon/lemon)"
rm -rf "$(dirname "$TAPDEST")"
mkdir -p "$TAPDEST/Formula"
cp /tmp/lemon-local-formula.rb "$TAPDEST/Formula/lemon.rb"

# 3. pour through brew
export HOMEBREW_NO_INSTALL_CLEANUP=1
export HOMEBREW_NO_AUTO_UPDATE=1
brew install --force lemon/lemon/lemon

# 4. smoke-test the installed executable (js + react need node; native needs
#    an OCaml toolchain; run what this environment provides)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/lemon-brew-smoke.XXXXXX")
cd "$TMP"
printf 'print_endline("brewed lemon");\n' > hello.re
lemon build --target js --react --out-dir js-out hello.re
NODE=$(node -e 'console.log(process.execPath)' 2>/dev/null || echo node)
"$NODE" js-out/Hello.js
echo "local-test.sh: brew install poured and ran lemon $VERSION ($TAG)"
