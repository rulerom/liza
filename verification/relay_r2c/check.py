"""Lifecycle obligations around the unchanged R2-B cuts, with explicit scope."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import z3
from .semantic import Executor,equal
from .mutations import MUTATIONS,mutate
from .replay import run as replay
from verification.relay_r2b.fragment import Fragment,CUTS,Unsupported,require
from verification.relay_r2b.check import compile_source,analyze,partition,save
from verification.relay_r2b.specification import valid,inputs
from verification.relay_r2b.semantic import Executor as ByteExecutor

ROOT=Path(__file__).resolve().parents[2]
PAIR='liza_proxy.Pair'
EXCHANGE='liza_proxy.exchange'


def empty():
    d=(z3.IntVal(0),z3.IntVal(0),z3.BoolVal(False),z3.BoolVal(False))
    return dict(client=('None',),upstream=('None',),connected=z3.BoolVal(False),forward=d,reverse=d)


def symbolic_pair(prefix='old'):
    result=dict(client=('Some','client'),upstream=('Some','upstream'),connected=z3.Bool(prefix+'_connected'))
    for side in ('forward','reverse'):
        result[side]=(z3.Int(prefix+side+'_head'),z3.Int(prefix+side+'_tail'),z3.Bool(prefix+side+'_eof'),z3.Bool(prefix+side+'_fin'))
    return result


def valid_pair(pair):return z3.And(valid(pair['forward']),valid(pair['reverse']))


class Checks:
    def __init__(self,module,output,timeout=10000):
        self.module=module;self.output=output;self.timeout=timeout;self.rows=[]
        self.visited=set()
        self.composition_checked=False
        self.function=next(f for f in module['functions'] if f['name']==EXCHANGE)
        self.blocks={b['name']:b for b in self.function['blocks']}

    def prove(self,name,pre,bad):
        solver=z3.Solver();solver.set(timeout=self.timeout);solver.add(pre,bad)
        self.output.mkdir(parents=True,exist_ok=True)
        (self.output/(name+'.smt2')).write_text(solver.to_smt2())
        result=solver.check()
        row=dict(obligation=name,status='proved' if result==z3.unsat else 'unknown',smt_result=str(result))
        if result==z3.sat:row.update(status='abstract_counterexample',model=str(solver.model()))
        if result==z3.unknown:row['reason']=solver.reason_unknown()
        self.rows.append(row)
        return row

    def run(self,name,executor,pre,exits,post):
        bad=[]
        for path,kind,env,ghost in exits:
            bad.append(z3.And(path,z3.Not(post(env,ghost)) if kind=='Cut' else True))
        self.prove(name,pre,z3.Or(*bad))
        self.prove(name+'_coverage',pre,z3.Not(z3.Or(*[p for p,*_ in exits])))
        for label,condition in executor.obligations:
            bad.append(condition)
        self.prove(name+'_runtime',pre,z3.Or(*[c for _,c in executor.obligations]))
        self.visited.update(executor.visited)

    def lifecycle(self,slots=range(8),scan=True):
        # Real empty_pair, move and array.repeat; stop before diagnostic I/O.
        ex=Executor(self.module)
        out=ex.execute(EXCHANGE,'b0',None,dict(p0='reactor',p1='buffer',p2=z3.IntVal(9003),p3=z3.Bool('once')),{},stop_operation='v6')
        self.run('initialization',ex,True,out,lambda e,g:z3.And(equal(e['v2'],[empty()]*8),e['v0']=='buffer'))
        # The finite free-slot scan is checked for every occupancy pattern.
        scan_bad=[];scan_cover=[]
        for mask in range(256 if scan else 0):
            occupied=symbolic_pair('scan')
            table=[occupied if mask&(1<<i) else empty() for i in range(8)]
            ex=Executor(self.module)
            env=dict(v32='buffer',v33=table,v48=z3.BoolVal(True),v35=z3.BoolVal(False),v49=z3.IntVal(0),p3=z3.BoolVal(False))
            # b22's leading phis depend on poll; seed their output explicitly.
            env.update(v50=z3.IntVal(8),v51=z3.IntVal(0))
            out=ex.execute(EXCHANGE,'b23',{'b42','b58'},env,{},previous='b22')
            expected=next((i for i in range(8) if not mask&(1<<i)),8)
            scan_bad.extend(z3.And(p,z3.Not(equal(e['v53'],table)) if k=='Cut' else True) for p,k,e,g in out)
            scan_bad.extend(z3.And(p,e['v57']!=expected) for p,k,e,g in out if k=='Cut')
            scan_cover.append(z3.Not(z3.Or(*[p for p,*_ in out])))
            self.visited.update(ex.visited)
        if scan:self.prove('free_slot_scan',True,z3.Or(*scan_bad,*scan_cover))
        for slot in slots:self.slot(slot)

    def slot(self,slot):
        before=symbolic_pair();table=[empty()]*8;table[slot]=before
        once=z3.Bool('once');phase=z3.Bool('socket_connected')
        ghost=dict(live={'client','upstream'},closed=[],upstream='upstream',connected=phase,failed=z3.BoolVal(False),epoch=z3.Int('epoch'))
        pre=z3.And(z3.Int('epoch')>=0,valid_pair(before),z3.Implies(before['connected'],phase))
        common=dict(p0='reactor',p2=z3.IntVal(9003),p3=once,v121='buffer',v122=table,
                    v123=z3.BoolVal(True),v124=z3.BoolVal(True),v125=z3.IntVal(0),v126=z3.IntVal(slot),v127=z3.IntVal(slot))
        ex=Executor(self.module)
        out=ex.execute(EXCHANGE,'b59','b60',common,ghost,after_phi=True)
        self.run('inner_enters_'+str(slot),ex,pre,out,lambda e,g:z3.And(equal(e['v122'],table),e['v127']==slot))
        ex=Executor(self.module)
        out=ex.execute(EXCHANGE,'b59','b13',dict(common,v123=z3.BoolVal(False)),ghost,after_phi=True)
        self.run('stopped_inner_'+str(slot),ex,pre,out,lambda e,g:z3.And(equal(e['v33'],table),z3.Not(e['v34'])))
        ex=Executor(self.module)
        out=ex.execute(EXCHANGE,'b60','b91',common,ghost)
        def entry(e,g):
            pair=e['v183'];alive=e['v184']
            return z3.And(valid_pair(pair),equal(pair['client'],before['client']),equal(pair['upstream'],before['upstream']),
                          equal(pair['forward'],before['forward']),equal(pair['reverse'],before['reverse']),
                          z3.Implies(pair['connected'],g['connected']),
                          e['v127']==slot,e['v136']=='client',e['v141']=='upstream')
        self.run('entry_'+str(slot),ex,pre,out,entry)
        # Actual publication after accept, including connect error cleanup.
        ex=Executor(self.module)
        env=dict(p0='reactor',p2=z3.IntVal(9003),p3=once,v81=('Ok','new_client'),v52='buffer',v53=[empty()]*8,
                 v54=z3.BoolVal(True),v55=z3.BoolVal(False),v56=z3.IntVal(0),v57=z3.IntVal(slot))
        g=dict(live=set(),closed=[],upstream='new_upstream',connected=z3.BoolVal(False),failed=z3.BoolVal(False),epoch=z3.Int('epoch'))
        out=ex.execute(EXCHANGE,'b42','b59',env,g)
        def created(e,g):
            expected=empty()
            if 'new_upstream' in g['live']:
                expected=dict(expected,client=('Some','new_client'),upstream=('Some','new_upstream'))
            target=[empty()]*8;target[slot]=expected
            return z3.And(equal(e['v122'],target),z3.BoolVal(g['live']==({'new_client','new_upstream'} if 'new_upstream' in g['live'] else set())),g['epoch']==z3.Int('epoch')+(1 if 'new_upstream' in g['live'] else 0))
        self.run('publish_'+str(slot),ex,z3.Int('epoch')>=0,out,created)
        # Post-R2-B state is universally quantified, NOT assumed equal to old
        # table entry. This exposes missing/old/wrong-slot persistence.
        after=symbolic_pair('updated');alive=z3.Bool('alive_after')
        ex=Executor(self.module)
        env=dict(common,v459=after,v460=alive,v461=z3.IntVal(0),v376='buffer',v136='client',v141='upstream')
        suffix_ghost=dict(ghost,failed=z3.Not(alive))
        out=ex.execute(EXCHANGE,'b217','b59',env,suffix_ghost,after_phi=True)
        def stored(e,g):
            expected=after if g['live'] else empty()
            target=list(table);target[slot]=expected
            normal=z3.And(alive,after['forward'][3],after['reverse'][3])
            # No resource remains in a reset slot; no live slot is dropped.
            return z3.And(equal(e['v122'],target),z3.BoolVal(g['live'] in ({'client','upstream'},set())),
                          z3.Implies(normal,z3.BoolVal(not g['live'])),
                          z3.Implies(z3.Not(alive),z3.BoolVal(not g['live'])),
                          z3.Implies(z3.BoolVal(bool(g['live'])),z3.Implies(after['connected'],g['connected'])),
                          z3.Implies(z3.Not(g['failed']),z3.BoolVal(not g['live'])==z3.And(after['forward'][3],after['reverse'][3])),
                          e['v127']==slot+1,e['v121']=='buffer',g['epoch']==z3.Int('epoch'))
        self.run('persist_or_reset_'+str(slot),ex,z3.And(pre,valid_pair(after),z3.Implies(after['connected'],phase)),out,stored)
        # Finite inner scan: an inactive slot cannot alter the carried table.
        idle_table=[empty()]*8;idle_table[(slot+1)%8]=before
        ex=Executor(self.module)
        out=ex.execute(EXCHANGE,'b60','b59',dict(common,v122=idle_table),ghost)
        self.run('inactive_scan_'+str(slot),ex,pre,out,lambda e,g:z3.And(equal(e['v122'],idle_table),e['v127']==slot+1))
        # Exit the inner loop and execute the outer header's actual phis.
        ex=Executor(self.module)
        out=ex.execute(EXCHANGE,'b59','b13',dict(common,v127=z3.IntVal(8)),ghost,after_phi=True)
        self.run('inner_to_outer_'+str(slot),ex,pre,out,lambda e,g:z3.And(equal(e['v33'],table),e['v32']=='buffer'))
        # Poll, the free-slot scan, and once guard must not change the table.
        ex=Executor(self.module)
        env=dict(p0='reactor',p3=once,v32='buffer',v33=table,v34=z3.BoolVal(True),v35=z3.Bool('accepted'),v36=z3.IntVal(0))
        out=ex.execute(EXCHANGE,'b13',{'b42','b58'},env,ghost,after_phi=True)
        def outer(e,g):
            carried=e.get('v116',e['v53'])
            return equal(carried,table)
        self.run('outer_to_table_'+str(slot),ex,pre,out,outer)
        # Outer backedge must preserve the newly stored table and buffer.
        ex=Executor(self.module)
        env=dict(common,v121='buffer',v122=table)
        out=ex.execute(EXCHANGE,'b61','b13',env,ghost)
        self.run('outer_backedge_'+str(slot),ex,pre,out,lambda e,g:z3.And(equal(e['v33'],table),e['v32']=='buffer',e['v34']==True))

    def composition(self):
        fragments=[Fragment(self.module,name) for name in CUTS]
        require(fragments[0].start=='b91' and fragments[0].entry_pair=='v183','prefix/cut binding')
        require(fragments[-1].stop=='b217' and fragments[-1].exit_pair=='v459','cut/suffix binding')
        for left,right in zip(fragments,fragments[1:]):
            require(left.stop==right.start and left.exit_pair==right.entry_pair and left.exit_alive==right.entry_alive,'adjacent cut SSA binding')
        expected={fragment.call[1] for fragment in fragments}
        actual={o['result'] for b in self.function['blocks'] for o in b['operations'] if o['op']=='call' and o['callee'] in ('net.reactor_read','net.reactor_write','net.reactor_shutdown_write')}
        require(actual==expected,'uncovered byte event')
        # There is no buffer mutation between summaries: bytes change only at
        # the six checked I/O cuts. Resource release is a terminal boundary.
        for b in self.function['blocks']:
            for o in b['operations']:
                if o['op'].startswith(('buffer.','region.','vec.')):
                    require(o['op'] in ('buffer.view','buffer.release'),'uncovered memory operation')
        initial=self.blocks['b0']['operations']
        at=next(i for i,o in enumerate(initial) if o['result']=='v6')
        tail=initial[at:]
        require(len(tail)==2 and tail[0]['op']=='call' and tail[0]['callee']=='net.reactor_port' and tail[0]['args']==['p0'] and tail[1]['op']=='variant.tag' and tail[1]['args']==['v6'],'startup boundary')
        covered={label for fn,label in self.visited if fn==EXCHANGE}
        covered.update(label for fragment in fragments for label in fragment.selected)
        # Diagnostic startup, terminal cleanup, and the invalid-Option path
        # are exact frozen boundaries, not silently accepted arbitrary code.
        boundary=json.loads((Path(__file__).parent/'boundaries.json').read_text())
        for b in self.function['blocks']:
            if b['name'] in covered:continue
            if not b['operations'] and b['terminator']['op']=='unreachable':continue
            canonical={k:b[k] for k in ('name','operations','terminator')}
            def strip(value):
                if isinstance(value,dict):return {k:strip(v) for k,v in value.items() if k not in ('span','may_trap','storage_contract')}
                if isinstance(value,list):return [strip(v) for v in value]
                return value
            digest=hashlib.sha256(json.dumps(strip(canonical),sort_keys=True).encode()).hexdigest()
            require(boundary.get(b['name'])==digest,'uncovered/changed boundary '+b['name'])
        # Initialization is carried through the real outer-header phis on
        # both diagnostic success and failure paths.
        for predecessor in ('b2','b11'):
            ex=Executor(self.module)
            env=dict(v0='buffer',v2=[empty()]*8,v4=z3.BoolVal(False),v10=z3.BoolVal(False),v9=z3.IntVal(3),v28=z3.Bool('initial_running'),v29=z3.IntVal(0))
            out=ex.execute(EXCHANGE,'b12','b13',env,{},previous=predecessor)
            self.run('initial_header_'+predecessor,ex,True,out,lambda e,g:z3.And(equal(e['v33'],[empty()]*8),z3.Not(e['v35'])))
        self.composition_checked=True
        save(self.output/'composition.json',dict(status='checked',cuts=[f.manifest() for f in fragments],boundary='boundaries.json',histories='per fresh epoch; discarded only on terminal paths'))

    def local_closure(self):
        self.rows.extend(partition(self.output/'partition',self.timeout))
        for name in CUTS:
            # R2-B's own conditions are rechecked against this exact IR.
            rows=analyze(self.module,name,self.output/'r2b'/name,self.timeout)
            self.rows.extend(rows)
            values,memory,pre,_=inputs(name)
            exits=ByteExecutor(self.module,Fragment(self.module,name),values).execute(memory)
            bad=[]
            for path,kind,pair,alive,after in exits:
                if kind!='Return':bad.append(path);continue
                post=z3.And(valid_pair(pair),equal(pair['client'],values['pair']['client']),
                            equal(pair['upstream'],values['pair']['upstream']),pair['connected']==values['pair']['connected'])
                for side in ('forward','reverse'):
                    post=z3.And(post,z3.Implies(values['pair'][side][2],pair[side][2]),z3.Implies(values['pair'][side][3],pair[side][3]))
                post=z3.And(post,z3.Implies(z3.Not(values['alive']),z3.Not(alive)))
                if after.fatal:post=z3.And(post,equal(pair,values['pair']),z3.Not(alive))
                bad.append(z3.And(path,z3.Not(post)))
            self.prove(name+'_closure_including_fatal',pre,z3.Or(*bad))


def controls(source,helper,output,timeout):
    results=[]
    for name in MUTATIONS:
        directory=output/name
        module=compile_source(mutate(source.decode('utf-8'),name).encode('utf-8'),helper,directory)
        checker=Checks(module,directory/'checks',timeout)
        try:
            checker.lifecycle(slots=(0,),scan=False)
            failures=[r for r in checker.rows if r['status']=='abstract_counterexample']
            witness=replay(module)
            result=dict(name=name,status='confirmed' if failures and witness['confirmed'] else 'unknown',
                        failed_obligations=failures,concrete_witness=witness,
                        confirmation='independent trace from initialization; not a replay of an arbitrary SMT abstract state')
        except (Unsupported,KeyError,ValueError) as error:
            result=dict(name=name,status='unknown',reason=str(error))
        save(directory/'results.json',result);results.append(result)
    return results


def expected_obligations():
    names={'free_slot_scan','all_sixteen_bounds','distinct_directions_disjoint'}
    groups=['initialization','initial_header_b2','initial_header_b11']
    groups += [name+'_'+str(i) for i in range(8) for name in ('inner_enters','stopped_inner','entry','publish','persist_or_reset','inactive_scan','inner_to_outer','outer_to_table','outer_backedge')]
    names.update(name+suffix for name in groups for suffix in ('','_coverage','_runtime'))
    names.update(name+'_closure_including_fatal' for name in CUTS)
    result={('lifecycle',name) for name in names}
    properties={'no_trap_or_undefined','call_binding_and_guard','state_and_count_binding','byte_conservation','exact_buffer_frame','other_directions_unchanged','exact_histories','fatal_stops_direction','coverage'}
    for name in CUTS:
        result.update((name,prop) for prop in properties)
        if name.endswith('.write'):result.add((name,'pending_suffix'))
    return result


def accepted(rows,negative,composition):
    keys=[(r.get('cut','lifecycle'),r['obligation']) for r in rows]
    return (composition and len(keys)==len(expected_obligations()) and set(keys)==expected_obligations() and
            all(r['status']=='proved' for r in rows) and
            len(negative)==len(MUTATIONS) and {r['name'] for r in negative}==set(MUTATIONS) and
            all(r['status']=='confirmed' and r['concrete_witness']['confirmed'] for r in negative))


def check(output,timeout=10000):
    if timeout<=0:raise ValueError('timeout must be positive')
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output must be absent or empty')
    output.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'examples/apps/liza_proxy.liza').read_bytes()
    helper=(ROOT/'examples/apps/relay/direction.liza').read_bytes()
    dependencies=[ROOT/'verification/requirements.txt']
    for directory in ('liza','verification/relay_r1','verification/relay_r2b','verification/relay_r2c'):
        dependencies.extend(p for p in (ROOT/directory).rglob('*') if p.suffix in ('.py','.liza','.json') and p.is_file())
    for file in dependencies:
        target=output/'tools'/file.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
    module=compile_source(source,helper,output/'program')
    checker=Checks(module,output/'checks',timeout)
    try:
        checker.lifecycle();checker.local_closure();checker.composition()
        negative=controls(source,helper,output/'mutations',timeout)
        passed=accepted(checker.rows,negative,checker.composition_checked)
        baseline=replay(module)
        passed=passed and not baseline['confirmed'] and baseline.get('completed_epochs')==2
        save(output/'baseline-replay.json',baseline)
        report=dict(status='passed' if passed else 'incomplete',obligations=checker.rows,
                    controls=[{k:v for k,v in n.items() if k!='concrete_witness'} for n in negative],
                    conditional_inductive_pair_verified=passed,composition_checked=checker.composition_checked,
                    whole_program_verified=False,event_loop_verified=False,liveness_verified=False,
                    runtime_verified=False,llvm_verified=False,end_to_end_verified=False,proof_certificate=False,
                    scope='one pair, either direction, any selected slot; other-pair frame and abstract runtime contracts; exchange receives live initialized buffer',
                    assumptions=['fresh opaque socket identities per successful creation','disconnect consumes valid ID even on error',
                                 'R2-B byte I/O contracts, including temporary errors without hidden transfer',
                                 'other pairs do not mutate selected table entry or buffer sections','live initialized 32768-byte Buffer at exchange entry'],
                    exclusions=['main/serve allocation proof','diagnostic startup and terminal reactor_close implementation',
                                'whole multi-pair event loop','fairness/termination','runtime and machine-code correctness'],
                    visited=sorted([list(x) for x in checker.visited]),
                    baseline_commit='05dcc9c1c8c2166454d2c4064b2a7c3401c6b095',
                    python=platform.python_version(),z3=z3.get_version_string())
    except (Unsupported,KeyError,ValueError) as error:
        report=dict(status='unknown',reason=str(error),obligations=checker.rows,conditional_inductive_pair_verified=False,end_to_end_verified=False)
    report['semantic_ir_sha256']=hashlib.sha256((output/'program/semantic.json').read_bytes()).hexdigest()
    report['artifacts']={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    save(output/'report.json',report)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/verified-relay-r2c');parser.add_argument('--timeout-ms',type=int,default=10000)
    args=parser.parse_args();report=check(args.output,args.timeout_ms)
    print(json.dumps({k:v for k,v in report.items() if k not in ('obligations','controls','artifacts','visited')},indent=2))
    raise SystemExit(0 if report['status']=='passed' else 1)
