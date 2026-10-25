"""Independent R2-A byte-buffer proof, without application/IR/runtime claims."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import z3
from .model import CAPACITY, OPERATIONS, MUTATIONS, queries, endpoints
from .replay import confirm

REPLAY_HISTORY_LIMIT = 16384


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2) + '\n', encoding='utf-8')


def witness(model, s, data, count, position, operation, mutation):
    integer = lambda v: model.eval(v, model_completion=True).as_long()
    size = integer(s.wlen)
    n, h, t = integer(count), integer(s.head), integer(s.tail)
    if not 0 <= size <= REPLAY_HISTORY_LIMIT: return {'confirmed': False, 'reason': 'concrete history budget exceeded'}
    if operation == 'read' and not 0 <= n <= CAPACITY:
        return {'confirmed': False, 'reason': 'concrete input budget exceeded'}
    def bytes_of(array, size):
        return [integer(z3.Select(array, i)) for i in range(size)]
    B, W = bytes_of(s.B, CAPACITY), bytes_of(s.W, size)
    # The solver uses only one instance of the old universal invariant. Extend
    # its witness to a genuinely valid entire history; never replay arbitrary
    # unconstrained R entries as if the complete pre-invariant were established.
    before = {'B': B, 'W': W, 'R': W + B[h:t], 'head': h, 'tail': t,
              'eof': z3.is_true(model.eval(s.eof, model_completion=True)),
              'fin': z3.is_true(model.eval(s.fin, model_completion=True))}
    content = bytes_of(data, n) if operation == 'read' else []
    replay = confirm(before, operation, n, content, mutation)
    replay['observation_position'] = integer(position)
    replay['history_construction'] = 'R := W ++ B[head:tail]; full pre-invariant checked concretely'
    return replay


def solve(name, pre, post, directory, timeout, replay=None):
    solver = z3.Solver(); solver.set(timeout=timeout); solver.add(pre, z3.Not(post))
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (name + '.smt2')).write_text(solver.to_smt2(), encoding='utf-8')
    result = solver.check()
    row = {'name': name, 'smt_result': str(result), 'status': 'unknown'}
    if result == z3.unsat: row['status'] = 'proved_model_obligation'
    elif result == z3.unknown: row['reason'] = solver.reason_unknown()
    else:
        row['solver_model'] = str(solver.model())
        if replay is not None:
            row['replay'] = replay(solver.model())
            if row['replay']['confirmed']: row['status'] = 'counterexample_replayed'
            else: row['reason'] = 'symbolic witness not confirmed in a valid concrete state'
        else:
            row['status'] = 'counterexample_to_model_obligation'
    return row


def check(output, timeout=10000):
    output = Path(output)
    if timeout <= 0: raise ValueError('timeout must be positive')
    if output.exists() and any(output.iterdir()): raise ValueError('output must be new or empty')
    output.mkdir(parents=True, exist_ok=True)
    for path in Path(__file__).parent.glob('*.py'):
        destination = output / 'model' / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    (output / 'requirements.txt').write_bytes((Path(__file__).parents[1] / 'requirements.txt').read_bytes())
    rows = [solve(name, pre, post, output / 'queries', timeout) for name, pre, post in endpoints()]
    for operation in OPERATIONS:
        s, data, n, i, pre, posts = queries(operation)
        for name, post in posts.items():
            rows.append(solve(operation + '.' + name, pre, post, output / 'queries', timeout,
                              lambda m: witness(m, s, data, n, i, operation, '')))
    controls = []
    for mutation, operation in MUTATIONS.items():
        s, data, n, i, pre, posts = queries(operation, mutation)
        checks = [solve(name, pre, post, output / 'mutations' / mutation, timeout,
                        lambda m: witness(m, s, data, n, i, operation, mutation)) for name, post in posts.items()]
        detected = any(r['status'] == 'counterexample_replayed' for r in checks)
        complete = all(r['status'] in ('proved_model_obligation', 'counterexample_replayed') for r in checks)
        controls.append({'name': mutation, 'operation': operation, 'checks': checks,
                         'status': 'detected_and_replayed' if detected and complete else 'unknown'})
    proved = len(rows) == 34 and all(r['status'] == 'proved_model_obligation' for r in rows)
    passed = proved and len(controls) == len(MUTATIONS) and all(r['status'] == 'detected_and_replayed' for r in controls)
    report = {
        'experiment': 'Verified Relay R2-A — Byte Conservation Model',
        'status': 'passed' if passed else 'incomplete', 'model_byte_conservation_verified': proved,
        'program_verified': False, 'semantic_ir_verified': False, 'runtime_verified': False,
        'llvm_verified': False, 'end_to_end_verified': False, 'proof_certificate': False,
        'scope': {'capacity': CAPACITY, 'directions': 1,
                  'representation': 'finite sequences as length plus Int -> BV8; buffer indices [0,2048)',
                  'proof': 'initialization and inductive preservation of lengths and arbitrary indexed byte equality',
                  'old_invariant_encoding': 'single arbitrary-index consequence; weaker than full pre-invariant',
                  'histories': 'unbounded mathematical lengths; no finite execution unrolling',
                  'concrete_replay_history_limit': REPLAY_HISTORY_LIMIT,
                  'excluded': ['application Semantic IR', '16-region partition', 'socket runtime', 'fatal error recovery',
                               'resource release', 'fairness', 'termination', 'peer receipt', 'LLVM', 'machine code']},
        'assumptions': [
            'valid mathematical pre-state: bounds, R=W++B[head:tail], FIN implies EOF and empty queue',
            'single direction, exclusive buffer ownership, no concurrent writes',
            'successful read transfers exactly reported data into requested free range, no other writes',
            'successful nonempty write accepts exactly reported nonempty prefix; buffer unchanged',
            'reported count does not exceed request or capacity; requested range is valid',
            'WouldBlock has no hidden successful transfer or memory changes; readiness is not success',
            'EOF is read returning zero with positive available capacity; no bytes removed',
            'FIN is issued only after EOF and draining, and its successful effect changes no bytes',
            'other errors terminate modeled successful execution; no error-side-effect or delivery guarantee',
        ],
        'trusted_base': ['manually authored model and contracts', 'pointwise sequence equality encoding',
                         'symbolic orchestration', 'concrete control replay', 'Python', 'Z3'],
        'tools': {'python': platform.python_version(), 'z3': z3.get_version_string(), 'timeout_ms': timeout},
        'obligations': rows, 'mutations': controls,
    }
    save(output / 'results.json', {'obligations': rows, 'mutations': controls})
    report['artifacts'] = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(output.rglob('*')) if p.is_file()}
    save(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/verified-relay-r2a'))
    parser.add_argument('--timeout', type=int, default=10000)
    args = parser.parse_args()
    report = check(args.output, args.timeout)
    print(json.dumps({key: report[key] for key in ('experiment', 'status', 'model_byte_conservation_verified', 'program_verified', 'end_to_end_verified')}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
