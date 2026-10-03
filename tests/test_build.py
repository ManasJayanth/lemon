"""End-to-end tests: execute every produced program, including parallel builds."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
lemon = root / '_esy/default/build/lemon.byte'

def call(args, cwd, success=True):
    p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert (p.returncode == 0) == success, (args, p.stdout, p.stderr)
    return p

with tempfile.TemporaryDirectory(prefix='lemon test ') as directory:
    cwd = Path(directory)
    def write(name, text):
        (cwd / name).write_text(text)
    write('value.mli', 'val answer : int\n')
    write('value.ml', 'let answer = 40\n')
    for i in range(12):
        write(f'part{i}.ml', f'let answer = Value.answer + {i}\n')
    write('main.ml', 'let () = Printf.printf "%d\\n" (Part0.answer + Part2.answer)\n')
    sources = ['main.ml'] + [f'part{i}.ml' for i in range(12)] + ['value.ml', 'value.mli']
    for native in (False, True):
        output = 'program.exe' if native else 'program.byte'
        for workers in (1, 4):
            call(['ocamlrun', str(lemon), 'build', '-j', str(workers), '-o', output]
                 + (['--native'] if native else []) + sources, cwd)
            run = [str(cwd / output)] if native else ['ocamlrun', output]
            assert call(run, cwd).stdout == '82\n'
        before = (cwd / output).read_bytes()
        write('bad.ml', 'let x : int = "wrong"\n')
        p = call(['ocamlrun', str(lemon), 'build', '-o', output]
                 + (['--native'] if native else []) + ['bad.ml'], cwd, False)
        assert 'int' in p.stderr and 'string' in p.stderr, p.stderr
        assert (cwd / output).read_bytes() == before, 'Failed build replaced output'
    write('a.ml', 'let x = B.x\n')
    write('b.ml', 'let x = A.x\n')
    p = call(['ocamlrun', str(lemon), 'build', 'a.ml', 'b.ml'], cwd, False)
    assert 'cycle' in p.stderr, p.stderr
    call(['ocamlrun', str(lemon), 'build', '-j', '0', 'value.ml'], cwd, False)
    # The compatibility invocation still works, and building never runs the program.
    write('hello.ml', 'let () = print_endline "hello"\n')
    p = call(['ocamlrun', str(lemon), 'hello.ml', 'hello.byte'], cwd)
    assert '\nhello\n' not in p.stdout
    assert call(['ocamlrun', 'hello.byte'], cwd).stdout == 'hello\n'
    assert not list((cwd / '.lemon').iterdir()), 'Temporary artifacts were not cleaned'
print('PASS: bytecode/native, 1/4 workers, interfaces, dependencies, errors, output preservation')
