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
# No external interpreter is used: the dune patch is a sed script.
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

# Patch the library stanza with awk: findlib-qualified names, explicit
# include paths, module exclusion (inserted before libraries), and an
# executable stanza appended.
awk '
  /^\(library$/ { in_lib = 1 }
  in_lib && /^ \(flags :standard -warn-error -58\)$/ {
    print " (flags :standard -w -a -warn-error -a"
    print "   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melange_compiler_libs/.public_cmi"
    print "   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melstd/.public_cmi"
    print "   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melange_ffi/.public_cmi"
    print "   -I %{env:MELANGE_LIB=/nonexistent}/__private__/pp/.public_cmi"
    print "   -I %{env:MELANGE_LIB=/nonexistent}/__private__/melange_wrapper/.public_cmi)"
    next
  }
  in_lib && /^ \(libraries$/ {
    print " (modules :standard \\ embed_version)"
    print " (libraries"
    next
  }
  in_lib && /^  melange_compiler_libs$/ { print "  melange.__private__.melange_compiler_libs"; next }
  in_lib && /^  melage_ffi$/ { print "  melange.__private__.melange_ffi"; next }
  in_lib && /^  melange_ffi$/ { print "  melange.__private__.melange_ffi"; next }
  in_lib && /^  melstd$/ { print "  melange.__private__.melstd"; next }
  { print }
  /^\)\)$/ { if (in_lib) in_lib = 0 }
' work/core/dune > work/core/dune.tmp && mv work/core/dune.tmp work/core/dune
cat >> work/core/dune <<'STANZA'

(executable
 (name embed_version)
 (modes byte)
 (flags :standard -w -a)
 (modules embed_version)
 (libraries melangelib melange.__private__.melstd))
STANZA

cd work
dune build core/melangelib.cma core/embed_version.exe

OUT=${LEMON_EMBED_OUT:?}
rm -rf "$OUT/melangelib" "$OUT/version"
mkdir -p "$OUT/melangelib" "$OUT/version"
cp _build/default/core/.melangelib.objs/byte/*.cmo "$OUT/melangelib/"
cp _build/default/core/.melangelib.objs/byte/*.cmi "$OUT/melangelib/"
cp _build/default/core/.embed_version.eobjs/byte/build_info__Build_info_data.cmo "$OUT/version/"
echo "melange-embed: melangelib built"
