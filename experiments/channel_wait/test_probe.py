import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class WaitProbe(unittest.TestCase):
    def test_native(self):
        with tempfile.TemporaryDirectory(prefix='liza-wait-') as tmp:
            exe=Path(tmp)/('wait.exe' if sys.platform=='win32' else 'wait')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'wait.c'),str(HERE/'test_wait.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            built=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            for _ in range(3):
                run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                self.assertIn('wait probe passed',run.stdout)
    def test_lost_notification_negative_control(self):
        with tempfile.TemporaryDirectory(prefix='liza-wait-') as tmp:
            exe=Path(tmp)/('broken.exe' if sys.platform=='win32' else 'broken')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DWAIT_TEST_SKIP_NOTIFY',str(HERE/'wait.c'),str(HERE/'test_wait.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            built=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
            self.assertNotEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('sender_state.result==W_OK',run.stderr)

    def test_extended_deadline_negative_control(self):
        with tempfile.TemporaryDirectory(prefix='liza-wait-') as tmp:
            exe=Path(tmp)/('broken.exe' if sys.platform=='win32' else 'broken')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DWAIT_TEST_RESTART_DEADLINE',str(HERE/'wait.c'),str(HERE/'test_wait.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            built=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
            self.assertNotEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('deadline_changes==0',run.stderr)

if __name__=='__main__':unittest.main()
