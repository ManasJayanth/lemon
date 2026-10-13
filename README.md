# Lemon

Lemon is a build system for OCaml and Reason. The current implementation builds
OCaml `.ml` and `.mli` files; embedded Reason parsing is the next integration.

Install and build with `esy`. Build an executable with:

```sh
esy ocamlrun ./_esy/default/build/lemon.byte build -j 4 -o hello.byte examples/hello.ml
esy ocamlrun ./hello.byte
```

Bytecode is the default. Lemon loads a private copy of the unmodified OCaml
compiler libraries for each worker domain. Compiler values stay inside their
worker; workers exchange artifact paths and text diagnostics. Libraries are
loaded sequentially before compilation starts, and linking is serialized.
The coordinator has no compiler-library dependency. A fixed worker pool avoids
continually loading libraries, which OCaml cannot unload.

Pass all source files, in any order. Lemon discovers module dependencies and
compiles independent files concurrently. Include explicit `.mli` files when
present. Modules must have unique names; dependencies outside the supplied
files are currently limited to the standard library. Builds use a fresh
`.lemon` directory and are not yet incremental.

For native output, add `--native`:

```sh
esy ocamlrun ./_esy/default/build/lemon.byte build --native -j 4 -o hello.native examples/hello.ml
```

Native jobs run stock `ocamlopt` in separate processes. Both modes build without
running the resulting program. A failed build preserves any existing output.
The original `lemon.byte SOURCE.ml OUTPUT.byte` invocation remains supported.

Run the end-to-end checks with `esy python tests/test_build.py`. GitHub Actions
runs these checks on Linux, macOS ARM/Intel, and Windows. The checks execute
bytecode and native programs, exercise interfaces and parallel dependency
scheduling, and verify failed builds do not replace successful output.


## Reason, JavaScript, and React

Lemon accepts `.ml/.mli/.re/.rei` sources for every target. Reason is parsed
by an embedded copy of the pinned Reason parser (no `refmt`, no `-pp`); for
bytecode and native the parse trees are written as normalized binary AST
files that the stock compiler pipeline consumes, with diagnostics pointing
at the original sources.

`--target js` compiles through an embedded private copy of the pinned
Melange driver in one process (no `melc` subprocesses) and publishes an ES
module directory guarded by an ownership marker, a sibling lock, staging,
and backup/rollback. Add `--react` to run the embedded React JSX transform
in-process and bundle the pinned react/react-dom runtimes into the output.

```sh
esy ocamlrun ./_esy/default/build/lemon.byte build --target js --react \
  --out-dir js-out Main.re
node js-out/Main.js
```

`examples/react-counter` is a Vite application built this way; see the
browser scenarios in `tests/`.

The full end-to-end catalog lives in `tests/test_build.py` (see
`docs/compatibility.md` for the pinned toolchain and the embedding
recipes). Every scenario compiles and executes a real artifact.
