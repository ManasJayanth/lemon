#!/bin/sh
# Point the Homebrew formula at a released source tarball and its bottles.
#
# usage: update-formula.sh <version> <source-tarball> [<tag>=<bottle-file>]...
#   e.g. packaging/homebrew/update-formula.sh 0.2.0 dist/lemon-source-0.2.0.tar.gz \
#          arm64_sequoia=dist/lemon--0.2.0.arm64_sequoia.bottle.tar.gz \
#          sequoia=dist/lemon--0.2.0.sequoia.bottle.tar.gz
set -eu
VERSION=$1
TARBALL=$2
shift 2
REPO=${LEMON_REPO:-prometheansacrifice/lemon}

if command -v shasum >/dev/null 2>&1; then
  SHACMD="shasum -a 256"
else
  SHACMD="sha256sum"
fi
sha() { (cd "$(dirname "$1")" && $SHACMD "$(basename "$1")" | cut -d' ' -f1); }
SRC_SHA=$(sha "$TARBALL")

BOTTLES=""
for pair in "$@"; do
  TAG=${pair%%=*}
  FILE=${pair#*=}
  BOTTLES="$BOTTLES $TAG $(sha "$FILE")"
done

FORMULA=$(dirname "$0")/../../Formula/lemon.rb
python3 - "$FORMULA" "$VERSION" "$REPO" "$SRC_SHA" $BOTTLES <<'PYEOF'
import sys
formula, version, repo, src_sha = sys.argv[1:5]
bottles = sys.argv[5:]  # tag sha256 tag sha256 ...

stable = f'''  url "https://github.com/{repo}/releases/download/v{version}/lemon-source-{version}.tar.gz"
  version "{version}"
  sha256 "{src_sha}"
'''
if bottles:
    entries = ", ".join(f"{tag}: \\"{digest}\\"" for tag, digest in zip(bottles[::2], bottles[1::2]))
    stable += f'''  bottle do
    root_url "https://github.com/{repo}/releases/download/v{version}"
    sha256 {entries}
  end
'''
marker = '  # Stable releases: fill in via packaging/homebrew/update-formula.sh, e.g.\n'
s = open(formula).read()
i = s.index(marker)
j = s.index("\n\n", i)
s = s[:i] + stable + s[j:]
open(formula, "w").write(s)
print(f"formula updated: v{version} source sha256={src_sha} bottles={bottles[::2]}")
PYEOF
