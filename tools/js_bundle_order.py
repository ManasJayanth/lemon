#!/usr/bin/env python3
"""Post-process tools/bundle_order.py output for the Melange worker plugin:
reorder archives by an explicit provider-before-consumer priority (the unit
toposorter cannot see through cma-internal unit order)."""
import sys

PRIORITY = [
    "/compiler-libs/ocamlcommon.cma", "ocaml_shadow.cma", "sexplib0.cma",
    "ppx_derivers.cma", "astlib.cma", "ppxlib_ast.cma", "ppxlib_print_diff.cma",
    "stdppx.cma", "ppxlib_traverse_builtins.cma", "/ppxlib/ppxlib.cma",
    "menhirLib.cma", "reason_easy_format.cma", "reason_omp.cma", "/reason/reason.cma",
    "js_parser.cma", "/pp/pp.cma", "melange_wrapper.cma", "melstd.cma",
    "melange_compiler_libs.cma", "melange_ffi.cma",
    "/dune-build-info/build_info.cma",
    "melange_ppx.cma", "reason_react_ppx.cma",
]


def rank(t):
    for i, suffix in enumerate(PRIORITY):
        if t.endswith(suffix):
            return i
    return len(PRIORITY)


def main():
    toks = sys.stdin.read().split()
    bid = [t for t in toks if "Build_info_data" in t]
    rest = [t for t in toks if "Build_info_data" not in t]
    out = []
    for t in rest:
        if t.endswith("/dune-build-info/build_info.cma") and bid:
            out += bid
        out.append(t)
    out.sort(key=rank)
    # the generated build_info data unit must precede its consumer archive
    if bid:
        out = [t for t in out if t not in bid]
        i = next(i for i, t in enumerate(out) if t.endswith("/dune-build-info/build_info.cma"))
        out = out[:i] + bid + out[i:]
    print(" ".join(out))


if __name__ == "__main__":
    main()
