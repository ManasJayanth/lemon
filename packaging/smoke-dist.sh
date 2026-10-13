#!/bin/sh
# Smoke-test a Lemon distribution tree IN PLACE: relocate it first so the
# baked development paths cannot apply, then compile and run OCaml and
# Reason for every target, executing the produced applications.
#
# usage: smoke-dist.sh <dist-tree>     (the lemon-<ver>-<os>-<arch> directory)
set -eu
DIST=$(cd "$1" && pwd)
WORK=$(mktemp -d "${TMPDIR:-/tmp}/lemon-smoke.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

# relocate: prove the tree is position independent
MOVED="$WORK/relocated"
cp -R "$DIST" "$MOVED"
LEMON=$MOVED/bin/lemon
[ -f "$LEMON" ] || LEMON=$MOVED/bin/lemon.exe
[ -f "$LEMON" ] || { echo "smoke-dist.sh: no lemon executable in $DIST" >&2; exit 1; }

cd "$MOVED"
mkdir "$WORK/proj" && cd "$WORK/proj"
printf 'let base = 40\n' > base.ml
printf 'let () = Printf.printf "%%d\\n" (Base.base + 2)\n' > app.ml
printf 'print_endline("hello from packaged reason");\n' > greet.re

run_if() { command -v "$1" >/dev/null 2>&1; }

for target in bytecode native; do
  "$LEMON" build --target $target -o out-$target app.ml base.ml >/dev/null
  if [ $target = native ]; then
    ./out-native
  elif run_if ocamlrun; then
    ocamlrun out-bytecode
  fi
  "$LEMON" build --target $target -o g-$target greet.re >/dev/null
  if [ $target = native ]; then
    ./g-native
  elif run_if ocamlrun; then
    ocamlrun g-bytecode
  fi
done

printf 'let () = print_endline "packaged js"\n' > japp.ml
"$LEMON" build --target js --out-dir js-out japp.ml >/dev/null
if run_if node; then
  NODE=$(node -e 'console.log(process.execPath)' 2>/dev/null || echo node)
  "$NODE" js-out/Japp.js
fi

printf '[@react.component]\nlet make = () => <b> {React.string("packaged jsx")} </b>;\n' > comp.re
printf 'print_endline(ReactDOMServer.renderToStaticMarkup(<Comp />));\n' > rmain.re
"$LEMON" build --target js --react --out-dir react-out rmain.re comp.re >/dev/null
if run_if node; then
  NODE=$(node -e 'console.log(process.execPath)' 2>/dev/null || echo node)
  "$NODE" react-out/Rmain.js
fi

echo "smoke-dist.sh: $DIST ok"
