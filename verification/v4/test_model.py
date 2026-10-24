import unittest
import hashlib
import tempfile
from pathlib import Path

from liza.frontend import Parser, CompileError
from liza.ir import lower, dump, Terminator
from .check import SAFE, UNSAFE, compile_source, mutant, run
from .model import check, State, Resource, Variant, Violation


class ResourceModelTests(unittest.TestCase):
    def setUp(self):
        self.module, self.audit = compile_source(SAFE)

    def test_report_hashes_match_saved_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = run(root)
            for name, result in report['results'].items():
                for filename, expected in result['artifacts'].items():
                    self.assertEqual(hashlib.sha256((root/name/filename).read_bytes()).hexdigest(), expected)

    def test_audit_does_not_change_ir(self):
        self.assertEqual(dump(lower(Parser(SAFE).parse())), dump(self.module))

    def test_all_resource_outcomes(self):
        result = check(self.module, self.audit)
        self.assertEqual(result['status'], 'verified_fragment')
        self.assertEqual(result['normal_paths'], 3)

    def test_summaries_are_not_axioms(self):
        for fn in self.module:
            fn.storage_contract = {'deliberately': 'false'}
        self.assertEqual(check(self.module, self.audit)['status'], 'verified_fragment')

    def test_original_rejects_unsafe_source(self):
        with self.assertRaisesRegex(CompileError, 'dependent buffer or Result'):
            compile_source(UNSAFE)

    def test_lost_dependency_and_forbidden_move(self):
        with mutant('lose_unresolved_result'):
            module, audit = compile_source(UNSAFE)
        report = check(module, audit)
        self.assertEqual(report['status'], 'model_violation')
        self.assertTrue(report['coverage_failures'])
        self.assertIn('live dependency', report['reason'])
        self.assertEqual(report['traces'][0]['steps'][-1]['operation'], 'move')

    def test_guard_failure_without_dependency_loss(self):
        with mutant('bypass_region_guard'):
            module, audit = compile_source(UNSAFE)
        report = check(module, audit)
        self.assertEqual(report['status'], 'model_violation')
        self.assertFalse(report['coverage_failures'])
        self.assertTrue(report['guard_failures'])

    def test_missing_audit_is_unknown(self):
        self.assertEqual(check(self.module, {})['status'], 'unknown')
        self.audit['main']['points'].clear()
        self.assertEqual(check(self.module, self.audit)['status'], 'unknown')

    def test_wrong_creation_correspondence_is_unknown(self):
        self.audit['main']['sites']['0'] = 'nonexistent'
        self.assertEqual(check(self.module, self.audit)['status'], 'unknown')

    def test_budget_is_not_success(self):
        self.assertEqual(check(self.module, self.audit, max_states=0)['status'], 'unknown')

    def test_unsupported_opcode_is_unknown(self):
        self.module[0].blocks[0].operations[0].op = 'future.operation'
        self.assertEqual(check(self.module, self.audit)['status'], 'unknown')

    def test_resource_neutral_infinite_loop_has_closed_safety_graph(self):
        self.module[0].blocks[0].operations = []
        self.module[0].blocks[0].terminator = Terminator('jump', ['b0'])
        self.audit['main']['sites'] = {}
        report=check(self.module,self.audit)
        self.assertEqual(report['status'],'verified_fragment')
        self.assertGreater(report['closed_edges'],0)

    def test_ir_leak_without_frontend(self):
        # Keep the move, replace close with a scalar constant. Real ownership
        # obligations must still be found even though the frontend accepted
        # the original source and its storage_contract promises a clean exit.
        for block in self.module[0].blocks:
            for op in block.operations:
                if op.op == 'region.close':
                    op.op, op.args = 'constant', [0]
        report = check(self.module, self.audit)
        self.assertEqual(report['status'], 'model_violation')
        self.assertIn('normal exit', report['reason'])

    def test_extra_static_dependency_is_not_unsound(self):
        origin = "('fresh', 'main', '0')"
        # Extra dependence at a non-destructive operation is conservative.
        for observation in self.audit['main']['points']['v0'].values():
            observation['dependencies'].append(origin)
        self.assertEqual(check(self.module, self.audit)['status'], 'verified_fragment')

    def test_static_guard_is_distinct_from_runtime_guard(self):
        origin = "('fresh', 'main', '0')"
        for block in self.module[0].blocks:
            for op in block.operations:
                if op.op == 'region.close':
                    self.audit['main']['points'][op.result]['before']['dependencies'] = [origin]
        report = check(self.module, self.audit)
        self.assertEqual(report['status'], 'guard_failure')
        self.assertTrue(report['guard_failures'])
        self.assertFalse(report['coverage_failures'])
        self.assertFalse(report['traces'])  # no actual live-dependent violation

    def test_runtime_identities_distinguish_same_site(self):
        state = State()
        first, second = state.fresh(), state.fresh()
        state.regions = {first: 'same_site', second: 'same_site'}
        state.buffers[2] = first
        state.region_guard(Resource('region', second))
        with self.assertRaises(Violation):
            state.region_guard(Resource('region', first))

    def test_move_consumes_whole_conditional_resource(self):
        state = State(values={'result': Variant('Result', 'Ok', Resource('buffer', 1))})
        state.take('result')
        with self.assertRaises(Violation):
            state.take('result')

