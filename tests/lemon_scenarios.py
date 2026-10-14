"""Scenario catalog. Each scenario receives (project, target, jobs)."""
import os
import platform
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lemon_harness import case, Skip, EXECUTABLE_TARGETS, LEMON as LEMON_PATH  # noqa: E402


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


# --------------------------------------------------------------------------
# A. Reason syntax and application behavior (R01-R12)
# --------------------------------------------------------------------------

@case("R01", "reason", targets=EXECUTABLE_TARGETS, jobs=(1, 4))
def r01(p, target, jobs):
    p.write("greet.re", 'print_endline("hello from reason");\n')
    out = p.dir / f"greet{exe(target)}"
    p.build(["greet.re"], target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == "hello from reason\n"


@case("R02", "reason", targets=EXECUTABLE_TARGETS)
def r02(p, target, jobs):
    p.write("funcs.re", '''
let add = (a, b) => a + b;
let greet = (~name, ~punct="!", ()) => "hi " ++ name ++ punct;
let rec fact = n => n <= 1 ? 1 : n * fact(n - 1);
let () = {
  print_int(add(19, 23));
  print_newline();
  print_endline(greet(~name="reason", ()));
  print_endline(greet(~name="reason", ~punct="?", ()));
  print_int(fact(5));
  print_newline();
};
''')
    out = p.dir / f"funcs{exe(target)}"
    p.build(["funcs.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "42\nhi reason!\nhi reason?\n120\n"


@case("R03", "reason", targets=EXECUTABLE_TARGETS)
def r03(p, target, jobs):
    p.write("data.re", '''
type shape = Circle(float) | Rect(float, float);
type person = {name: string, age: int};
let describe = s =>
  switch (s) {
  | Circle(r) => "circle r=" ++ string_of_float(r)
  | Rect(w, h) => "rect " ++ string_of_float(w) ++ "x" ++ string_of_float(h)
  };
let people = [{name: "ada", age: 36}, {name: "alan", age: 41}];
let nums = [1, 2, 3];
let arr = [|10, 20|];
let pair = (true, "yes");
let () = {
  print_endline(describe(Circle(2.0)));
  print_endline(describe(Rect(3.0, 4.0)));
  print_int(List.fold_left((a, b) => a + b, 0, nums));
  print_newline();
  print_int(arr[0] + arr[1]);
  print_newline();
  print_endline(snd(pair));
  let names = List.map(p => p.name, people);
  List.iter(print_endline, names);
  switch (List.nth(nums, 1)) {
  | 2 => print_endline("second is two")
  | _ => print_endline("second is not two")
  };
};
''')
    out = p.dir / f"data{exe(target)}"
    p.build(["data.re"], target=target, out=out)
    assert p.execute(target, out).stdout == (
        "circle r=2.\nrect 3.x4.\n6\n30\nyes\nada\nalan\nsecond is two\n")


@case("R04", "reason", targets=EXECUTABLE_TARGETS)
def r04(p, target, jobs):
    p.write("mods.re", '''
module Math = {
  let double = x => x * 2;
  module Inner = {
    let triple = x => x * 3;
  };
};
let () = {
  print_int(Math.double(7));
  print_newline();
  print_int(Math.Inner.triple(7));
  print_newline();
};
''')
    out = p.dir / f"mods{exe(target)}"
    p.build(["mods.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "14\n21\n"


@case("R05", "reason", targets=EXECUTABLE_TARGETS)
def r05(p, target, jobs):
    p.write("exn.re", '''
exception Boom(string);
let () =
  try (raise(Boom("caught"))) {
  | Boom(msg) => print_endline("caught: " ++ msg)
  };
''')
    out = p.dir / f"exn{exe(target)}"
    p.build(["exn.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "caught: caught\n"


@case("R06", "reason", targets=EXECUTABLE_TARGETS)
def r06(p, target, jobs):
    import json
    text = 'quote " back\\slash tab\t unicode: ünïcødé ✓ multi:\nline two'
    p.write("strings.re", "let () = print_endline(%s);\n" % json.dumps(text, ensure_ascii=False))
    out = p.dir / f"strings{exe(target)}"
    p.build(["strings.re"], target=target, out=out)
    got = p.execute(target, out).stdout
    assert got == text + "\n", (got, text)


@case("R07", "reason", targets=EXECUTABLE_TARGETS)
def r07(p, target, jobs):
    p.write("helper.ml", 'let twice x = x * 2\n')
    p.write("main.re", 'print_int(Helper.twice(21)); print_newline();\n')
    out = p.dir / f"mix{exe(target)}"
    p.build(["main.re", "helper.ml"], target=target, out=out)
    assert p.execute(target, out).stdout == "42\n"


@case("R08", "reason", targets=EXECUTABLE_TARGETS)
def r08(p, target, jobs):
    p.write("helper.re", 'let thrice = x => x * 3;\n')
    p.write("main.ml", 'let () = Printf.printf "%d\\n" (Helper.thrice 14)\n')
    out = p.dir / f"mix{exe(target)}"
    p.build(["main.ml", "helper.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "42\n"


@case("R09", "reason", targets=EXECUTABLE_TARGETS, jobs=(4,))
def r09(p, target, jobs):
    p.write("leaf.ml", "let value = 40\n")
    p.write("mid.re", 'let value = Leaf.value + 1;\n')
    p.write("top.ml", "let () = Printf.printf \"%d\\n\" (Mid.value + 1)\n")
    out = p.dir / f"chain{exe(target)}"
    p.build(["top.ml", "mid.re", "leaf.ml"], target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == "42\n"


@case("R10", "reason", targets=EXECUTABLE_TARGETS)
def r10(p, target, jobs):
    p.write("greet.re", 'let () = print_endline("no trailing newline")')
    out = p.dir / f"greet{exe(target)}"
    p.build(["greet.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "no trailing newline\n"


@case("R11", "reason")
def r11(p, target, jobs):
    p.write("legacy.re", 'print_endline("legacy reason");\n')
    r = p.lemon("legacy.re", "legacy.byte")
    assert "legacy reason" not in r.stdout
    assert p.execute("bytecode", p.dir / "legacy.byte").stdout == "legacy reason\n"


@case("R12", "reason", targets=EXECUTABLE_TARGETS)
def r12(p, target, jobs):
    p.write("default.re", 'print_endline("default name");\n')
    p.build(["default.re"], target=target, jobs=jobs)
    out = p.default_output("default.re", target)
    assert out.exists(), f"missing default output {out}"
    assert p.execute(target, out).stdout == "default name\n"


# --------------------------------------------------------------------------
# B. Interface enforcement (I01-I12)
# --------------------------------------------------------------------------

def build_runs(p, target, sources, out, expect):
    expected = "hi abstract\n" if expect is None else expect
    p.build(sources, target=target, out=out)
    assert p.execute(target, out).stdout == expected


@case("I01", "interface", targets=EXECUTABLE_TARGETS)
def i01(p, target, jobs):
    p.write("lib.mli", "val greet : unit -> string\n")
    p.write("lib.ml", 'let greet () = "hi abstract"\n')
    p.write("main.re", 'print_endline(Lib.greet());\n')
    build_runs(p, target, ["main.re", "lib.ml", "lib.mli"], p.dir / f"i01{exe(target)}", None)


@case("I02", "interface", targets=EXECUTABLE_TARGETS)
def i02(p, target, jobs):
    p.write("lib.rei", 'let greet: unit => string;\n')
    p.write("lib.ml", 'let greet () = "hi abstract"\n')
    p.write("main.re", 'print_endline(Lib.greet());\n')
    build_runs(p, target, ["main.re", "lib.ml", "lib.rei"], p.dir / f"i02{exe(target)}", None)


@case("I03", "interface", targets=EXECUTABLE_TARGETS)
def i03(p, target, jobs):
    p.write("lib.mli", "val greet : unit -> string\n")
    p.write("lib.re", 'let greet = () => "hi abstract";\n')
    p.write("main.ml", 'let () = print_endline (Lib.greet ())\n')
    build_runs(p, target, ["main.ml", "lib.re", "lib.mli"], p.dir / f"i03{exe(target)}", None)


@case("I04", "interface", targets=EXECUTABLE_TARGETS)
def i04(p, target, jobs):
    p.write("lib.rei", 'let greet: unit => string;\n')
    p.write("lib.re", 'let greet = () => "hi abstract";\n')
    p.write("main.re", 'print_endline(Lib.greet());\n')
    build_runs(p, target, ["main.re", "lib.re", "lib.rei"], p.dir / f"i04{exe(target)}", None)


@case("I05", "interface", targets=EXECUTABLE_TARGETS)
def i05(p, target, jobs):
    p.write("lib.rei", 'let value: int;\n')
    p.write("lib.re", 'let value = "forty two";\n')
    r = p.build(["lib.re", "lib.rei"], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "int" in r.stderr and "string" in r.stderr, r.stderr


@case("I06", "interface", targets=EXECUTABLE_TARGETS)
def i06(p, target, jobs):
    p.write("lib.rei", 'let present: int;\nlet missing: int;\n')
    p.write("lib.re", 'let present = 1;\n')
    r = p.build(["lib.re", "lib.rei"], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "missing" in r.stderr, r.stderr


@case("I07", "interface", targets=EXECUTABLE_TARGETS)
def i07(p, target, jobs):
    p.write("lib.rei", 'let exported: int;\n')
    p.write("lib.re", 'let exported = 40;\nlet hidden = 2;\n')
    p.write("main.re", 'print_int(Lib.exported + Lib.hidden); print_newline();\n')
    r = p.build(["main.re", "lib.re", "lib.rei"], target=target,
                out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "hidden" in r.stderr, r.stderr     # the interface is actually enforced


@case("I08", "interface", targets=EXECUTABLE_TARGETS)
def i08(p, target, jobs):
    p.write("counter.rei", '''
type t;
let make: int => t;
let value: t => int;
''')
    p.write("counter.re", '''
type t = int;
let make = n => n;
let value = t => t;
''')
    p.write("main.re", '''
let c = Counter.make(41);
print_int(Counter.value(c) + 1); print_newline();
''')
    build_runs(p, target, ["main.re", "counter.re", "counter.rei"],
               p.dir / f"i08{exe(target)}", "42\n")


@case("I09", "interface", targets=EXECUTABLE_TARGETS)
def i09(p, target, jobs):
    p.write("counter.rei", 'type t;\nlet make: int => t;\nlet value: t => int;\n')
    p.write("counter.re", 'type t = int;\nlet make = n => n;\nlet value = t => t;\n')
    p.write("main.re", 'print_int(Counter.value(99)); print_newline();\n')
    r = p.build(["main.re", "counter.re", "counter.rei"], target=target,
                out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "t" in r.stderr, r.stderr             # constructing the abstract type directly fails


@case("I10", "interface", targets=EXECUTABLE_TARGETS)
def i10(p, target, jobs):
    p.write("types.re", 'type id = int;\n')
    p.write("store.rei", 'let wrap: Types.id => int;\n')
    p.write("store.re", 'let wrap = (id: Types.id) => id + 1;\n')
    p.write("main.re", 'print_int(Store.wrap(41)); print_newline();\n')
    build_runs(p, target, ["main.re", "store.re", "store.rei", "types.re"],
               p.dir / f"i10{exe(target)}", "42\n")


@case("I11", "interface", targets=EXECUTABLE_TARGETS)
def i11(p, target, jobs):
    bad = p.write("broken.rei", 'let a: int;\nlet b: (int;\n')
    p.write("broken.re", 'let a = 1; let b = 2; let c = 3;\n')
    r = p.build(["broken.re", "broken.rei"], target=target,
                out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "broken.rei" in r.stderr, r.stderr
    assert "line 2" in r.stderr or "line 3" in r.stderr, r.stderr


@case("I12", "interface", targets=EXECUTABLE_TARGETS)
def i12(p, target, jobs):
    p.write("only.rei", 'let x: int;\n')
    out = p.dir / f"x{exe(target)}"
    r = p.build(["only.rei"], target=target, out=out, check=False)
    assert r.returncode != 0
    assert "implementation" in r.stderr, r.stderr
    assert not out.exists(), "nothing may be published when no implementation exists"


# --------------------------------------------------------------------------
# C. Dependency graph and input validation (G01-G14)
# --------------------------------------------------------------------------

@case("G01", "graph", targets=EXECUTABLE_TARGETS, jobs=(4,))
def g01(p, target, jobs):
    p.write("base.ml", "let value = 40\n")
    p.write("left.re", 'let value = Base.value + 1;\n')
    p.write("right.ml", "let value = Base.value + 2\n")
    p.write("main.re", 'print_int(Left.value + Right.value); print_newline();\n')
    out = p.dir / f"diamond{exe(target)}"
    p.build(["main.re", "left.re", "right.ml", "base.ml"], target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == "83\n"


@case("G02", "graph", targets=EXECUTABLE_TARGETS)
def g02(p, target, jobs):
    p.write("alpha.re", 'print_string("a");\n')
    p.write("beta.ml", 'let () = print_string "b\\n"\n')
    out = p.dir / f"both{exe(target)}"
    p.build(["alpha.re", "beta.ml"], target=target, out=out)
    assert p.execute(target, out).stdout == "ab\n"


@case("G03", "graph", targets=EXECUTABLE_TARGETS)
def g03(p, target, jobs):
    # module Local shadows nothing; no external dependency may be invented
    p.write("app.re", '''
module Helper = { let v = 40; };
print_int(Helper.v + 2); print_newline();
''')
    out = p.dir / f"shadow{exe(target)}"
    p.build(["app.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "42\n"


@case("G04", "graph", targets=EXECUTABLE_TARGETS)
def g04(p, target, jobs):
    p.write("app.ml", 'let () = print_endline "/* Phantom.other is only in a comment"\n')
    p.write("phantom.ml", "let unused = 1\n")
    out = p.dir / f"comment{exe(target)}"
    p.build(["app.ml"], target=target, out=out)   # phantom not supplied: must not be needed
    assert p.execute(target, out).stdout == "/* Phantom.other is only in a comment\n"


@case("G05", "graph", targets=EXECUTABLE_TARGETS)
def g05(p, target, jobs):
    p.write("app.re", 'print_int(Absent.value); print_newline();\n')
    r = p.build(["app.re"], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "Absent" in r.stderr, r.stderr


@case("G06", "graph")
def g06(p, target, jobs):
    p.write("a.ml", "let x = B.y\n")
    p.write("b.re", 'let y = A.x;\n')
    r = p.build(["a.ml", "b.re"], check=False)
    assert r.returncode != 0
    low = r.stderr.lower()
    assert "cycle" in low, r.stderr
    assert "A" in r.stderr and "B" in r.stderr, r.stderr


@case("G07", "graph")
def g07(p, target, jobs):
    p.write("one.ml", "let v = Two.v\n")
    p.write("two.re", 'let v = Three.v;\n')
    p.write("three.ml", "let v = One.v\n")
    p.write("valid.re", 'print_endline("valid module");\n')
    out = p.dir / "never"
    r = p.build(["valid.re", "three.ml", "two.re", "one.ml"], out=out, check=False)
    assert r.returncode != 0
    assert "cycle" in r.stderr.lower(), r.stderr
    assert not out.exists()


@case("G08", "graph")
def g08(p, target, jobs):
    src = p.write("dup.re", 'print_endline("dup");\n')
    r = p.build([src, src], check=False)
    assert r.returncode != 0
    assert "duplicate" in r.stderr.lower(), r.stderr


@case("G09", "graph")
def g09(p, target, jobs):
    p.write("thing.ml", "let x = 1\n")
    p.write("thing.re", 'let x = 2;\n')
    r = p.build(["thing.ml", "thing.re"], check=False)
    assert r.returncode != 0
    assert "Thing" in r.stderr and "implementation" in r.stderr, r.stderr


@case("G10", "graph")
def g10(p, target, jobs):
    p.write("thing.mli", "val x : int\n")
    p.write("thing.rei", 'let x: int;\n')
    r = p.build(["thing.mli", "thing.rei"], check=False)
    assert r.returncode != 0
    assert "Thing" in r.stderr and "interface" in r.stderr, r.stderr


@case("G11", "graph")
def g11(p, target, jobs):
    p.write("a/thing.ml", "let x = 1\n")
    p.write("b/thing.re", 'let x = 2;\n')
    r = p.build(["a/thing.ml", "b/thing.re"], check=False)
    assert r.returncode != 0
    assert "Thing" in r.stderr, r.stderr


@case("G12", "graph")
def g12(p, target, jobs):
    # different basenames that normalize to the same compiler module name
    p.write("thing.ml", "let x = 1\n")
    p.write("Thing.re", 'let x = 2;\n')
    r = p.build(["thing.ml", "Thing.re"], check=False)
    assert r.returncode != 0
    assert "Thing" in r.stderr, r.stderr


@case("G13", "graph")
def g13(p, target, jobs):
    r = p.build(["nowhere.re"], check=False)
    assert r.returncode != 0
    assert "nowhere.re" in r.stderr, r.stderr


@case("G14", "graph")
def g14(p, target, jobs):
    p.write("app.txt", "not ocaml\n")
    r = p.build(["app.txt"], check=False)
    assert r.returncode != 0
    for ext in (".ml", ".mli", ".re", ".rei"):
        assert ext in r.stderr, r.stderr


# --------------------------------------------------------------------------
# D. Errors, diagnostics, and preservation (E01-E09)
# --------------------------------------------------------------------------

@case("E01", "errors", targets=EXECUTABLE_TARGETS)
def e01(p, target, jobs):
    p.write("unbalanced.re", 'let start = "x";\nlet f = a => (a + 1;\nprint_endline("done");\n')
    r = p.build(["unbalanced.re"], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "unbalanced.re" in r.stderr, r.stderr
    assert "line 2" in r.stderr, r.stderr


@case("E02", "errors", targets=EXECUTABLE_TARGETS)
def e02(p, target, jobs):
    bad = p.write("bad.re", 'let x: int = "not an int";\n')
    r = p.build([bad], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "bad.re" in r.stderr, r.stderr
    assert "build-" not in r.stderr.replace(".lemon/build-", "\0").replace("\0", ""), \
        "diagnostics must not name normalized AST files"


@case("E03", "errors", targets=EXECUTABLE_TARGETS)
def e03(p, target, jobs):
    p.write("late.re",
            '/* a comment line */\n\n/* another comment */\n\n\n'
            'let ok = 1;\n\n\nlet bad: int = "wrong";\n')
    r = p.build(["late.re"], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "late.re" in r.stderr, r.stderr
    assert "line 9" in r.stderr, r.stderr


@case("E04", "errors", targets=EXECUTABLE_TARGETS)
def e04(p, target, jobs):
    p.write("uni.re", 'let greek = "αβγδε ζηθικ λμνξο πρστυφ";\nlet bad: int = true;\n')
    r = p.build(["uni.re"], target=target, out=p.dir / f"x{exe(target)}", check=False)
    assert r.returncode != 0
    assert "uni.re" in r.stderr and "line 2" in r.stderr, r.stderr


@case("E05", "errors", targets=EXECUTABLE_TARGETS)
def e05(p, target, jobs):
    p.write("app.re", 'print_endline("first version");\n')
    out = p.dir / f"app{exe(target)}"
    p.build(["app.re"], target=target, out=out)
    before = out.read_bytes()
    p.write("app.re", 'let x : int = "broken"\n')
    r = p.build(["app.re"], target=target, out=out, check=False)
    assert r.returncode != 0
    p.assert_output_intact(out, before)
    assert p.execute(target, out).stdout == "first version\n"


@case("E06", "errors", targets=EXECUTABLE_TARGETS)
def e06(p, target, jobs):
    p.write("lib.rei", 'let v: int;\n')
    p.write("lib.re", 'let v = 1;\n')
    p.write("main.re", 'print_int(Lib.v); print_newline();\n')
    out = p.dir / f"app{exe(target)}"
    p.build(["main.re", "lib.re", "lib.rei"], target=target, out=out)
    before = out.read_bytes()
    p.write("lib.rei", 'let v: string;\n')
    r = p.build(["main.re", "lib.re", "lib.rei"], target=target, out=out, check=False)
    assert r.returncode != 0
    p.assert_output_intact(out, before)
    assert p.execute(target, out).stdout == "1\n"


@case("E07", "errors", targets=EXECUTABLE_TARGETS)
def e07(p, target, jobs):
    # a mid-wave failure with many other jobs active
    for i in range(10):
        p.write(f"part{i}.re", f'print_endline("part{i}");\n')
    p.write("boom.re", 'let x : int = "explodes";\n')
    sources = [f"part{i}.re" for i in range(10)] + ["boom.re"]
    out = p.dir / f"app{exe(target)}"
    r = p.build(sources, target=target, jobs=4, out=out, check=False)
    assert r.returncode != 0
    assert not out.exists(), "no partial executable may be published"
    assert not out.with_suffix(".tmp").exists()


@case("E08", "errors", targets=EXECUTABLE_TARGETS)
def e08(p, target, jobs):
    p.write("app.re", 'let broken : int = "x";\n')
    r = p.build(["app.re"], target=target, out=p.dir / f"a{exe(target)}", check=False)
    assert r.returncode != 0
    p.write("app.re", 'print_endline("recovered");\n')
    out = p.dir / f"a{exe(target)}"
    p.build(["app.re"], target=target, out=out)
    assert p.execute(target, out).stdout == "recovered\n"
    leftovers = list((p.dir / ".lemon").iterdir()) if (p.dir / ".lemon").exists() else []
    assert leftovers == [], f"stale build dirs: {leftovers}"


@case("E09", "errors", targets=EXECUTABLE_TARGETS)
def e09(p, target, jobs):
    p.write("warn.re",
            'let pick = (x: option(int)) => switch (x) { | Some(v) => v };\n'
            'let () = print_int(pick(Some(2))); print_newline();\n')
    out = p.dir / f"w{exe(target)}"
    r = p.build(["warn.re"], target=target, out=out)   # succeeds with a warning
    assert "warn.re" in r.stderr, r.stderr             # warning names the original source
    assert p.execute(target, out).stdout == "2\n"


# --------------------------------------------------------------------------
# E. Worker isolation and build semantics (W01-W06, W10, W12)
# --------------------------------------------------------------------------

def write_twelve_modules(p, reason=True):
    for i in range(12):
        if reason:
            p.write(f"part{i}.re", f'let answer = 30 + {i};\n')
        else:
            p.write(f"part{i}.ml", f"let answer = 30 + {i}\n")


@case("W01", "workers", targets=EXECUTABLE_TARGETS, jobs=(4,))
def w01(p, target, jobs):
    write_twelve_modules(p)
    p.write("sum.re",
            'let total = [| Part0.answer, Part1.answer, Part2.answer, Part3.answer,'
            ' Part4.answer, Part5.answer, Part6.answer, Part7.answer,'
            ' Part8.answer, Part9.answer, Part10.answer, Part11.answer |]'
            ' |> Array.fold_left((a, b) => a + b, 0);\n'
            'print_int(total); print_newline();\n')
    out = p.dir / f"sum{exe(target)}"
    p.build(["sum.re"] + [f"part{i}.re" for i in range(12)], target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == f"{sum(30 + i for i in range(12))}\n"


@case("W02", "workers", targets=EXECUTABLE_TARGETS, jobs=(4,))
def w02(p, target, jobs):
    # six dependent layers: five-plus waves through a four-worker pool
    chain = ["level0.ml", "level1.re", "level2.ml", "level3.re", "level4.ml", "level5.re"]
    p.write("level0.ml", "let v = 1\n")
    for n, prev in zip(chain[1:], chain):
        lang = ".re" if n.endswith(".re") else ".ml"
        mod = prev.split(".")[0].capitalize()
        if lang == ".re":
            p.write(n, f'let v = {mod}.v + 1;\n')
        else:
            p.write(n, f"let v = {mod}.v + 1\n")
    p.write("main.re", 'print_int(Level5.v); print_newline();\n')
    out = p.dir / f"chain{exe(target)}"
    p.build(["main.re"] + list(reversed(chain)), target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == "6\n"


@case("W03", "workers", targets=EXECUTABLE_TARGETS, jobs=(4,))
def w03(p, target, jobs):
    # identical local names, different types and values
    p.write("a.re", 'let common = "alpha";\n')
    p.write("b.re", 'let common = 2;\n')
    p.write("c.re", 'type t = {common: bool};\nlet common = {common: true};\n')
    p.write("main.re", 'print_endline(A.common); print_int(B.common); print_endline(C.common.common ? " t" : " f");\n')
    out = p.dir / f"iso{exe(target)}"
    p.build(["main.re", "a.re", "b.re", "c.re"], target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == "alpha\n2 t\n"


@case("W04", "workers", targets=EXECUTABLE_TARGETS, jobs=(4,))
def w04(p, target, jobs):
    for i in range(5):
        proj = p.mkdir(f"run{i}")
        # reuse the scenario body inline: independent modules + chain + shadows
        for j in range(12):
            (proj / f"part{j}.re").write_text(f'let answer = {i}0 + {j};\n')
        (proj / "leaf.ml").write_text("let v = 1\n")
        for n, prev in zip(("l1.re", "l2.ml", "l3.re"), ("leaf.ml", "l1.re", "l2.ml")):
            mod = prev.split(".")[0].capitalize()
            code = f'let v = {mod}.v + 1;\n' if n.endswith(".re") else f"let v = {mod}.v + 1\n"
            (proj / n).write_text(code)
        (proj / "main.re").write_text(
            'let s = Part0.answer + Part11.answer; print_int(s + L3.v); print_newline();\n')
        out = proj / f"m{exe(target)}"
        r = p.run(["ocamlrun", str(LEMON_PATH),
                   "build", "--target", target, "-j", "4", "-o", str(out),
                   str(proj / "main.re")] +
                  [str(proj / f"part{j}.re") for j in range(12)] +
                  [str(proj / x) for x in ("l3.re", "l2.ml", "l1.re", "leaf.ml")],
                  check=True)
        assert p.execute(target, out).stdout == f"{i * 10 + 0 + i * 10 + 11 + 4}\n"


@case("W05", "workers", targets=EXECUTABLE_TARGETS)
def w05(p, target, jobs):
    write_twelve_modules(p)
    p.write("sum.re", 'print_int(Part0.answer + Part11.answer); print_newline();\n')
    sources = ["sum.re"] + [f"part{i}.re" for i in range(12)]
    results = []
    for workers in (1, 4):
        out = p.dir / f"sum{workers}{exe(target)}"
        p.build(sources, target=target, jobs=workers, out=out)
        results.append(p.execute(target, out).stdout)
    assert results[0] == results[1], "worker count changed observable results"


@case("W06", "workers", targets=("native",), jobs=(4,))
def w06(p, target, jobs):
    write_twelve_modules(p, reason=False)
    p.write("sum.ml", 'let () = Printf.printf "%d\\n" (Part0.answer + Part11.answer)\n')
    out = p.dir / "sum.native"
    p.build(["sum.ml"] + [f"part{i}.ml" for i in range(12)], target=target, jobs=jobs, out=out)
    assert p.execute(target, out).stdout == f"{30 + 30 + 11}\n"


@case("W10", "workers", needs=("strace",))
def w10(p, target, jobs):
    import subprocess
    if __import__("platform").system() != "Linux":
        import lemon_harness
        raise lemon_harness.Skip("strace fixtures run on Linux")
    p.write("app.re", 'print_endline("traced");\n')
    out = p.dir / "app.byte"
    trace = p.dir / "trace.txt"
    with open(trace, "w") as fh:
        subprocess.run(["strace", "-f", "-e", "trace=execve,fork,vfork",
                        "ocamlrun", str(LEMON_PATH), "build", "-o", str(out), "app.re"],
                       cwd=str(p.dir), stdout=fh, stderr=fh, timeout=int(__import__("os").environ.get("LEMON_BUILD_TIMEOUT","180")), check=True)
    lines = [l for l in trace.read_text().splitlines() if "execve" in l]
    # No compiler processes, ever. Two allowed shapes:
    # - the initial ocamlrun (and strace's own execve line)
    # - the stock OCaml linker's ONE shell probe: with a long esy toolchain
    #   path the executable shebang header falls back to a /bin/sh script,
    #   and Bytelink.find_bin_sh runs `command -p -v sh` (Sys.command) once
    #   when the output executable is linked (bytecomp/bytelink.ml).
    def allowed(line):
        if "ocamlrun" in line or "strace" in line:
            return True
        return "command" in line and "-v" in line and "sh" in line
    bad = [l for l in lines if not allowed(l)]
    probes = [l for l in lines if "command" in l and "ocamlrun" not in l]
    assert lines, "no trace captured"
    assert not bad, bad
    assert len(probes) <= 1, probes


@case("W12", "workers", targets=EXECUTABLE_TARGETS)
def w12(p, target, jobs):
    import os
    import stat
    shims = p.mkdir("shims")
    for name in ("refmt", "ocamlfind", "ppx_jane", "ocamlpp"):
        shim = shims / name
        shim.write_text("#!/bin/sh\nexit 42\n")
        shim.chmod(0o755)
        assert shim.stat().st_mode & stat.S_IXUSR
    env = dict(os.environ)
    env["PATH"] = f"{shims}:{env['PATH']}"
    p.write("app.re", 'print_endline("no external tools");\n')
    out = p.dir / f"app{exe(target)}"
    p.build(["app.re"], target=target, out=out, env=env)
    assert p.execute(target, out).stdout == "no external tools\n"


# --------------------------------------------------------------------------
# F. JavaScript backend (J01-J12)
# --------------------------------------------------------------------------

@case("J01", "js", targets=("js",))
def j01(p, target, jobs):
    p.write("main.ml", 'let () = print_endline "hello from ocaml js"\n')
    p.build(["main.ml"], target="js", out=p.dir / "out")
    assert p.execute("js", p.dir / "out" / "main.js").stdout == "hello from ocaml js\n"


@case("J02", "js", targets=("js",))
def j02(p, target, jobs):
    p.write("main.re", 'print_endline("hello from reason js");\n')
    p.build(["main.re"], target="js", out=p.dir / "out")
    assert p.execute("js", p.dir / "out" / "main.js").stdout == "hello from reason js\n"


@case("J03", "js", targets=("js",), jobs=(2,))
def j03(p, target, jobs):
    p.write("dep.ml", "let v = List.length [1; 2; 3]\n")
    p.write("mid.re", 'let v = Dep.v + 1;\n')
    p.write("main.re", 'print_int(Mid.v); print_newline();\n')
    p.build(["main.re", "mid.re", "dep.ml"], target="js", jobs=jobs, out=p.dir / "out")
    assert p.execute("js", p.dir / "out" / "main.js").stdout == "4\n"


@case("J04", "js", targets=("js",))
def j04(p, target, jobs):
    p.write("ops.re", '''
type color = Red | Green | Blue;
exception TooBig;
let describe = c =>
  switch (c) {
  | Red => "red"
  | Green => "green"
  | Blue => "blue"
  };
let safeDouble = n =>
  if (n > 100) { raise(TooBig); } else { n * 2 };
let () = {
  print_endline(describe(Red));
  print_endline(describe(Blue));
  print_int(safeDouble(21));
  print_newline();
  print_int(List.fold_left((a, b) => a + b, 0, [1, 2, 3, 4]));
  print_newline();
  print_endline(string_of_int(int_of_string("7")));
  print_int(String.length("héllo"));  // UTF-16 code units under JS
  print_newline();
  (try (ignore(safeDouble(1000))) {
   | TooBig => print_endline("caught TooBig")
   });
};
''')
    p.build(["ops.re"], target="js", out=p.dir / "out")
    assert p.execute("js", p.dir / "out" / "ops.js").stdout == (
        "red\nblue\n42\n10\n7\n6\ncaught TooBig\n")


@case("J05", "js", targets=("js",), jobs=(2,))
def j05(p, target, jobs):
    # each dependency is compiled by a different private worker instance
    for i in range(6):
        p.write(f"m{i}.re", f'let v = {i};\n')
    p.write("main.re", 'print_int(M0.v + M5.v); print_newline();\n')
    p.build(["main.re"] + [f"m{i}.re" for i in range(6)], target="js", jobs=jobs,
             out=p.dir / "out")
    assert p.execute("js", p.dir / "out" / "main.js").stdout == "5\n"


@case("J06", "js", targets=("bytecode", "native", "js"))
def j06(p, target, jobs):
    p.write("lib.re", 'let answer = 42;\n')
    p.write("main.re", 'print_int(Lib.answer); print_newline();\n')
    if target == "js":
        p.build(["main.re", "lib.re"], target="js", out=p.dir / "js-out")
        got = p.execute("js", p.dir / "js-out" / "main.js").stdout
    else:
        out = p.dir / f"app{exe(target)}"
        p.build(["main.re", "lib.re"], target=target, out=out)
        got = p.execute(target, out).stdout
    assert got == "42\n"


@case("J07", "js", targets=("js",))
def j07(p, target, jobs):
    import shutil as _sh
    p.write("main.re", 'print_endline("relocatable");\n')
    p.build(["main.re"], target="js", out=p.dir / "out")
    moved = p.dir / "moved elsewhere"
    _sh.move(str(p.dir / "out"), str(moved))
    assert p.execute("js", moved / "main.js").stdout == "relocatable\n"


@case("J08", "js", targets=("js",))
def j08(p, target, jobs):
    p.mkdir("sp ace dir")
    p.write("sp ace dir/main.re", 'print_endline("spaces");\n')
    p.build(["sp ace dir/main.re"], target="js", out="sp ace dir/out")
    assert p.execute("js", p.dir / "sp ace dir" / "out" / "main.js").stdout == "spaces\n"


@case("J09", "js", targets=("js",))
def j09(p, target, jobs):
    p.write("app.re", 'print_endline("x");\n')
    r = p.build(["app.re"], target="js", out=p.dir / "out", extra=["--native"], check=False)
    assert r.returncode != 0 and "combine" in r.stderr.lower(), r.stderr


@case("J10", "js", targets=("js", "bytecode"))
def j10(p, target, jobs):
    p.write("app.re", 'print_endline("x");\n')
    if target == "js":
        r = p.build(["app.re"], target="js", out=p.dir / "o", extra=["-o", "x.js"], check=False)
    else:
        r = p.build(["app.re"], target="bytecode", out=p.dir / "x.byte",
                    extra=["--out-dir", "d"], check=False)
    assert r.returncode != 0, "conflicting output option accepted"


@case("J11", "js", targets=("js",))
def j11(p, target, jobs):
    p.write("app.re", 'print_endline("x");\n')
    r = p.build(["app.re"], target="js", out=p.dir / "out", extra=["--target", "wasm"], check=False)
    assert r.returncode != 0
    assert "bytecode" in r.stderr and "native" in r.stderr and "js" in r.stderr, r.stderr


@case("J12", "js", targets=("js",))
def j12(p, target, jobs):
    p.write("lib.re", 'let v = 1;\n')
    p.write("main.re", 'print_int(Lib.v); print_newline();\n')
    p.build(["main.re", "lib.re"], target="js", out=p.dir / "out")
    assert p.execute("js", p.dir / "out" / "main.js").stdout == "1\n"
    p.write("lib.re", 'let v : int = "broken";\n')
    r = p.build(["main.re", "lib.re"], target="js", out=p.dir / "out", check=False)
    assert r.returncode != 0
    assert p.execute("js", p.dir / "out" / "main.js").stdout == "1\n"   # earlier output intact


# --------------------------------------------------------------------------
# G. JavaScript output publication (P01-P12)
# --------------------------------------------------------------------------

@case("P01", "publication", targets=("js",))
def p01(p, target, jobs):
    p.write("main.re", 'print_endline("first publish");\n')
    out = p.dir / "out"
    p.build(["main.re"], target="js", out=out)
    assert (out / ".lemon-owned").exists(), "ownership marker missing"
    assert (out / "main.js").exists()
    assert (out / "node_modules" / "melange").is_dir()
    assert p.execute("js", out / "main.js").stdout == "first publish\n"


@case("P02", "publication", targets=("js",))
def p02(p, target, jobs):
    p.write("main.re", 'print_endline("v1");\n')
    out = p.dir / "out"
    p.build(["main.re"], target="js", out=out)
    p.write("main.re", 'print_endline("v2");\n')
    p.build(["main.re"], target="js", out=out)
    assert p.execute("js", out / "main.js").stdout == "v2\n"
    assert (out / ".lemon-owned").exists()


@case("P03", "publication", targets=("js",))
def p03(p, target, jobs):
    p.write("extra.re", 'let x = 1;\n')
    p.write("main.re", 'print_endline("shrunk");\n')
    out = p.dir / "out"
    p.build(["main.re", "extra.re"], target="js", out=out)
    assert (out / "extra.js").exists()
    p.build(["main.re"], target="js", out=out)
    assert not (out / "extra.js").exists(), "obsolete module still published"
    assert p.execute("js", out / "main.js").stdout == "shrunk\n"


@case("P04", "publication", targets=("js",))
def p04(p, target, jobs):
    out = p.mkdir("out")
    (out / "precious.txt").write_text("do not touch\n")
    p.write("main.re", 'print_endline("nope");\n')
    r = p.build(["main.re"], target="js", out=out, check=False)
    assert r.returncode != 0
    assert "refus" in r.stderr.lower(), r.stderr
    assert (out / "precious.txt").read_text() == "do not touch\n"
    assert not (out / "main.js").exists()


@case("P05", "publication", targets=("js",))
def p05(p, target, jobs):
    out = p.mkdir("out")
    p.write("out/main.re", 'print_endline("inside");\n')
    src = p.dir / "out" / "main.re"
    out2 = p.dir / "out2"
    (out / ".lemon-owned").write_text("lemon js output\n")
    # a fresh destination publishes fine even when the source happens to live
    # inside some other (owned) lemon output directory
    p.build([src], target="js", out=out2)
    # now target the directory that actually contains the source
    r2 = p.build([src], target="js", out=out, check=False)
    assert r2.returncode != 0
    assert "refusing" in r2.stderr, r2.stderr
    assert src.exists(), "input source was harmed"


@case("P06", "publication", targets=("js",), needs=("symlinks",))
def p06(p, target, jobs):
    import os
    real = p.mkdir("real")
    out = p.dir / "out"
    os.symlink(str(real), str(out))
    (real / "keep.txt").write_text("kept\n")
    p.write("main.re", 'print_endline("no");\n')
    r = p.build(["main.re"], target="js", out=out, check=False)
    assert r.returncode != 0
    assert "symlink" in r.stderr.lower(), r.stderr
    assert (real / "keep.txt").exists()
    assert out.is_symlink()


@case("P07", "publication", targets=("js",))
def p07(p, target, jobs):
    out = p.dir / "out"
    (p.dir / "out.lock").write_text("")          # a publisher is already active
    p.write("main.re", 'print_endline("no");\n')
    r = p.build(["main.re"], target="js", out=out, check=False)
    assert r.returncode != 0
    assert "lock" in r.stderr.lower(), r.stderr
    assert not out.exists()


@case("P08", "publication", targets=("js",))
def p08(p, target, jobs):
    p.write("main.re", 'print_endline("good");\n')
    out = p.dir / "out"
    p.build(["main.re"], target="js", out=out)
    before = sorted((f.relative_to(out), f.read_bytes()) for f in out.rglob("*") if f.is_file())
    p.write("main.re", 'let x : int = "bad";\n')
    r = p.build(["main.re"], target="js", out=out, check=False)
    assert r.returncode != 0
    after = sorted((f.relative_to(out), f.read_bytes()) for f in out.rglob("*") if f.is_file())
    assert before == after, "failed rebuild changed published output"
    assert p.execute("js", out / "main.js").stdout == "good\n"


@case("P09", "publication", targets=("js",))
def p09(p, target, jobs):
    import shutil as _sh
    p.write("main.re", 'print_endline("v1");\n')
    out = p.dir / "out"
    p.build(["main.re"], target="js", out=out)
    # simulate an interrupted replacement: output moved to backup, staging gone
    _sh.move(str(out), str(p.dir / "out.lemon-backup"))
    p.write("main.re", 'print_endline("v2");\n')
    r = p.build(["main.re"], target="js", out=out)
    assert "recovering previous output" in r.stdout, r.stdout
    assert p.execute("js", out / "main.js").stdout == "v2\n"
    assert not (p.dir / "out.lemon-backup").exists()


@case("P10", "publication", targets=("js",))
def p10(p, target, jobs):
    out = p.dir / "out"
    p.write("main.re", 'print_endline("stage");\n')
    stale = p.mkdir("out.lemon-stage-99999")
    (stale / "junk.js").write_text("// stale\n")
    p.build(["main.re"], target="js", out=out)
    assert (out / "main.js").exists()
    assert not stale.exists(), "stale staging directory not cleaned"
    assert p.execute("js", out / "main.js").stdout == "stage\n"


@case("P11", "publication", targets=("js",), needs=("unprivileged",))
def p11(p, target, jobs):
    import os, stat as stat_mod
    if not hasattr(os, "geteuid") or os.geteuid() == 0:
        import lemon_harness
        raise lemon_harness.Skip("meaningful only for unprivileged users")
    locked = p.mkdir("locked")
    os.chmod(locked, stat_mod.S_IREAD | stat_mod.S_IEXEC)
    p.write("main.re", 'print_endline("x");\n')
    r = p.build(["main.re"], target="js", out=locked / "out", check=False)
    assert r.returncode != 0
    assert not (locked / "out").exists()
    assert list(locked.glob(".lemon*")) == [], "staging or lock leaked"


@case("P12", "publication", targets=("js",))
def p12(p, target, jobs):
    import subprocess
    p.write("a.re", 'print_endline("A");\n')
    p.write("b.re", 'print_endline("B");\n')
    env = None
    targets = [("outa", "a.re"), ("outb", "b.re")]
    procs = [
        subprocess.Popen(["ocamlrun", str(LEMON_PATH), "build", "--target", "js",
                          "--out-dir", str(p.dir / outdir), str(p.dir / src)],
                         cwd=str(p.dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for outdir, src in targets]
    for pr in procs:
        o, e = pr.communicate(timeout=300)
        assert pr.returncode == 0, (o, e)
    assert p.execute("js", p.dir / "outa" / "a.js").stdout == "A\n"
    assert p.execute("js", p.dir / "outb" / "b.js").stdout == "B\n"


# --------------------------------------------------------------------------
# W11: JavaScript builds stay in-process
# --------------------------------------------------------------------------

@case("W11", "workers", needs=("strace",))
def w11(p, target, jobs):
    import subprocess
    import platform
    if platform.system() != "Linux":
        import lemon_harness
        raise lemon_harness.Skip("strace fixtures run on Linux")
    p.write("dep.re", 'let v = 1;\n')
    p.write("main.re", 'print_int(Dep.v); print_newline();\n')
    out = p.dir / "out"
    trace = p.dir / "trace.txt"
    with open(trace, "w") as fh:
        subprocess.run(["strace", "-f", "-e", "trace=execve,fork,vfork",
                        "ocamlrun", str(LEMON_PATH), "build", "--target", "js",
                        "--out-dir", str(out), "main.re", "dep.re"],
                       cwd=str(p.dir), stdout=fh, stderr=fh,
                       timeout=int(__import__("os").environ.get("LEMON_BUILD_TIMEOUT", "180")),
                       check=True)
    lines = [l for l in trace.read_text().splitlines() if "execve" in l]
    assert lines
    assert all("ocamlrun" in l or "strace" in l for l in lines), lines
    assert len(lines) <= 2, lines


# --------------------------------------------------------------------------
# H. JSX and React compilation (X01-X18), server-rendered
# --------------------------------------------------------------------------

def render_js(p, sources, entry):
    out = p.dir / "out"
    p.build(sources, target="js", out=out, extra=["--react"])
    # melange publishes module files lowercase-first (dune melange mode
    # convention); only the first character differs from the module name
    return p.execute("js", out / (entry[0].lower() + entry[1:] + ".js")).stdout


@case("X01", "react", targets=("js",))
def x01(p, target, jobs):
    p.write("greet.re", '''
[@react.component]
let make = () => <p id="hello"> {React.string("intrinsic text")} </p>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<Greet />));
''')
    assert render_js(p, ["main.re", "greet.re"], "Main") == '<p id="hello">intrinsic text</p>\n'


@case("X02", "react", targets=("js",))
def x02(p, target, jobs):
    p.write("nameplate.re", '''
[@react.component]
let make = () => <span> {React.string("a component")} </span>;
''')
    p.write("app.re", '''
let markup = ReactDOMServer.renderToStaticMarkup(<Nameplate />);
print_endline(markup);
''')
    assert render_js(p, ["app.re", "nameplate.re"], "App") == "<span>a component</span>\n"


@case("X03", "react", targets=("js",))
def x03(p, target, jobs):
    p.write("badge.re", '''
[@react.component]
let make = (~label, ~count) =>
  <div className=label> <em> {React.string(label)} </em> <strong> {React.string(string_of_int(count))} </strong> </div>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<Badge label="hi" count=7 />));
''')
    assert render_js(p, ["main.re", "badge.re"], "Main") == \
        '<div class="hi"><em>hi</em><strong>7</strong></div>\n'




@case("X04", "react", targets=("js",))
def x04(p, target, jobs):
    p.write("app.re", '''
[@react.component]
let make = () =>
  <>
    <li> {React.string("first")} </li>
    <li> {React.string("second")} </li>
    <li> {React.string("third")} </li>
  </>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<App />));
''')
    assert render_js(p, ["main.re", "app.re"], "Main") == \
        "<li>first</li><li>second</li><li>third</li>\n"


@case("X05", "react", targets=("js",))
def x05(p, target, jobs):
    p.write("app.re", '''
[@react.component]
let make = (~show) =>
  <div>
    {show ? <b> {React.string("visible")} </b> : React.null}
  </div>;
''')
    p.write("main.re", '''
let () = {
  print_endline(ReactDOMServer.renderToStaticMarkup(<App show=true />));
  print_endline(ReactDOMServer.renderToStaticMarkup(<App show=false />));
};
''')
    assert render_js(p, ["main.re", "app.re"], "Main") == "<div><b>visible</b></div>\n<div></div>\n"


@case("X06", "react", targets=("js",))
def x06(p, target, jobs):
    p.write("app.re", '''
[@react.component]
let make = () =>
  <ol>
    <li key="a"> {React.string("alpha")} </li>
    <li key="b"> {React.string("beta")} </li>
    <li key="c"> {React.string("gamma")} </li>
  </ol>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<App />));
''')
    assert render_js(p, ["main.re", "app.re"], "Main") == \
        "<ol><li>alpha</li><li>beta</li><li>gamma</li></ol>\n"


@case("X07", "react", targets=("js",))
def x07(p, target, jobs):
    p.write("label.re", '''
[@react.component]
let make = (~suffix=?, ()) =>
  <span> {React.string("text" ++ (switch (suffix) { | None => "" | Some(s) => s }))} </span>;
''')
    p.write("main.re", '''
let () = {
  print_endline(ReactDOMServer.renderToStaticMarkup(<Label />));
  print_endline(ReactDOMServer.renderToStaticMarkup(<Label suffix="!" />));
};
''')
    got = render_js(p, ["main.re", "label.re"], "Main")
    assert got == "<span>text</span>\n<span>text!</span>\n"


@case("X08", "react", targets=("js",))
def x08(p, target, jobs):
    p.write("app.re", '''
let text = {|<b> & 'quoted' "double"</b>|};
[@react.component]
let make = () => <code> {React.string(text)} </code>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<App />));
''')
    got = render_js(p, ["main.re", "app.re"], "Main")
    assert got == "<code>&lt;b&gt; &amp; &#x27;quoted&#x27; &quot;double&quot;&lt;/b&gt;</code>\n"


@case("X09", "react", targets=("js",))
def x09(p, target, jobs):
    p.write("annotated.re", '''
[@react.component]
let make = (~width: int, ~title: string, ~children) =>
  <section className={string_of_int(width) ++ " " ++ title}> children </section>;
''')
    p.write("main.re", '''
print_endline(
  ReactDOMServer.renderToStaticMarkup(
    <Annotated width=42 title="the title"> {React.string("kid")} </Annotated>,
  ),
);
''')
    assert render_js(p, ["main.re", "annotated.re"], "Main") == \
        '<section class="42 the title">kid</section>\n'


@case("X10", "react", targets=("js",))
def x10(p, target, jobs):
    # Lazy is referenced only through JSX; it must still be scheduled
    p.write("lazy.re", '''
[@react.component]
let make = () => <u> {React.string("scheduled")} </u>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<Lazy />));
''')
    assert render_js(p, ["main.re", "lazy.re"], "Main") == "<u>scheduled</u>\n"


@case("X11", "react", targets=("js",), jobs=(4,))
def x11(p, target, jobs):
    for i in range(5):
        p.write(f"c{i}.re", f'''
[@react.component]
let make = () => <i className="part{i}"> {{React.string("part{i}")}} </i>;
''')
    p.write("main.re", "let markup = <main> " +
            " ".join(f"<C{i} />" for i in range(5)) + " </main>;\n" +
            'print_endline(ReactDOMServer.renderToStaticMarkup(markup));\n')
    expected = "<main>" + "".join(f'<i class="part{i}">part{i}</i>' for i in range(5)) + "</main>\n"
    got = render_js(p, ["main.re"] + [f"c{i}.re" for i in range(5)], "Main")
    assert got == expected


@case("X12", "react", targets=("js",))
def x12(p, target, jobs):
    p.write("helper.ml", "let tag = \"ml-helper\"\n")
    p.write("widget.re", '''
[@react.component]
let make = () => <small> {React.string(Helper.tag)} </small>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<Widget />));
''')
    assert render_js(p, ["main.re", "widget.re", "helper.ml"], "Main") == \
        "<small>ml-helper</small>\n"


@case("X13", "react", targets=("js",))
def x13(p, target, jobs):
    p.write("typed.re", '''
[@react.component]
let make = (~level: int) => <h1> {React.string(string_of_int(level))} </h1>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<Typed level="high" />));
''')
    r = p.build(["main.re", "typed.re"], target="js", out=p.dir / "out",
                extra=["--react"], check=False)
    assert r.returncode != 0
    assert ("typed.re" in r.stderr or "main.re" in r.stderr), r.stderr  # original sources


@case("X14", "react", targets=("js",))
def x14(p, target, jobs):
    p.write("needs.re", '''
[@react.component]
let make = (~name) => <p> {React.string(name)} </p>;
''')
    p.write("main.re", '''
print_endline(ReactDOMServer.renderToStaticMarkup(<Needs />));
''')
    r = p.build(["main.re", "needs.re"], target="js", out=p.dir / "out",
                extra=["--react"], check=False)
    assert r.returncode != 0
    assert "name" in r.stderr, r.stderr


@case("X15", "react", targets=("js",))
def x15(p, target, jobs):
    p.write("broken.re", '''
[@react.component]
let make = () => <div> <span> {React.string("unbalanced")}
</div>;
''')
    r = p.build(["broken.re"], target="js", out=p.dir / "out",
                extra=["--react"], check=False)
    assert r.returncode != 0
    assert "broken.re" in r.stderr and "line" in r.stderr, r.stderr


@case("X16", "react", targets=("js",))
def x16(p, target, jobs):
    p.write("badannot.re", '''
[@react.component nonsense]
let make = () => <div/>;
print_endline("never");
''')
    r = p.build(["badannot.re"], target="js", out=p.dir / "out",
                extra=["--react"], check=False)
    assert r.returncode != 0
    assert not (p.dir / "out").exists(), "partial publication after bad annotation"


@case("X17", "react", targets=("bytecode",))
def x17(p, target, jobs):
    p.write("app.re", '[@react.component]\nlet make = () => <div/>;\n')
    r = p.build(["app.re"], target="bytecode", out=p.dir / "x.byte",
                extra=["--react"], check=False)
    assert r.returncode != 0
    assert "React JSX requires the JavaScript target" in r.stderr
    assert "bytecode" in r.stderr


@case("X18", "react", targets=("native",))
def x18(p, target, jobs):
    p.write("app.re", '[@react.component]\nlet make = () => <div/>;\n')
    r = p.build(["app.re"], target="native", out=p.dir / "x.native",
                extra=["--react"], check=False)
    assert r.returncode != 0
    assert "React JSX requires the JavaScript target" in r.stderr
    assert "native" in r.stderr


# --------------------------------------------------------------------------
# I. Browser application (B01-B08): production Vite bundle + Playwright
# --------------------------------------------------------------------------

def build_browser_app(p):
    """Clean install + Lemon compile + Vite production build in a fresh copy
    of examples/react-counter (B08: no preexisting generated output)."""
    import shutil
    import subprocess
    src = Path(__file__).resolve().parent.parent / "examples" / "react-counter"
    app = p.mkdir("app")
    for name in ("App.re", "Counter.re", "Main.re", "index.html",
                 "vite.config.js", "package.json"):
        shutil.copy(src / name, app / name)
    p.build(["App.re", "Counter.re", "Main.re"], target="js", out=app / "js-out",
            extra=["--react"], cwd=app)
    real_node = __import__("lemon_harness").NODE
    npm_cli = Path(real_node).parent / ".." / "libexec/lib/node_modules/npm/bin/npm-cli.js"
    npm_cli = str(npm_cli.resolve())
    install_env = dict(os.environ)
    install_env["PATH"] = str(Path(real_node).parent) + os.pathsep + install_env["PATH"]
    r = subprocess.run([real_node, npm_cli, "install", "--no-audit", "--no-fund"],
                       cwd=str(app), timeout=600, env=install_env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("npm install failed:\n" + r.stdout + r.stderr)
    (app / "npm-install.log").write_text(r.stdout + r.stderr)
    subprocess.run([real_node, "node_modules/vite/bin/vite.js", "build"],
                   cwd=str(app), check=True, timeout=600,
                   stdout=subprocess.DEVNULL)
    return app


def run_browser_check(app, p, step):
    import shutil
    import subprocess
    import threading
    import time
    import urllib.request
    import lemon_harness
    node = lemon_harness.NODE
    # serve the production bundle
    port = 4180 + (hash(step) % 500)
    server = subprocess.Popen(
        [node, "node_modules/vite/bin/vite.js", "preview", "--port", str(port), "--strictPort"],
        cwd=str(app), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://localhost:{port}/", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        spec = app / "counter.spec.mjs"
        shutil.copy(Path(__file__).resolve().parent / "browser" / "counter.spec.mjs", spec)
        env = dict(os.environ)
        env["DIST_DIR"] = str(app / "dist")
        env["PORT"] = str(port)
        env["STEP"] = step
        r = subprocess.run([node, str(spec)], cwd=str(app), env=env,
                           text=True, capture_output=True, timeout=180)
        assert r.returncode == 0, (step, r.stdout, r.stderr)
    finally:
        server.terminate()
        server.wait(timeout=30)


@case("B01", "browser", targets=("js",))
def b01(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "mount")


@case("B02", "browser", targets=("js",))
def b02(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "click-once")


@case("B03", "browser", targets=("js",))
def b03(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "click-many")


@case("B04", "browser", targets=("js",))
def b04(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "click-many")   # nested <p.hint> state update


@case("B05", "browser", targets=("js",))
def b05(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "click-many")   # conditional render appears


@case("B06", "browser", targets=("js",))
def b06(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "reload")


@case("B07", "browser", targets=("js",))
def b07(p, target, jobs):
    app = build_browser_app(p)
    run_browser_check(app, p, "full")         # console/page-error watcher covers all flows


@case("B08", "browser", targets=("js",))
def b08(p, target, jobs):
    app = build_browser_app(p)                # clean install: built from scratch above
    run_browser_check(app, p, "mount")
