# Known limitations

Honest boundaries of the current implementation. Items marked **by design**
are the non-goals the plan fixed upfront; the rest are real limitations with
their symptom, cause, and the guard that fails loudly if they drift.

## Scope (by design, per the plan)

- **No incremental builds.** Every build uses a fresh `.lemon/build-<pid>-<n>`
  directory and is fully recompiled. Nothing caches across invocations.
- **No relative-path imports / general package resolution.** Module
  dependencies must resolve within the supplied source files plus the
  standard library (and, for `--react`, the pinned ReasonReact interfaces).
  No findlib/opam package resolution happens inside Lemon.
- **No watch mode.**
- **No Lemon-managed bundler.** JavaScript output is plain ES modules;
  bundling/minification is the application's business (the example uses
  Vite).
- **No unit tests.** The catalog is end-to-end only, again per the plan.

## Reason and the normalized-AST path

- **Reason IDE error recovery is force-disabled** (`Reason_config.recoverable
  := false`, its default). That is required for builds to fail on syntax
  errors; it also means a `.re`/`.rei` file that Reason's recovering parser
  could patch in an editor context will be rejected here. Newline-separated
  signature items, however, are *legal* Reason grammar (I11 originally
  assumed otherwise); fixture authors must use genuinely malformed syntax
  (e.g. an unclosed delimiter) to test parse failures.
- **A module cannot render its own component in the same file**
  (`<MyModule />` inside `MyModule.re` is `Unbound module MyModule`). This
  is stock module semantics (a unit cannot reference itself during its own
  type-checking), not a Lemon bug; fixtures keep the render entry in a
  separate `Main.re`.
- **Version pinning is enforced at compile time.** The reason findlib
  wrapper's parsetree is 5.02-shaped while `Versions.OCaml_current` in this
  resolution is 5.05; `compiler_worker.ml` and `melange_worker.ml` contain
  `Fun.id`-style pin checks and explicit `Convert(502)(505)`/`Convert(505)(502)`
  bridges. If any pin drifts, the worker **fails to build** rather than
  silently miscompiling — upgrading ppxlib/reason/ocaml requires revisiting
  those two files.
- **Normalized binary AST files are a private format contract.** Lemon writes
  `magic ^ input_name ^ tree` files that `ocamlc`/`ocamlopt` accept for
  `.ml/.mli`. This matches stock `Pparse` behavior at the pinned compiler
  version but is not a stable interface across OCaml releases.

## JavaScript backend

- **Runtime asset generation uses `melc` subprocesses — at Lemon *build*
  time only.** The no-child-process guarantee (W10/W11) applies to Lemon's
  own build operations; `build.sh` shells out to the pinned `melc`/`melppx`
  and to upstream's `runtime-export` dune alias to produce the
  `node_modules/melange{,.js,.belt}` assets once. Lemon-the-tool never
  spawns a compiler when *you* run `lemon build`.
- **Some runtime modules upstream itself cannot emit are skipped.** The
  asset generator stages interface cmis shipped inside the melange package
  and retries to a fixpoint; modules that still fail (e.g. `weak`, whose
  primitives emit Warning 106 even upstream) are skipped with a note. The
  emitted set covers everything in the catalog and typical programs; if an
  exotic module is missing, the symptom is Node's
  `ERR_MODULE_NOT_FOUND` at run time.
- **Melange internals are reached through their installed layout.**
  `vendor/melange-embed` compiles the vendored `jscomp/core` against the
  `melange.__private__.*` directories of the pinned melange package and
  patches only the library stanza of the copied dune file; a build-time
  `assert` fails if upstream's stanza changes shape.
- **`.ml` sources under `--react` cross three AST views**
  (melange → 5.05 → 5.02 → transform → 5.05 → melange). The tested construct
  set (X-group) passes exactly; OCaml syntax that only exists in 5.05 and
  has no 5.02 representation will not survive the down-conversion and will
  surface as a conversion error rather than silent miscompilation.
- **React prop type errors are reported at the use site.** X13 documents
  that the wrong-prop-type error points at `main.re` (where the prop is
  passed) rather than the component definition; both name original sources.
- **The vendored React runtime is production-only and partial.** `react`,
  `react-dom`, and `scheduler` production builds are vendored under
  `vendor/react-npm` with an `exports` map covering only the subpaths the
  emitted code uses (`.`, `./jsx-runtime`, `react-dom/server`, client via
  the main build). Server rendering uses the *legacy synchronous* server
  build (`renderToStaticMarkup`); the streaming node build is not included.
  Development builds and React DevTools hooks are not bundled.

## Publication and output semantics

- **Executable output to a missing parent directory fails at link time**
  (a clear `Sys_error` naming the path from temporary-file creation), not
  during option validation; the JS target pre-validates its output parent
  (J-group behavior). No misleading success message is printed either way.
- **A fresh `.lemon` directory per build also means stale artifacts never
  leak between builds, but nothing is shared**: compiling the same project
  twice costs full recompilation.
- **Only the melange/react runtimes are copied into JS output**; the output
  does not become an npm package (no `package.json`), it is a directory of
  ES modules plus `node_modules` runtime. Relocation works (J07) as long as
  the tree moves as a whole.

## Operational notes

- **Each worker domain holds a full private compiler stack.** A `--react`
  worker carries stock compiler-libs + reason + ppxlib + the vendored
  melange driver; expect on the order of a hundred megabytes RSS per domain
  at `-j 4`. Worker plugins are loaded sequentially under a mutex (dynlink
  loads are not concurrent-safe), and a failed compiler instance is not
  recovered mid-build — the build fails and the pool is discarded, per the
  plan.
- **esy 0.9 sandbox caching can serve stale sources.** The root project and
  `path:` wrapper packages are snapshotted from the *git index*: untracked
  or unstaged edits may not reach the build sandbox. Symptom: a freshly
  edited `build.sh`/`lemon.ml` behaving like the old version. Mitigation
  used throughout development: `git add -A` before `esy build`; for wrapper
  packages, also clear `~/.esy/source/1/i/opam__s__<pkg>__*` when their
  content changes.

## Testing environment quirks (encoded in the harness)

- **`node` must be the real binary.** esy puts a pnp-shimmed `node` first on
  `PATH` inside `esy sh`; the shim's CommonJS-ESM interop drops named
  exports of required CJS packages (`JsxRuntime.jsx is not a function`).
  The harness resolves `process.execPath` and reuses it (`NODE` in
  `lemon_harness.py`). `npm install` in browser scenarios is invoked
  through the real node's `npm-cli.js` with the real node's `bin` prepended
  to `PATH`, so esbuild's postinstall script does not hit the shim either.
- **Linux-only scenarios run in the dedicated CI job**: E12/P11
  (permission-denied as an unprivileged user; these are *reported* as
  `unsupported` elsewhere, never silently skipped), W10/W11 (strace).
- **Windows fixtures avoid POSIX-only permissions and shell assumptions**;
  symlink scenarios gate on filesystem support (`needs=("symlinks",)`).
