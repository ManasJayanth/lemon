#!/usr/bin/env python3
"""Render a winget manifest from packaging/winget/template.

usage: render-manifest.py <output-dir> <version> <installer-url> <installer-file>

Computes the installer SHA256 from the local file, substitutes it into the
three manifest YAMLs, and writes them into <output-dir> (one version per
render; winget validate --manifest <dir> checks the result).
"""
import hashlib
import os
import sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    outdir, version, url, installer = sys.argv[1:5]
    digest = sha256(installer)
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(outdir, exist_ok=True)
    for name in os.listdir(os.path.join(here, "template")):
        with open(os.path.join(here, "template", name)) as fh:
            text = fh.read()
        text = (text.replace("__VERSION__", version)
                    .replace("__URL__", url)
                    .replace("__SHA__", digest))
        with open(os.path.join(outdir, name), "w") as fh:
            fh.write(text)
    print(f"manifest rendered in {outdir} (sha256={digest})")


if __name__ == "__main__":
    sys.exit(main())
