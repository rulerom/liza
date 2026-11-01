import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class RuntimeTrace(unittest.TestCase):
    @unittest.skipUnless(shutil.which('clang'), 'Clang required')
    def test_selected_fifo_schedules(self):
        with tempfile.TemporaryDirectory(prefix='liza-notification-') as tmp:
            exe = Path(tmp) / ('trace.exe' if sys.platform == 'win32' else 'trace')
            cmd = ['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                   '-I', str(ROOT / 'liza/runtime'), str(HERE / 'trace.c'),
                   str(ROOT / 'liza/runtime/scoped_channel_core.c'), '-o', str(exe)]
            cmd += ['-lws2_32'] if sys.platform == 'win32' else ['-pthread']
            built = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            result = subprocess.run([str(exe)], text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
