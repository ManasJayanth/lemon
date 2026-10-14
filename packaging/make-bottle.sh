#!/bin/sh
# Assemble a Homebrew bottle tarball from a completed distribution tree.
#
# usage: make-bottle.sh <staging-dist-dir> <bottle-tag>
#
# A bottle is a tarball whose root is <name>/<version>/ containing the
# Cellar layout. Run this on the platform the tag describes; the resulting
# file is published on the GitHub release and referenced by Formula/lemon.rb.
set -eu
DIST=$(cd "$1" && pwd)
TAG=$2
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON_CMD:-$(command -v python3 || command -v python)}

VERSION=${LEMON_VERSION:-$($PY -c 'import json; print(json.load(open("'"$ROOT"'/esy.json"))["version"])')}
NAME=$(basename "$DIST")          # lemon-<version>-<platform>-<arch>
WORK=$(mktemp -d "${TMPDIR:-/tmp}/lemon-bottle.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/lemon/$VERSION"
cp -R "$DIST/bin" "$DIST/lib" "$WORK/lemon/$VERSION/"
cp "$ROOT/README.md" "$WORK/lemon/$VERSION/" 2>/dev/null || true

mkdir -p "$ROOT/dist"
( cd "$WORK" && tar czf "$ROOT/dist/lemon--${VERSION}.${TAG}.bottle.tar.gz" lemon )

if command -v shasum >/dev/null 2>&1; then
  ( cd "$ROOT/dist" && shasum -a 256 "lemon--${VERSION}.${TAG}.bottle.tar.gz" )
else
  ( cd "$ROOT/dist" && sha256sum "lemon--${VERSION}.${TAG}.bottle.tar.gz" )
fi