class InterproceduralAndLoopTests(unittest.TestCase):
    def test_selected_function_cfg_and_loop_matrix(self):
        from . import fixtures
        for name in ['CALL','RESULT_CALL','UPDATE','FACTORY','CFG','LOOP','LIVE_LOOP',
                     'WRAP','TWO_BUFFERS','TWO_REGIONS_SAFE']:
            with self.subTest(name=name):
                module,audit=compile_source(getattr(fixtures,name))
                report=check(module,audit)
                self.assertEqual(report['status'],'verified_fragment',report)
                if name in {'LOOP','LIVE_LOOP'}:
                    self.assertGreater(report['closed_edges'],0)

    def test_return_summary_is_checked_not_trusted(self):
        from .fixtures import CALL
        module,audit=compile_source(CALL)
        helper=next(f for f in module if f.name!='main')
        helper.storage_contract['returns']={}
        report=check(module,audit)
        self.assertEqual(report['status'],'summary_failure')
        self.assertTrue(report['summary_failures'])
        self.assertFalse(report['traces'])

    def test_correct_return_origin_does_not_excuse_second_resource_leak(self):
        from .fixtures import TWO_BUFFERS
        module,audit=compile_source(TWO_BUFFERS)
        helper=next(f for f in module if f.name=='choose')
        for block in helper.blocks:
            for op in block.operations:
                if op.op=='buffer.release':op.op,op.args='constant',[0]
        report=check(module,audit)
        self.assertEqual(report['status'],'model_violation',report)
        self.assertFalse(report['summary_failures'])
        self.assertTrue(any(t['reproduced'] for t in report['traces']))
        self.assertIn('normal exit',report['reason'])

    def test_all_seven_analyzer_mutations_are_replayed(self):
        with tempfile.TemporaryDirectory() as temporary:
            report=run(Path(temporary))
            from .check import MUTATIONS
            self.assertEqual(len(MUTATIONS),7)
            for name in MUTATIONS:
                result=report['results'][name]
                self.assertTrue(result['original_rejection'])
                self.assertTrue(result['mutated_analyzer_accepts'])
                self.assertEqual(result['status'],'model_violation',name)
                self.assertTrue(any(t['reproduced'] for t in result['traces']),name)

    def test_infeasible_abstract_counterexample_is_unknown(self):
        from .fixtures import RESOLVED_UNSAFE
        source=RESOLVED_UNSAFE.replace('closed=memory.close(move region)\nreleased=memory.release(move next)',
             '''if 1==2 {closed=memory.close(move region)
released=memory.release(move next)} else {
released=memory.release(move next)
closed=memory.close(move region)}''')
        with mutant('bypass_region_guard'):module,audit=compile_source(source)
        report=check(module,audit)
        self.assertEqual(report['status'],'unknown',report)
        self.assertTrue(report['traces'])
        self.assertFalse(any(t['reproduced'] for t in report['traces']))

    def test_induction_does_not_depend_on_numeric_loop_bound(self):
        from .fixtures import LOOP
        small=check(*compile_source(LOOP))
        large=check(*compile_source(LOOP.replace('i<2','i<4294967295')))
        self.assertEqual(large['status'],'verified_fragment')
        self.assertEqual(small['states'],large['states'])
        self.assertEqual(small['closed_edges'],large['closed_edges'])

    def test_break_continue_preserve_resource_obligations(self):
        from .fixtures import LOOP
        source=LOOP.replace('i=i+1','i=i+1\nif i==1 {continue}\nif i==2 {break}')
        report=check(*compile_source(source))
        self.assertEqual(report['status'],'verified_fragment',report)
        self.assertGreater(report['closed_edges'],0)

    def test_budget_cannot_truncate_loop_into_success(self):
        from .fixtures import LOOP
        self.assertEqual(check(*compile_source(LOOP),max_states=30)['status'],'unknown')

    def test_concrete_replay_preserves_bounds_trap_before_bad_move(self):
        from .fixtures import RESOLVED_UNSAFE
        source=RESOLVED_UNSAFE.replace('next=move buffer','next=memory.set(move buffer,100,0)')
        with mutant('bypass_region_guard'):module,audit=compile_source(source)
        report=check(module,audit)
        self.assertEqual(report['status'],'unknown',report)
        self.assertFalse(any(t['reproduced'] for t in report['traces']))


if __name__ == '__main__':
    unittest.main()
