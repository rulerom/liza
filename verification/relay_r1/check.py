"""Verified Relay R1: fixed real module, all inputs, separate from V0--V4."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import z3
from .semantic import Executor, Unsupported, equal, OPS
from .specification import SUBJECTS, cases, concrete
from .mutations import MUTATIONS, mutate
from .replay import run

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'examples/apps/relay/direction.liza'
PREFIX = 'relay.direction.'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def compile_source(source, directory):
    # Only this boundary invokes compiler code. The executor reads saved JSON.
    from liza.modules import load_program
    from liza.ir import lower, dump
    module_path = directory / 'source/relay/direction.liza'
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_bytes(source)
    harness = directory / 'source/subject.liza'
    harness.write_bytes(b'import relay.direction\nfn main()->u32{return 0}\n')
    ir_path = directory / 'semantic.json'
    ir_path.write_text(dump(lower(load_program(harness))), encoding='utf-8')
    return json.loads(ir_path.read_text(encoding='utf-8'))


def analyze(module, name, directory, timeout=10000):
    directory.mkdir(parents=True, exist_ok=True)
    h, t, n = z3.Ints('head tail count'); e, f = z3.Bools('eof fin')
    d = (h, t, e, f)
    domain = z3.And(*[z3.And(x >= 0, x < 2**32) for x in (h, t, n)])
    arguments = [] if name == 'empty' else [d, n] if name in ('read', 'write') else [d]
    rows = []
    try:
        exits = Executor(module).execute(PREFIX + name, arguments)
        expected = cases(name, d, n)
        traps = z3.Or(*[p for p, k, _ in exits if k == 'Trap'])
        mismatch = z3.Or(*[z3.And(p, q, z3.Not(equal(v, w)))
                              for p, k, v in exits if k == 'Return' for q, w in expected])
        obligations = {
            'no_trap': traps,
            'exact_outcome': z3.Or(traps, mismatch, z3.Not(z3.Or(*[p for p, _, _ in exits]))),
        }
        for obligation, bad in obligations.items():
            solver = z3.Solver(); solver.set(timeout=timeout); solver.add(domain, bad)
            (directory / (obligation + '.smt2')).write_text(solver.to_smt2(), encoding='utf-8')
            result = solver.check()
            row = {'function': name, 'obligation': obligation, 'status': 'unknown'}
            if result == z3.unsat: row['status'] = 'proved'
            elif result == z3.unknown: row['reason'] = solver.reason_unknown()
            else:
                model = solver.model()
                state = tuple(model.eval(x, model_completion=True).as_long() for x in (h, t)) + tuple(z3.is_true(model.eval(x, model_completion=True)) for x in (e, f))
                count = model.eval(n, model_completion=True).as_long()
                args = [] if name == 'empty' else [state, count] if name in ('read', 'write') else [state]
                replay = run(module, PREFIX + name, args)
                reference = concrete(name, state, count)
                confirmed = replay['outcome'] == 'Trap' or (obligation != 'no_trap' and replay['value'] != reference)
                row.update(status='counterexample' if confirmed else 'unknown', inputs={'direction': state, 'count': count}, expected=reference, replay=replay)
                if not confirmed: row['reason'] = 'symbolic witness not confirmed by concrete execution'
            rows.append(row)
    except (Unsupported, KeyError, IndexError, TypeError, ValueError, z3.Z3Exception) as exc:
        rows.append({'function': name, 'status': 'unknown', 'reason': str(exc)})
    save(directory / 'result.json', rows)
    return rows


def check(output, timeout=10000):
    output = Path(output)
    if timeout <= 0: raise ValueError('timeout must be positive')
    if output.exists() and any(output.iterdir()):
        raise ValueError('output must be a new or empty directory')
    # Capture verifier/compiler sources BEFORE execution; hashes describe these bytes.
    source = SOURCE.read_bytes()
    inputs = sorted(set((ROOT / 'liza').rglob('*.py')) | set((ROOT / 'verification/relay_r1').glob('*.py')))
    for path in inputs:
        destination = output / 'tools' / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    requirements = output / 'tools/verification/requirements.txt'
    requirements.write_bytes((ROOT / 'verification/requirements.txt').read_bytes())
    module = compile_source(source, output / 'original')
    positives = [row for name in SUBJECTS for row in analyze(module, name, output / 'original' / name, timeout)]
    controls = []
    for control in MUTATIONS:
        name, subject, _, _ = control
        directory = output / 'mutations' / name
        mutant = compile_source(mutate(source.decode('utf-8'), control).encode('utf-8'), directory)
        rows = analyze(mutant, subject, directory / 'checks', timeout)
        controls.append({'name': name, 'function': subject, 'status': 'detected_and_replayed' if any(r['status'] == 'counterexample' for r in rows) else 'unknown', 'checks': rows})
    passed = len(positives) == 16 and all(r['status'] == 'proved' for r in positives) and all(r['status'] == 'detected_and_replayed' for r in controls)
    report = {
        'experiment': 'Verified Relay R1 — Direction State Validation',
        'status': 'passed' if passed else 'incomplete',
        'direction_semantic_ir_verified': len(positives) == 16 and all(r['status'] == 'proved' for r in positives),
        'byte_conservation_verified': False, 'runtime_verified': False,
        'llvm_verified': False, 'end_to_end_verified': False, 'proof_certificate': False,
        'tools': {'python': platform.python_version(), 'z3': z3.get_version_string(),
                  'semantic_ir_version': module['version'], 'solver_timeout_ms': timeout},
        'scope': {'functions': list(SUBJECTS), 'instructions': list(OPS),
                  'inputs': 'all u32 head, tail, count and all boolean eof, fin; no Valid precondition',
                  'model': 'pure acyclic CFG, scalar helper calls, value structs and Result; checked integer u32',
                  'trust': ['specification', 'IR interpreter', 'compiler IR serialization', 'Python', 'Z3'],
                  'excluded': ['loops', 'recursion', 'memory', 'byte transfers', 'sockets', 'LLVM', 'machine code']},
        'obligations': positives, 'mutations': controls,
    }
    report['artifacts'] = {str(p.relative_to(output)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(output.rglob('*')) if p.is_file() and p != output / 'report.json'}
    save(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/verified-relay-r1'))
    parser.add_argument('--timeout', type=int, default=10000)
    args = parser.parse_args()
    report = check(args.output, args.timeout)
    print(json.dumps({k: report[k] for k in ('experiment', 'status', 'direction_semantic_ir_verified', 'end_to_end_verified')}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
