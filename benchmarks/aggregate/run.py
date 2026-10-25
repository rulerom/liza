#!/usr/bin/env python3
"""A0–A3 core-only ablation, against an immutable committed compiler snapshot."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'json'))
spec=importlib.util.spec_from_file_location('json_baseline_runner',HERE.parent/'json'/'run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
from corpus import workloads, SEED


def instrument(ir):
    lines=[];sites=0
    for line in ir.splitlines():
        if 'call ' in line and re.search(r'@llvm.mem(?:cpy|move)\.',line):
            size=re.search(r', i64 ([^,]+), i1 ',line)
            if not size:raise ValueError('unsupported transfer intrinsic: '+line)
            lines.append('  call void @study_record_copy(i64 '+size[1]+')')
            sites+=1
        # Recording counters writes globals. Discard inferred memory effects in
        # this diagnostic build; all original transfers and guards remain.
        lines.append(re.sub(r'\bmemory\([^)]*\)|\breadonly\b|\breadnone\b','',line))
    lines.append('declare void @study_record_copy(i64)')
    return '\n'.join(lines)+'\n',sites


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',required=True)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--check-only',action='store_true')
    a=p.parse_args();out=a.output.resolve()
    if out.exists():p.error('output must not exist')
    candidate=base.run(['git','rev-parse',a.candidate+'^{commit}'],cwd=ROOT).decode().strip()
    out.mkdir(parents=True)
    report={'status':'incomplete','created_at':datetime.now(timezone.utc).isoformat(),
            'baseline':base.BASE,'candidate':candidate,'commands':[],
            'machine':platform.platform(),'architecture':platform.machine(),
            'variants':{'A0':'Unchanged compiler at b320611',
                        'A1':'Research-only readonly/nocapture JsonState input + noalias sret',
                        'A2':'Research-only acyclic local storage/slot reuse; immutable ABI',
                        'A3':'Production direct owned callee variants; no JSON source changes'},
            'limits':['Core-only, one machine; no CLI speed or liveness claim.',
                      'A1/A2 are explicit experimental emitters, not shipped compiler behavior.',
                      'Copy counters count executed memcpy/memmove sites in optimized IR, not every scalar/register copy.',
                      'Instrumented builds use O0 after optimized-IR instrumentation; never timed.',
                      'Frames are individual Clang stack-usage records, not peak call-chain sizes.']}
    def run(args,**kw):
        report['commands'].append([str(x) for x in args]);return base.run(args,**kw)
    try:
        snapshots={}
        for name,commit in [('baseline',base.BASE),('candidate',candidate)]:
            folder=out/name;folder.mkdir();archive=out/(name+'.tar')
            archive.write_bytes(run(['git','archive',commit],cwd=ROOT));run(['tar','-xf',archive,'-C',folder])
            snapshots[name]=folder
        for name in ('run.py','corpus.py','driver.c','emit_liza.py'):
            if (HERE.parent/'json'/name).read_bytes() != (snapshots['candidate']/'benchmarks/json'/name).read_bytes():
                raise ValueError('benchmark driver drift: '+name)
        report['study_driver_sha256']=base.digest(__file__)
        for name in ('json.liza','utf8_stream.liza'):
            paths=[x/'liza'/'stdlib'/name for x in snapshots.values()]
            if paths[0].read_bytes()!=paths[1].read_bytes():raise ValueError('parser source drift: '+name)
        clang=shutil.which('clang')
        if not clang:raise ValueError('Clang required')
        report['clang']=run([clang,'--version']).decode()
        exes={};diagnostics={};flags=None
        for variant in ('A0','A1','A2','A3'):
            directory=out/variant;directory.mkdir();snapshot=snapshots['baseline' if variant=='A0' else 'candidate']
            env={**os.environ,'PYTHONPATH':str(snapshot)}
            emitter=snapshots['candidate']/'benchmarks/aggregate/emit.py'
            run([sys.executable,emitter,variant,directory/'module.ll',clang],cwd=snapshot,env=env)
            target=json.loads((directory/'module.target.json').read_text())
            if flags is not None and flags!=target['flags']:raise ValueError('target mismatch')
            flags=target['flags'];report['target']=target
            if variant!='A0' and (directory/'module.semantic.txt').read_bytes()!=(out/'A0/module.semantic.txt').read_bytes():
                raise ValueError('Semantic IR changed between ablations')
            run([clang,*flags,'-Werror=override-module','-O2','-S','-emit-llvm',directory/'module.ll','-o',directory/'optimized.ll'])
            run([clang,*flags,'-Werror=override-module','-O2','-fstack-usage','-c',directory/'module.ll','-o',directory/'module.o'])
            run([clang,*flags,'-Werror=override-module','-O2','-S',directory/'module.ll','-o',directory/'module.s'])
            exe=directory/'probe'
            run([clang,*flags,'-O2',snapshots['candidate']/'benchmarks/json/driver.c',directory/'module.o','-o',exe])
            exes[variant]=exe
            counted,sites=instrument((directory/'optimized.ll').read_text());(directory/'counted.ll').write_text(counted)
            run([clang,*flags,'-O0',directory/'counted.ll',snapshots['candidate']/'benchmarks/aggregate/copy_counts.c',snapshots['candidate']/'benchmarks/json/driver.c','-o',directory/'counted'])
            diagnostics[variant]={'copy_sites':sites,'stack_usage':(directory/'module.su').read_text().splitlines()}
        # Same independent expected outcomes/partitions as the baseline. Each
        # ablation's file driver is checked as well; timing below is core-only.
        cli=out/'liza-json'
        run([sys.executable,'-m','liza','build','examples/apps/liza_json.liza','-O','2','--clang',clang,'-o',cli],cwd=snapshots['candidate'],env={**os.environ,'PYTHONPATH':str(snapshots['candidate'])})
        report['correctness']=base.correctness(exes,cli,out)
        print('A0/A1/A2/A3 agree on all partitioned cases and CLI probes',flush=True)
        paths={};manifest=[]
        for name,data in workloads(262144).items():
            path=out/'corpus'/('bench-'+name+'.json');path.write_bytes(data);paths[name]=path
            manifest.append({'name':name,'sha256':base.digest(path),'bytes':len(data)})
            for variant,exe in exes.items():
                if run([exe,'check',path])!=b'OK\n':raise ValueError('invalid timing input')
                counted=subprocess.run([str(out/variant/'counted'),'bench',str(path),'2048','1'],capture_output=True,timeout=120)
                if counted.returncode:raise ValueError('copy instrumentation failed')
                state=json.loads(counted.stdout);counts=json.loads(counted.stderr)
                if state['status']!=0 or state['value']!=len(data):raise ValueError('instrumented result mismatch')
                # Driver executes one warmup + one diagnostic iteration.
                counts.update({'passes':2,'input_bytes':len(data),'copy_bytes_per_input_byte':counts['copy_bytes']/(2*len(data))})
                diagnostics[variant].setdefault('executed_copies',{})[name]=counts
        report['diagnostics']=diagnostics;report['workloads']=manifest
        samples=[]
        if not a.check_only:
            for repeat in range(10):
                schedule=[(variant,name) for variant in exes for name in paths]
                random.Random(SEED+repeat).shuffle(schedule)
                for variant,name in schedule:
                    path=paths[name];length=path.stat().st_size;rounds=max(1,4*1024*1024//length)
                    row=json.loads(run([exes[variant],'bench',path,2048,rounds]))
                    if row['status']!=0 or row['value']!=length or row['checksum']!=(rounds+1)*length:raise ValueError('timed result mismatch')
                    row.update(variant=variant,workload=name,repeat=repeat,mib_s=length*rounds/1048576/row['seconds'])
                    samples.append(row);(out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
            report['samples']=samples;report['summary']=[]
            for name in paths:
                for variant in exes:
                    values=[r['mib_s'] for r in samples if r['variant']==variant and r['workload']==name]
                    report['summary'].append({'variant':variant,'workload':name,'median_mib_s':statistics.median(values),'min_mib_s':min(values),'max_mib_s':max(values)})
        report['evidence']={str(f.relative_to(out)):base.digest(f) for variant in exes for f in (out/variant).iterdir() if f.is_file()}
        if sys.platform=='darwin':report['hardware']=run(['sysctl','-n','machdep.cpu.brand_string','hw.memsize']).decode()
        report['status']='correctness_passed' if a.check_only else 'measured'
    except Exception as error:
        report['error']=str(error);raise
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status']+': '+str(out/'report.json'))

if __name__=='__main__':main()
