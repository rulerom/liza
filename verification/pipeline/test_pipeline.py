import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from . import runner
from .artifacts import digest, inside
from .reports import validate, observations


def arithmetic_report():
    return {'success':True,
            'results':[{'subject':str(i),'stage':str(j),'status':'proved'} for i in range(10) for j in range(4)],
            'negative_controls':[{'mutation':str(i),'status':'counterexample'} for i in range(8)],
            'unsupported_control':{'status':'unknown'}}


class ReportTests(unittest.TestCase):
    def test_empty_success_is_not_evidence(self):
        for stage in runner.STAGES:
            self.assertEqual(validate(stage,{'success':True,'status':'verified'})['status'],'failed')

    def test_expected_unsupported_control_does_not_verify_a_subject(self):
        raw=arithmetic_report()
        self.assertEqual(validate('v0',raw)['status'],'passed')
        seen=observations(raw,'v0')
        self.assertTrue(any(x['role']=='unsupported_control' and x['category']=='unknown' for x in seen))
        raw['results'][0]['status']='unknown'
        self.assertEqual(validate('v0',raw)['status'],'failed')

    def test_duplicate_obligations_cannot_fill_coverage(self):
        raw=arithmetic_report();raw['results'][1]=copy.deepcopy(raw['results'][0])
        self.assertEqual(validate('v0',raw)['status'],'failed')

    def test_missing_control_rejected(self):
        raw=arithmetic_report();raw['negative_controls'].pop()
        self.assertEqual(validate('v0',raw)['status'],'failed')

    def test_abstract_counterexample_is_not_confirmed_defect(self):
        raw={'status':'unknown','results':[{'status':'counterexample_to_obligation'}]}
        seen=observations(raw,'v2')
        self.assertTrue(any(r['category']=='inconclusive_obligation_failure' for r in seen))
        self.assertFalse(any(r['category']=='confirmed_model_violation' for r in seen))

    def test_concrete_replay_and_summary_failure_have_distinct_categories(self):
        raw={'results':{'lose_phi_dependency':{'status':'model_violation','traces':[{'reproduced':True}]},
                        'summary_wrong_parameter':{'status':'summary_failure','concrete_status':'summary_failure'}}}
        seen=observations(raw,'v4')
        self.assertEqual({r['category'] for r in seen},{'confirmed_model_violation','confirmed_return_contract_failure'})
        self.assertEqual({r['role'] for r in seen},{'negative_control','summary_control'})

    def test_unsuitable_is_preserved(self):
        self.assertEqual(observations({'status':'unsuitable'},'v3')[0]['category'],'unsuitable')

    def test_partial_selection_never_becomes_full_success(self):
        stages={s:{'status':'not_selected'} for s in runner.STAGES}
        stages['v4']={'status':'passed'}
        self.assertEqual(runner.aggregate(stages),'partial')
        stages['v3']={'status':'unknown'}
        self.assertEqual(runner.aggregate(stages),'incomplete')


class RunnerTests(unittest.TestCase):
    def test_timeout_is_unknown_execution_and_keeps_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            r=runner.execute([sys.executable,'-c','import time;time.sleep(10)'],root,root/'logs',0.05)
            self.assertIsNone(r['returncode'])
            self.assertEqual(r['error'],'stage timeout')
            self.assertTrue((root/'logs/stderr.log').exists())

    def test_missing_executable_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            r=runner.execute([str(root/'missing')],root,root/'logs',1)
            self.assertIsNone(r['returncode']);self.assertIn('error',r)

    def test_zero_exit_without_report_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=runner.parser().parse_args(['--output',str(Path(tmp)/'bundle'),'--stages','v4'])
            with patch.object(runner,'commands',return_value=[sys.executable,'-c','pass']):
                report=runner.run(args)
            self.assertEqual(report['status'],'incomplete')
            self.assertEqual(report['stages']['v4']['status'],'unknown')

    def test_new_output_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'report.json').write_text('{}')
            args=runner.parser().parse_args(['--output',tmp,'--stages','v4'])
            with self.assertRaisesRegex(ValueError,'new or empty'):runner.run(args)

    def test_missing_alive2_does_not_skip_v3(self):
        args=runner.parser().parse_args(['--output','unused'])
        with self.assertRaisesRegex(ValueError,'not skipped'):
            runner.commands(args,Path('/snapshot'),'v3',Path('/output'))

    def test_artifact_tamper_and_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);artifact=root/'a.ll';artifact.write_text('before')
            expected=runner.sha(artifact);artifact.write_text('after')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):digest(root,'a.ll',expected)
            with self.assertRaisesRegex(ValueError,'escapes'):inside(root,'../outside')

    def test_actual_v4_bundle_partial_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'bundle'
            code=runner.main(['--output',str(root),'--stages','v4'])
            self.assertEqual(code,2)
            report=json.loads((root/'report.json').read_text())
            self.assertEqual(report['status'],'partial')
            self.assertTrue(report['source_unchanged'])
            self.assertTrue(report['stages']['v4']['declared_artifacts_verified'])
            self.assertEqual(runner.verify_bundle(root),'partial')
            (root/'stages/v4/artifacts/safe/semantic-ir.json').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'integrity mismatch'):runner.verify_bundle(root)


if __name__=='__main__':unittest.main()
