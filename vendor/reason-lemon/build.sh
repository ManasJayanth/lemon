#!/bin/sh
# Build the pinned upstream Reason tree (unmodified submodule) with dune,
# selecting the reason.opam package, and install its artifacts.
set -eu
cd "$(dirname "$0")/reason"
dune build -p reason @install
mkdir -p "$cur__install/lib" "$cur__install/bin"
cp -RL _build/install/default/lib/. "$cur__install/lib/"
if [ -d _build/install/default/bin ]; then
  cp -RL _build/install/default/bin/. "$cur__install/bin/"
fi
