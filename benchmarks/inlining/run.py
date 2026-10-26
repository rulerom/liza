#!/usr/bin/env python3
"""Compare LLVM inliner thresholds with explicit post-codegen resource gates."""
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
import time
from policy import STRATEGIES, guided, decision
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE.parent/'json'))
spec=importlib.util.spec_from_file_location('base',HERE.parent/'json/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.modules import load_program
from liza.backend import llvm
from liza.target import resolve


def stress_source():
    # Many distinct callers of one moderately sized branchy function.
    leaf='fn mix(x:u32)->u32 {var n=x;'
    for i in range(64):
        leaf+=f'if (n & {1<<(i%16)})!=0 {{n=n ^ {12345+i*997}}} else {{n=n ^ {45678+i*991}}}\n'
    leaf+='return n}\n'
    return leaf+'\n'.join(f'fn caller_{i}(x:u32)->u32 {{return mix(x ^ {i+1})}}' for i in range(48))+'\nfn main()->u32 {return caller_0(42)}'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();ref=a.reference.resolve();out=a.output.resolve()
    if out.exists():p.error('fresh output required')
    old=json.loads((ref/'report.json').read_text())
    if old['status'] not in ('measured','correctness_passed'):p.error('incomplete reference')
    for name,digest in old['evidence'].items():
        if base.digest(ref/name)!=digest:raise ValueError('reference drift: '+name)
    if base.run(['git','diff',old['candidate'],'HEAD','--','liza','examples'],cwd=ROOT):
        raise ValueError('auxiliary compiler/examples differ from reference')
    out.mkdir(parents=True)
    report={'status':'incomplete','reference_commit':old['candidate'],'study_base':base.run(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
            'tools':old['tools'],'hardware':old['hardware'],'target':old['target'],'commands':[],
            'harness_hashes':{p.name:base.digest(p) for p in HERE.glob('*.py')},'samples':[],'builds':{},'gates':{}}
    def run(args,**kw):
        report['commands'].append([str(x) for x in args]);return base.run(args,**kw)
    try:
        clang=shutil.which('clang');flags=old['target']['flags']
        if run([clang,'--version']).decode()!=old['tools']['clang']:raise ValueError('Clang changed')
        target=resolve(clang)
        units={'json':((ref/'M0/module.ll').read_text(),json.loads((ref/'M0/module.semantic.txt').read_text()))}
        for label,path in [('rtp',ROOT/'examples/rtp_result.liza'),('relay',ROOT/'examples/apps/liza_proxy.liza'),('growth',None)]:
            module=lower(load_program(path)) if path else lower(Parser(stress_source()).parse())
            units[label]=(llvm(module,target),json.loads(dump(module)))
        (out/'growth.liza').write_text(stress_source())
        exes={'rust':ref/'baseline/rust'}
        for unit,(ir,semantic) in units.items():
            report['builds'][unit]={}
            for variant,extra in STRATEGIES.items():
                folder=out/unit/variant;folder.mkdir(parents=True)
                source,selected=guided(ir,semantic) if variant=='guided' else (ir,[])
                if source.replace(' inlinehint {',' {')!=ir:raise ValueError('non-attribute IR edit')
                path=folder/'module.ll';path.write_text(source)
                (folder/'semantic.json').write_text(json.dumps(semantic))
                run([clang,*flags,'-O2',*extra,'-S',path,'-o',folder/'module.s'])
                run([clang,*flags,'-O2',*extra,'-S','-emit-llvm',path,'-o',folder/'optimized.ll'])
                command=[clang,*flags,'-O2',*extra,'-fstack-usage','-c',path,'-o',folder/'module.o']
                run(command) # Untimed warmup before repeated compiler measurements.
                seconds=[]
                for _ in range(3):
                    t=time.perf_counter();run(command);seconds.append(time.perf_counter()-t)
                sizes=run(['size','-m',folder/'module.o']).decode()
                (folder/'size.txt').write_text(sizes)
                text=int(re.search(r'Section \(__TEXT, __text\): (\d+)',sizes)[1])
                frames={}
                for line in (folder/'module.su').read_text().splitlines():
                    name,size,kind=line.rsplit(':',1)[1].split('\t')
                    if kind!='static':raise ValueError('unbounded frame: '+line)
                    frames[name]=int(size)
                report['builds'][unit][variant]={'text_bytes':text,'frames':frames,'compile_seconds':seconds,'median_compile_seconds':statistics.median(seconds),'selected':selected}
                if unit=='json':
                    for opt in (0,2):
                        obj=folder/f'O{opt}.o';exe=folder/f'O{opt}'
                        run([clang,*flags,f'-O{opt}',*extra,'-c',path,'-o',obj])
                        run([clang,*flags,ref/'baseline/driver.o',obj,'-o',exe]);exes[f'{variant}-O{opt}']=exe
            report['gates'][unit]={v:decision(report['builds'][unit]['default'],m) for v,m in report['builds'][unit].items()}
            for v,gate in report['gates'][unit].items():
                chosen=v if gate['accepted'] else 'default'
                shutil.copy2(out/unit/chosen/'module.o',out/unit/v/'selected.o')
                gate['selected_object_sha256']=base.digest(out/unit/v/'selected.o')
            print(unit,[(v,m['text_bytes'],report['gates'][unit][v]['accepted']) for v,m in report['builds'][unit].items()],flush=True)
        report['correctness']=base.correctness(exes,ref/'baseline/liza-json',out)
        report['correctness']['cli_cases']=report['correctness']['documents']*(len(exes)+1)
        print('O0/O2 agreement passed',flush=True)
        timing={k[:-3]:v for k,v in exes.items() if k.endswith('-O2')};timing['rust']=exes['rust']
        # Same-session P0 ceiling control; not a candidate policy.
        ceiling=out/'p0-control';ceiling.mkdir()
        sys.path.insert(0,str(HERE.parent/'parity'))
        spec=importlib.util.spec_from_file_location('p0',HERE.parent/'parity/run.py');p0=importlib.util.module_from_spec(spec);spec.loader.exec_module(p0)
        (ceiling/'module.ll').write_text(p0.transform(units['json'][0],p0.VARIANTS['combined']))
        run([clang,*flags,'-O2','-c',ceiling/'module.ll','-o',ceiling/'module.o'])
        run([clang,*flags,ref/'baseline/driver.o',ceiling/'module.o','-o',ceiling/'probe']);timing['p0-control']=ceiling/'probe'
        # Reuse independent probe expectations for the control, too.
        data=(out/'probe-input.bin').read_bytes()
        if run([ceiling/'probe','probe'],input=data)!=(out/'default-O2.probe.bin').read_bytes():raise ValueError('control mismatch')
        paths={}
        for row in old['workloads']:
            path=ref/'corpus'/('bench-'+row['name']+'.json')
            if base.digest(path)!=row['sha256']:raise ValueError('corpus drift')
            paths[row['name']]=path
            for exe in timing.values():
                if run([exe,'check',path])!=b'OK\n':raise ValueError('timing input mismatch')
        report['workloads']=old['workloads']
        for repeat in range(10):
            schedule=[(v,n) for v in timing for n in paths];random.Random(100+repeat).shuffle(schedule)
            for v,n in schedule:
                path=paths[n];length=path.stat().st_size;rounds=16*1024*1024//length
                row=json.loads(run([timing[v],'bench',path,2048,rounds]))
                if row['status'] or row['value']!=length or row['checksum']!=(rounds+1)*length:raise ValueError('timing result mismatch')
                row.update(variant=v,workload=n,repeat=repeat,mib_s=length*rounds/1048576/row['seconds']);report['samples'].append(row)
            print('series',repeat+1,flush=True)
        report['summary']=[{'variant':v,'workload':n,'median_mib_s':statistics.median(x['mib_s'] for x in report['samples'] if x['variant']==v and x['workload']==n)} for v in timing for n in paths]
        report['effective']={v:('default' if not report['gates']['json'][v]['accepted'] else v) for v in STRATEGIES}
        for name in ('rust','rust.s','rust.optimized.ll','source.tar','driver.o'):
            shutil.copy2(ref/'baseline'/name,out/('reference-'+name))
        shutil.copy2(ref/'M0/source.tar',out/'candidate-source.tar')
        report['status']='measured'
    except Exception as e:
        report['error']=str(e);raise
    finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
