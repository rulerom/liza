"""Exercise bounded RTP recipient state through the real compiler at O0/O2."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/apps/rtp_receivers.liza'

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class ReceiverNative(unittest.TestCase):
    def test_capacity_reuse_addresses_and_snapshots(self):
        with tempfile.TemporaryDirectory(prefix='liza-rtp-receivers-') as tmp:
            for opt in ('0', '2'):
                with self.subTest(opt=opt):
                    exe = Path(tmp) / ('receivers-' + opt + ('.exe' if sys.platform == 'win32' else ''))
                    build = subprocess.run([sys.executable, '-m', 'liza', 'build', str(EXAMPLE),
                                            '-O', opt, '-o', str(exe)], cwd=ROOT,
                                           text=True, capture_output=True, timeout=60)
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                    run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=10)
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

if __name__ == '__main__':
    unittest.main()
