---
sidebar_position: 1
---

# Introduction

**Lemon is a build system for OCaml and Reason.** The current implementation
builds OCaml `.ml` and `.mli` files, accepts Reason `.re`/`.rei` sources for
every target, and compiles to bytecode, native executables, and JavaScript
(via an embedded Melange driver).

## Highlights

- **Concurrent by construction.** Pass all source files, in any order —
  Lemon discovers module dependencies and compiles independent files
  concurrently across a fixed worker pool.
- **Embedded toolchain.** Reason parsing, the React JSX transform, and the
  Melange JS driver run in-process. No `refmt`, no `melc`, no `-pp`, no
  external PPX subprocesses — diagnostics always point at your original
  sources.
- **Every scenario executes a real artifact.** The end-to-end catalog
  (`tests/test_build.py`) compiles *and runs* the result; GitHub Actions
  repeats it on Linux, macOS ARM/Intel, and Windows.

## How it works

Bytecode is the default. Lemon loads a private copy of the unmodified OCaml
compiler libraries for each worker domain. Compiler values stay inside their
worker; workers exchange artifact paths and text diagnostics. Libraries are
loaded sequentially before compilation starts, and linking is serialized.
The coordinator has no compiler-library dependency. A fixed worker pool
avoids continually loading libraries, which OCaml cannot unload.

Include explicit `.mli` files when present. Modules must have unique names;
dependencies outside the supplied files are currently limited to the standard
library. Builds use a fresh `.lemon` directory and are not yet incremental.
A failed build preserves any existing output.

Head to [Getting started](./getting-started.mdx) to build your first
program, see [Targets](./targets.mdx) for Reason/JavaScript/React builds,
and read [Known limitations](./limitations.md) for the exact boundaries of
the current implementation.
