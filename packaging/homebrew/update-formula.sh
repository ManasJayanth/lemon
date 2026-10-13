#!/bin/sh
# Point the Homebrew formula at a released source tarball.
#
# usage: update-formula.sh <version> <tarball-file>
#   e.g. packaging/homebrew/update-formula.sh 0.2.0 dist/lemon-source-0.2.0.tar.gz
set -eu
VERSION=$1
TARBALL=$2
REPO=${LEMON_REPO:-prometheansacrifice/lemon}

if command -v shasum >/dev/null 2>&1; then
  SHA=$(shasum -a 256 "$TARBALL" | cut -d' ' -f1)
else
  SHA=$(sha256sum "$TARBALL" | cut -d' ' -f1)
fi

FORMULA=$(dirname "$0")/Formula/lemon.rb
python3 - "$FORMULA" "$VERSION" "$REPO" "$SHA" <<'PYEOF'
import sys
formula, version, repo, sha = sys.argv[1:5]
s = open(formula).read()
stable = f'''  url "https://github.com/{repo}/releases/download/v{version}/lemon-source-{version}.tar.gz"
  version "{version}"
  sha256 "{sha}"
'''
marker = '  # Stable releases: fill in via packaging/homebrew/update-formula.sh, e.g.\n'
i = s.index(marker)
j = s.index("\n\n", i)
s = s[:i] + stable + s[j:]
open(formula, "w").write(s)
print(f"formula updated: v{version} sha256={sha}")
PYEOF
