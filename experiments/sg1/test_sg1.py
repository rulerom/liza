import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def build(tmp, mutation=None):
    exe=Path(tmp)/('probe.exe' if sys.platform=='win32' else 'probe')
    command=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'liza/runtime'),
             str(HERE/'probe.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
    if mutation:command+=['-D'+mutation]
    command+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if result.returncode:raise AssertionError(result.stdout+result.stderr)
    return exe

def events(output):
    rows=[line.split() for line in output.splitlines() if line and line[0].isdigit()]
    assert [int(r[0]) for r in rows]==list(range(len(rows))), rows
    return [r[1] for r in rows]

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class SG1(unittest.TestCase):
    def test_scenarios(self):
        with tempfile.TemporaryDirectory(prefix='liza-sg1-') as tmp:
            exe=build(tmp)
            for scenario in ('normal','idle','fault','mutex_stall','supervisor_stall','startup_fail','startup_fail_first','stale_idle','admission_race','snapshot_stall','snapshot','abort','network','simultaneous'):
                with self.subTest(scenario=scenario):
                    run=subprocess.run([str(exe),scenario],capture_output=True,text=True,timeout=12)
                    self.assertEqual(run.returncode,86 if scenario=='abort' else 0,run.stdout+run.stderr)
                    if scenario=='snapshot':
                        self.assertIn('snapshot_consistent',run.stdout);continue
                    metrics=[line for line in run.stdout.splitlines() if line.startswith('metrics ')]
                    if metrics:
                        print(scenario,metrics[0],flush=True)
                        values=dict(item.split('=') for item in metrics[0].split()[1:])
                        if scenario=='idle':
                            self.assertGreaterEqual(int(values['wall_ms']),750)
                            self.assertEqual(int(values['poll_calls']),1)
                            self.assertEqual(int(values['poll_returns']),1)
                            self.assertGreaterEqual(float(values['worker_cpu_ms']),0)
                    log=events(run.stdout)
                    if scenario=='abort':
                        self.assertIn('unresponsive',log);self.assertIn('process_abort',log)
                        self.assertNotIn('destroy',log);self.assertNotIn('stopped',log);continue
                    self.assertEqual(log.count('destroy'),1)
                    if scenario!='startup_fail_first':
                        self.assertLess(log.index('worker_exit'),log.index('worker_join'))
                        self.assertLess(log.index('worker_join'),log.index('stopped'))
                    if scenario not in ('startup_fail','startup_fail_first'):
                        self.assertLess(log.index('network_close'),log.index('worker_exit'))
                        self.assertLess(log.index('supervisor_exit'),log.index('supervisor_join'))
                        self.assertLess(log.index('worker_join'),log.index('supervisor_join'))
                        self.assertLess(log.index('supervisor_join'),log.index('stopped'))
                    self.assertLess(log.index('stopped'),log.index('destroy'))
                    if scenario in ('mutex_stall','supervisor_stall','stale_idle','snapshot_stall'):
                        self.assertLess(log.index('unresponsive'),log.index('retained'))
                        self.assertLess(log.index('retained'),log.index('supervisor_join'))
                    if scenario in ('normal','idle','network','simultaneous'):self.assertNotIn('unresponsive',log)
                    if scenario=='admission_race':
                        self.assertLess(log.index('producer_exit'),log.index('producer_join'))
                        self.assertLess(log.index('producer_join'),log.index('worker_join'))
                    if scenario=='fault':self.assertLess(log.index('faulted'),log.index('stopping'))

    def test_negative_controls(self):
        with tempfile.TemporaryDirectory(prefix='liza-sg1-negative-') as tmp:
            for mutation,scenario,diagnostic in (
                ('SG1_DROP_SHUTDOWN','idle','!saw_unresponsive'),
                ('SG1_SKIP_RECHECK','simultaneous','!saw_unresponsive'),
                ('SG_BROKEN_RELEASE','mutex_stall','!release_allowed(state)'),
            ):
                with self.subTest(mutation=mutation):
                    exe=build(tmp,mutation)
                    run=subprocess.run([str(exe),scenario],capture_output=True,text=True,timeout=12)
                    self.assertEqual(run.returncode,2,run.stdout+run.stderr)
                    self.assertIn(diagnostic,run.stderr)

if __name__=='__main__':unittest.main()
