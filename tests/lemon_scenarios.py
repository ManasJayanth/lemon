"""Scenario catalog. Each scenario receives (project, target, jobs)."""
import os
import platform
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lemon_harness import case, Skip, EXECUTABLE_TARGETS  # noqa: E402


def exe(target):
    return {"bytecode": ".byte",
            "native": ".exe" if platform.system() == "Windows" else ".native"}[target]


# --------------------------------------------------------------------------
# Baseline matrix (ported from the pre-catalog test suite)
# --------------------------------------------------------------------------

INTERFACE_SOURCES = {
    "value.mli": "val answer : int\n",
    "value.ml": "let answer = 40\n",
    "main.ml": 'let () = Printf.printf "%d\\n" (Part0.answer + Part2.answer)\n',
}


@case("L01", "baseline", targets=EXECUTABLE_TARGETS, jobs=(1, 4))
def l01(p, target, jobs):
    p.write("value.mli", "val answer : int\n")
    p.write("value.ml", "let answer = 40\n")
    for i in range(12):
        p.write(f"part{i}.ml", f"let answer = Value.answer + {i}\n")
    p.write("main.ml", 'let () = Printf.printf "%d\\n" (Part0.answer + Part2.answer)\n')
    sources = ["main.ml"] + [f"part{i}.ml" for i in range(12)] + ["value.ml", "value.mli"]
    out = p.dir / f"program{exe(target)}"
    p.build(sources, target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == "82\n"


@case("L02", "baseline", targets=EXECUTABLE_TARGETS)
def l02(p, target, jobs):
    p.write("value.ml", "let answer = 40\n")
    out = p.dir / f"program{exe(target)}"
    p.build(["value.ml"], target=target, out=out)
    before = out.read_bytes()
    p.write("bad.ml", 'let x : int = "wrong"\n')
    r = p.build(["bad.ml"], target=target, out=out, check=False)
    assert r.returncode != 0
    assert "int" in r.stderr and "string" in r.stderr, r.stderr
    p.assert_output_intact(out, before)


@case("L03", "baseline")
def l03(p, target, jobs):
    p.write("a.ml", "let x = B.x\n")
    p.write("b.ml", "let x = A.x\n")
    r = p.build(["a.ml", "b.ml"], check=False)
    assert r.returncode != 0 and "cycle" in r.stderr.lower(), r.stderr


@case("L04", "baseline")
def l04(p, target, jobs):
    p.write("value.ml", "let x = 1\n")
    r = p.build(["value.ml"], jobs=0, check=False)
    assert r.returncode != 0
    assert not (p.dir / ".lemon").exists(), "failed -j must not start a build"


@case("L05", "baseline")
def l05(p, target, jobs):
    p.write("hello.ml", 'let () = print_endline "hello"\n')
    r = p.lemon("hello.ml", "hello.byte")
    assert "\nhello\n" not in r.stdout          # building never runs the program
    assert p.execute("bytecode", p.dir / "hello.byte").stdout == "hello\n"


@case("L06", "baseline")
def l06(p, target, jobs):
    p.write("value.ml", "let x = 1\n")
    p.build(["value.ml"], out=p.dir / "value.byte")
    leftover = list((p.dir / ".lemon").iterdir()) if (p.dir / ".lemon").exists() else []
    assert leftover == [], f"temporary artifacts not cleaned: {leftover}"


# --------------------------------------------------------------------------
# E10-E12: output-path error handling
# --------------------------------------------------------------------------

@case("E10", "errors")
def e10(p, target, jobs):
    dirn = "späces ünicode dir"
    src = p.write(f"{dirn}/app.ml", 'let () = print_endline "ok"\n')
    out = p.dir / f"{dirn}/app.byte"
    p.build([src], out=out)
    assert p.execute("bytecode", out).stdout == "ok\n"
    bad = p.write(f"{dirn}/broken.ml", "let x : int = true\n")
    r = p.build([bad], out=out, check=False)
    assert r.returncode != 0
    assert "broken.ml" in r.stderr, r.stderr


@case("E11", "errors")
def e11(p, target, jobs):
    p.write("app.ml", 'let () = print_endline "no"\n')
    r = p.build(["app.ml"], out="missing/parent/app.byte", check=False)
    assert r.returncode != 0
    assert "built" not in r.stdout, r.stdout       # no misleading success message


@case("E12", "errors", needs=("unprivileged",))
def e12(p, target, jobs):
    if platform.system() != "Linux":
        raise Skip("permission-denied fixtures run in Linux CI as an unprivileged user")
    locked = p.mkdir("locked")
    os.chmod(locked, stat.S_IREAD | stat.S_IEXEC)
    out = locked / "app.byte"
    r = p.build(["app.ml"], out=out, check=False)
    assert r.returncode != 0
    assert not out.exists()
    assert not any(locked.glob(".lemon-*")), "staging files leaked"


# --------------------------------------------------------------------------
# W07-W09: build-vs-run semantics and worker-count validation
# --------------------------------------------------------------------------

@case("W07", "workers", targets=EXECUTABLE_TARGETS)
def w07(p, target, jobs):
    import json
    sentinel = p.dir / "sentinel.txt"
    literal = json.dumps(str(sentinel))
    p.write("app.ml", f'let () = let oc = open_out {literal} in output_string oc "ran"; close_out oc\n')
    out = p.dir / f"app{exe(target)}"
    p.build(["app.ml"], target=target, out=out)
    assert not sentinel.exists(), "building must not execute the program"
    p.execute(target, out)
    assert sentinel.exists(), "executing must create the sentinel"


@case("W08", "workers")
def w08(p, target, jobs):
    p.write("value.ml", "let x = 1\n")
    for bad in ("0", "-2", "abc", "4.5"):
        r = p.build(["value.ml"], jobs=bad, check=False)
        assert r.returncode != 0, f"-j {bad} was accepted"
        assert "-j" in r.stderr or "worker" in r.stderr.lower(), (bad, r.stderr)
        assert not (p.dir / ".lemon").exists(), f"-j {bad} started a build"


@case("W09", "workers", targets=EXECUTABLE_TARGETS)
def w09(p, target, jobs):
    p.write("a.ml", "let x = 1\n")
    p.write("b.ml", "let x = A.x + 1\n")
    p.write("c.ml", "let x = B.x + 1\n")
    out = p.dir / f"total{exe(target)}"
    p.build(["c.ml", "b.ml", "a.ml"], target=target, jobs=8, out=out)
    assert p.execute(target, out).stdout == ""   # links fine; no side effects
