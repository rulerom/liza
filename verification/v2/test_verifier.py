"""Induction-rule, model, mutation and boundary checks. No test bound is used
by the quantified/inductive verification obligations themselves."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import z3 as z
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm as emit_llvm
from verification.v2 import core,semantic,llvm,mutations,replay
from verification.v2.check import analyze,solve

ROOT=Path(__file__).resolve().parents[2]

class VerifiedV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=lower(Parser((ROOT/'verification/v2/loops.liza').read_text()).parse())
        cls.functions={fn.name:fn for fn in cls.module}
        cls.raw=emit_llvm(cls.module)
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-v2-tests-')
        src=Path(cls.temp.name)/'module.ll';src.write_text(cls.raw)
        out=Path(cls.temp.name)/'O2.ll'
        subprocess.run(['clang','-Wno-override-module','-O2','-S','-emit-llvm',str(src),'-o',str(out)],check=True,capture_output=True)
        cls.optimized=out.read_text()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def prove(self,claim):
        solver=z.Solver();solver.set(timeout=10000);solver.add(z.Not(claim))
        self.assertEqual(solver.check(),z.unsat)
    def test_all_semantic_inductive_obligations(self):
        for name in ('search','sum'):
            ctx=core.Context(name);result=analyze(semantic.Engine(self.functions[name],ctx),ctx)
            self.assertEqual(len(result['results']),10)
            self.assertTrue(all(r['status']=='proved' for r in result['results']))
    def test_actual_llvm_both_loop_forms(self):
        for text,strict in ((self.raw,False),(self.optimized,True)):
            for name in ('search','sum'):
                ctx=core.Context(name,True);engine=llvm.Engine(text,name,ctx)
                self.assertEqual(engine.strict,strict)
                rows=analyze(engine,ctx)['results']
                self.assertEqual(len(rows),9)
                self.assertTrue(all(r['status']=='proved' for r in rows))
    def test_eight_mutations_and_concrete_replay(self):
        cases=list(mutations.cases(self.module));self.assertEqual(len(cases),8)
        for label,fn,data,needle in cases:
            with self.subTest(mutation=label):
                ctx=core.Context(fn.name);rows=analyze(semantic.Engine(fn,ctx),ctx)['results']
                self.assertTrue(any(r['status']=='counterexample_to_obligation' for r in rows))
                actual=replay.run(fn,data,needle);expected=replay.reference(fn.name,data,needle)
                self.assertNotEqual(actual['kind'],'ReplayLimit')
                self.assertTrue(replay.differs(expected,actual))
    def test_empty_and_first_match(self):
        self.assertEqual(replay.run(self.functions['search'],[],7)['value'],0)
        self.assertEqual(replay.run(self.functions['search'],[7,7],7)['value'],0)
        self.assertEqual(replay.run(self.functions['sum'],[])['value'],0)
    def test_first_overflow_not_final_sum(self):
        fn=self.functions['sum']
        actual=replay.run(fn,[core.MAX,1,-1]);self.assertEqual(actual['kind'],'Trap')
        self.assertEqual(actual['reads'],[0,1])
        actual=replay.run(fn,[core.MIN,-1,1]);self.assertEqual(actual['kind'],'Trap')
        self.assertEqual(actual['reads'],[0,1])
        self.assertEqual(replay.run(fn,[core.MAX,-1,1])['value'],core.MAX)
    def test_sum_replay_differential(self):
        import itertools
        for size in range(4):
            for data in itertools.product((core.MIN,-1,0,1,core.MAX),repeat=size):
                self.assertFalse(replay.differs(replay.reference('sum',data),replay.run(self.functions['sum'],data)))
    def test_frozen_v0_v1(self):
        baseline=json.loads((ROOT/'verification/v2/baseline.json').read_text())
        for path,digest in baseline.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
    def test_false_invariant_is_not_accepted(self):
        ctx=core.Context('search');ctx.invariant=lambda *args,**kwargs:z.BoolVal(False)
        result=analyze(semantic.Engine(self.functions['search'],ctx),ctx)
        row=next(r for r in result['results'] if r['obligation']=='entry.invariant_and_exits')
        self.assertEqual(row['status'],'counterexample_to_obligation')
    def test_invariant_without_history_fails(self):
        ctx=core.Context('search');ctx.history=lambda index:z.BoolVal(True)
        # Preserve the real postcondition, weakening ONLY the loop invariant.
        real=core.Context('search');real.data=ctx.data;real.needle=ctx.needle;real.length=ctx.length
        ctx.post=real.post
        result=analyze(semantic.Engine(self.functions['search'],ctx),ctx)
        self.assertEqual(next(r for r in result['results'] if r['obligation']=='exit.postcondition')['status'],'counterexample_to_obligation')
    def test_stuttering_can_preserve_invariant_but_not_ranking(self):
        fn=next(fn for label,fn,_,_ in mutations.cases(self.module) if label=='no_progress')
        ctx=core.Context('search');rows={r['obligation']:r['status'] for r in analyze(semantic.Engine(fn,ctx),ctx)['results']}
        self.assertEqual(rows['backedge.invariant'],'proved')
        self.assertEqual(rows['backedge.strict_ranking'],'counterexample_to_obligation')
    def test_max_length_last_step_never_computes_length_plus_one(self):
        for physical,text in ((False,None),(True,self.raw),(True,self.optimized)):
            ctx=core.Context('search',physical);ctx.length=z.IntVal(core.U32);ctx.needle=z.IntVal(1)
            ctx.data=z.K(z.IntSort(),z.IntVal(0))
            engine=llvm.Engine(text,'search',ctx) if physical else semantic.Engine(self.functions['search'],ctx)
            seed=next(e.env for e in engine.entry() if e.kind=='Back')
            env,_=engine.symbolic_header(seed);env[engine.index]=z.IntVal(core.U32-1)
            exits=engine.step(env)
            self.prove(z.Not(z.Or(*[e.path for e in exits if e.kind in ('Trap','Undefined')])))
            for e in exits:
                if e.kind=='Back':self.prove(z.Implies(e.path,engine.roles(e.env)[0]==core.U32))
                if e.kind=='Return':self.prove(z.Implies(e.path,e.value==core.U32))
    def test_additional_cycle_is_unknown(self):
        fn=copy.deepcopy(self.functions['search'])
        # Reachable internal self-loop bypasses the annotated cutpoint.
        block=next(b for b in fn.blocks if b.name=='b5')
        block.terminator.args=[block.name]
        with self.assertRaises(core.Unsupported):semantic.Engine(fn,core.Context('search'))
    def test_unsupported_operations_are_unknown(self):
        fn=copy.deepcopy(self.functions['search'])
        next(o for b in fn.blocks for o in b.operations if o.op=='view.read').op='unknown.read'
        ctx=core.Context('search')
        self.assertEqual(analyze(semantic.Engine(fn,ctx),ctx)['status'],'unknown')
        text=self.raw.replace('%v4 = load i8, ptr %v4_ptr','%v4 = freeze i8 %p1')
        ctx=core.Context('search',True)
        self.assertEqual(analyze(llvm.Engine(text,'search',ctx),ctx)['status'],'unknown')
    def test_physical_wrong_stride_is_detected(self):
        text=self.raw.replace('getelementptr i32, ptr %v6_base','getelementptr i8, ptr %v6_base')
        ctx=core.Context('sum',True)
        rows=analyze(llvm.Engine(text,'sum',ctx),ctx)['results']
        self.assertEqual(next(r for r in rows if r['obligation']=='step.no_undefined')['status'],'counterexample_to_obligation')
    def test_unknown_solver_is_not_proved(self):
        with patch('verification.v2.check.z.Solver') as solver:
            solver.return_value.check.return_value=z.unknown
            solver.return_value.reason_unknown.return_value='timeout'
            rows=solve([('test',z.BoolVal(True),z.BoolVal(True))],1)
        self.assertEqual(rows[0]['status'],'unknown')
    def test_byte_decoding_is_complete_and_little_endian(self):
        ctx=core.Context('sum',True)
        data=z.K(z.IntSort(),z.IntVal(0))
        for i,v in enumerate((255,255,255,127,0,0,0,128)):data=z.Store(data,i,v)
        ctx.data=data
        self.prove(ctx.element(0)==core.MAX);self.prove(ctx.element(1)==core.MIN)
        ctx=core.Context('sum',False);x=z.Int('raw_element')
        ctx.data=z.K(z.IntSort(),x)
        self.prove(core.fits(ctx.element(0),True))

if __name__=='__main__':unittest.main()
