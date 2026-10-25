"""Actual source controls, byte witnesses, cutpoint and uncertainty regressions."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import z3
from .check import APP, HELPER, ROOT, analyze, check
from .fragment import Fragment, CUTS
from .replay import replay_record, run, violations
from .semantic import Executor
from .specification import inputs, properties


class ByteBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.report = check(cls.root / 'run')
        cls.module = json.loads((cls.root / 'run/original/semantic.json').read_text())

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def query(self, module, cut='forward.read'):
        return analyze(module, cut, self.root / self.id().split('.')[-1])

    def test_full_matrix(self):
        self.assertEqual(self.report['status'], 'passed')
        self.assertEqual(len(self.report['obligations']), 58)
        self.assertTrue(all(r['status'] == 'proved' for r in self.report['obligations']))
        self.assertEqual({r['cut'] for r in self.report['obligations'] if 'cut' in r}, set(CUTS))

    def test_sources_are_unmodified(self):
        original = self.root / 'run/original/source'
        self.assertEqual((original / 'liza_proxy.liza').read_bytes(), APP.read_bytes())
        self.assertEqual((original / 'relay/direction.liza').read_bytes(), HELPER.read_bytes())

    def test_eight_source_mutations_replay_from_saved_json(self):
        self.assertEqual(len(self.report['mutations']), 8)
        for control in self.report['mutations']:
            with self.subTest(control=control['name']):
                self.assertEqual(control['status'], 'detected_and_replayed')
                root = self.root / 'run/mutations' / control['name']
                self.assertNotEqual((root / 'source/liza_proxy.liza').read_bytes(), APP.read_bytes())
                self.assertEqual((root / 'source/relay/direction.liza').read_bytes(), HELPER.read_bytes())
                module = json.loads((root / 'semantic.json').read_text())
                record = json.loads((root / 'checks/results.json').read_text())[0]['replay']
                _, bad = replay_record(module, Fragment(module, control['cut']), record)
                self.assertTrue(bad); self.assertEqual(bad, record['violations'])

    def test_byte_controls_demonstrate_successful_byte_corruption(self):
        targets = {'read_wrong_half': 'other_directions_unchanged',
                   'read_base_off_by_one': 'exact_buffer_frame', 'write_from_tail': 'exact_histories',
                   'consume_extra_byte': 'byte_conservation', 'overwrite_other_direction': 'other_directions_unchanged'}
        for control in self.report['mutations']:
            if control['name'] in targets:
                record = control['checks'][0]['replay']
                self.assertEqual(record['inputs']['outcome'], 0)
                self.assertGreater(record['inputs']['count'], 0)
                self.assertIn(targets[control['name']], record['violations'])

    def test_standalone_concrete_replay_without_site_packages(self):
        root = self.root / 'run/mutations/read_wrong_half'
        result = subprocess.run([sys.executable, '-S', '-m', 'verification.relay_r2b.replay',
                                 '--ir', str(root / 'semantic.json'), '--cut', 'forward.read',
                                 '--witness', str(root / 'checks/results.json')], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['replayed'])

    def test_artifact_hashes_and_smt_replay(self):
        root = self.root / 'run'
        for path, digest in self.report['artifacts'].items():
            self.assertEqual(hashlib.sha256((root / path).read_bytes()).hexdigest(), digest)
        for path in (root / 'original/checks').rglob('*.smt2'):
            solver = z3.Solver(); solver.set(timeout=10000); solver.from_file(str(path))
            self.assertEqual(solver.check(), z3.unsat, path)

    def test_claim_boundaries(self):
        self.assertTrue(self.report['conditional_ir_byte_binding_verified'])
        for key in ('whole_program_verified', 'event_loop_verified', 'runtime_verified', 'llvm_verified', 'end_to_end_verified', 'proof_certificate'):
            self.assertIs(self.report[key], False)

    def concrete_case(self, name, direction, count, outcome=0, connected=True, alive=True, slot=7):
        pair = dict(client=('Some','client'), upstream=('Some','upstream'), connected=connected,
                    forward=(0,0,False,False), reverse=(0,0,False,False))
        side = name.split('.')[0]; pair[side] = direction
        inp = dict(pair=pair, slot=slot, count=count, outcome=outcome, alive=alive,
                   client='client', upstream='upstream', reactor='reactor', failure=0,
                   client_ready=0xFFFFFFFF, upstream_ready=0xFFFFFFFF, data=[(17*i)%256 for i in range(count)])
        B = [(i*13)%256 for i in range(32768)]; base=4096*slot+(2048 if side=='reverse' else 0)
        h,t,_,_=direction; before=dict(B=B,W=[99],R=[99]+B[base+h:base+t])
        f = Fragment(self.module,name); result=run(self.module,f,inp,before)
        self.assertEqual(result['outcome'],'Return')
        self.assertEqual(violations(f,inp,before,result),[],(name,result))
        return inp,before,result

    def test_last_pair_both_directions_and_partial_write(self):
        for side in ('forward','reverse'):
            _,before,result=self.concrete_case(side+'.read',(0,2047,False,False),1)
            self.assertEqual(len(result['memory']['R']),len(before['R'])+1)
            _,before,result=self.concrete_case(side+'.write',(3,9,False,False),2)
            self.assertEqual(result['pair'][side],(5,9,False,False))
            self.assertEqual(result['memory']['B'],before['B'])

    def test_full_queue_does_not_read(self):
        for side in ('forward','reverse'):
            _,before,result=self.concrete_case(side+'.read',(0,2048,False,False),0,1)
            self.assertIsNone(result['memory']['call']);self.assertEqual(result['memory']['B'],before['B'])

    def test_eof_does_not_discard_queue_or_send_early_fin(self):
        for side in ('forward','reverse'):
            _,before,result=self.concrete_case(side+'.read',(1,4,False,False),0)
            self.assertEqual(result['pair'][side],(1,4,True,False))
            self.assertEqual(result['memory']['B'],before['B'])
            _,_,result=self.concrete_case(side+'.fin',(1,4,True,False),0)
            self.assertIsNone(result['memory']['call'])
            _,_,result=self.concrete_case(side+'.fin',(0,0,True,False),0)
            self.assertTrue(result['pair'][side][3])

    def test_wouldblock_and_interrupted_leave_bytes_and_coords(self):
        for outcome in (1,2):
            for side in ('forward','reverse'):
                for operation in ('read','write'):
                    _,before,result=self.concrete_case(side+'.'+operation,(1,4,False,False),0,outcome)
                    self.assertEqual(result['memory']['B'],before['B'])
                    self.assertEqual(result['pair'][side],(1,4,False,False))

    def test_terminal_error_stops_direction(self):
        _,_,result=self.concrete_case('forward.read',(0,0,False,False),0,3)
        self.assertFalse(result['alive']);self.assertTrue(result['memory']['fatal'])

    def test_connection_gates(self):
        _,_,result=self.concrete_case('forward.read',(0,0,False,False),1,connected=False)
        self.assertIsNotNone(result['memory']['call'])
        for name in ('reverse.read','forward.write','reverse.write'):
            _,_,result=self.concrete_case(name,(0,1,False,False),0,1,connected=False)
            self.assertIsNone(result['memory']['call'])

    def test_unbounded_history_and_nonvacuous_success(self):
        for name in ('forward.read','reverse.write'):
            values,mem,pre,context=inputs(name)
            solver=z3.Solver();solver.add(pre,context['enabled'],values['outcome']==0,values['count']==1,mem.wlen>2**40)
            self.assertEqual(solver.check(),z3.sat)
            clauses=[]
            for path,kind,pair,alive,after in Executor(self.module,Fragment(self.module,name),values).execute(mem):
                if kind=='Return' and not after.fatal:
                    clauses.append(z3.And(path,z3.Not(properties(values,mem,context,pair,alive,after)['byte_conservation'])))
            solver.add(z3.Or(*clauses));self.assertEqual(solver.check(),z3.unsat)

    def test_unsupported_instruction_unknown(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        next(o for o in f.blocks['b101']['operations'] if o['op']=='mul')['op']='unknown.compute'
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_changed_cut_boundary_unknown(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        f.blocks['b91']['operations'][0]['op']='copy'
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_loop_inside_cut_unknown(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        f.blocks['b102']['terminator']={'op':'jump','args':['b91']}
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_extra_io_inside_cut_unknown(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        o=copy.deepcopy(next(o for o in f.blocks['b101']['operations'] if o['callee']=='net.reactor_read'))
        o['result']='extra_call';f.blocks['b101']['operations'].append(o)
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_unknown_livein_rejected(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        next(o for o in f.blocks['b101']['operations'] if o['op']=='mul')['args'][0]='not_in_manifest'
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_duplicate_ssa_unknown(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        f.blocks['b101']['operations'].append(copy.deepcopy(f.blocks['b101']['operations'][0]))
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_additional_entry_parameter_not_silently_seeded(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        extra=copy.deepcopy(f.blocks['b91']['operations'][-1]);extra['result']='unexpected_parameter'
        f.blocks['b91']['operations'].append(extra)
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_io_outside_declared_cuts_makes_run_unknown(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        extra=copy.deepcopy(next(o for o in f.blocks['b101']['operations'] if o['callee']=='net.reactor_read'))
        extra['result']='uncovered_io';f.blocks['b0']['operations'].append(extra)
        with patch('verification.relay_r2b.check.compile_source',return_value=m):
            report=check(self.root/'uncovered')
        self.assertEqual(report['status'],'incomplete')
        self.assertEqual(report['obligations'][0]['status'],'unknown')
        self.assertIn('uncovered',report['obligations'][0]['reason'])

    def test_overflow_policy_not_assumed(self):
        m=copy.deepcopy(self.module);f=Fragment(m,'forward.read')
        next(o for o in f.blocks['b101']['operations'] if o['op']=='mul')['overflow']='wrap'
        self.assertEqual(self.query(m)[0]['status'],'unknown')

    def test_timeout_is_unknown(self):
        with patch('z3.Solver.check',return_value=z3.unknown),patch('z3.Solver.reason_unknown',return_value='test timeout'):
            rows=self.query(self.module)
        self.assertTrue(all(r['status']=='unknown' for r in rows))

    def test_nonreproduced_witness_is_unknown(self):
        root=self.root/'run/mutations/read_wrong_half'
        m=json.loads((root/'semantic.json').read_text())
        with patch('verification.relay_r2b.check.replay_witness',return_value={'confirmed':False}):
            rows=analyze(m,'forward.read',self.root/'bad-replay',negative=('other_directions_unchanged',0))
        self.assertEqual(rows[0]['status'],'unknown')

    def test_summaries_do_not_establish_helper_behavior(self):
        m=copy.deepcopy(self.module)
        for f in m['functions']:
            f['may_trap']=False;f['storage_contract']={'incorrect':'ignored'}
        self.assertTrue(all(r['status']=='proved' for r in self.query(m)))

    def test_bad_timeout_and_output_rejected(self):
        with self.assertRaisesRegex(ValueError,'timeout'):check(self.root/'bad',0)
        with self.assertRaisesRegex(ValueError,'empty'):check(self.root/'run')


if __name__=='__main__':unittest.main()
