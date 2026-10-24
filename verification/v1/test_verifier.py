"""Adversarial checks of the V1 model, not just successful proof fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import z3 as z
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm as emit_llvm
from verification.v1 import reference,semantic,llvm
from verification.v1.common import Unsupported,collect
from verification.v1.memory import Memory,Pointer
from verification.v1.check import analyze,check,mutations

ROOT=Path(__file__).resolve().parents[2]


class MemoryTests(unittest.TestCase):
    def prove(self,condition):
        solver=z.Solver();solver.add(z.Not(condition));self.assertEqual(solver.check(),z.unsat)

    def test_symbolic_store_tracks_initialization(self):
        memory=Memory();base=memory.allocate('a',4,4)
        index=z.BitVec('index',32);offset=z.BV2Int(index)
        p=Pointer(base.origin,offset);value=z.BitVec('value',8)
        valid=memory.store(p,(value,),1)
        values,readable,init=memory.load(p,1,1)
        self.prove(z.Implies(z.ULT(index,4),z.And(valid,readable,init,values[0]==value)))
        neighbor=Pointer('a',(offset+1)%4)
        _,_,neighbor_init=memory.load(neighbor,1,1)
        self.prove(z.Implies(z.ULT(index,4),z.Not(neighbor_init)))

    def test_whole_load_requires_every_byte(self):
        memory=Memory();p=memory.allocate('a',4,4)
        memory.store(p,(z.BitVecVal(7,8),),1)
        _,valid,init=memory.load(p,4,4)
        self.prove(valid);self.prove(z.Not(init))

    def test_distinct_origins_and_real_aliases(self):
        memory=Memory();a=memory.allocate('a',4,4);b=memory.allocate('b',4,4)
        memory.store(a,(z.BitVecVal(7,8),),1)
        _,_,initialized=memory.load(b,1,1);self.prove(z.Not(initialized))
        alias=Pointer('a',z.IntVal(0));memory.store(alias,(z.BitVecVal(9,8),),1)
        values,_,_=memory.load(a,1,1);self.prove(values[0]==9)

    def test_path_forks_do_not_share_writes(self):
        memory=Memory();p=memory.allocate('a',1,1)
        memory.store(p,(z.BitVecVal(1,8),),1)
        branch=memory.fork();branch.store(p,(z.BitVecVal(2,8),),1)
        self.prove(memory.load(p,1,1)[0][0]==1)
        self.prove(branch.load(p,1,1)[0][0]==2)

    def test_one_past_pointer_is_not_readable(self):
        memory=Memory();p=memory.allocate('a',4,4)
        end,valid=memory.gep(p,[z.BitVecVal(4,64)],[1],['inbounds'])
        self.prove(valid);self.prove(z.Not(memory.access(end,1,1)))
        outside,valid=memory.gep(p,[z.BitVecVal(5,64)],[1],['inbounds'])
        self.prove(z.Not(valid))

    def test_negative_and_misaligned_offsets(self):
        memory=Memory();p=memory.allocate('a',4,4)
        self.prove(z.Not(memory.access(Pointer('a',z.IntVal(-1)),1,1)))
        self.prove(z.Not(memory.access(Pointer('a',z.IntVal(1)),2,2)))
        with self.assertRaises(Unsupported):memory.access(p,1,8)

    def test_unknown_origin_is_unknown(self):
        with self.assertRaises(Unsupported):Memory().load(Pointer('missing',z.IntVal(0)),1,1)

    def test_integer_storage_is_little_endian(self):
        bytes_=llvm.to_bytes('i32',z.BitVecVal(0x12345678,32))
        self.assertEqual([z.simplify(v).as_long() for v in bytes_],[0x78,0x56,0x34,0x12])
        self.prove(llvm.from_bytes('i32',bytes_)==0x12345678)


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=lower(Parser((ROOT/'verification/v1/bounds.liza').read_text()).parse())
        cls.raw=emit_llvm(cls.module)
        cls.mutants={label:(name,text) for label,name,text in mutations(cls.raw)}

    def prove(self,condition):
        solver=z.Solver();solver.add(z.Not(condition));self.assertEqual(solver.check(),z.unsat)

    def test_all_semantic_subjects(self):
        for name in reference.SUBJECTS:
            fn=next(f for f in self.module if f.name==name)
            with self.subTest(name=name):self.assertEqual(analyze(name,lambda args:semantic.evaluate(fn,args),10000)['status'],'proved')

    def test_all_generated_subjects(self):
        for name in reference.SUBJECTS:
            with self.subTest(name=name):self.assertEqual(analyze(name,lambda args:llvm.evaluate(self.raw,name,args),10000)['status'],'proved')

    def test_mutations_require_counterexamples(self):
        for label,(name,text) in self.mutants.items():
            with self.subTest(mutation=label):self.assertEqual(analyze(name,lambda args:llvm.evaluate(text,name,args),10000)['status'],'counterexample')

    def test_full_u32_domain_includes_maximum(self):
        args=reference.inputs('read');actual=llvm.evaluate(self.raw,'read',args)
        self.prove(z.Implies(args[4]==0xffffffff,actual['trap']))
        self.prove(z.Not(actual['undefined']))
        name,text=self.mutants['signed_bounds'];actual=llvm.evaluate(text,name,args)
        self.prove(z.Implies(args[4]==0xffffffff,actual['undefined']))

    def test_uninitialized_is_undefined_not_unknown(self):
        name,text=self.mutants['uninitialized_in_bounds']
        args=reference.inputs(name);actual=llvm.evaluate(text,name,args)
        self.prove(z.Implies(z.ULT(args[4],4),actual['undefined']))
        self.prove(z.Implies(z.ULT(args[4],4),z.Not(actual['trap'])))

    def test_dead_rhs_with_maximum_index(self):
        for name,take in [('short_and',0),('short_or',1),('branch',0)]:
            args=reference.inputs(name);actual=llvm.evaluate(self.raw,name,args)
            condition=z.And(args[4]==0xffffffff,args[5]==take)
            self.prove(z.Implies(condition,z.And(z.Not(actual['trap']),z.Not(actual['undefined']))))

    def test_semantic_wrong_element_is_detected(self):
        fn=copy.deepcopy(next(f for f in self.module if f.name=='read'))
        fn.blocks[0].operations[0].args.reverse()
        self.assertEqual(analyze('read',lambda args:semantic.evaluate(fn,args),10000)['status'],'counterexample')

    def test_semantic_unsupported_is_unknown(self):
        fn=copy.deepcopy(next(f for f in self.module if f.name=='read'))
        fn.blocks[0].operations[1].op='imaginary.read'
        self.assertEqual(analyze('read',lambda args:semantic.evaluate(fn,args),10000)['status'],'unknown')

    def test_unknown_instructions_and_metadata(self):
        for replacement in ('%v1 = freeze i8 %p0','%v1 = call i8 @external()',
                            '%v1 = load i8, ptr %v1_ptr, !range !0'):
            text=self.raw.replace('%v1 = load i8, ptr %v1_ptr',replacement,1)
            self.assertEqual(analyze('read',lambda args:llvm.evaluate(text,'read',args),10000)['status'],'unknown')

    def test_missing_paths_and_solver_unknown(self):
        args=reference.inputs('read')
        self.assertEqual(check('read',collect([]),args,10000)['status'],'counterexample')
        with patch('verification.v1.check.z.Solver') as solver:
            solver.return_value.check.return_value=z.unknown
            solver.return_value.reason_unknown.return_value='timeout'
            self.assertEqual(check('read',collect([]),args,1),{'status':'unknown','reason':'timeout'})

    def test_no_memory_select_model(self):
        text='''define i8 @liza_choose(i8 %p0, i8 %p1, i8 %p2, i8 %p3, i32 %p4, i1 %p5) {
b0:
 %v = select i1 %p5, i8 %p1, i8 %p0
 ret i8 %v
}'''
        self.assertEqual(analyze('choose',lambda args:llvm.evaluate(text,'choose',args),10000)['status'],'proved')

    def test_returned_attribute_is_checked(self):
        text='''define i8 @liza_constant_read(i8 returned %p0, i8 %p1, i8 %p2, i8 %p3, i32 %p4) {
b0:
 ret i8 %p2
}'''
        r=analyze('constant_read',lambda args:llvm.evaluate(text,'constant_read',args),10000)
        self.assertEqual(r['status'],'counterexample')
        self.assertEqual(r['ir_model'][0]['kind'],'Undefined')

    def test_optimization_flags_are_checked(self):
        for instruction,condition in (
            ('%unused = zext nneg i32 %p4 to i64',lambda args:args[4]==0xffffffff),
            ('%unused = or disjoint i8 %p2, %p2',lambda args:args[2]==1),
            ('%unused = shl nuw i8 %p2, 1',lambda args:args[2]==128),
        ):
            text='define i8 @liza_constant_read(i8 %p0, i8 %p1, i8 %p2, i8 %p3, i32 %p4) {\nb0:\n '+instruction+'\n ret i8 %p2\n}'
            args=reference.inputs('constant_read');actual=llvm.evaluate(text,'constant_read',args)
            self.prove(z.Implies(condition(args),actual['undefined']))

    def test_aggregate_value_instructions_without_memory(self):
        body=' %a = insertvalue [4 x i8] zeroinitializer, i8 %p2, 2\n %b = extractvalue [4 x i8] %a, 2\n %vec = insertelement <4 x i8> zeroinitializer, i8 %b, i32 1\n %v = extractelement <4 x i8> %vec, i32 1\n ret i8 %v'
        text='define i8 @liza_constant_read(i8 %p0, i8 %p1, i8 %p2, i8 %p3, i32 %p4) {\nb0:\n'+body+'\n}'
        self.assertEqual(analyze('constant_read',lambda args:llvm.evaluate(text,'constant_read',args),10000)['status'],'proved')

    def test_v0_files_are_frozen(self):
        baseline=json.loads((ROOT/'verification/v1/v0-baseline.json').read_text())
        for path,digest in baseline.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)

    def test_reference_boundary_replay(self):
        for name in reference.SUBJECTS:
            for index in (0,1,2,3,4,255,256,0x7fffffff,0x80000000,0xffffffff):
                for observe in range(4):
                    for take in (0,1):
                        values=[0,17,128,255,index]
                        if name in ('update','snapshot'):values += [42,observe]
                        elif name in ('short_and','short_or','branch','choose'):values += [take]
                        args=[z.BitVecVal(v,a.size()) for v,a in zip(values,reference.inputs(name))]
                        trap,value=reference.specification(name,args);expected=reference.concrete(name,values)
                        self.assertEqual(z.is_true(z.simplify(trap)),expected['kind']=='Trap')
                        if expected['kind']=='Return':self.assertEqual(z.simplify(value).as_long(),expected['value'])


if __name__=='__main__':unittest.main()
