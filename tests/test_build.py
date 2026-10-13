"""CLI entry for the Lemon end-to-end catalog. See lemon_harness.py."""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lemon_harness as H  # noqa: E402
import lemon_scenarios      # noqa: F401,E402  (registers the catalog)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", default=[])
    ap.add_argument("--group", action="append", default=[])
    ap.add_argument("--suite", default=None)
    ap.add_argument("--target", default=None,
                    choices=["bytecode", "native", "js"])
    ap.add_argument("--jobs", default=None)
    args = ap.parse_args()

    if not H.LEMON.exists():
        print(f"lemon.byte not built: {H.LEMON}\nrun: esy", file=sys.stderr)
        return 2

    ids = []
    for cid in args.case:
        if cid not in H.CASES:
            print(f"unknown case {cid}", file=sys.stderr)
            return 2
        ids.append(cid)
    for g in args.group:
        if g not in H.GROUPS:
            print(f"unknown group {g}", file=sys.stderr)
            return 2
        ids += H.GROUPS[g]
    if args.suite:
        if args.suite not in H.SUITES:
            print(f"unknown suite {args.suite}", file=sys.stderr)
            return 2
        ids += H.SUITES[args.suite]()
    if not ids:
        ids = H.SUITES["baseline"]()

    scratch = Path(tempfile.mkdtemp(prefix="lemon-e2e "))
    counts = {}
    failures = []
    try:
        for cid in ids:
            jobs = int(args.jobs) if args.jobs is not None else None
            for r in H.run_case(H.CASES[cid], target=args.target, jobs=jobs, base=scratch):
                counts[r.status] = counts.get(r.status, 0) + 1
                mark = {"passed": "ok", "failed": "FAIL", "skipped": "skip",
                        "unsupported": "unsup"}[r.status]
                print(f"[{mark}] {r.label()} {r.detail if r.status != 'passed' else ''}")
                if r.status == "failed":
                    failures.append(r)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    print(f"\n{len(ids)} scenarios: "
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if failures:
        print("failures preserved under tests/artifacts/")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
