import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class NotificationRefinement(unittest.TestCase):
    @unittest.skipUnless(shutil.which('clang'), 'Clang required')
    def test_schedules_and_negative_controls(self):
        with tempfile.TemporaryDirectory(prefix='liza-notify-refine-') as tmp:
            exe = Path(tmp) / ('probe.exe' if sys.platform == 'win32' else 'probe')
            command = ['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-I', str(ROOT / 'liza/runtime'), str(HERE / 'probe.c'),
                       str(ROOT / 'liza/runtime/scoped_channel_core.c'), '-o', str(exe)]
            command += ['-lws2_32'] if sys.platform == 'win32' else ['-pthread']
            built = subprocess.run(command, text=True, capture_output=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            for _ in range(3):
                run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=20)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                for expected in ('scenario=0 mutation=0 result=0', 'scenario=1 mutation=0 result=0',
                                 'scenario=2 mutation=0 result=0 fault_observed=1',
                                 'scenario=0 mutation=1 result=1', 'scenario=1 mutation=2 result=1'):
                    self.assertIn(expected, run.stdout)


if __name__ == '__main__':
    unittest.main()
