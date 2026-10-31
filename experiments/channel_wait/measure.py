#!/usr/bin/env python3
"""Record bounded wait probe timings; these are not latency guarantees."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=10);a=p.parse_args()
if a.output.exists() or not 1<=a.repeats<=100:p.error('fresh output and repeats in 1..100 required')
with tempfile.TemporaryDirectory(prefix='liza-wait-measure-') as tmp:
    exe=Path(tmp)/('wait.exe' if sys.platform=='win32' else 'wait')
    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'wait.c'),str(HERE/'test_wait.c'),'-o',str(exe)]
    if sys.platform!='win32':cmd.append('-pthread')
    subprocess.run(cmd,check=True)
    rows=[]
    for repeat in range(a.repeats):
        run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15,check=True)
        parsed={}
        for line in run.stdout.splitlines():
            if 'deadline_ms=' in line:
                values={k:int(v) for k,v in (x.split('=') for x in line.split())}
                prefix='reacquire_' if line.startswith('reacquire_') else 'lock_' if line.startswith('lock_') else ''
                parsed[prefix+'decision_late_ms']=values[prefix+'decision_ms']-values[prefix+'deadline_ms']
                parsed[prefix+'return_late_ms']=values[prefix+'return_ms']-values[prefix+'deadline_ms']
                parsed[prefix+'raw']=values
        if len(parsed) not in (6,9):raise RuntimeError('missing timing output')
        if 'reacquire_raw' not in parsed:parsed['reacquire_skipped']='scheduling'
        parsed['repeat']=repeat;rows.append(parsed)
    paths=[HERE/'wait.h',HERE/'wait.c',HERE/'test_wait.c',Path(__file__)]
    report={'platform':platform.platform(),'clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0],
            'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'compile_command':cmd,'samples':rows,
            'limitations':['millisecond clock; small local sample, not p99 or hard timing bound',
                           'test injects spurious returns and holds mutex deliberately; not production workload',
                           'instrumentation, clock overhead and OS scheduling change timings',
                           'mutex acquisition and condition-wait mutex reacquisition are not deadline bounded']}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
