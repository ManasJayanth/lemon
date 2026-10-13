"""Catalog-driven end-to-end runner for Lemon.

Usage:
  esy python tests/test_build.py --case R01
  esy python tests/test_build.py --group reason --target bytecode --jobs 4
  esy python tests/test_build.py --suite all

Every scenario runs in a fresh temporary project. On failure the fixtures,
commands, stdout/stderr and artifacts are preserved under tests/artifacts/.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEMON = ROOT / "_esy/default/build/lemon.byte"
ARTIFACTS = ROOT / "tests/artifacts"

BUILD_TIMEOUT = int(os.environ.get("LEMON_BUILD_TIMEOUT", "180"))
RUN_TIMEOUT = int(os.environ.get("LEMON_RUN_TIMEOUT", "60"))

EXECUTABLE_TARGETS = ("bytecode", "native")

def _real_node():
    """esy puts a pnp-shimmed node first on PATH; its CJS-ESM interop drops
    named exports of required CommonJS packages. Prefer the real binary."""
    import subprocess
    cached = os.environ.get("LEMON_NODE")
    if cached:
        return cached
    try:
        out = subprocess.run(["node", "-e", "console.log(process.execPath)"],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        if out and out.endswith("node"):
            return out.splitlines()[-1]
    except Exception:
        pass
    return "node"

NODE = _real_node()

CASES = {}          # id -> Case
GROUPS = {}         # group name -> [case ids]


class Skip(Exception):
    """Raised when the environment cannot run a scenario."""


class Case:
    def __init__(self, cid, group, fn, targets, jobs, needs):
        self.id = cid
        self.group = group
        self.fn = fn
        self.targets = targets          # tuple of targets or None (target-free)
        self.jobs = jobs                # tuple of worker counts to exercise
        self.needs = needs              # tuple of capability strings


def case(cid, group, targets=None, jobs=(None,), needs=()):
    """Register a scenario.

    targets: targets the scenario matrix runs under; None runs it once,
    target-free. The --target filter narrows the matrix.
    jobs: worker counts to repeat the scenario with (None = default).
    needs: capabilities ("symlinks", "unprivileged", "node", "browser").
    """
    def wrap(fn):
        CASES[cid] = Case(cid, group, fn, targets, jobs, needs)
        GROUPS.setdefault(group, []).append(cid)
        return fn
    return wrap


def have_symlinks():
    if platform.system() == "Windows":
        return os.environ.get("LEMON_WINDOWS_SYMLINKS") == "1"
    return True


def have_capability(cap):
    return {
        "symlinks": have_symlinks,
        "unprivileged": lambda: os.environ.get("LEMON_UNPRIVILEGED") == "1",
        "node": lambda: shutil.which("node") is not None,
        "strace": lambda: shutil.which("strace") is not None,
        "browser": lambda: os.environ.get("LEMON_BROWSER_TESTS") == "1",
    }.get(cap, lambda: False)()


class Result:
    def __init__(self, cid, target, jobs, status, detail=""):
        self.cid, self.target, self.jobs = cid, target, jobs
        self.status, self.detail = status, detail

    def label(self):
        parts = [self.cid]
        if self.target:
            parts.append(self.target)
        if self.jobs:
            parts.append(f"j{self.jobs}")
        return "/".join(parts)


class Project:
    """A fresh temporary project directory for one scenario run."""

    def __init__(self, base, name=None):
        self.name = name or base
        self.dir = Path(tempfile.mkdtemp(prefix=f"lemon-{self.name}-", dir=str(base)))
        self.kept = False
        self.log = []

    # -- fixtures ---------------------------------------------------------
    def write(self, name, text):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def mkdir(self, name):
        path = self.dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    # -- commands ---------------------------------------------------------
    def run(self, args, timeout=RUN_TIMEOUT, cwd=None, check=None, env=None):
        args = [str(a) for a in args]
        proc = subprocess.run(
            args, cwd=str(cwd or self.dir), text=True, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.log.append((args, proc.returncode, proc.stdout, proc.stderr))
        if check is not None:
            expected = check
            ok = (proc.returncode == 0) == expected
            detail = f"args={args}\nexit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            assert ok, detail
        return proc

    def lemon(self, *args, check=True, timeout=BUILD_TIMEOUT, env=None, cwd=None):
        argv = ["ocamlrun", str(LEMON)]
        argv += [str(a) for a in args]
        return self.run(argv, timeout=timeout, check=(True if check is None else check), env=env, cwd=cwd)

    # -- helpers ----------------------------------------------------------
    def build(self, sources, target=None, jobs=None, out=None, extra=(), check=True, env=None, cwd=None):
        """Invoke `lemon build` with the given options."""
        args = ["build"]
        if target:
            args += ["--target", target]
        if jobs is not None:
            args += ["-j", str(jobs)]
        if target == "js" and out:
            args += ["--out-dir", str(out)]
        elif out:
            args += ["-o", str(out)]
        args += list(extra) + [str(s) for s in sources]
        return self.lemon(*args, check=check, env=env, cwd=cwd)

    def execute(self, target, artifact, timeout=RUN_TIMEOUT):
        """Run a produced application: bytecode via ocamlrun, native directly,
        JS with node."""
        if target == "bytecode":
            return self.run(["ocamlrun", str(artifact)], timeout=timeout, check=True)
        if target == "native":
            return self.run([str(artifact)], timeout=timeout, check=True)
        if target == "js":
            return self.run([NODE, str(artifact)], timeout=timeout, check=True)
        raise AssertionError(f"unknown target {target}")

    def default_output(self, source, target):
        stem = Path(source).stem
        suffix = {"bytecode": ".byte", "native": ".exe" if platform.system() == "Windows" else ".native"}[target]
        return self.dir / (stem + suffix)

    def assert_output_intact(self, artifact: Path, before: bytes):
        after = artifact.read_bytes()
        assert after == before, "existing output was modified by a failed build"


def preserve(project: Project, result: Result, exc=None):
    if project.kept:
        return
    project.kept = True
    dest = ARTIFACTS / result.label().replace("/", "__")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(project.dir, dest / "project", dirs_exist_ok=True)
    with open(dest / "log.txt", "w") as fh:
        for args, code, out, err in project.log:
            fh.write(f"$ {' '.join(args)}\n[exit {code}]\n--stdout--\n{out}\n--stderr--\n{err}\n\n")
        if exc:
            import traceback as tb
            fh.write("Exception:\n" + "".join(tb.format_exception(type(exc), exc, exc.__traceback__)))


def run_case(c: Case, target=None, jobs=None, base=None):
    """Run one scenario, possibly across its target/jobs matrix."""
    results = []
    targets = c.targets or (None,)
    if target:
        targets = tuple(t for t in targets if t == target)
        if not targets:
            return [Result(c.id, target, jobs, "skipped", "target not in scenario matrix")]
    for cap in c.needs:
        if not have_capability(cap):
            return [Result(c.id, target, jobs, "unsupported",
                           f"environment lacks capability: {cap}")]
    job_matrix = (jobs,) if jobs is not None else c.jobs
    for t in targets:
        for j in job_matrix:
            project = Project(base, c.id)
            r = Result(c.id, t, j, "passed")
            start = time.time()
            try:
                c.fn(project, t, j)
                assert not project.kept
            except Skip as s:
                r.status, r.detail = "unsupported", str(s)
            except Exception as e:               # noqa: BLE001 - report all
                r.status, r.detail = "failed", f"{type(e).__name__}: {e}"
                preserve(project, r, e)
            finally:
                shutil.rmtree(project.dir, ignore_errors=True)
            r.detail += f" [{time.time()-start:.1f}s]"
            results.append(r)
    return results


SUITES = {
    "all": lambda: list(CASES),
    "baseline": lambda: GROUPS.get("baseline", []) + GROUPS.get("errors", [])
                       + GROUPS.get("workers", []),
}
