"""Liza Verified arithmetic experiment, deliberately separate from compiler CLI."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import z3 as z
from liza.frontend import Parser
from liza.ir import lower, dump
from liza.backend import llvm as emit_llvm
from verification import model, reference


def check(name, actual, args, timeout, query_path=None):
    trap, value = reference.specification(name,args)
    mismatch = z.Or(actual['bad'], z.Not(actual['covered']),
                    actual['trap'] != trap,
                    *[z.And(path,z.Or(trap,got!=value)) for path,got in actual['returns']])
    solver = z.Solver()
    solver.set(timeout=timeout)
    solver.add(mismatch)
    if query_path:
        query_path.write_text('; Counterexample query; unsat means equivalence within the model.\n'+solver.to_smt2(),encoding='utf-8')
    answer = solver.check()
    if answer == z.unsat: return {'status':'proved'}
    if answer == z.unknown: return {'status':'unknown','reason':solver.reason_unknown()}
    witness = solver.model()
    values = [witness.eval(a,model_completion=True).as_long() for a in args]
    expected_trap, expected_value = reference.concrete(name,values)
    return {'status':'counterexample','inputs':dict(zip([str(a) for a in args],values)),
            'input_encoding':'unsigned bit patterns (i8: 128..255 mean -128..-1)',
            'reference_replay':{'trap':expected_trap,'value_bits':None if expected_trap else expected_value},
            'ir_model':{'trap':z.is_true(witness.eval(actual['trap'],model_completion=True)),
                        'bad':z.is_true(witness.eval(actual['bad'],model_completion=True)),
                        'returned_bits':[witness.eval(v,model_completion=True).as_long() for p,v in actual['returns']
                                         if z.is_true(witness.eval(p,model_completion=True))]}}


def analyze(name, build, timeout, query_path=None):
    args = reference.inputs(name)
    try:
        return check(name,build(args),args,timeout,query_path)
    except (model.Unsupported, KeyError, IndexError, z.Z3Exception) as error:
        return {'status':'unknown','reason':str(error)}


def mutations(raw, module):
    """Mutate real generated subjects, never the production compiler."""
    start = raw.index('define i8 @liza_add_u8(')
    end = raw.index('\n}',start)+2
    function = raw[start:end]
    yield 'missing_guard', 'add_u8', function.replace('br i1 %v0_overflow,','br i1 false,')
    yield 'inverted_guard', 'add_u8', function.replace('label %v0_trap, label %v0_ok','label %v0_ok, label %v0_trap')
    yield 'wrong_operation', 'add_u8', function.replace('llvm.uadd.','llvm.usub.')
    yield 'wrong_signedness', 'add_u8', function.replace('llvm.uadd.','llvm.sadd.')
    yield 'removed_intermediate_trap', 'sequence_u8', 'define i8 @liza_sequence_u8(i8 %p0) {\nb0:\n ret i8 %p0\n}'
    start = raw.index('define i8 @liza_branch_u8(')
    end = raw.index('\n}',start)+2
    yield 'executed_dead_branch', 'branch_u8', raw[start:end].replace('br i1 %p1,','br i1 true,')
    # Poison is not a valid implementation of checked arithmetic, even if its
    # modular value happens to match every non-overflowing result.
    yield 'poison_instead_of_trap', 'add_u8', 'define i8 @liza_add_u8(i8 %p0, i8 %p1) {\nb0:\n %v = add nuw i8 %p0, %p1\n ret i8 %v\n}'


def run(output, clang, timeout):
    output.mkdir(parents=True,exist_ok=True)
    source = (ROOT/'verification/arithmetic.liza').read_text(encoding='utf-8')
    module = lower(Parser(source).parse())
    raw = emit_llvm(module)
    (output/'subjects.liza').write_text(source,encoding='utf-8')
    (output/'semantic.json').write_text(dump(module),encoding='utf-8')
    (output/'generated.ll').write_text(raw,encoding='utf-8')
    texts={'LLVM-generated':raw}
    for level in ('0','2'):
        target = output/f'O{level}.ll'
        subprocess.run([clang,'-Wno-override-module',f'-O{level}','-S','-emit-llvm',str(output/'generated.ll'),'-o',str(target)],check=True,capture_output=True,text=True)
        texts['LLVM-O'+level] = target.read_text(encoding='utf-8')
    results=[]
    for name in reference.SUBJECTS:
        fn = next(f for f in module if f.name==name)
        builders={'Semantic IR':lambda args,fn=fn:model.semantic(fn,args)}
        builders.update({stage:lambda args,text=text,name=name:model.llvm(text,name,args) for stage,text in texts.items()})
        for stage,build in builders.items():
            query=output/(name+'-'+stage.replace(' ','-')+'.smt2')
            result=analyze(name,build,timeout,query)
            results.append({'subject':name,'stage':stage,**result})
            print(name,stage,result,flush=True)
    controls=[]
    for mutation,name,text in mutations(raw,module):
        (output/(mutation+'.ll')).write_text(text,encoding='utf-8')
        result=analyze(name,lambda args:model.llvm(text,name,args),timeout,output/(mutation+'.smt2'))
        controls.append({'mutation':mutation,**result})
        print(mutation,result,flush=True)
    # The Semantic IR reader must also notice a bad lowering from the source.
    fn=copy.deepcopy(next(f for f in module if f.name=='add_u8'))
    fn.blocks[0].operations[0].op='sub'
    controls.append({'mutation':'semantic_wrong_operation',**analyze('add_u8',lambda args:model.semantic(fn,args),timeout,output/'semantic-mutation.smt2')})
    unsupported='define i8 @liza_sequence_u8(i8 %p0) {\nb0:\n %v = call i8 @opaque(i8 %p0)\n ret i8 %v\n}'
    unknown=analyze('sequence_u8',lambda args:model.llvm(unsupported,'sequence_u8',args),timeout)
    success=all(r['status']=='proved' for r in results) and all(r['status']=='counterexample' for r in controls) and unknown['status']=='unknown'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.suffix in ('.ll','.liza','.json','.smt2') and p.name!='report.json'}
    report={'experiment':'Liza Verified arithmetic v1','success':success,
            'scope':'Ten fixed acyclic u8/i8 functions; all input bit patterns; no binary verification',
            'trusted_base':['fixed specifications','Python symbolic interpreters and query generator','Z3','Python/runtime/host'],
            'certificate':'none; Z3 is trusted, SMT-LIB files are counterexample queries, not proof certificates',
            'z3':z.get_version_string(),'clang':subprocess.run([clang,'--version'],check=True,capture_output=True,text=True).stdout,
            'model_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted((ROOT/'verification').glob('*.py'))},
            'timeout_ms':timeout,'results':results,'negative_controls':controls,'unsupported_control':unknown,'sha256':hashes}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'{len(results)} obligations; {len(controls)} negative controls; success={success}',flush=True)
    return success


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/verified')
    parser.add_argument('--clang',default='clang')
    parser.add_argument('--timeout-ms',type=int,default=10000)
    args=parser.parse_args()
    if args.timeout_ms<=0: parser.error('timeout must be positive')
    try:
        return 0 if run(args.output,args.clang,args.timeout_ms) else 1
    except (OSError,subprocess.CalledProcessError) as error:
        print('verification infrastructure error:',error,file=sys.stderr)
        if isinstance(error,subprocess.CalledProcessError): print(error.stderr,file=sys.stderr)
        return 2


if __name__=='__main__': sys.exit(main())
