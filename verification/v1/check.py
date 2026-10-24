"""V1: bounds, value snapshots and control flow, separate from frozen V0."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import z3 as z
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.backend import llvm as emit_llvm
from verification.v1 import reference,semantic,llvm
from verification.v1.common import Unsupported


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name,actual,args,timeout,query_path=None):
    trap,value=reference.specification(name,args)
    mismatch=z.Or(actual['undefined'],z.Not(actual['covered']),actual['trap']!=trap,
                  *[z.And(p,z.Or(trap,v!=value)) for p,v in actual['returns']])
    solver=z.Solver();solver.set(timeout=timeout);solver.add(mismatch)
    if query_path:query_path.write_text('; V1 counterexample query, not a proof certificate.\n'+solver.to_smt2(),encoding='utf-8')
    result=solver.check()
    if result==z.unsat:return {'status':'proved'}
    if result==z.unknown:return {'status':'unknown','reason':solver.reason_unknown()}
    model=solver.model()
    values=[model.eval(a,model_completion=True).as_long() for a in args]
    holds=lambda p:z.is_true(model.eval(p,model_completion=True))
    undefined=holds(actual['undefined'])
    outcomes=([{'kind':'Undefined','reasons':sorted({reason for p,reason in actual['violations'] if holds(p)})}] if undefined else
              [{'kind':'Trap'}] if holds(actual['trap']) else
              [{'kind':'Return','value':model.eval(v,model_completion=True).as_long()} for p,v in actual['returns'] if holds(p)])
    return {'status':'counterexample','inputs':dict(zip(map(str,args),values)),
            'reference_replay':reference.concrete(name,values),'ir_model':outcomes}


def analyze(name,build,timeout,query_path=None):
    args=reference.inputs(name)
    if query_path and query_path.exists():query_path.unlink()
    try:
        actual=build(args)
        return {**check(name,actual,args,timeout,query_path),
                'observed_instructions':actual.get('observed_instructions',[])}
    except (Unsupported,KeyError,IndexError,z.Z3Exception) as error:
        return {'status':'unknown','reason':str(error)}


def changed(text,old,new):
    if old not in text:raise ValueError('mutation anchor missing: '+old)
    return text.replace(old,new,1)


def mutations(raw):
    def fn(name):return llvm.function(raw,name)[0]
    read=fn('read');update=fn('update');snapshot=fn('snapshot')
    yield 'bounds_off_by_one','read',changed(read,'icmp uge i32 %p4, 4','icmp ugt i32 %p4, 4')
    yield 'signed_bounds','read',changed(read,'icmp uge i32 %p4, 4','icmp sge i32 %p4, 4')
    truncated=changed(read,'  %v1_invalid =','  %small = trunc i32 %p4 to i8\n  %narrow = zext i8 %small to i32\n  %v1_invalid =')
    truncated=changed(truncated,'icmp uge i32 %p4, 4','icmp uge i32 %narrow, 4')
    truncated=changed(truncated,'%v1_offset = zext i32 %p4 to i64','%v1_offset = zext i32 %narrow to i64')
    yield 'truncated_index','read',truncated
    shifted=changed(read,'  %v1_ptr =','  %wrong = add i64 %v1_offset, 1\n  %v1_ptr =')
    yield 'wrong_load_offset','read',changed(shifted,'i64 0, i64 %v1_offset','i64 0, i64 %wrong')
    neighbor=changed(update,'  store i8 %p5, ptr %v2_ptr','  %neighbor_index = xor i64 %v2_offset, 1\n  %neighbor = getelementptr [4 x i8], ptr %v2_scratch, i64 0, i64 %neighbor_index\n  store i8 %p5, ptr %neighbor\n  store i8 %p5, ptr %v2_ptr')
    yield 'changed_neighbor','update',neighbor
    # Alias the update's scratch storage to the still-observable original.
    aliased=changed(snapshot,'  %v3_scratch = alloca [4 x i8]\n','')
    yield 'aliased_snapshot','snapshot',aliased.replace('%v3_scratch','%v0_storage')
    yield 'eager_and','short_and',changed(fn('short_and'),'br i1 %p5,','br i1 true,')
    yield 'eager_or','short_or',changed(fn('short_or'),'br i1 %p5,','br i1 false,')
    uninit=changed(read,'  %v0_storage = alloca [4 x i8]','  %uninitialized = alloca [4 x i8]\n  %v0_storage = alloca [4 x i8]')
    yield 'uninitialized_in_bounds','read',changed(uninit,'%v1 = load i8, ptr %v1_ptr','%v1 = load i8, ptr %uninitialized')


def run(output,clang,timeout):
    # Freeze existing V0 sources/specifications/tests, not generated toolchain IR.
    baseline=json.loads((ROOT/'verification/v1/v0-baseline.json').read_text())
    if any(sha(ROOT/p)!=digest for p,digest in baseline.items()):raise ValueError('V0 baseline changed')
    output.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'verification/v1/bounds.liza').read_text()
    module=lower(Parser(source).parse());raw=emit_llvm(module)
    (output/'subjects.liza').write_text(source,encoding='utf-8')
    (output/'semantic.json').write_text(dump(module),encoding='utf-8')
    (output/'generated.ll').write_text(raw,encoding='utf-8')
    texts={'LLVM-generated':raw}
    for opt in ('0','2'):
        file=output/f'O{opt}.ll'
        subprocess.run([clang,'-Wno-override-module',f'-O{opt}','-S','-emit-llvm',str(output/'generated.ll'),'-o',str(file)],check=True,capture_output=True,text=True)
        texts['LLVM-O'+opt]=file.read_text(encoding='utf-8')
    results=[]
    stage_files={'Semantic IR':'semantic.json','LLVM-generated':'generated.ll','LLVM-O0':'O0.ll','LLVM-O2':'O2.ll'}
    for name in reference.SUBJECTS:
        fn=next(f for f in module if f.name==name)
        builds={'Semantic IR':lambda args,fn=fn:semantic.evaluate(fn,args)}
        builds.update({stage:lambda args,text=text,name=name:llvm.evaluate(text,name,args) for stage,text in texts.items()})
        for stage,build in builds.items():
            query=output/(name+'-'+stage.replace(' ','-')+'.smt2')
            result=analyze(name,build,timeout,query)
            item={'subject':name,'stage':stage,'artifact':stage_files[stage],
                  'artifact_sha256':sha(output/stage_files[stage]),'query':query.name if query.exists() else None,
                  **result}
            results.append(item);print(name,stage,result,flush=True)
    controls=[]
    for mutation,name,text in mutations(raw):
        # Save compilable mutated modules, retaining declarations and the rest
        # of the program. Clang validates syntax but does not optimize mutants.
        full=raw.replace(llvm.function(raw,name)[0],text)
        file=output/(mutation+'.ll');file.write_text(full,encoding='utf-8')
        subprocess.run([clang,'-Wno-override-module','-O0','-S','-emit-llvm',str(file),'-o',str(output/(mutation+'-parsed.ll'))],check=True,capture_output=True,text=True)
        result=analyze(name,lambda args,text=full,name=name:llvm.evaluate(text,name,args),timeout,output/(mutation+'.smt2'))
        controls.append({'mutation':mutation,'subject':name,'artifact_sha256':sha(file),**result})
        print(mutation,result,flush=True)
    unknown_text=changed(raw,'%v1 = load i8, ptr %v1_ptr','%v1 = freeze i8 %p0')
    unknown=analyze('read',lambda args:llvm.evaluate(unknown_text,'read',args),timeout)
    success=all(r['status']=='proved' for r in results) and all(r['status']=='counterexample' for r in controls) and unknown['status']=='unknown'
    files={p.name:sha(p) for p in output.iterdir() if p.suffix in ('.ll','.json','.liza','.smt2') and p.name!='report.json'}
    report={'experiment':'Liza Verified V1: Bounds and Control Flow','success':success,
            'scope':'eight fixed functions; all symbolic u8 elements, u32 index and u32 observer; observer & 3 covers all four positions',
            'outcomes':['Return(value)','Trap','Undefined (model violation, never allowed by Liza)'],
            'unknown':'unsupported semantics or solver uncertainty; not a program outcome',
            'supported_llvm':llvm.SUPPORTED,'assumptions':llvm.ASSUMPTIONS,
            'trusted_base':['independent reference specification','V1 IR readers and models','query generator','Z3','Python/runtime/host'],
            'certificate':'none; SMT-LIB queries are not independently checked proof certificates',
            'clang':subprocess.run([clang,'--version'],check=True,capture_output=True,text=True).stdout,
            'z3':z.get_version_string(),'timeout_ms':timeout,'v0_baseline':baseline,
            'model_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'verification/v1').glob('*.py'))},
            'results':results,'negative_controls':controls,'unsupported_control':unknown,'sha256':files}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'{len(results)} obligations; {len(controls)} mutations; success={success}',flush=True)
    return success


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/verified-v1')
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
