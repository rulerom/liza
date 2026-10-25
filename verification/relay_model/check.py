"""Independent mathematical relay model, NOT verification of IR or socket code."""
import argparse
import hashlib
import json
from pathlib import Path
import z3


def obligations():
    seq=z3.SeqSort(z3.BitVecSort(8))
    R,W,Q,P,S,D=z3.Consts('R W Q prefix suffix data',seq)
    h,t=z3.Ints('head tail');eof,fin=z3.Bools('eof fin')
    empty=z3.Empty(seq);cat=z3.Concat;size=z3.Length
    valid=z3.And(0<=h,h<=t,t<=2048,size(Q)==t-h,R==cat(W,Q),z3.Implies(fin,z3.And(eof,size(Q)==0)))
    def invariant(r,w,q,head,tail,end,closed):
        return z3.And(0<=head,head<=tail,tail<=2048,size(q)==tail-head,r==cat(w,q),z3.Implies(closed,z3.And(end,size(q)==0)))
    n=size(D)
    read=z3.And(valid,z3.Not(eof),t<2048,n>0,n<=2048-t)
    split=z3.And(valid,Q==cat(P,S),size(P)>0)
    head=z3.If(size(S)==0,0,h+size(P));tail=z3.If(size(S)==0,0,t)
    yield 'entry.empty',z3.BoolVal(True),invariant(empty,empty,empty,0,0,False,False),False
    yield 'read.conservation_and_bounds',read,invariant(cat(R,D),W,cat(Q,D),h,t+n,False,False),False
    yield 'read.checked_index',read,z3.And(t+n<=2048,t+n<2**32),False
    yield 'eof.preserves_queue',z3.And(valid,z3.Not(eof),t<2048),invariant(R,W,Q,h,t,True,False),False
    yield 'write.conservation_and_bounds',split,invariant(R,cat(W,P),S,head,tail,eof,fin),False
    yield 'write.checked_index',split,h+size(P)<=2048,False
    yield 'would_block.identity',valid,invariant(R,W,Q,h,t,eof,fin),False
    yield 'shutdown.drained_only',z3.And(valid,eof,size(Q)==0,z3.Not(fin)),invariant(R,W,Q,h,t,True,True),False
    yield 'normal_completion.equality',z3.And(valid,fin),R==W,False
    # Each mutation must produce a satisfiable counterexample to its claimed invariant.
    yield 'drop_written_prefix',split,invariant(R,W,S,head,tail,eof,fin),True
    yield 'duplicate_written_prefix',split,invariant(R,cat(W,P,P),S,head,tail,eof,fin),True
    yield 'overwrite_pending_read',z3.And(read,size(Q)>0),invariant(cat(R,D),W,D,h,t+n,False,False),True
    yield 'discard_on_would_block',z3.And(valid,size(Q)>0),invariant(R,W,empty,0,0,eof,fin),True
    yield 'premature_shutdown',z3.And(valid,eof,size(Q)>0,z3.Not(fin)),invariant(R,W,Q,h,t,True,True),True
    a,b=z3.BitVecs('a b',8)
    yield 'reorder_written_bytes',z3.And(split,P==cat(z3.Unit(a),z3.Unit(b)),a!=b),invariant(R,cat(W,z3.Unit(b),z3.Unit(a)),S,head,tail,eof,fin),True


def check(timeout=10000):
    rows=[]
    for name,pre,post,mutation in obligations():
        solver=z3.Solver();solver.set(timeout=timeout);solver.add(pre,z3.Not(post))
        result=solver.check()
        status='unknown'
        if result==z3.unsat:status='proved_model_obligation'
        if result==z3.sat:status='counterexample_to_model_obligation'
        row={'name':name,'mutation':mutation,'result':status,'expected':str(z3.sat if mutation else z3.unsat),'smt_result':str(result)}
        if result==z3.sat:row['counterexample']=str(solver.model())
        if result==z3.unknown:row['reason']=solver.reason_unknown()
        rows.append(row)
    return {'scope':'independent mathematical single-direction relay model',
            'program_verified':False,'runtime_verified':False,'end_to_end_verified':False,
            'assumptions':['successful read appends exactly the reported bytes',
                           'successful write removes exactly the reported nonempty prefix',
                           'WouldBlock/Interrupted do not alter byte histories or pending storage',
                           'shutdown occurs only after EOF and an empty queue; failures abort the pair',
                           'single-threaded, disjoint storage for the two directions; no delivery or termination guarantee'],
            'trusted_base':['this manually authored mathematical model','Z3 and its sequence/integer theories','Python orchestration'],
            'z3':z3.get_version_string(),'model_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'status':'passed' if all(r['smt_result']==r['expected'] for r in rows) else 'incomplete',
            'obligations':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=check();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status']+': independent model only, no program/runtime proof')
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
