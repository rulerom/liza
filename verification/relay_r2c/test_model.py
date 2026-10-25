import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import z3

from .check import check,Checks,accepted,empty
from .mutations import MUTATIONS
from .replay import run
from .semantic import Executor,Unsupported


class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-r2c-');cls.root=Path(cls.temp.name)
        cls.output=cls.root/'evidence';cls.report=check(cls.output)
        cls.module=json.loads((cls.output/'program/semantic.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_complete_inductive_matrix(self):
        self.assertEqual(self.report['status'],'passed',self.report.get('reason'))
        self.assertEqual(len(self.report['obligations']),290)
        self.assertTrue(all(r['status']=='proved' for r in self.report['obligations']))
        self.assertTrue(self.report['conditional_inductive_pair_verified'])

    def test_scope_never_claims_whole_server_or_binary(self):
        for key in ('whole_program_verified','event_loop_verified','liveness_verified','runtime_verified','llvm_verified','end_to_end_verified','proof_certificate'):
            self.assertFalse(self.report[key])
        self.assertTrue(self.report['assumptions']);self.assertTrue(self.report['exclusions'])

    def test_all_source_mutations_have_symbolic_failure_and_real_trace(self):
        self.assertEqual({c['name'] for c in self.report['controls']},set(MUTATIONS))
        for name in MUTATIONS:
            result=json.loads((self.output/'mutations'/name/'results.json').read_text())
            self.assertEqual(result['status'],'confirmed',name)
            self.assertTrue(result['failed_obligations']);self.assertTrue(result['concrete_witness']['confirmed'])
            self.assertTrue(result['concrete_witness']['trace'])

    def test_standalone_replay_without_z3(self):
        for name in ('one_fin_closes_pair','lost_persistence','retained_closed_pair'):
            target=self.root/(name+'.json')
            result=subprocess.run([sys.executable,'-S','-m','verification.relay_r2c.replay','--ir',str(self.output/'mutations'/name/'semantic.json'),'--output',str(target)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(target.read_text())['confirmed'])

    def test_actual_unmodified_ir_reuses_slot_for_two_epochs(self):
        result=run(self.module)
        self.assertFalse(result['confirmed']);self.assertEqual(result['completed_epochs'],2)

    def test_hashes_and_source_snapshot(self):
        for name,digest in self.report['artifacts'].items():
            self.assertEqual(hashlib.sha256((self.output/name).read_bytes()).hexdigest(),digest,name)
        root=Path(__file__).resolve().parents[2]
        self.assertEqual((root/'examples/apps/liza_proxy.liza').read_bytes(),(self.output/'program/source/liza_proxy.liza').read_bytes())

    def test_missing_or_unknown_obligation_cannot_pass(self):
        negative=[json.loads((self.output/'mutations'/name/'results.json').read_text()) for name in MUTATIONS]
        self.assertTrue(accepted(self.report['obligations'],negative,True))
        self.assertFalse(accepted(self.report['obligations'][:-1],negative,True))
        renamed=copy.deepcopy(self.report['obligations']);renamed[0]['obligation']='unrelated_proof'
        self.assertFalse(accepted(renamed,negative,True))
        rows=copy.deepcopy(self.report['obligations']);rows[0]['status']='unknown'
        self.assertFalse(accepted(rows,negative,True))
        self.assertFalse(accepted(self.report['obligations'],negative,False))
        negative[0]['concrete_witness']['confirmed']=False
        self.assertFalse(accepted(self.report['obligations'],negative,True))

    def test_unsupported_instruction_fails_closed(self):
        module=copy.deepcopy(self.module)
        f=next(f for f in module['functions'] if f['name']=='liza_proxy.exchange')
        f['blocks'][0]['operations'][0]['op']='invented.memory_write'
        with self.assertRaises(Unsupported):
            Executor(module).execute('liza_proxy.exchange','b0',None,dict(p1='buffer'),{},stop_operation='v6')

    def test_changed_unproved_boundary_is_unknown(self):
        module=copy.deepcopy(self.module)
        f=next(f for f in module['functions'] if f['name']=='liza_proxy.exchange')
        b=next(b for b in f['blocks'] if b['name']=='b15');b['operations'][0]['op']='unknown.cleanup'
        checker=Checks(module,self.root/'boundary')
        checker.visited={tuple(x) for x in self.report['visited']}
        with self.assertRaises(Unsupported):checker.composition()

    def test_bad_phi_predecessor_rejected(self):
        with self.assertRaises(Unsupported):
            Executor(self.module).execute('liza_proxy.exchange','b13','b14',{}, {},previous='not_a_predecessor')

    def test_summaries_do_not_define_empty_pair(self):
        module=copy.deepcopy(self.module)
        for function in module['functions']:
            function['storage_contract']={'returns':{'depends_on':['made_up']}}
            for block in function['blocks']:
                for op in block['operations']:op['may_trap']=True
        ex=Executor(module)
        outputs=ex.helper('liza_proxy.empty_pair',[])
        self.assertEqual(len(outputs),1)
        from .semantic import equal
        self.assertTrue(z3.is_true(z3.simplify(equal(outputs[0][2],empty()))))

    def test_runtime_success_and_error_do_not_share_mutable_ghost(self):
        ex=Executor(self.module)
        ghost=dict(live={'client'},closed=[],upstream='upstream',connected=z3.BoolVal(True),failed=z3.BoolVal(False),epoch=z3.IntVal(1))
        outcomes=list(ex.runtime('net.reactor_interest',['reactor','client',z3.IntVal(1)],ghost,z3.BoolVal(True)))
        self.assertTrue(z3.is_false(outcomes[0][2]['failed']))
        self.assertTrue(z3.is_true(outcomes[1][2]['failed']))
        self.assertTrue(z3.is_false(ghost['failed']))

    def test_output_and_timeout_validation(self):
        with self.assertRaises(ValueError):check(self.output)
        with self.assertRaises(ValueError):check(self.root/'bad',0)

    def test_replay_budget_is_not_proof(self):
        with self.assertRaises(ValueError):run(self.module,budget=1)
