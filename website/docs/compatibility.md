---
title: Compatibility
sidebar_position: 10
---


Locked revisions and the exact embedding recipes this build relies on.
Every item below was verified with a runnable fixture during the investigation
phase. Re-verify with the same commands after any pin bump.

## Toolchain

| Component | Pin | Notes |
|---|---|---|
| OCaml | 5.5.1 (`ocaml: 5.5.1000` in esy) | stock, unchanged |
| Reason | `reasonml/reason@19bad260aff7a124aaec54797642cfa4a6aaaae0` | parse + AST conversion in-process |
| Melange | `melange@7.0.1-55` (opam release tarball; commit `08cd3ca8`) | includes vendored `melange-compiler-libs` submodule |
| reason-react | `0.17.0` (ppx + runtime) | JSX ppx v2 API (`Driver.V2.register_transformation "reactjs"`) |
| ppxlib | 0.39.0 (solver) | provides `Driver.map_structure` for in-process transforms |

## Reason (embedded parsing)

Entry points from the `reason` findlib package:

```ocaml
Reason_toolchain.setup_lexbuf ~use_stdin:false file
Reason_toolchain.RE.implementation_with_comments lexbuf  (* .re -> Parsetree.structure *)
Reason_toolchain.RE.interface_with_comments lexbuf        (* .rei -> Parsetree.signature *)
```

Compiler-grade AST (what refmt feeds the compiler) additionally applies
`Reason_syntax_util.remove_stylistic_attrs_mapper` and
`Reason_syntax_util.backport_letopt_mapper` (see `reason_implementation_printer.ml`,
`Binary` branch, in the pinned tree).

Normalized binary AST files for the stock pipeline are written as
`magic ^ input_name ^ ast` (three marshalled values; this is the format
`ocamlc`/`ocamlopt` accept for `.ml`/`.mli` files — see `Pparse` in the
compiler and `Ml_binary.write_ast` in melange). Locations inside the AST
reference the original `.re`/`.rei` file, so diagnostics point at the real
source.

No `refmt` execution, no `-pp`, no external PPX processes: the reason library
is linked into the worker plugin.

## Melange (in-process JS compilation)

The opam package installs the driver's libraries as *private* findlib
packages under `melange.__private__.*`: `melange_compiler_libs` (fork of the
compiler middle-end), `melstd`, `melange_ffi`, `melange_wrapper`, `pp`.
`melangelib` (jscomp/core: `Js_implementation`, `Js_packages_state`, ...) is
NOT installed; we rebuild it from the unmodified `jscomp/core` sources
vendored at the pinned tag, against the installed private packages.

Dune stanza for the vendored copy (only the `(libraries ...)` names and the
`-I` flags differ from upstream `jscomp/core/dune`):

```
(library
 (name melangelib)
 (flags :standard -warn-error -a
   -I <esy>/melange/__private__/melange_compiler_libs/.public_cmi
   -I <esy>/melange/__private__/melstd/.public_cmi
   -I <esy>/melange/__private__/melange_ffi/.public_cmi
   -I <esy>/melange/__private__/pp/.public_cmi
   -I <esy>/melange/__private__/melange_wrapper/.public_cmi)
 (libraries
  melange.__private__.melstd
  melange.__private__.melange_compiler_libs
  melange.__private__.melange_ffi
  ppxlib.ast
  dune-build-info))
```

The explicit `-I` (not `-H`) is required: hidden include dirs do not satisfy
module references outside dune's own project. The project env must define
`CPPO_FLAGS` (upstream root dune sets `-D=MELANGE_RELEASE_BUILD`).

Compilation driver call (in-process):

```ocaml
Js_packages_state.set_output_info ~suffix:(Js_suffix.of_string ".js") Module_system.ESM;
Clflags.include_dirs := [...];   (* MELANGELIB-style stdlib dir is added via env MELANGELIB *)
Js_implementation.implementation ~parser ppf source_file
```

`parser` returns our already-parsed (and, for React, already-JSX-rewritten)
AST. `Clflags.all_ppx` stays empty, so `Cmd_ppx_apply` is the identity and
no ppx subprocess is spawned.

The JS runtime assets (`melange/*.js`, `melange.js/*`, `melange.belt/*`) are
not shipped in the opam install; they are produced once at Lemon build time
by running the embedded compiler over the runtime/stdlib sources installed at
`$ESY_LIB/melange/melange` and `$ESY_LIB/melange/js/melange`.

## React JSX (embedded transform)

`reason-react-ppx` 0.17.0 registers `Driver.V2.register_transformation
"reactjs"` and leaves `jsxMapper` exported (no `.mli`). Two supported ways to
apply it in-process:

1. link `reason_react_ppx` into the plugin and call
   `Ppxlib.Driver.map_structure` / `map_signature` (ppxlib >= 0.33), or
2. invoke `Reason_react_ppx.jsxMapper#structure ctxt ast` directly with a
   fresh `Expansion_context`.

We use (1): `Driver.map_structure` runs all registered transformations with
proper contexts and cookies.

## Plugin bundling and coexistence (verified fixture)

Two plugins, each a single `.cma`:

- **bytecode worker**: stock `ocamlcommon.cma ocamlbytecomp.cma` + reason +
  ppxlib + worker module.
- **melange worker**: stock `ocamlcommon.cma` (unpacked units; the fork links
  against the same identity through wrapper aliases) + menhirLib + ppxlib +
  private melange libraries + vendored `melangelib` + reason + reason-react-ppx
  + worker module.

Build rules discovered by experiment:

- `ocamlc -a` rejects non-topological file orders. Order inputs with an
  `ocamlobjinfo`-based toposort of unit `Requires` lists
  (tools/bundle_order.py).
- Use `ocamlc -nostdlib -a -linkall ...`: with the implicit stdlib loaded,
  `-a` silently drops stdlib units from the bundle. Even with `-nostdlib`,
  `stdlib.cma` cannot be repacked into a plugin; instead the main executable
  force-links every stdlib unit (generated `force_stdlib.ml`, one
  first-class-module reference per unit) so dynlinked plugins can reference
  any stdlib unit.
- `melangelib`'s `git_commit.ml` needs dune's generated
  `build_info__Build_info_data` unit; the plugin bundles the one generated by
  our dune project.
- Private loads of the two plugins (overlapping stock unit names included)
  coexist in one process, in one domain, repeatedly, and across domains
  (fixture: `DYNLINK-COEXIST-OK` matrix). Dynlink loads are serialized with a
  mutex; Lemon loads all worker plugins sequentially before spawning compute
  domains, which satisfies this.

## Verification commands (summary)

- `esy` builds the pinned toolchain; `esy dune build src/melangelib.cma`
  (vendored copy) succeeds against the installed private packages.
- In-process compile of `let () = print_endline "hello from melange"` through
  the embedded driver emits a working `hello.js` (ESM).
- The two-plugin dynlink fixture loads 2x per domain over 3 domains and
  reports both plugin identities.
