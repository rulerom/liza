"""V2 inductive proof experiment. Counterexamples are to obligations, not
necessarily reachable executions; concrete mutation replay is reported apart."""
from pathlib import Path
import sys
import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import z3 as z
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.backend import llvm as emit_llvm
from verification.v2 import core,semantic,llvm,mutations,replay


def solve(obligations,timeout=10000,directory=None,prefix=''):
    results=[]
    for name,assumptions,claim in obligations:
        solver=z.Solver();solver.set(timeout=timeout);solver.add(assumptions,z.Not(claim))
        if directory:(directory/(prefix+name+'.smt2')).write_text(solver.to_smt2(),encoding='utf-8')
        answer=solver.check()
        row={'obligation':name,'query':prefix+name+'.smt2' if directory else None,'status':'proved' if answer==z.unsat else 'unknown' if answer==z.unknown else 'counterexample_to_obligation'}
        if answer==z.sat:row['model']=str(solver.model())
        if answer==z.unknown:row['reason']=solver.reason_unknown()
        print(prefix,name,row['status'],flush=True);results.append(row)
    return results


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(engine,ctx,timeout=10000,directory=None,prefix=''):
    try:
        vcs=core.obligations(engine,ctx)
        return {'status':'supported','cutpoint':engine.header,'index_phi':engine.index,
                'accumulator_phi':engine.acc,'strict_body_invariant':engine.strict,
                'observed_instructions':sorted(getattr(engine,'observed',set())),
                'results':solve(vcs,timeout,directory,prefix)}
    except (core.Unsupported,KeyError,IndexError,z.Z3Exception) as error:
        return {'status':'unknown','reason':str(error),'results':[]}


def run(output,clang,timeout):
    baseline=json.loads((ROOT/'verification/v2/baseline.json').read_text())
    if any(sha(ROOT/path)!=value for path,value in baseline.items()):raise ValueError('frozen V0/V1 changed')
    output.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'verification/v2/loops.liza').read_text()
    module=lower(Parser(source).parse());raw=emit_llvm(module)
    (output/'subjects.liza').write_text(source,encoding='utf-8')
    (output/'semantic.json').write_text(dump(module),encoding='utf-8')
    (output/'generated.ll').write_text(raw,encoding='utf-8')
    texts={'LLVM-generated':raw}
    for opt in ('0','2'):
        path=output/f'O{opt}.ll'
        subprocess.run([clang,'-Wno-override-module',f'-O{opt}','-S','-emit-llvm',str(output/'generated.ll'),'-o',str(path)],check=True,capture_output=True,text=True)
        texts['LLVM-O'+opt]=path.read_text(encoding='utf-8')
    artifacts={'Semantic IR':'semantic.json','LLVM-generated':'generated.ll','LLVM-O0':'O0.ll','LLVM-O2':'O2.ll'}
    proofs=[]
    for fn in module:
        if fn.name=='main':continue
        for stage in artifacts:
            ctx=core.Context(fn.name,physical=stage!='Semantic IR')
            try:
                engine=semantic.Engine(fn,ctx) if stage=='Semantic IR' else llvm.Engine(texts[stage],fn.name,ctx)
                result=analyze(engine,ctx,timeout,output,fn.name+'-'+stage.replace(' ','-')+'-')
            except core.Unsupported as error:result={'status':'unknown','reason':str(error),'results':[]}
            proofs.append({'function':fn.name,'stage':stage,'artifact':artifacts[stage],
                           'artifact_sha256':sha(output/artifacts[stage]),**result})
    controls=[]
    for label,fn,data,needle in mutations.cases(module):
        file=output/(label+'.semantic.json');file.write_text(json.dumps(asdict(fn),indent=2)+'\n',encoding='utf-8')
        ctx=core.Context(fn.name)
        result=analyze(semantic.Engine(fn,ctx),ctx,timeout,output,label+'-')
        expected=replay.reference(fn.name,data,needle);actual=replay.run(fn,data,needle)
        detected=any(r['status']=='counterexample_to_obligation' for r in result['results'])
        controls.append({'mutation':label,'artifact_sha256':sha(file),'detected':detected,
                         'replay':{'input':data,'needle':needle,'expected':expected,'actual':actual,
                                   'different':replay.differs(expected,actual)},**result})
    success=all(p['status']=='supported' and all(r['status']=='proved' for r in p['results']) for p in proofs)
    success=success and all(c['detected'] and c['replay']['different'] and c['replay']['actual']['kind']!='ReplayLimit' for c in controls)
    report={'experiment':'Liza Verified V2: Loop Invariants','success':success,
            'scope':'search over View<u8>, sequential sum over View<i32>; full u32 length, no unroll bound',
            'search_result':'first matching index, or length if absent',
            'invariants':{'search':'0 <= i <= length; all j in [0,i) differ from needle',
                          'sum':'0 <= i <= length; acc=S(i); all S(k), 0<=k<=i, fit i32',
                          'body_header':'optimized header before load requires i < length',
                          'ranking':'length-i, nonnegative and strictly decreasing on every back edge'},
            'prefix_definition':'S(0)=0; S(k+1)=S(k)+data[k]. Only the true current-step equation is instantiated; other S values are unconstrained except the invariant. This weakens assumptions, not input coverage.',
            'memory_assumptions':['one live initialized readonly object of length*element_size bytes',
                                  'u32 length; pointer origin preserved; base offset zero; no address wrap; little endian; 64-bit index space',
                                  'base aligned to element size; symbolic byte array with byte values normalized modulo 256',
                                  'all valid views are inputs; allocation failure, aliasing, mutation, freeing and concurrency excluded'],
            'llvm_supported_instructions':['phi, br, ret','extractvalue (view and overflow pair)','icmp (integer predicates)','zext/trunc including nneg/nuw','getelementptr i8/i32 (optional inbounds)','readonly load i8/i32','uadd/sadd.with.overflow.i32','add i32/i64 with nuw/nsw','llvm.trap and unreachable'],
            'llvm_forms':['single cutpoint, acyclic entry/body segments','guarded i32 phi header','i64 body header with latch exit'],
            'unsupported':'other cycles, instructions, attributes or forms yield unknown; no inherited Semantic IR proof',
            'trusted_base':['external specifications and induction-rule implementation','IR readers/executors and byte model','Z3','Python/runtime/host'],
            'certificate':'none; hashes and SMT queries are not independently checked proof certificates',
            'counterexamples':'SMT models refute inductive obligations and may describe unreachable states. Separate concrete replay establishes defects for the eight mutations.',
            'machine_code':'not verified','timeout_ms':timeout,'z3':z.get_version_string(),
            'clang':subprocess.run([clang,'--version'],check=True,capture_output=True,text=True).stdout,
            'baseline':baseline,'proofs':proofs,'negative_controls':controls,
            'model_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'verification/v2').glob('*.py'))},
            'sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='report.json'}}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    count=sum(len(p['results']) for p in proofs)
    print(f'{count} obligations; {len(controls)} mutations with replay; success={success}',flush=True)
    return success


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/verified-v2')
    parser.add_argument('--clang',default='clang')
    parser.add_argument('--timeout-ms',type=int,default=10000)
    args=parser.parse_args()
    if args.timeout_ms<=0:parser.error('timeout must be positive')
    try:return 0 if run(args.output,args.clang,args.timeout_ms) else 1
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        print('verification infrastructure error:',error,file=sys.stderr)
        if isinstance(error,subprocess.CalledProcessError):print(error.stderr,file=sys.stderr)
        return 2


if __name__=='__main__':sys.exit(main())
