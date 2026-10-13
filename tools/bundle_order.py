#!/usr/bin/env python3
"""Topologically order OCaml object files and archives for `ocamlc -a`.

Reads each input with ocamlobjinfo, sorts units by their Requires lists, and
prints the input files in valid link order (one command-line-friendly line).
Usage: bundle_order.py FILE... > order.txt
"""
import re
import subprocess
import sys


def objinfo(path):
    out = subprocess.run(["ocamlobjinfo", path],
                         capture_output=True, text=True, check=True).stdout
    units = []
    cur, reqs = None, []
    for line in out.splitlines():
        m = re.match(r"Unit name: (\S+)", line)
        if m:
            if cur is not None:
                units.append((cur, reqs))
            cur, reqs = m.group(1), []
            continue
        m = re.match(r"\t[0-9a-f]+\t(\S+)", line)
        if m and cur is not None:
            reqs.append(m.group(1))
    if cur is not None:
        units.append((cur, reqs))
    return units


def main():
    files = sys.argv[1:]
    unit_file, deps = {}, {}
    for f in files:
        for unit, requires in objinfo(f):
            unit_file[unit] = f
            deps.setdefault(unit, set()).update(requires)
    order, done, in_progress = [], set(), set()

    def visit(unit):
        if unit in done or unit in in_progress:
            return
        in_progress.add(unit)
        for dep in deps.get(unit, ()):
            if dep in unit_file:
                visit(dep)
        in_progress.discard(unit)
        done.add(unit)
        order.append(unit)

    for unit in unit_file:
        visit(unit)
    ordered, emitted = [], set()
    for unit in order:
        f = unit_file[unit]
        if f not in emitted:
            emitted.add(f)
            ordered.append(f)
    for f in files:
        if f not in emitted:
            ordered.append(f)
    print("\n".join(ordered))


if __name__ == "__main__":
    main()
