"""Bind child reports to the bytes produced in their own output directories."""
import hashlib
import json
from pathlib import Path
import re


def inside(root, name):
    root=root.resolve()
    path=(root/name).resolve()
    if path==root or root not in path.parents:raise ValueError('artifact escapes its root: '+str(name))
    if not path.is_file():raise ValueError('missing artifact: '+str(name))
    return path


def digest(root,name,expected):
    path=inside(root,name)
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=expected:raise ValueError('artifact hash mismatch: '+str(name))


def functions(path):
    return set(re.findall(r'^fn (\w+)\(',path.read_text(encoding='utf-8'),re.M))-{'main'}


def verify(stage,raw,output,source):
    if stage in {'v0','v1','v2'}:
        hashes=raw['sha256']
        if not hashes:raise ValueError('empty artifact manifest')
        for name,value in hashes.items():digest(output,name,value)
        for name,value in raw['model_sha256'].items():digest(source,name,value)
        relative={'v0':'verification/arithmetic.liza','v1':'verification/v1/bounds.liza',
                  'v2':'verification/v2/loops.liza'}[stage]
        subjects=functions(source/relative)
        rows=raw['proofs'] if stage=='v2' else raw['results']
        name_key='function' if stage=='v2' else 'subject'
        expected={(f,s) for f in subjects for s in ('Semantic IR','LLVM-generated','LLVM-O0','LLVM-O2')}
        if {(r[name_key],r['stage']) for r in rows}!=expected:raise ValueError('subject/stage coverage mismatch')
    elif stage=='v3':
        manifest=json.loads((source/'verification/v3/fixtures/manifest.json').read_text())
        if {(r['name'],r['negative']) for r in raw['calibration']}!={(r['name'],r['negative']) for r in manifest}:
            raise ValueError('calibration coverage mismatch')
        digest(source,'verification/v3/fixtures/manifest.json',raw['manifest_sha256'])
        expected=set()
        for suite,relative in [('V0','verification/arithmetic.liza'),('V1','verification/v1/bounds.liza')]:
            for fn in functions(source/relative):
                for phase in ('O0','O2','opt-O0','opt-O2','O0-to-O2'):
                    expected.add(f'{suite}-{phase}-liza_{fn}')
        if {r['name'] for r in raw['actual']}!=expected:raise ValueError('LLVM pair coverage mismatch')
        for row in raw['calibration']+raw['actual']:
            # The child's command is retained as data, never executed here.
            for key,name in zip(('source','target'),row['command'][-2:]):
                digest(output,Path(name),row[key]['sha256'])
            inside(output,Path(row['log']))
    elif stage=='v4':
        for name,result in raw['results'].items():
            for artifact,value in result['artifacts'].items():digest(output,Path(name)/artifact,value)
        for name,value in raw['tools'].items():digest(source,name,value)
