import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class SG2(unittest.TestCase):
    def test_runner(self):
        with tempfile.TemporaryDirectory(prefix='liza-sg2-') as tmp:
            exe=Path(tmp)/('runner.exe' if sys.platform=='win32' else 'runner')
            platform='windows' if sys.platform=='win32' else 'posix'
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DLIZA_SG2_TESTING',
                 '-I',str(ROOT/'liza/runtime'),str(ROOT/'tests/native/sg2_runner.c'),
                 str(ROOT/f'liza/runtime/sg2_{platform}.c'),str(ROOT/f'liza/runtime/net_{platform}.c'),
                 str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
            cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
            build=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            def run(*args,code=0):
                r=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=20)
                self.assertEqual(r.returncode,code,r.stdout+r.stderr)
                return r.stdout
            normal=run('normal');steps=json.loads(normal)['startup_steps']
            for n in range(1,steps+1):
                with self.subTest(startup=n):run('startup',str(n))
            for case in ('idle','long_running','fault','nested','budget','stack_overflow','handles','process_budget','reactor_budget','reuse','rollback_reuse'):
                with self.subTest(case=case):
                    output=run(case)
                    if case=='reuse':self.assertEqual(len(output.splitlines()),100)
            for case in ('double_fault','worker_stall','handback','stale','supervisor_stall'):
                with self.subTest(case=case):
                    output=run(case,code=86)
                    self.assertIn('process_abort no-cleanup',output)
                    self.assertNotIn('"phase":"destroyed"',output)
            for macro,case,code,diagnostic in (
                ('SG2_BREAK_EARLY_RELEASE','worker_stall',86,'release_rejected'),
                ('SG2_BREAK_EARLY_REUSE','handback',2,'destroy_count'),
                ('SG2_BREAK_RECEIPT_ORDER','normal',2,'oracle_joins'),
                ('SG2_BREAK_ROLLBACK','normal',2,'group_managed_bytes_live'),
            ):
                mutated=subprocess.run(cmd+['-D'+macro],capture_output=True,text=True,timeout=30)
                self.assertEqual(mutated.returncode,0,mutated.stderr)
                r=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=10)
                self.assertEqual(r.returncode,code,r.stdout+r.stderr)
                self.assertIn(diagnostic,r.stdout+r.stderr)
            print(f'SG2: {steps} startup fault boundaries, 100 groups, ownership and escalation passed')
