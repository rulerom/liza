import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ChannelProbe(unittest.TestCase):
    def test_native(self):
        with tempfile.TemporaryDirectory(prefix='liza-channel-') as tmp:
            exe=Path(tmp)/('probe.exe' if sys.platform=='win32' else 'probe')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'channel.c'),str(HERE/'test_channel.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(b.returncode,0,b.stdout+b.stderr)
            r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('channel probe passed',r.stdout)
    def test_instrumented_probe(self):
        with tempfile.TemporaryDirectory(prefix='liza-channel-') as tmp:
            exe=Path(tmp)/('measured.exe' if sys.platform=='win32' else 'measured')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DCH_MEASURE',str(HERE/'channel.c'),str(HERE/'test_channel.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(b.returncode,0,b.stdout+b.stderr)
            r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertEqual(sum(line.startswith('capacity=') for line in r.stdout.splitlines()),4)

    def test_allocation_failure_and_negative_control(self):
        with tempfile.TemporaryDirectory(prefix='liza-channel-') as tmp:
            tmp=Path(tmp);exe=tmp/('probe.exe' if sys.platform=='win32' else 'probe')
            fail=tmp/'alloc.c'
            fail.write_text('#include "channel.h"\n#include <stdint.h>\nint main(void){channel *c=0;size_t b=7;return ch_create(1,SIZE_MAX,&c,&b)==CH_NOMEM && !c && b==0 ? 0 : 1;}\n')
            for flag,source,expected in [('CH_TEST_FAIL_ALLOC',fail,0),('CH_TEST_BREAK_FULL',HERE/'test_channel.c',1)]:
                with self.subTest(flag=flag):
                    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(HERE),'-D'+flag,str(HERE/'channel.c'),str(source),'-o',str(exe)]
                    if sys.platform!='win32':cmd.append('-pthread')
                    b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
                    self.assertEqual(b.returncode,0,b.stdout+b.stderr)
                    r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=60)
                    self.assertEqual(r.returncode,expected,r.stdout+r.stderr)

if __name__=='__main__':unittest.main()
