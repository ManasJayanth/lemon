#!/usr/bin/env python3
"""Build a self-contained source tarball (submodules included).

GitHub's auto-generated tag archives omit git submodules, and the pinned
Reason / reason-react / Melange trees live in submodules. This walks the
tracked files of the super-repository and each submodule and packs them
under lemon-<version>/ as a tarball suitable for the Homebrew stable
formula.

usage: make-src-dist.py <repo-root> <output-dir>
"""
import json
import os
import subprocess
import sys
import tarfile

SUBMODULES = [
    "vendor/reason-lemon/reason",
    "vendor/reason-react-lemon/reason-react",
    "vendor/melange-embed/melange",
]


def tracked(repo, prefix=""):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=repo,
                         capture_output=True, check=True).stdout
    return [os.path.join(prefix, f.decode()) for f in out.split(b"\0") if f]


def main():
    repo, outdir = sys.argv[1], sys.argv[2]
    version = os.environ.get("LEMON_VERSION") or \
        json.load(open(os.path.join(repo, "esy.json")))["version"]
    base = f"lemon-source-{version}"
    files = tracked(repo)
    for sub in SUBMODULES:
        subrepo = os.path.join(repo, sub)
        files += tracked(subrepo, prefix=sub)
    archive = os.path.join(outdir, base + ".tar.gz")
    os.makedirs(outdir, exist_ok=True)
    with tarfile.open(archive, "w:gz") as tf:
        for rel in sorted(files):
            tf.add(os.path.join(repo, rel), arcname=os.path.join(base, rel))
    print(archive)


if __name__ == "__main__":
    sys.exit(main())
