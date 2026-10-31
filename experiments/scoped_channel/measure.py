#!/usr/bin/env python3
"""Instrumented diagnostics, not a benchmark of uninstrumented channel cost."""
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
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
if a.output.exists() or not 1<=a.repeats<=10:p.error('fresh output and repeats in 1..10 required')
with tempfile.TemporaryDirectory(prefix='liza-channel-measure-') as tmp:
    exe=Path(tmp)/('probe.exe' if sys.platform=='win32' else 'probe')
    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DCH_MEASURE',str(HERE/'channel.c'),str(HERE/'test_channel.c'),'-o',str(exe)]
    if sys.platform!='win32':cmd.append('-pthread')
    subprocess.run(cmd,check=True)
    rows=[]
    for repeat in range(a.repeats):
        r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=60,check=True)
        for line in r.stdout.splitlines():
            if line.startswith('capacity='):
                row={k:int(v) for k,v in (item.split('=') for item in line.split())};row['repeat']=repeat;rows.append(row)
    if len(rows)!=4*a.repeats:raise RuntimeError('incomplete measurement')
    paths=[HERE/'channel.c',HERE/'channel.h',HERE/'test_channel.c',Path(__file__)]
    report={'status':'measured','platform':platform.platform(),'clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0],
            'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
            'source_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths},
            'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'compile_command':cmd,'samples':rows,
            'limitations':['Instrumented build; clock and try-lock calls change timing, memory footprint and contention',
                           'Wall-clock hold time includes scheduling and preemption',
                           'Busy-yield producer and consumer; one host, not network workload or Liza',
                           'Aggregate and maxima only, no p99; get_metrics adds one lock acquisition',
                           'Counters do not saturate; intended only for short diagnostic runs']}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
