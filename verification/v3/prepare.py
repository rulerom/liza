"""Generate untouched V3 artifacts on the target platform, before validation."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from liza.target import resolve
from liza.frontend import Parser
from liza.ir import lower, dump
from liza.backend import llvm
from verification.v3.check import module_metadata, sha


def prepare(output, clang, triple=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = resolve(clang, triple)
    info = {'target': target.metadata(), 'clang_version': subprocess.check_output(
        [clang, '--version'], text=True), 'suites': {}, 'artifacts': {}}
    for suite, subject in [('V0', ROOT/'verification/arithmetic.liza'),
                           ('V1', ROOT/'verification/v1/bounds.liza')]:
        directory = output/suite
        directory.mkdir(exist_ok=True)
        text = subject.read_text(encoding='utf-8')
        module = lower(Parser(text).parse())
        raw = directory/'generated.ll'
        raw.write_text(llvm(module, target), encoding='utf-8')
        shutil.copyfile(subject, directory/'subjects.liza')
        (directory/'semantic.json').write_text(dump(module), encoding='utf-8')
        functions = re.findall(r'^define .*?@(liza_\w+)\(', raw.read_text(), re.M)
        info['suites'][suite] = {'functions': [f for f in functions if f != 'liza_main'], 'commands': {}}
        for level in ('0', '2'):
            path = directory/f'O{level}.ll'
            cmd = [clang, *target.flags, '-Werror=override-module', f'-O{level}',
                   '-S', '-emit-llvm', str(raw), '-o', str(path)]
            p = subprocess.run(cmd, capture_output=True, text=True)
            (directory/f'O{level}.optimizer.log').write_text(p.stdout+p.stderr)
            if p.returncode:
                raise ValueError('Clang failed: '+p.stderr)
            info['suites'][suite]['commands'][f'O{level}'] = cmd
        for path in directory.glob('*.ll'):
            meta = module_metadata(path)
            if (meta['triple'], meta['data_layout']) != (target.triple, target.data_layout):
                raise ValueError('target environment changed: '+str(path))
        # No runtime calls or non-default address spaces in the selected fragment.
        if re.search(r'addrspace\([1-9]', raw.read_text()):
            raise ValueError('unexpected non-default address space')
    for path in output.rglob('*'):
        if path.is_file() and path.name != 'environment.json':
            info['artifacts'][str(path.relative_to(output)).replace('\\', '/')] = sha(path)
    (output/'environment.json').write_text(json.dumps(info, indent=2)+'\n')
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--target')
    args = parser.parse_args()
    prepare(args.output, args.clang, args.target)
