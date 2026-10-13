# Homebrew tap for Lemon

`Formula/lemon.rb` packages Lemon for Homebrew. The default install pours a
**bottle** (a prebuilt, relocatable tree built by this repository's release
workflow); `--build-from-source` rebuilds the pinned toolchain through esy.

Validated in CI on every push (`homebrew` job): the distribution and a
bottle are built locally, a tap is installed by placement with a `file://`
formula, `brew install` pours the bottle, and the installed `lemon` builds
and runs a React application.

## Publishing as a tap

Homebrew taps are git repositories named `homebrew-<name>`. To publish:

1. Create a public repository `homebrew-lemon` under your GitHub account
   containing `Formula/lemon.rb`.

2. On each release (the `release.yml` workflow builds the bottles and the
   source tarball for macOS arm64 and x86_64 and attaches them with
   checksums), fill the stable stanza:

   ```sh
   packaging/homebrew/update-formula.sh 0.2.0 dist/lemon-source-0.2.0.tar.gz \
     arm64_sequoia=dist/lemon--0.2.0.arm64_sequoia.bottle.tar.gz \
     sequoia=dist/lemon--0.2.0.sequoia.bottle.tar.gz
   cp Formula/lemon.rb ../homebrew-lemon/Formula/lemon.rb
   ```

   (Use the bottle tags `brew ruby -e 'print Hardware::CPU.intel? ?
   MacOS.version.to_sym.to_s : "arm64_" + MacOS.version.to_sym.to_s'`
   names on the runners that produced them; the release job records them.)

3. Users install with:

   ```sh
   brew install <owner>/lemon/lemon
   ```

## Layout

The bottle contains `lemon/<version>/{bin,lib}`:

- `bin/lemon` - custom-runtime executable (no ocamlrun needed)
- `lib/lemon/compiler_worker.cma`, `melange_worker.cma` - dynlinked plugins
- `lib/lemon/melange-stdlib/`, `melange-js/`, `react-lib/` - interface trees
- `lib/lemon/react-npm/`, `melange-assets/` - JS runtimes for publication

The executable finds `lib/lemon` through its own location (resolving the
`/opt/homebrew/bin` symlink and bare `PATH` invocations); `LEMON_LIB`
overrides.

## Notes and caveats

- `--build-from-source` runs esy inside Homebrew's build environment. Two
  esy 0.9 quirks are worked around in the formula: esy's store requires a
  shallow `HOME` (Homebrew's temp tree is too deep), and esy's per-package
  `sandbox-exec` cannot nest inside Homebrew's build sandbox on newer
  macOS - the bottle path avoids both.
- Native (`--target native`) builds shell out to `ocamlopt` from an OCaml
  installation; bytecode, JavaScript, and React builds are self-contained.
- HEAD installs (`brew install --HEAD`) build from git and need network
  access plus a non-sandboxed build (`HOMEBREW_NO_SANDBOX=1`).
