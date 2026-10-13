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
