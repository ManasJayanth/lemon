#!/usr/bin/env python3
"""Cross-platform archiver for distribution trees (zip and tar.gz)."""
import os
import sys
import tarfile
import zipfile


def make_zip(source_dir, archive):
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(source_dir):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, source_dir)
                zf.write(full, rel)


def make_tgz(source_dir, archive):
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(source_dir, arcname=os.path.basename(source_dir.rstrip("/")))


def main():
    if len(sys.argv) != 5:
        print("usage: zipdir.py zip|tgz SOURCE_DIR OUTPUT_DIR ARCHIVE_BASENAME",
              file=sys.stderr)
        return 2
    fmt, source, outdir, base = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    os.makedirs(outdir, exist_ok=True)
    if fmt == "zip":
        archive = os.path.join(outdir, base + ".zip")
        make_zip(source, archive)
    elif fmt == "tgz":
        archive = os.path.join(outdir, base + ".tar.gz")
        make_tgz(source, archive)
    else:
        print("unknown format: " + fmt, file=sys.stderr)
        return 2
    print(archive)


if __name__ == "__main__":
    sys.exit(main())
