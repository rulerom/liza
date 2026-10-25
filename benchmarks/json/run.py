#!/usr/bin/env python3
"""Pinned scalar JSON comparison. No timings are accepted before agreement."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import struct
import subprocess
import sys
import time

from corpus import SEED, cases, partitions, workloads, sha

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
BASE='b3206117a225f6f852cec5bef18928fe1bd43856'

def digest(path):return sha(Path(path).read_bytes())

def run(command, **kwargs):
    kwargs.setdefault('timeout',180)
    r=subprocess.run([str(x) for x in command],capture_output=True,**kwargs)
    if r.returncode:
        raise RuntimeError(f'{command}: exit {r.returncode}\n{r.stderr.decode(errors="replace")}')
    return r.stdout

def build(out, opt, commands):
    snapshot=out/'source';snapshot.mkdir()
    archive=out/'source.tar'
    archive.write_bytes(run(['git','archive',BASE],cwd=REPO))
    run(['tar','-xf',archive,'-C',snapshot])
    env={**os.environ,'PYTHONPATH':str(snapshot)}
    def command(args, **kw):
        commands.append([str(x) for x in args]);return run(args,**kw)
    clang=shutil.which('clang');cpp=shutil.which('clang++');rust=shutil.which('rustc')
    if not all((clang,cpp,rust)):raise RuntimeError('clang, clang++ and rustc are required; no partial baseline')
    ir=out/'liza.ll'
    command([sys.executable,HERE/'emit_liza.py',ir,clang],cwd=snapshot,env=env)
    target=json.loads(ir.with_suffix('.target.json').read_text())
    flags=target['flags']
    command([clang,*flags,f'-O{opt}','-c',HERE/'driver.c','-o',out/'driver.o'])
    command([clang,*flags,'-Werror=override-module',f'-O{opt}','-fstack-usage','-c',ir,'-o',out/'liza.o'])
    command([clang,*flags,'-Werror=override-module',f'-O{opt}','-S','-emit-llvm',ir,'-o',out/'liza.optimized.ll'])
    command([clang,*flags,'-Werror=override-module',f'-O{opt}','-S',ir,'-o',out/'liza.s'])
    executables={}
    for name in ('cpp-inplace','cpp-value'):
        variant=['-DVALUE_STATE'] if name=='cpp-value' else []
        common=[cpp,*flags,'-std=c++17',f'-O{opt}',*variant,HERE/'parser.cpp']
        command([*common,'-fstack-usage','-c','-o',out/f'{name}.o'])
        command([*common,'-S','-emit-llvm','-o',out/f'{name}.optimized.ll'])
        command([*common,'-S','-o',out/f'{name}.s'])
        exe=out/name;command([cpp,*flags,out/'driver.o',out/f'{name}.o','-o',exe]);executables[name]=exe
    cpu='generic' if target['triple'].startswith(('arm64','aarch64')) else 'x86-64'
    common=[rust,'--edition','2021','-C',f'target-cpu={cpu}','-C',f'opt-level={opt}','-C','overflow-checks=yes','-C','panic=abort','--crate-type','staticlib',HERE/'parser.rs']
    command([*common,'--emit',f'link={out}/rust.a,llvm-ir={out}/rust.optimized.ll,asm={out}/rust.s'])
    for name,obj in [('liza',out/'liza.o'),('rust',out/'rust.a')]:
        exe=out/name
        libs=['-ldl','-lpthread','-lm'] if name=='rust' and sys.platform.startswith('linux') else []
        command([clang,*flags,out/'driver.o',obj,*libs,'-o',exe]);executables[name]=exe
    cli=out/'liza-json'
    command([sys.executable,'-m','liza','build','examples/apps/liza_json.liza','-O',str(opt),'--clang',clang,'-o',cli],cwd=snapshot,env=env)
    return executables,cli,{tool:run([path,'--version']).decode() for tool,path in [('clang',clang),('clang++',cpp),('rustc',rust)]}

def assert_results(actual,expected,label):
    if actual!=expected:
        i=next((i for i,(a,e) in enumerate(zip(actual,expected)) if a!=e),min(len(actual),len(expected)))
        raise AssertionError(f'{label}: mismatch at case {i}: {actual[i:i+1]} != {expected[i:i+1]}')

def correctness(exes,cli,out):
    data=bytearray();expected=[];manifest=[]
    root=out/'corpus';root.mkdir()
    for idx,(value,status,offset) in enumerate(cases()):
        path=root/f'{idx:03}.bin';path.write_bytes(value)
        chunks_list=list(partitions(value))
        manifest.append({'file':str(path.relative_to(out)),'sha256':digest(path),'bytes':len(value),'expected':[status,offset],'partitions':len(chunks_list)})
        for chunks in chunks_list:
            expected.append((status,offset));data+=struct.pack('<I',len(chunks))
            for chunk in chunks:data+=struct.pack('<I',len(chunk))+chunk
    (out/'probe-input.bin').write_bytes(data)
    for name,exe in exes.items():
        output=run([exe,'probe'],input=data,timeout=120)
        (out/f'{name}.probe.bin').write_bytes(output)
        if len(output)%12:raise AssertionError(f'{name}: truncated probe result')
        actual=list(struct.iter_unpack('<IQ',output))
        assert_results(actual,expected,name)
    kinds=['','Syntax','InvalidNumber','InvalidEscape','InvalidSurrogate','InvalidUtf8','UnexpectedEof','DepthLimit','SizeOverflow']
    for row in manifest:
        status,offset=row['expected']
        expected_code=0 if status==0 else (4 if status>=7 else 1)
        expected_text=b'OK\n' if status==0 else f'{kinds[status]} at byte {offset}\n'.encode()
        for name,exe in {**exes,'liza-cli':cli}.items():
            r=subprocess.run([str(exe),'check',str(out/row['file'])],capture_output=True,timeout=30)
            if r.returncode!=expected_code or (r.stdout if status==0 else r.stderr)!=expected_text:
                raise AssertionError(f'{name}: CLI mismatch for {row["file"]}')
    return {'status':'passed','cli_cases':len(manifest)*5,'cases':len(expected),'documents':len(manifest),'manifest':manifest,'probe_sha256':sha(data)}

def summaries(samples):
    groups={}
    for s in samples:groups.setdefault((s['mode'],s['workload'],s['implementation']),[]).append(s)
    result=[]
    for (mode,workload,name),rows in sorted(groups.items()):
        times=[r['seconds'] for r in rows]
        result.append({'mode':mode,'workload':workload,'implementation':name,'samples':len(rows),
                       'median_seconds':statistics.median(times),'min_seconds':min(times),'max_seconds':max(times),
                       'median_mib_s':statistics.median([r['mib_s'] for r in rows])})
    return result

def measurements(exes,cli,out,size,repeats):
    paths={};manifest=[]
    for name,data in workloads(size).items():
        path=out/'corpus'/f'bench-{name}.json';path.write_bytes(data);paths[name]=path
        manifest.append({'file':str(path.relative_to(out)),'sha256':digest(path),'bytes':len(data)})
        # Every actual timing input is checked by every implementation before timing.
        for implementation,exe in {**exes,'liza-cli':cli}.items():
            if run([exe,'check',path],timeout=120)!=b'OK\n':raise AssertionError(implementation)
    samples=[];schedule=[]
    for repeat in range(repeats):
        batch=[(mode,name,impl) for mode in ('core','cli') for name in paths for impl in exes]
        random.Random(SEED+repeat).shuffle(batch)
        schedule.extend((repeat,*x) for x in batch)
    # CLI warmup uses the real applications; timings below include process and I/O.
    for name,path in paths.items():
        for impl,exe in exes.items():run([cli if impl=='liza' else exe,'check',path],timeout=120)
    for repeat,mode,name,impl in schedule:
        path=paths[name];length=path.stat().st_size;exe=exes[impl]
        if mode=='core':
            rounds=max(1,4*1024*1024//length)
            row=json.loads(run([exe,'bench',path,2048,rounds],timeout=180))
            if row['status']!=0 or row['value']!=length or row['checksum']!=(rounds+1)*length:
                raise AssertionError(f'{impl}: benchmark result changed')
        else:
            start=time.perf_counter()
            if run([cli if impl=='liza' else exe,'check',path],timeout=120)!=b'OK\n':raise AssertionError(impl)
            row={'seconds':time.perf_counter()-start,'iterations':1}
        row.update({'mode':mode,'workload':name,'implementation':impl,'repeat':repeat,
                    'input_bytes':length,'chunk_bytes':2048,
                    'mib_s':length*row['iterations']/1048576/row['seconds']})
        samples.append(row)
        # Keep raw evidence even if a later sample fails.
        (out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    return samples,manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--size',type=int,default=262144)
    p.add_argument('--repeats',type=int,default=10)
    p.add_argument('-O',type=int,choices=(0,2),default=2)
    a=p.parse_args();out=a.output.resolve()
    if out.exists():p.error('output must be a fresh directory')
    if not 1<=a.size<=8*1024*1024:p.error('size must be 1..8388608')
    if a.repeats<10:p.error('at least 10 timed samples required')
    out.mkdir(parents=True);commands=[]
    report={'status':'incomplete','created_at':datetime.now(timezone.utc).isoformat(),'source_commit':BASE,'seed':SEED,'opt':a.O,'machine':platform.platform(),
            'architecture':platform.machine(),'python':sys.version,'commands':commands,
            'limits':['One-machine scalar baseline, not a compiler benchmark for all programs.',
                      'C++/Rust CLI uses the common C file driver; Liza CLI is the actual application.',
                      'No LTO across the common driver ABI; kernel includes init/feed/status/finish.',
                      'Warm filesystem cache; CLI includes process launch and I/O.',
                      'Unsigned C++ arithmetic uses reachable-state bounds and explicit u64 guards; Rust overflow checks enabled.',
                      'RSS includes loaded input/driver/runtime; no measured allocation count or universal zero-allocation claim.',
                      'Negative corpus is correctness-only; throughput is reported only for valid complete inputs.']}
    try:
        exes,cli,versions=build(out,a.O,commands);report['tools']=versions;report['target']=json.loads((out/'liza.target.json').read_text())
        report['correctness']=correctness(exes,cli,out)
        print(f"Agreement: {report['correctness']['cases']} partitioned cases across four implementations",flush=True)
        if not a.check_only:
            samples,manifest=measurements(exes,cli,out,a.size,a.repeats)
            report.update(samples=samples,workloads=manifest,summary=summaries(samples))
        report['binaries']={n:{'sha256':digest(v),'bytes':v.stat().st_size} for n,v in {**exes,'liza-cli':cli}.items()}
        report['state_diagnostics']={}
        for name in exes:
            ir=(out/f'{name}.optimized.ll').read_text()
            report['state_diagnostics'][name]={'ir_sha256':sha(ir.encode()),'assembly_sha256':digest(out/f'{name}.s'),
                'memcpy_call_sites':sum('call ' in line and '@llvm.memcpy' in line for line in ir.splitlines()),
                'alloca_sites':sum(' alloca ' in line for line in ir.splitlines()),
                'note':'Static sites in full module, not executed bytes/copies; stack-usage entries are per-function frames, not peak call-chain usage.'}
            usage=out/f'{name}.su'
            report['state_diagnostics'][name]['stack_usage']=usage.read_text().splitlines() if usage.exists() else None
        report['sources']={str(f.relative_to(REPO)):digest(f) for f in HERE.glob('*') if f.suffix in ('.py','.c','.cpp','.rs')}
        report['snapshot_sha256']=digest(out/'source.tar')
        if sys.platform=='darwin':
            report['hardware']=run(['sysctl','-n','machdep.cpu.brand_string','hw.memsize']).decode()
        elif sys.platform.startswith('linux'):
            report['hardware']={'cpuinfo':Path('/proc/cpuinfo').read_text(),'meminfo':Path('/proc/meminfo').read_text()}
        report['status']='correctness_passed' if a.check_only else 'measured'
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(f"{report['status']}: {out}/report.json")

if __name__=='__main__':main()
