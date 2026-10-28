#!/usr/bin/env python3
"""Diagnostic inlining ablations; consumes a completed immutable M0 reference run."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'json'))
spec = importlib.util.spec_from_file_location('baseline', HERE.parent / 'json/run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
VARIANTS = {
    'M0': [],
    'utf8-inline': ['liza_utf8_stream.feed_byte'],
    'step-inline': ['liza___liza_json_mut_step'],
    'done-inline': ['liza___liza_json_mut_done'],
    'combined': ['liza_utf8_stream.feed_byte', 'liza___liza_json_mut_step', 'liza___liza_json_mut_done'],
}


def transform(ir, names):
    original = ir
    for name in names:
        pattern = r'(?m)^(define [^\n]*@' + re.escape(name) + r'\([^\n]*) \{$'
        ir, count = re.subn(pattern, r'\1 alwaysinline {', ir)
        if count != 1:
            raise ValueError('unsupported/missing function: ' + name)
    if ir.replace(' alwaysinline {', ' {') != original:
        raise ValueError('experiment must change only function inline attributes')
    return ir


def instrument(ir):
    """Function-entry counts in optimized IR; never used for timing."""
    names = []
    lines = []
    pending = False
    for line in ir.splitlines():
        # Counter calls have global writes; remove inferred read-only effects.
        line = re.sub(r'\bmemory\([^)]*\)|\breadonly\b|\breadnone\b', '', line)
        if line.startswith('define '):
            name = re.search(r'@([^ (]+)', line)[1]
            names.append(name)
            pending = True
        elif pending and line.strip() and not line.lstrip().startswith(';') and not re.match(r'^[\w.]+:', line):
            if ' = phi ' in line:
                raise ValueError('unsupported entry phi')
            lines.append(f'  call void @parity_enter(i32 {len(names)-1})')
            pending = False
        lines.append(line)
    lines.append('declare void @parity_enter(i32)')
    return '\n'.join(lines) + '\n', names


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repeats', type=int, default=10)
    a = p.parse_args()
    if a.repeats < 3 or a.output.exists():
        p.error('at least 3 repeats and a fresh output directory required')
    ref, out = a.reference.resolve(), a.output.resolve()
    if sys.platform != 'darwin' or __import__('platform').machine() != 'arm64':
        p.error('this first investigation requires macOS ARM64')
    previous = json.loads((ref / 'report.json').read_text())
    if previous['status'] not in ('correctness_passed', 'measured'):
        p.error('reference run must have completed successfully')
    for name, digest in previous['evidence'].items():
        if base.digest(ref / name) != digest:
            raise ValueError('reference evidence changed: ' + name)
    out.mkdir(parents=True)
    report = {'status': 'incomplete', 'created_at': datetime.now(timezone.utc).isoformat(),
              'candidate': previous['candidate'], 'reference_report_sha256': base.digest(ref / 'report.json'),
              'harness_sha256': base.digest(__file__), 'variants': VARIANTS,
              'tools': previous['tools'], 'hardware': previous.get('hardware'),
              'target': previous['target'], 'commands': [], 'samples': []}
    report['limits'] = [
        'Research-only name-selected inline attributes, not a production compiler policy.',
        'Function counters count optimized LLVM function entries, not hardware instructions or cycles.',
        'Counter binaries are untimed; each diagnostic includes one warmup and one measured pass.',
        'Inlining ablations also change layout and register allocation; speedups are not additive.',
        'Agreement tests are not a proof for all possible parser states or LLVM transformations.',
    ]
    def run(args, **kw):
        report['commands'].append([str(x) for x in args])
        return base.run(args, **kw)
    try:
        flags = previous['target']['flags']
        clang = shutil.which('clang')
        if run([clang, '--version']).decode() != previous['tools']['clang']:
            raise ValueError('Clang changed since reference build')
        ir = (ref / 'M0/module.ll').read_text()
        exes = {'rust': ref / 'baseline/rust'}
        for label, names in VARIANTS.items():
            folder = out / label
            folder.mkdir()
            module = folder / 'module.ll'
            module.write_text(transform(ir, names))
            for opt in (0, 2):
                obj = folder / f'O{opt}.o'
                exe = folder / f'O{opt}'
                run([clang, *flags, f'-O{opt}', '-Werror=override-module', '-fstack-usage', '-c', module, '-o', obj])
                run([clang, *flags, ref / 'baseline/driver.o', obj, '-o', exe])
                exes[f'{label}-O{opt}'] = exe
            run([clang, *flags, '-O2', '-S', '-emit-llvm', module, '-o', folder / 'optimized.ll'])
            run([clang, *flags, '-O2', '-S', module, '-o', folder / 'module.s'])
        report['correctness'] = base.correctness(exes, ref / 'baseline/liza-json', out)
        report['correctness']['cli_cases'] = report['correctness']['documents'] * (len(exes) + 1)
        print('O0/O2 correctness and offsets agree for all variants', flush=True)
        timing = {k[:-3]: v for k, v in exes.items() if k.endswith('-O2')}
        timing['rust'] = exes['rust']
        paths = {}
        report['workloads'] = previous['workloads']
        for row in previous['workloads']:
            path = ref / 'corpus' / ('bench-' + row['name'] + '.json')
            if base.digest(path) != row['sha256']:
                raise ValueError('corpus changed')
            paths[row['name']] = path
            for exe in exes.values():
                if run([exe, 'check', path]) != b'OK\n':
                    raise ValueError('timing input mismatch')
        for repeat in range(a.repeats):
            schedule = [(variant, name) for variant in timing for name in paths]
            random.Random(20261026 + repeat).shuffle(schedule)
            for variant, name in schedule:
                path = paths[name]
                rounds = max(1, 16 * 1024 * 1024 // path.stat().st_size)
                row = json.loads(run([timing[variant], 'bench', path, 2048, rounds]))
                if row['status'] or row['value'] != path.stat().st_size or row['checksum'] != (rounds+1)*row['value']:
                    raise ValueError('timed result mismatch')
                row.update(variant=variant, workload=name, repeat=repeat,
                           mib_s=path.stat().st_size*rounds/1048576/row['seconds'])
                report['samples'].append(row)
            print(f'series {repeat+1}/{a.repeats}', flush=True)
        report['summary'] = []
        for variant in timing:
            for name in paths:
                values = [s['mib_s'] for s in report['samples'] if s['variant']==variant and s['workload']==name]
                report['summary'].append(dict(variant=variant, workload=name, median_mib_s=statistics.median(values), min_mib_s=min(values), max_mib_s=max(values)))
        report['function_entries'] = {}
        for variant in VARIANTS:
            folder = out / variant
            counted, names = instrument((folder / 'optimized.ll').read_text())
            (folder / 'counted.ll').write_text(counted)
            c = '#include <stdint.h>\n#include <stdio.h>\nstatic uint64_t counts['+str(len(names))+'];\nvoid parity_enter(unsigned n){counts[n]++;}\n__attribute__((destructor)) static void report(void){'
            c += ''.join('fprintf(stderr,"%u %llu\\n",'+str(i)+',(unsigned long long)counts['+str(i)+']);' for i in range(len(names))) + '}\n'
            (folder / 'counts.c').write_text(c)
            run([clang, *flags, '-O0', folder / 'counted.ll', folder / 'counts.c', ref / 'baseline/driver.o', '-o', folder / 'counted'])
            entries = {}
            for name, path in paths.items():
                cmd = [str(folder / 'counted'), 'bench', str(path), '2048', '1']
                report['commands'].append(cmd)
                r = subprocess.run(cmd, capture_output=True, check=True, timeout=120)
                result = json.loads(r.stdout)
                if result['status'] or result['checksum'] != 2*path.stat().st_size:
                    raise ValueError('counter result mismatch')
                entries[name] = {names[int(i)]: int(n)/(2*path.stat().st_size) for i,n in (s.split() for s in r.stderr.decode().splitlines()) if int(n)}
            report['function_entries'][variant] = entries
        evidence = out / 'reference'
        evidence.mkdir()
        for name in ('rust', 'rust.optimized.ll', 'rust.s', 'source.tar', 'driver.o'):
            shutil.copy2(ref / 'baseline' / name, evidence / name)
        shutil.copy2(ref / 'M0/source.tar', evidence / 'candidate-source.tar')
        shutil.copy2(ref / 'report.json', evidence / 'reference-report.json')
        report['artifacts'] = {str(f.relative_to(out)): base.digest(f) for f in out.rglob('*') if f.is_file()}
        report['status'] = 'measured'
    except Exception as e:
        report['error'] = str(e)
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(out / 'report.json')

if __name__ == '__main__':
    main()
