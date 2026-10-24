"""Tests for the verifier itself, run only in the optional Z3 environment."""
import unittest
from unittest.mock import patch
import z3 as z
from verification import model, reference
from verification.check import analyze, check


class VerifierTests(unittest.TestCase):
    def verify(self, body, name='sequence_u8'):
        text='define i8 @liza_'+name+'(i8 %p0) {\nb0:\n'+body+'\n}'
        return analyze(name,lambda args:model.llvm(text,name,args),10000)

    def test_removed_trap_has_exact_counterexample(self):
        r=self.verify('ret i8 %p0')
        self.assertEqual(r['status'],'counterexample')
        self.assertEqual(r['inputs'],{'x':255})

    def test_poison_cannot_replace_checked_trap(self):
        r=self.verify('%v = add nuw i8 %p0, 1\nret i8 %p0')
        self.assertEqual(r['status'],'counterexample')

    def test_unreachable_is_not_trap(self):
        self.assertEqual(self.verify('unreachable')['status'],'counterexample')

    def test_unsupported_is_unknown(self):
        for body in ('%v = call i8 @opaque(i8 %p0)\nret i8 %v',
                     '%v = freeze i8 %p0\nret i8 %v',
                     'br label %b0', 'ret i8 poison'):
            with self.subTest(body=body):
                self.assertEqual(self.verify(body)['status'],'unknown')

    def test_unsatisfied_return_range_is_not_assumed(self):
        text='define range(i8 0, 10) i8 @liza_sequence_u8(i8 %p0) {\nb0:\nret i8 %p0\n}'
        r=analyze('sequence_u8',lambda args:model.llvm(text,'sequence_u8',args),10000)
        self.assertEqual(r['status'],'counterexample')

    def test_missing_paths_cannot_pass_vacuously(self):
        args=reference.inputs('sequence_u8')
        r=check('sequence_u8',model.outcome([]),args,10000)
        self.assertEqual(r['status'],'counterexample')

    def test_solver_unknown_never_passes(self):
        args=reference.inputs('sequence_u8')
        with patch('verification.check.z.Solver') as solver:
            solver.return_value.check.return_value=z.unknown
            solver.return_value.reason_unknown.return_value='timeout'
            r=check('sequence_u8',model.outcome([]),args,1)
        self.assertEqual(r,{'status':'unknown','reason':'timeout'})

    def test_reference_boundary_replay(self):
        for name in reference.SUBJECTS:
            op,ty=name.split('_')
            values=(0,1,127,128,254,255)
            for x in values:
                ys=values if op in ('add','sub','mul') else (0,1) if op=='branch' else (None,)
                for y in ys:
                    integers=[x] if y is None else [x,y]
                    args=[z.BitVecVal(v,1 if op=='branch' and i==1 else 8) for i,v in enumerate(integers)]
                    trap,value=reference.specification(name,args)
                    t,v=reference.concrete(name,integers)
                    self.assertEqual(z.is_true(z.simplify(trap)),t,(name,integers))
                    if not t:self.assertEqual(z.simplify(value).as_long(),v,(name,integers))

    def test_branch_keeps_dead_trap_unexecuted(self):
        text='''define i8 @liza_branch_u8(i8 %p0, i1 %p1) {
b0:
 br i1 %p1, label %calc, label %exit
calc:
 %pair = call {i8, i1} @llvm.uadd.with.overflow.i8(i8 %p0, i8 1)
 %value = extractvalue {i8, i1} %pair, 0
 %overflow = extractvalue {i8, i1} %pair, 1
 br i1 %overflow, label %trap, label %done
trap:
 call void @llvm.trap()
 unreachable
done:
 ret i8 %value
exit:
 ret i8 %p0
}'''
        r=analyze('branch_u8',lambda args:model.llvm(text,'branch_u8',args),10000)
        self.assertEqual(r['status'],'proved')
        broken=text.replace('br i1 %p1,','br i1 true,')
        r=analyze('branch_u8',lambda args:model.llvm(broken,'branch_u8',args),10000)
        self.assertEqual(r['status'],'counterexample')


if __name__=='__main__':unittest.main()
