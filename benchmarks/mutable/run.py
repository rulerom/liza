#!/usr/bin/env python3
"""Frozen A0/A3 and explicit M0, same corpus/driver and scalar C++/Rust."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'json'))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
base=load('baseline',HERE.parent/'json/run.py')
aggregate=load('aggregate',HERE.parent/'aggregate/run.py')
from corpus import workloads, SEED
A3='b210c9fd7edc05b407aa6f95ab111c2d1db1986f'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--check-only',action='store_true')
    a=parser.parse_args();out=a.output.resolve()
    if out.exists():parser.error('output must not exist')
    candidate=base.run(['git','rev-parse',a.candidate+'^{commit}'],cwd=ROOT).decode().strip()
    out.mkdir(parents=True)
    report={'status':'incomplete','created_at':datetime.now(timezone.utc).isoformat(),
            'baseline':base.BASE,'A3':A3,'candidate':candidate,'commands':[],
            'machine':platform.platform(),'architecture':platform.machine(),
            'limits':['Core-only; no universal speed or semantic proof claim.',
                      'M0 uses the same JSON transition rules with explicit mutation; UTF-8 helpers remain value-based.',
                      'Counter instrumentation is untimed and counts optimized-IR bulk copies, not all memory traffic.',
                      'A0/A3 source and reports are immutable; M0 has different Semantic IR.']}
    def run(args,**kwargs):
        report['commands'].append([str(x) for x in args]);return base.run(args,**kwargs)
    try:
        baseline=out/'baseline';baseline.mkdir()
        exes,cli,versions=base.build(baseline,2,report['commands'])
        exes['A0']=exes.pop('liza');report['tools']=versions
        target=json.loads((baseline/'liza.target.json').read_text());flags=target['flags'];report['target']=target
        clang=shutil.which('clang')
        ir_paths={'A0':baseline/'liza.optimized.ll'}
        for label,commit in [('A3',A3),('M0',candidate)]:
            directory=out/label;directory.mkdir();snapshot=directory/'source';snapshot.mkdir()
            archive=directory/'source.tar';archive.write_bytes(run(['git','archive',commit],cwd=ROOT));run(['tar','-xf',archive,'-C',snapshot])
            emitter=snapshot/('benchmarks/mutable/emit.py' if label=='M0' else 'benchmarks/json/emit_liza.py')
            ir=directory/'module.ll'
            run([sys.executable,emitter,ir,clang],cwd=snapshot,env={**os.environ,'PYTHONPATH':str(snapshot)})
            if json.loads(ir.with_suffix('.target.json').read_text())['flags']!=flags:raise ValueError('target mismatch')
            run([clang,*flags,'-O2','-Werror=override-module','-fstack-usage','-c',ir,'-o',directory/'module.o'])
            run([clang,*flags,'-O2','-S','-emit-llvm',ir,'-o',directory/'optimized.ll'])
            run([clang,*flags,'-O2','-S',ir,'-o',directory/'module.s'])
            exe=directory/'probe';run([clang,*flags,baseline/'driver.o',directory/'module.o','-o',exe]);exes[label]=exe
            ir_paths[label]=directory/'optimized.ll'
            if label=='M0':
                for filename in ('driver.c','parser.cpp','parser.rs','corpus.py','run.py','emit_liza.py'):
                    if (snapshot/'benchmarks/json'/filename).read_bytes()!=(HERE.parent/'json'/filename).read_bytes():raise ValueError('baseline harness drift')
        report['correctness']=base.correctness(exes,cli,out)
        report['correctness']['cli_cases']=report['correctness']['documents']*(len(exes)+1)
        print('All implementations agree before measurement',flush=True)
        paths={};report['workloads']=[];report['diagnostics']={}
        for label,ir in ir_paths.items():
            counted,sites=aggregate.instrument(ir.read_text());path=ir.parent/'counted.ll';path.write_text(counted)
            run([clang,*flags,'-O0',path,HERE.parent/'aggregate/copy_counts.c',HERE.parent/'json/driver.c','-o',ir.parent/'counted'])
            su=ir.parent/('liza.su' if label=='A0' else 'module.su')
            report['diagnostics'][label]={'copy_sites':sites,'stack_usage':su.read_text().splitlines(),'executed_copies':{}}
        for name,data in workloads(262144).items():
            path=out/'corpus'/('bench-'+name+'.json');path.write_bytes(data);paths[name]=path
            report['workloads'].append({'name':name,'bytes':len(data),'sha256':base.digest(path)})
            for exe in exes.values():
                if run([exe,'check',path])!=b'OK\n':raise ValueError('invalid timing input')
            import subprocess
            for label,ir in ir_paths.items():
                r=subprocess.run([str(ir.parent/'counted'),'bench',str(path),'2048','1'],capture_output=True,timeout=120)
                if r.returncode:raise ValueError('instrumented execution failed')
                result=json.loads(r.stdout);counts=json.loads(r.stderr)
                if result['status']!=0 or result['value']!=len(data):raise ValueError('instrumented result mismatch')
                counts['copy_bytes_per_input_byte']=counts['copy_bytes']/(2*len(data));counts['passes']=2
                report['diagnostics'][label]['executed_copies'][name]=counts
        samples=[]
        if not a.check_only:
            for repeat in range(10):
                schedule=[(label,name) for label in exes for name in paths];random.Random(SEED+repeat).shuffle(schedule)
                for label,name in schedule:
                    path=paths[name];length=path.stat().st_size;rounds=max(1,4*1024*1024//length)
                    row=json.loads(run([exes[label],'bench',path,2048,rounds]))
                    if row['status']!=0 or row['value']!=length or row['checksum']!=(rounds+1)*length:raise ValueError('timed result mismatch')
                    row.update(variant=label,workload=name,repeat=repeat,mib_s=length*rounds/1048576/row['seconds']);samples.append(row)
                    (out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
            report['samples']=samples
            report['summary']=[{'variant':label,'workload':name,'median_mib_s':statistics.median(r['mib_s'] for r in samples if r['variant']==label and r['workload']==name)} for name in paths for label in exes]
        report['evidence']={str(p.relative_to(out)):base.digest(p) for p in out.rglob('*') if p.is_file() and 'source' not in p.parts and p.suffix in ('.ll','.s','.su','.json')}
        if sys.platform=='darwin':report['hardware']=run(['sysctl','-n','machdep.cpu.brand_string','hw.memsize']).decode()
        report['status']='correctness_passed' if a.check_only else 'measured'
    except Exception as error:
        report['error']=str(error);raise
    finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status']+': '+str(out/'report.json'))

if __name__=='__main__':main()
