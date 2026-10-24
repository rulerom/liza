"""Independent LLVM refinement calibration. No trap instrumentation or fallback.

A successful process exit is NOT a successful proof. Every selected function
must have exactly one classified result, and every essential negative control
must be rejected before actual IR validation is enabled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify(output, returncode):
    labels = ('correct transformations', 'incorrect transformations',
              'failed-to-prove transformations', 'Alive2 errors')
    counts = []
    for label in labels:
        matches = re.findall(r'^\s*(\d+) ' + re.escape(label) + r'\s*$', output, re.M)
        if len(matches) != 1:
            return 'unknown'
        counts.append(int(matches[0]))
    # Never accept partial coverage or an error masked by a successful query.
    if returncode != 0 or sum(counts) != 1:
        return 'unknown'
    if counts == [1, 0, 0, 0]:
        return 'refinement_verified'
    if counts == [0, 1, 0, 0]:
        return 'counterexample'
    return 'unknown'


def normalize(raw, negative):
    if raw == 'refinement_verified':
        return 'unsuitable' if negative else 'verified'
    return raw


def gate(rows):
    if any(row['status'] == 'unsuitable' for row in rows):
        return 'unsuitable'
    if all(row['status'] == ('counterexample' if row['negative'] else 'verified')
           for row in rows) and rows:
        return 'verified'
    return 'unknown'


def command(args, timeout=60):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b''
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        return -1, output + '\nHARNESS: wall-clock timeout\n'
    except OSError as error:
        return -1, 'HARNESS: ' + str(error)


def module_metadata(path):
    text = Path(path).read_text()
    def field(name):
        m = re.search(r'^target ' + name + r' = "([^"]*)"', text, re.M)
        return m[1] if m else None
    return {'sha256': sha(path), 'triple': field('triple'),
            'data_layout': field('datalayout')}


def compare(args, directory, name, source, target, function, negative=False):
    directory.mkdir(parents=True, exist_ok=True)
    src, tgt = directory / 'source.ll', directory / 'target.ll'
    shutil.copyfile(source, src)
    shutil.copyfile(target, tgt)
    cmd = [args.alive_tv, '--disable-undef-input', '--disable-poison-input',
           f'--func={function}', str(src), str(tgt)]
    src_meta, tgt_meta = module_metadata(src), module_metadata(tgt)
    if (src_meta['triple'], src_meta['data_layout']) != (tgt_meta['triple'], tgt_meta['data_layout']):
        code, output = -1, 'HARNESS: target environment mismatch\n'
    else:
        code, output = command(cmd, args.timeout)
    (directory / 'alive-tv.log').write_text(output)
    raw = classify(output, code)
    row = {'name': name, 'function': function, 'negative': negative,
           'status': normalize(raw, negative), 'raw_status': raw,
           'returncode': code, 'command': cmd,
           'source': module_metadata(src), 'target': module_metadata(tgt),
           'log': str(directory / 'alive-tv.log')}
    print(name, row['status'], flush=True)
    return row


def actual(args, output):
    sys.path.insert(0, str(ROOT))
    from verification.v3.prepare import prepare
    inputs = Path(args.inputs).resolve() if args.inputs else output/'inputs'
    if not args.inputs:
        prepare(inputs, args.clang, args.target)
    environment = json.loads((inputs/'environment.json').read_text())
    for path, digest in environment['artifacts'].items():
        if sha(inputs/path) != digest:
            raise ValueError('input artifact hash mismatch: '+path)
    output.mkdir(parents=True, exist_ok=True)
    (output/'environment.json').write_text(json.dumps(environment, indent=2)+'\n')
    results = []
    subjects = {'V0': ROOT/'verification/arithmetic.liza',
                'V1': ROOT/'verification/v1/bounds.liza'}
    if set(environment['suites']) != set(subjects):
        raise ValueError('incomplete subject coverage')
    for suite, spec in environment['suites'].items():
        expected_functions = {'liza_'+name for name in re.findall(
            r'^fn (\w+)\(', subjects[suite].read_text(), re.M) if name != 'main'}
        if set(spec['functions']) != expected_functions or len(spec['functions']) != len(expected_functions):
            raise ValueError('incomplete function coverage: '+suite)
        for name in ('generated.ll', 'O0.ll', 'O2.ll', 'subjects.liza'):
            if f'{suite}/{name}' not in environment['artifacts']:
                raise ValueError('missing artifact hash: '+suite+'/'+name)
        if sha(inputs/suite/'subjects.liza') != sha(subjects[suite]):
            raise ValueError('subject source changed: '+suite)
        directory = output/suite
        directory.mkdir(parents=True, exist_ok=True)
        raw = inputs/suite/'generated.ll'
        expected = environment['target']
        for path in (raw, inputs/suite/'O0.ll', inputs/suite/'O2.ll'):
            meta = module_metadata(path)
            if (meta['triple'], meta['data_layout']) != (expected['triple'], expected['data_layout']):
                raise ValueError('input target metadata mismatch: '+str(path))
        functions = spec['functions']
        for level in ('0', '2'):
            for fn in functions:
                row = compare(args, directory/f'O{level}-{fn}',
                              f'{suite}-O{level}-{fn}', raw, inputs/suite/f'O{level}.ll', fn)
                row['optimizer'] = spec['commands'][f'O{level}']
                results.append(row)
        for level in ('0', '2'):
            target = directory/f'opt-O{level}.ll'
            cmd = [args.opt, '-S', f'-passes=default<O{level}>', str(raw), '-o', str(target)]
            code, log = command(cmd, args.timeout)
            (directory/f'opt-O{level}.optimizer.log').write_text(log)
            if code:
                results.append({'name': f'{suite}-opt-O{level}', 'status': 'unknown',
                                'reason': 'opt failed', 'command': cmd})
                continue
            for fn in functions:
                row = compare(args, directory/f'opt-O{level}-{fn}',
                              f'{suite}-opt-O{level}-{fn}', raw, target, fn)
                row['optimizer'] = cmd
                results.append(row)
        for fn in functions:
            row = compare(args, directory/f'O0-to-O2-{fn}',
                          f'{suite}-O0-to-O2-{fn}', inputs/suite/'O0.ll', inputs/suite/'O2.ll', fn)
            row['optimizer'] = spec['commands']
            results.append(row)
    return results


def run(args):
    baseline = json.loads((HERE/'baseline.json').read_text())
    if any(sha(ROOT/path) != digest for path, digest in baseline.items()):
        raise ValueError('Frozen V0/V1/V2 files changed')
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'experiment': 'V3 LLVM Translation Validation',
              'scope': 'LLVM refinement; calibration is empirical, not a theorem about Alive2',
              'assumptions': ['function inputs are defined Liza values, not undef or poison'],
              'excluded_functions': ['main', 'liza_main'],
              'exclusions': ['Semantic IR to LLVM proof', 'machine code',
                             'loops', 'interprocedural transformations'],
              'calibration': [], 'actual': [], 'status': 'unknown'}
    for key, cmd in [('alive2_version', [args.alive_tv, '--version']),
                     ('llvm_version', [args.clang, '--version']),
                     ('opt_version', [args.opt, '--version']),
                     ('llvm_configuration', [args.llvm_config, '--version', '--host-target', '--build-mode']),
                     ('z3_version', [args.z3, '--version'])]:
        code, text = command(cmd)
        report[key] = {'command': cmd, 'returncode': code, 'output': text}
    # Exact source revision and dirty state, plus executable hash, prevent a
    # supplied version label from being mistaken for the identity of the binary.
    code, rev = command(['git', '-C', args.alive_source, 'rev-parse', 'HEAD'])
    report['alive2_commit'] = rev.strip() if not code else None
    code, dirty = command(['git', '-C', args.alive_source, 'status', '--porcelain'])
    report['alive2_source_dirty'] = dirty if not code else None
    exe = shutil.which(args.alive_tv)
    report['alive2_binary_sha256'] = sha(exe) if exe else None
    report['llvm_build_revision'] = args.llvm_revision
    clang_exe = shutil.which(args.clang)
    report['clang_binary_sha256'] = sha(clang_exe) if clang_exe else None
    manifest = json.loads((HERE/'fixtures/manifest.json').read_text())
    report['manifest_sha256'] = sha(HERE/'fixtures/manifest.json')
    for phase in ('traps', 'memory'):
        if phase == 'memory' and gate(report['calibration']) != 'verified':
            report['memory_gate'] = 'not run: trap calibration incomplete or unsuitable'
            break
        for case in manifest:
            if case['phase'] != phase:
                continue
            report['calibration'].append(compare(
                args, output/'calibration'/case['name'], case['name'],
                HERE/'fixtures'/case['source'], HERE/'fixtures'/case['target'],
                'subject', case['negative']))
    report['calibration_status'] = gate(report['calibration'])
    report['status'] = report['calibration_status']
    if args.actual and report['status'] == 'verified':
        try:
            report['actual'] = actual(args, output/'actual')
        except (ValueError, OSError, KeyError) as error:
            report['actual'] = [{'status': 'unknown', 'reason': str(error)}]
        if any(r['status'] == 'counterexample' for r in report['actual']):
            report['status'] = 'counterexample'
        elif not report['actual'] or any(r['status'] != 'verified' for r in report['actual']):
            report['status'] = 'unknown'
    elif args.actual:
        report['actual_gate'] = 'not run: calibration incomplete or unsuitable'
    if any(report[key]['returncode'] != 0 for key in
           ('alive2_version', 'llvm_version', 'opt_version', 'llvm_configuration', 'z3_version')):
        report['status'] = 'unknown'
        report['metadata_error'] = 'could not obtain required tool metadata'
    if not report['alive2_commit'] or report['alive2_source_dirty'] != '':
        report['status'] = 'unknown'
        report['provenance_error'] = 'missing or dirty Alive2 source revision'
    from collections import Counter
    report['counts'] = {section: dict(Counter(row['status'] for row in report[section]))
                        for section in ('calibration', 'actual')}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alive-tv', required=True)
    parser.add_argument('--alive-source', required=True)
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--llvm-config', default='llvm-config')
    parser.add_argument('--opt', default='opt')
    parser.add_argument('--llvm-revision', required=True,
                        help='exact LLVM source revision or distribution build identifier')
    parser.add_argument('--z3', default='z3')
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--output', default='build/verified-v3')
    parser.add_argument('--actual', action='store_true')
    parser.add_argument('--target', help='explicit Clang target')
    parser.add_argument('--inputs', help='validate hashed artifacts prepared on another platform')
    args = parser.parse_args()
    report = run(args)
    print('V3:', report['status'])
    return 0 if report['status'] == 'verified' else 1


if __name__ == '__main__':
    raise SystemExit(main())
