#!/usr/bin/env python3
"""P3: unchanged field forwarding across value phis; no production pass."""
import argparse
import importlib.util
import json
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'json'))
sys.path.insert(0,str(HERE.parent/'state'))
from traffic import instrument
spec=importlib.util.spec_from_file_location('base',HERE.parent/'json/run.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
VARIANTS=('default','forward')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rust-counter-clang',default='/opt/homebrew/opt/llvm/bin/clang');a=p.parse_args()
    ref=a.reference.resolve();out=a.output.resolve()
    if out.exists():p.error('fresh output required')
    previous=json.loads((ref/'report.json').read_text())
    if previous['status'] not in ('measured','correctness_passed'):p.error('reference incomplete')
    for n,h in previous['evidence'].items():
        if base.digest(ref/n)!=h:raise ValueError('reference drift: '+n)
    out.mkdir(parents=True)
    r={'status':'incomplete','candidate':previous['candidate'],'tools':previous['tools'],'hardware':previous['hardware'],'commands':[],'variants':{},'samples':[],
       'harness_hashes':{f.name:base.digest(f) for f in HERE.iterdir() if f.is_file()}}
    def run(args,**kw):r['commands'].append([str(x) for x in args]);return base.run(args,**kw)
    try:
        clang=shutil.which('clang');flags=previous['target']['flags'];r['target']=previous['target']
        r['rust_verbose']=run(['rustc','-vV']).decode()
        if run([clang,'--version']).decode()!=previous['tools']['clang']:raise ValueError('toolchain changed')
        raw=(ref/'M0/module.ll').read_text();exes={'rust':ref/'baseline/rust'}
        emitted=out/'emitted';emitted.mkdir()
        run([sys.executable,HERE/'emit.py',emitted/'module.ll',clang],env={**__import__('os').environ,'PYTHONPATH':str(ROOT)},cwd=ROOT)
        if (emitted/'module.original.ll').read_text()!=raw:raise ValueError('emitter/source drift from reference')
        r['forwarded_fields']=json.loads((emitted/'module.certificates.json').read_text())
        for label in VARIANTS:
            folder=out/label;folder.mkdir();ir=raw;sites=0
            if label=='forward':ir=(emitted/'module.ll').read_text();sites=len(r['forwarded_fields'])
            path=folder/'module.ll';path.write_text(ir);extra=[]
            for opt in (0,2):
                obj=folder/f'O{opt}.o';exe=folder/f'O{opt}'
                run([clang,*flags,f'-O{opt}',*extra,'-fstack-usage','-c',path,'-o',obj])
                run([clang,*flags,ref/'baseline/driver.o',obj,'-o',exe]);exes[f'{label}-O{opt}']=exe
            run([clang,*flags,'-O2',*extra,'-S','-emit-llvm',path,'-o',folder/'optimized.ll'])
            run([clang,*flags,'-O2',*extra,'-S',path,'-o',folder/'module.s'])
            sizes=run(['size','-m',folder/'O2.o']).decode();(folder/'size.txt').write_text(sizes)
            r['variants'][label]={'forwarding_sites':sites,'text_bytes':int(re.search(r'Section \(__TEXT, __text\): (\d+)',sizes)[1]),'stack':(folder/'O2.su').read_text().splitlines()}
        r['correctness']=base.correctness(exes,ref/'baseline/liza-json',out);r['correctness']['cli_cases']=r['correctness']['documents']*(len(exes)+1)
        print('All variants agree at O0/O2',flush=True)
        timing={k[:-3]:v for k,v in exes.items() if k.endswith('-O2')};timing['rust']=exes['rust']
        paths={}
        for row in previous['workloads']:
            path=ref/'corpus'/('bench-'+row['name']+'.json')
            if base.digest(path)!=row['sha256']:raise ValueError('corpus drift')
            paths[row['name']]=path
            for exe in exes.values():
                if run([exe,'check',path])!=b'OK\n':raise ValueError('timing input mismatch')
        r['workloads']=previous['workloads']
        for repeat in range(10):
            schedule=[(v,n) for v in timing for n in paths];random.Random(234+repeat).shuffle(schedule)
            for v,n in schedule:
                path=paths[n];length=path.stat().st_size;rounds=16*1024*1024//length
                row=json.loads(run([timing[v],'bench',path,2048,rounds]))
                if row['status'] or row['value']!=length or row['checksum']!=(rounds+1)*length:raise ValueError('timing mismatch')
                row.update(variant=v,workload=n,repeat=repeat,mib_s=length*rounds/1048576/row['seconds']);r['samples'].append(row)
            print('series',repeat+1,flush=True)
        r['summary']=[{'variant':v,'workload':n,'median_mib_s':statistics.median(s['mib_s'] for s in r['samples'] if s['variant']==v and s['workload']==n)} for v in timing for n in paths]
        r['traffic']={}
        r['rust_counter_tool']=run([a.rust_counter_clang,'--version']).decode()
        for label in [*VARIANTS,'rust']:
            folder=out/label;folder.mkdir(exist_ok=True)
            path=ref/'baseline/rust.optimized.ll' if label=='rust' else folder/'optimized.ll'
            sizes={s['state_bytes'] for s in r['samples'] if s['variant']==label}
            if len(sizes)!=1:raise ValueError('inconsistent state layout')
            counted,sites=instrument(path.read_text(),'p' if label=='rust' else 'state',sizes.pop())
            (folder/'counted.ll').write_text(counted)
            libs=[ref/'baseline/rust.a'] if label=='rust' else []
            run([a.rust_counter_clang if label=='rust' else clang,*flags,'-O0',folder/'counted.ll',HERE.parent/'state/traffic.c',ref/'baseline/driver.o',*libs,'-o',folder/'counted'])
            if run([folder/'counted','probe'],input=(out/'probe-input.bin').read_bytes(),timeout=120)!=(out/'default-O2.probe.bin').read_bytes():raise ValueError('instrumented probe disagreement')
            traffic={}
            for name,path in paths.items():
                cmd=[str(folder/'counted'),'bench',str(path),'2048','1'];r['commands'].append(cmd)
                result=subprocess.run(cmd,capture_output=True,timeout=120,check=True)
                data=json.loads(result.stdout)
                if data['status'] or data['checksum']!=2*path.stat().st_size:raise ValueError('counter result mismatch')
                counts=json.loads(result.stderr)
                counts['passes']=2;counts['input_bytes']=2*path.stat().st_size;traffic[name]=counts
            r['traffic'][label]={'static_sites':sites,'workloads':traffic}
            print('traffic',label,flush=True)
        for name in ('rust','rust.s','rust.optimized.ll','rust.a','source.tar','driver.o'):
            shutil.copy2(ref/'baseline'/name,out/('reference-'+name))
        shutil.copy2(ref/'M0/source.tar',out/'candidate-source.tar')
        r['status']='measured'
    except Exception as e:r['error']=str(e);raise
    finally:(out/'report.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
