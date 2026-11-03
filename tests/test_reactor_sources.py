"""Private runtime wait sources: real TCP reactor + command/control notifications."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class ReactorSources(unittest.TestCase):
    def test_native_runtime_wait(self):
        with tempfile.TemporaryDirectory(prefix='liza-reactor-sources-') as tmp:
            exe = Path(tmp) / ('probe.exe' if sys.platform == 'win32' else 'probe')
            platform = 'windows' if sys.platform == 'win32' else 'posix'
            cmd = ['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                   '-I', str(ROOT/'liza/runtime'), str(ROOT/'tests/native/reactor_sources.c'),
                   str(ROOT/'liza/runtime'/f'net_{platform}.c'),
                   str(ROOT/'liza/runtime/scoped_channel_core.c'), '-o', str(exe)]
            cmd += ['-lws2_32'] if sys.platform == 'win32' else ['-pthread']
            built = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            for scenario in ('boundary', 'idle', 'command', 'network', 'both', 'fault'):
                with self.subTest(scenario=scenario):
                    run = subprocess.run([str(exe), scenario], capture_output=True, text=True, timeout=10)
                    self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
                    print(run.stdout.strip(), flush=True)

if __name__ == '__main__':
    unittest.main()
