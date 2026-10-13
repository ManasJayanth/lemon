#!/bin/sh
# Build reason-react-ppx first, then reason-react (its sources are
# preprocessed with the ppx), and install both trees.
set -eu
cd "$(dirname "$0")/reason-react"
dune build @install
mkdir -p "$cur__install/lib" "$cur__install/bin"
cp -RL _build/install/default/lib/. "$cur__install/lib/"
if [ -d _build/install/default/bin ]; then
  cp -RL _build/install/default/bin/. "$cur__install/bin/"
fi
