# OCaml compiler API demo

The only dependency is the npm package `ocaml@5.5.1000`, which contains
upstream OCaml 5.5.1 and its compiler libraries.

```sh
esy
```

The build compiles and runs the sample, printing:

```text
Hello from the compiled program! 7 squared = 49
```

Esy first uses `ocamlc` to build `compile_program.ml`, linking the bundled
`ocamlcommon.cma` and `ocamlbytecomp.cma` libraries. That program then compiles
`examples/hello.ml` through `Compile.implementation`, which parses, typechecks,
and generates a `.cmo` bytecode object. `Bytelink.link` links it with the standard
library into `hello.byte`. The demo compiler does this in-process; it does not
invoke `ocamlc` as a subprocess. `ocamlrun` executes the resulting program.

To compile another `.ml` file, put it in this repository and run:

```sh
esy ocamlrun ./_esy/default/build/compile_program.byte examples/hello.ml another.byte
esy ocamlrun ./another.byte
```

This minimal driver handles a single source file using the standard library.
It emits `.cmi` and `.cmo` files beside that source in esy's build directory.
Compiler-library APIs are version-specific, so the dependency is pinned.
