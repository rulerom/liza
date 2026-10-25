"""R2-B first slice: conditional byte binding of six actual proxy IR cuts."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import z3
from verification.relay_r1.semantic import Unsupported
from .fragment import Fragment, CUTS, IO
from .semantic import Executor
from .specification import inputs, properties
from .mutations import MUTATIONS, TARGETS, mutate
from .replay import run, violations

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'examples/apps/liza_proxy.liza'
HELPER = ROOT / 'examples/apps/relay/direction.liza'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def compile_source(source, helper, output):
    from liza.modules import load_program
    from liza.ir import lower, dump
    app = output / 'source/liza_proxy.liza'; app.parent.mkdir(parents=True, exist_ok=True)
    direction = app.parent / 'relay/direction.liza'; direction.parent.mkdir(parents=True, exist_ok=True)
    app.write_bytes(source); direction.write_bytes(helper)
    ir = output / 'semantic.json'
    ir.write_text(dump(lower(load_program(app))), encoding='utf-8')
    return json.loads(ir.read_text(encoding='utf-8'))


def replay_witness(module, fragment, values, memory, solver_model):
    def evaluate(value):
        if isinstance(value, str): return value
        if isinstance(value, dict): return {k: evaluate(v) for k, v in value.items()}
        if isinstance(value, tuple): return tuple(evaluate(v) for v in value)
        result = solver_model.eval(value, model_completion=True)
        return z3.is_true(result) if z3.is_bool(value) else result.as_long()
    def byte_values(array, count): return [evaluate(z3.Select(array, i)) for i in range(count)]
    n = evaluate(values['count']); wn = evaluate(memory.wlen)
    if not 0 <= wn <= 16384: return {'confirmed': False, 'reason': 'replay history budget exceeded'}
    concrete = {k: evaluate(v) for k, v in values.items() if k != 'data'}
    concrete['data'] = byte_values(values['data'], n)
    B, W = byte_values(memory.B, 32768), byte_values(memory.W, wn)
    h, t, _, _ = concrete['pair'][fragment.direction]
    base = concrete['slot']*4096 + (2048 if fragment.direction == 'reverse' else 0)
    before = dict(B=B, W=W, R=W+B[base+h:base+t])
    result = run(module, fragment, concrete, before)
    bad = violations(fragment, concrete, before, result)
    # Hex makes the complete bytes portable without relying on the solver's
    # array pretty-printer. Concrete pre-history is fully valid, not just one
    # unconstrained SMT array with an invariant instance at one position.
    def encode(mem):
        return {k: bytes(v).hex() if k in ('B','R','W') else v for k, v in mem.items()}
    result['memory'] = encode(result['memory'])
    return {'confirmed': bool(bad), 'violations': bad, 'inputs': concrete,
            'before_hex': encode(before), 'execution': result,
            'pre_history': 'R reconstructed as W ++ B[base+head:base+tail]'}


def analyze(module, name, output, timeout=10000, negative=None):
    output.mkdir(parents=True, exist_ok=True)
    try:
        fragment = Fragment(module, name)
        save(output / 'cut.json', fragment.manifest())
        values, before, pre, context = inputs(name)
        exits = Executor(module, fragment, values).execute(before)
        bad = {'no_trap_or_undefined': []}
        for path, kind, pair, alive, after in exits:
            if kind != 'Return': bad['no_trap_or_undefined'].append(path); continue
            for prop, post in properties(values, before, context, pair, alive, after).items():
                bad.setdefault(prop, []).append(z3.And(path, z3.Not(post)))
        if negative:
            # Seek an actual executable violating path. Do not turn a coverage
            # hole (e.g. inconsistent mocked I/O) into a program counterexample.
            target, outcome = negative
            queries = {'executable_violation': z3.And(z3.Or(*bad[target]), values['outcome'] == outcome)}
        else:
            queries = {key: z3.Or(*items) for key, items in bad.items()}
            queries['coverage'] = z3.Not(z3.Or(*[path for path, *_ in exits]))
        rows = []
        for prop, condition in queries.items():
            solver = z3.Solver(); solver.set(timeout=timeout); solver.add(pre, condition)
            # Restrict only existential control searches so complete concrete
            # histories remain small. Positive universal proofs have no limit.
            if negative: solver.add(before.wlen <= 4096)
            (output / (prop + '.smt2')).write_text(solver.to_smt2(), encoding='utf-8')
            result = solver.check(); row = {'cut': name, 'obligation': prop, 'status': 'unknown', 'smt_result': str(result)}
            if result == z3.unsat: row['status'] = 'proved' if not negative else 'not_detected'
            elif result == z3.unknown: row['reason'] = solver.reason_unknown()
            else:
                row['solver_model'] = str(solver.model())
                row['replay'] = replay_witness(module, fragment, values, before, solver.model())
                confirmed = row['replay']['confirmed']
                if negative and confirmed:
                    observed = set(row['replay']['violations'])
                    required = {'call_guard', 'call_binding', 'slice_bounds'} if negative[0] == 'call_binding_and_guard' else {negative[0]}
                    confirmed = bool(observed & required)
                if confirmed: row['status'] = 'counterexample_replayed'
                else: row['reason'] = 'IR witness not confirmed by concrete execution'
            rows.append(row)
    except (Unsupported, ValueError, KeyError, TypeError, IndexError, StopIteration, z3.Z3Exception) as exc:
        rows = [{'cut': name, 'status': 'unknown', 'reason': str(exc)}]
    save(output / 'results.json', rows)
    return rows


def partition(output, timeout):
    i, j = z3.Ints('direction_i direction_j')
    domain = z3.And(0 <= i, i < 16, 0 <= j, j < 16)
    obligations = {
        'all_sixteen_bounds': z3.And(0 <= 2048*i, 2048*i+2048 <= 32768),
        'distinct_directions_disjoint': z3.Implies(i != j, z3.Or(2048*i+2048 <= 2048*j, 2048*j+2048 <= 2048*i)),
    }
    rows = []
    output.mkdir(parents=True, exist_ok=True)
    for name, post in obligations.items():
        solver = z3.Solver(); solver.set(timeout=timeout); solver.add(domain, z3.Not(post))
        (output / (name + '.smt2')).write_text(solver.to_smt2(), encoding='utf-8')
        result = solver.check()
        rows.append({'obligation': name, 'status': 'proved' if result == z3.unsat else 'unknown', 'smt_result': str(result)})
    return rows


def check(output, timeout=10000):
    output = Path(output)
    if timeout <= 0: raise ValueError('positive timeout required')
    if output.exists() and any(output.iterdir()): raise ValueError('new or empty output required')
    source, helper = APP.read_bytes(), HELPER.read_bytes()
    paths = list((ROOT / 'verification/relay_r2b').glob('*.py')) + [ROOT / 'verification/relay_r1/semantic.py', ROOT / 'verification/relay_r1/replay.py']
    paths += list((ROOT / 'liza').rglob('*.py')) + list((ROOT / 'liza/stdlib').rglob('*.liza')) + [ROOT / 'verification/requirements.txt']
    for path in paths:
        dest = output / 'tools' / path.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(path.read_bytes())
    module = compile_source(source, helper, output / 'original')
    # Make omissions visible: all six read/write/shutdown calls in exchange must
    # occur inside exactly the six declared cuts. Other event-loop code is out.
    scope_complete = True
    try:
        fragments = [Fragment(module, name) for name in CUTS]
        actual = [(b['name'], o['result'], o['callee']) for b in fragments[0].function['blocks'] for o in b['operations'] if o['callee'] in IO.values()]
        if sorted(actual) != sorted(f.call for f in fragments): raise ValueError('uncovered proxy I/O call')
    except (ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        scope_complete = False
        rows = [{'obligation': 'cut_scope', 'status': 'unknown', 'reason': str(exc)}]
    if scope_complete:
        rows = [r for name in CUTS for r in analyze(module, name, output / 'original/checks' / name, timeout)]
        rows += partition(output / 'partition', timeout)
    controls = []
    for control in MUTATIONS if scope_complete else ():
        name, subject, _, _ = control; directory = output / 'mutations' / name
        mutant = compile_source(mutate(source.decode('utf-8'), control).encode('utf-8'), helper, directory)
        results = analyze(mutant, subject, directory / 'checks', timeout, negative=TARGETS[name])
        controls.append({'name': name, 'cut': subject, 'target_and_outcome': TARGETS[name], 'status': 'detected_and_replayed' if len(results) == 1 and results[0]['status'] == 'counterexample_replayed' else 'unknown', 'checks': results})
    passed = len(rows) == 58 and all(r['status'] == 'proved' for r in rows) and len(controls) == 8 and all(c['status'] == 'detected_and_replayed' for c in controls)
    report = {
        'experiment': 'Verified Relay R2-B — Semantic IR Byte Binding (single transitions)',
        'status': 'passed' if passed else 'incomplete', 'conditional_ir_byte_binding_verified': passed,
        'whole_program_verified': False, 'event_loop_verified': False,
        'runtime_verified': False, 'llvm_verified': False, 'end_to_end_verified': False, 'proof_certificate': False,
        'tools': {'python': platform.python_version(), 'z3': z3.get_version_string(), 'semantic_ir_version': module['version'], 'timeout_ms': timeout},
        'scope': {'function': 'liza_proxy.exchange', 'cuts': list(CUTS), 'buffer_bytes': 32768, 'directions': 16,
                  'proof': 'acyclic one-I/O CFG cuts; entry after phi, exit after executing phi',
                  'byte_history': 'unbounded lengths, arbitrary indexed byte equality; concrete replay limit W=16384',
                  'negative_control_history_search_limit': 4096,
                  'outcomes': ['Ok', 'WouldBlock', 'Interrupted', 'Other (terminal)'],
                  'excluded': ['establishment of cutpoint preconditions', 'whole event loop', 'multi-event induction',
                               'resource cleanup', 'allocator', 'connect/accept/readiness implementation',
                               'other runtime error variants including Full', 'LLVM', 'machine code']},
        'assumptions': [
            'entry Pair has two valid Direction states, slot in [0,8), distinct valid client/upstream owned by reactor',
            'one live initialized u8 buffer of 32768 bytes, exclusive access for the cut',
            'entry phi values and external live-ins satisfy the documented cutpoint binding',
            'readonly view aliases exactly that buffer; resource identities/move validity follow compiler checks, not this proof',
            'read Ok(n) writes exactly n arbitrary input bytes to actual requested range, preserves all other bytes',
            'write Ok(n) accepts exactly actual view prefix, n>0 for nonempty request, preserves buffer',
            'Ok count <= actual requested; zero read is EOF; readiness imposes no successful-outcome guarantee',
            'WouldBlock and Interrupted preserve memory and histories; these are explicit runtime assumptions',
            'successful shutdown has no byte effects; program must establish drained EOF before calling',
            'Other is terminal; byte effects and delivery after this error are not modeled or certified',
        ],
        'trusted_base': ['cutpoint manifest and input relationships', 'independent specification',
                         'proxy symbolic and concrete IR interpreters', 'unchanged R1 IR interpreters for actual helper bodies',
                         'abstract socket contracts', 'IR serialization', 'Python', 'Z3'],
        'obligations': rows, 'mutations': controls,
    }
    save(output / 'results.json', {'obligations': rows, 'mutations': controls})
    report['artifacts'] = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(output.rglob('*')) if p.is_file()}
    save(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/verified-relay-r2b'))
    parser.add_argument('--timeout', type=int, default=10000)
    args = parser.parse_args(); report = check(args.output, args.timeout)
    print(json.dumps({key: report[key] for key in ('experiment', 'status', 'conditional_ir_byte_binding_verified', 'end_to_end_verified')}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
