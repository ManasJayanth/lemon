#!/usr/bin/env python3
"""Render a local-test formula pointing at local files.

usage: local-formula.py <output.rb> <repo-root>
Writes Formula/lemon.rb with:
  - stable url  = file://<repo>/dist/lemon-source-<version>.tar.gz
  - bottle root_url = file://<repo>/dist
  - bottle sha256 for every dist/lemon--<version>.<tag>.bottle.tar.gz found
"""
import hashlib
import glob
import json
import os
import re
import sys

out, root = sys.argv[1], sys.argv[2]
version = json.load(open(os.path.join(root, "esy.json")))["version"]
src = os.path.join(root, "dist", f"lemon-source-{version}.tar.gz")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


bottles = []
for path in sorted(glob.glob(os.path.join(root, "dist", f"lemon--{version}.*.bottle.tar.gz"))):
    tag = re.search(r"\.([a-z0-9_]+)\.bottle\.tar\.gz$", path).group(1)
    bottles.append((tag, sha(path)))

stable = f'''  url "file://{src}"
  version "{version}"
  sha256 "{sha(src)}"
  bottle do
    root_url "file://{os.path.join(root, "dist")}"
'''
for tag, digest in bottles:
    stable += f'    sha256 {tag}: "{digest}"\n'
stable += "  end\n"

s = open(os.path.join(root, "Formula", "lemon.rb")).read()
marker = "  # Stable releases: fill in via packaging/homebrew/update-formula.sh, e.g.\n"
i = s.index(marker)
j = s.index("\n\n", i)
s = s[:i] + stable + s[j:]
open(out, "w").write(s)
print(f"local formula written to {out} (bottles: {[t for t, _ in bottles]})")
