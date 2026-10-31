import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ReactorWakeupProbe(unittest.TestCase):
    def test_pollable_wakeup_and_network_readiness(self):
        with tempfile.TemporaryDirectory(prefix='liza-wakeup-') as tmp:
            exe=Path(tmp)/('probe.exe' if sys.platform=='win32' else 'probe')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'liza/runtime'),str(HERE/'probe.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
            cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
            b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(b.returncode,0,b.stdout+b.stderr)
            for _ in range(3):
                r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=40)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                self.assertIn('mode=socket preposted=1 received=256 network=1',r.stdout)
                self.assertIn('mode=socket preposted=0 received=256 network=1',r.stdout)
                if sys.platform=='linux':self.assertIn('mode=eventfd preposted=0 received=256 network=1',r.stdout)
    def test_lost_or_failed_notification_is_not_silent(self):
        with tempfile.TemporaryDirectory(prefix='liza-wakeup-') as tmp:
            exe=Path(tmp)/('probe.exe' if sys.platform=='win32' else 'probe')
            for flag in ('WAKE_TEST_DROP_NOTIFICATION','WAKE_TEST_FAIL_NOTIFICATION'):
                with self.subTest(flag=flag):
                    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-D'+flag,'-I',str(ROOT/'liza/runtime'),str(HERE/'probe.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
                    cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
                    b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
                    self.assertEqual(b.returncode,0,b.stdout+b.stderr)
                    r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=25)
                    self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
                    self.assertIn('probe failed',r.stderr)

if __name__=='__main__':unittest.main()
