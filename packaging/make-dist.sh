#!/bin/sh
# Assemble a relocatable Lemon distribution from a completed esy build.
#
# Layout (the runtime resolves everything relative to the executable,
# following symlinks; LEMON_LIB overrides):
#
#   lemon-<version>-<os>-<arch>/bin/lemon[.exe]
#   lemon-<version>-<os>-<arch>/lib/lemon/compiler_worker.cma
#   lemon-<version>-<os>-<arch>/lib/lemon/melange_worker.cma
#   lemon-<version>-<os>-<arch>/lib/lemon/melange-stdlib/     (cmis + sources)
#   lemon-<version>-<os>-<arch>/lib/lemon/melange-js/         (Js cmis)
#   lemon-<version>-<os>-<arch>/lib/lemon/react-lib/          (ReasonReact cmis)
#   lemon-<version>-<os>-<arch>/lib/lemon/react-npm/          (react runtime)
#   lemon-<version>-<os>-<arch>/lib/lemon/melange-assets/     (JS runtime)
#
# Outputs: dist/staging/<name>/ (the tree) and dist/<name>.zip (Windows)
# or dist/<name>.tar.gz (everything else), plus dist/SHA256SUMS.
#
# Run after `esy build` (e.g. `esy sh packaging/make-dist.sh`).
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PY=${PYTHON_CMD:-$(command -v python3 || command -v python)}
OCAMLC=$(command -v ocamlc)
BUILD=${LEMON_BUILD_DIR:-$ROOT/_esy/default/build}

if [ ! -f "$BUILD/lemon.byte" ] || [ ! -f "$BUILD/compiler_worker.cma" ]; then
  echo "make-dist.sh: build outputs missing under $BUILD; run esy first" >&2
  exit 1
fi

VERSION=$($PY -c 'import json; print(json.load(open("esy.json"))["version"])')
OS=$(uname -s)
case "$OS" in
  Linux) PLATFORM=linux ;;
  Darwin) PLATFORM=macos ;;
  MINGW*|MSYS*|CYGWIN*) PLATFORM=windows ;;
  *) echo "make-dist.sh: unknown OS: $OS" >&2; exit 1 ;;
esac
ARCH=$(uname -m)
case "$ARCH" in
  arm64|aarch64) ARCH2=arm64 ;;
  x86_64|amd64) ARCH2=x86_64 ;;
  *) ARCH2=$ARCH ;;
esac
NAME="lemon-$VERSION-$PLATFORM-$ARCH2"

# locate the melange / reason-react installations (same rules as build.sh)
pkgdir() {
  name=$1; saved=$IFS; IFS=:
  for d in $OCAMLPATH; do
    if [ -e "$d/$name" ]; then IFS=$saved; printf '%s\n' "$d/$name"; return 0; fi
  done
  IFS=$saved
  echo "make-dist.sh: cannot locate package '$name'" >&2
  exit 1
}
MELANGE=$(pkgdir melange)
RR=${reason_react_lemon__lib:-}
if [ -n "$RR" ]; then
  RRLIB=$RR/reason-react/melange
else
  RRLIB=$(pkgdir reason-react)/melange
fi

STAGING=$ROOT/dist/staging/$NAME
rm -rf "$STAGING"
mkdir -p "$STAGING/bin" "$STAGING/lib/lemon"

# Relink the coordinator as a custom-runtime executable (no ocamlrun needed)
# against an install-layout lemon_paths.ml: no baked sandbox paths, so the
# runtime resolves everything next to the installed executable.
DISTWORK=$ROOT/dist/.build-$NAME
rm -rf "$DISTWORK"; mkdir -p "$DISTWORK"
cp "$BUILD"/worker_api.cm[io] "$BUILD"/force_stdlib.cm[io] "$BUILD/lemon.ml" \
  "$ROOT/tools/gen_lemon_paths.py" "$DISTWORK/"
# install layout: regenerate path resolution with no baked sandbox paths, so
# the runtime resolves everything next to the installed executable
( cd "$DISTWORK" && \
  MELANGESTDLIB_VALUE=/nonexistent MELANGEASSETS_VALUE=/nonexistent \
  REACTLIB_VALUE=/nonexistent NPMREACT_VALUE=/nonexistent \
  $PY gen_lemon_paths.py && \
  "$OCAMLC" -c lemon_paths.ml && \
  "$OCAMLC" -custom -I +unix -I +dynlink -linkall \
    unix.cma dynlink.cma worker_api.cmo force_stdlib.cmo lemon_paths.cmo \
    lemon.ml -o lemon )
if [ -f "$DISTWORK/lemon.exe" ]; then
  mv "$DISTWORK/lemon.exe" "$STAGING/bin/lemon.exe"
else
  mv "$DISTWORK/lemon" "$STAGING/bin/lemon"
fi
rm -rf "$DISTWORK"

cp "$BUILD/compiler_worker.cma" "$BUILD/melange_worker.cma" "$STAGING/lib/lemon/"
cp -RL "$MELANGE/melange" "$STAGING/lib/lemon/melange-stdlib"
cp -RL "$MELANGE/js/melange" "$STAGING/lib/lemon/melange-js"
cp -RL "$RRLIB" "$STAGING/lib/lemon/react-lib"
cp -RL "$ROOT/vendor/react-npm/node_modules" "$STAGING/lib/lemon/react-npm"
cp -RL "$BUILD/melange-assets" "$STAGING/lib/lemon/melange-assets"
cp README.md "$STAGING/" 2>/dev/null || true

rm -f "$ROOT/dist/$NAME.zip" "$ROOT/dist/$NAME.tar.gz"
mkdir -p "$ROOT/dist"
if [ "$PLATFORM" = windows ]; then
  $PY packaging/zipdir.py zip "$STAGING" "$ROOT/dist" x >/dev/null && mv "$ROOT/dist/x.zip" "$ROOT/dist/$NAME.zip"
  ART=$NAME.zip
else
  $PY packaging/zipdir.py tgz "$STAGING" "$ROOT/dist" "$NAME" >/dev/null
  ART=$NAME.tar.gz
fi

if command -v shasum >/dev/null 2>&1; then
  SHACMD="shasum -a 256"
elif command -v sha256sum >/dev/null 2>&1; then
  SHACMD="sha256sum"
else
  SHACMD=""
fi
if [ -n "$SHACMD" ]; then
  ( cd "$ROOT/dist" && $SHACMD "$ART" >> SHA256SUMS )
fi

echo "make-dist.sh: dist/$ART ready (staging in dist/staging/$NAME)"
