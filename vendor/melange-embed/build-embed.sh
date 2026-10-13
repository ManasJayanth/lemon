#!/bin/sh
# Build the vendored melange driver library (jscomp/core at the pinned
# 7.0.1-55 tag) against the private libraries installed by the melange opam
# package. Upstream sources are copied unmodified from the submodule into an
# isolated dune workspace (the submodule tree must stay outside the
# workspace). Only the library stanza of the copied dune file differs from
# upstream: findlib-qualified dependency names and explicit include paths for
# the private .public_cmi directories (hidden include dirs do not satisfy
# module references outside dune's own project).
#
# Environment: MELANGE_LIB = installed lib dir of the melange package,
#              LEMON_EMBED_OUT = directory that receives the objects.
set -eu
cd "$(dirname "$0")"

rm -rf work
mkdir -p work
cp -R melange/jscomp/core work/core
cp melange/dune-project work/dune-project
printf '(env\n (_\n  (env-vars\n   (CPPO_FLAGS -D=MELANGE_RELEASE_BUILD))))\n' > work/dune
cat > work/core/embed_version.ml <<'EOF'
let () = print_endline Melangelib.Melange_version.version
EOF

${PYTHON_CMD:-python3} - <<'PYEOF'
import os
os.chdir("work/core")
dune = open("dune").read()
old_lib = """(library
 (name melangelib)
 (flags :standard -warn-error -58)
 (libraries
  melstd
  melange_compiler_libs
  melange_ffi
  ppxlib.ast
  dune-build-info))"""
new_lib = """(library
 (name melangelib)
 (flags :standard -w -a -warn-error -a
   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melange_compiler_libs/.public_cmi
   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melstd/.public_cmi
   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melange_ffi/.public_cmi
   -I %{env:MELANGE_LIB=/nonexistent}/__private__/pp/.public_cmi
   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melange_wrapper/.public_cmi)
 (modules :standard \\ embed_version)
 (libraries
  melange.__private__.melstd
  melange.__private__.melange_compiler_libs
  melange.__private__.melange_ffi
  ppxlib.ast
  dune-build-info))

(executable
 (name embed_version)
 (modes byte)
 (flags :standard -w -a)
 (modules embed_version)
 (libraries melangelib melange.__private__.melstd))"""
assert old_lib in dune, "upstream core/dune library stanza changed"
open("dune", "w").write(dune.replace(old_lib, new_lib))
PYEOF

cd work
dune build core/melangelib.cma core/embed_version.exe

OUT=${LEMON_EMBED_OUT:?}
rm -rf "$OUT/melangelib" "$OUT/version"
mkdir -p "$OUT/melangelib" "$OUT/version"
cp _build/default/core/.melangelib.objs/byte/*.cmo "$OUT/melangelib/"
cp _build/default/core/.melangelib.objs/byte/*.cmi "$OUT/melangelib/"
cp _build/default/core/.embed_version.eobjs/byte/build_info__Build_info_data.cmo "$OUT/version/" || {
  echo "melange-embed: byte build_info unit missing" >&2; exit 1; }
echo "melange-embed: melangelib built"
