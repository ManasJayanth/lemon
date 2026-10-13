class Lemon < Formula
  desc "Build system for OCaml and Reason with embedded Melange and React"
  homepage "https://github.com/prometheansacrifice/lemon"
  # Lemon links the OCaml compiler libraries and Melange (LGPL-2.1 with the
  # OCaml linking exception) plus MIT-licensed Reason/React bindings.
  license "LGPL-2.1-only" => { with: "OCaml-LGPL-linking-exception" }

  head "https://github.com/prometheansacrifice/lemon.git", branch: "main"

  # Stable releases: fill in via packaging/homebrew/update-formula.sh, e.g.
  #   url "https://github.com/prometheansacrifice/lemon/releases/download/v0.2.0/lemon-source-0.2.0.tar.gz"
  #   version "0.2.0"
  #   sha256 "..."
  #   bottle do
  #     root_url "https://github.com/prometheansacrifice/lemon/releases/download/v0.2.0"
  #     sha256 arm64_sequoia: "...", sequoia: "..."
  #   end

  depends_on "node" => :build

  def install
    # The pinned toolchain builds through esy (installed via npm; esy is not
    # in homebrew-core). esy derives its store path from HOME and refuses
    # deep prefixes, so give the build a shallow home; Homebrew's own
    # temporary directories are too deep.
    ENV["HOME"] = "/tmp/lemon-home-#{Process.pid}"
    FileUtils.mkdir_p ENV["HOME"]
    npm_prefix = Pathname.new("/tmp/lemon-npm-#{Process.pid}")
    system "npm", "install", "--prefix", npm_prefix.to_s, "esy@0.9.2"
    ENV.prepend_path "PATH", npm_prefix/"node_modules/.bin"

    # Homebrew clones HEAD without submodules; the pinned Reason, Melange,
    # and reason-react trees live in submodules.
    system "git", "submodule", "update", "--init", "--recursive" if File.exist?(".git")

    system "esy", "install"
    system "esy", "build"
    system "sh", "packaging/make-dist.sh"

    staging = Dir["dist/staging/lemon-*"].first
    odie "make-dist.sh produced no staging tree" unless staging
    # Installs bin/lemon + lib/lemon next to each other; the runtime
    # resolves the library through the executable's symlinked location.
    cp_r Dir["#{staging}/."], prefix
  end

  def caveats
    <<~EOS
      Native (--target native) compilation shells out to ocamlopt from an
      OCaml installation; bytecode, JavaScript, and React builds are fully
      self-contained. Set LEMON_LIB to override the library location.

      --build-from-source builds the pinned toolchain through esy; on newer
      macOS this can fail inside Homebrew's build sandbox because esy's own
      sandbox cannot nest (prefer the bottle, which is the default).
    EOS
  end

  test do
    (testpath/"hello.re").write 'print_endline("brewed lemon");\n'
    system bin/"lemon", "build", "--target", "js", "--out-dir", "js-out", "hello.re"
    assert_match "brewed lemon", shell_output("#{Formula["node"].opt_bin}/node js-out/Hello.js")
  end
end
