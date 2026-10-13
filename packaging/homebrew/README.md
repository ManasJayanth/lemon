# Homebrew tap for Lemon

This directory contains the Homebrew formula. The packaging is validated on
CI (the `homebrew` job builds and installs the formula, then runs the
formula's own test).

## Publishing as a tap

Homebrew taps are git repositories named `homebrew-<name>`. To publish:

1. Create a **public** repository `homebrew-lemon` under your GitHub account
   (or org), containing:

   ```
   Formula/lemon.rb        <- a copy of this directory's Formula/lemon.rb
   README.md               <- optional
   ```

   For a released version, first fill in the stable stanza:

   ```sh
   packaging/homebrew/update-formula.sh 0.2.0 dist/lemon-source-0.2.0.tar.gz
   cp Formula/lemon.rb ../homebrew-lemon/Formula/lemon.rb
   ```

2. Users then install with:

   ```sh
   brew install <owner>/lemon/lemon
   # or, before the tap exists / for development:
   brew install --HEAD --formula ./Formula/lemon.rb
   ```

## Notes

- The formula builds from source through esy (installed into the build
  prefix via npm, since esy is not in homebrew-core). Builds need network
  access; with Homebrew's build sandbox enabled, prefix the install with
  `HOMEBREW_NO_SANDBOX=1` (CI does this automatically).
- HEAD builds clone the repository without submodules; the formula runs
  `git submodule update --init --recursive` itself. Stable builds use the
  `lemon-source-<version>.tar.gz` release asset, which contains the pinned
  submodule trees.
- The installed tree is self-contained (`bin/lemon` plus `lib/lemon`
  resolved through the symlinked executable). Only `--target native`
  additionally requires an `ocaml` installation for its `ocamlopt`
  subprocesses.
