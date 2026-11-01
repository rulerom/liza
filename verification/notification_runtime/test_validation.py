import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from check import check

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

class RuntimeValidation(unittest.TestCase):
    @unittest.skipUnless(shutil.which('clang'), 'Clang required')
    def test_boundaries_and_mutations(self):
        source=(ROOT/'experiments/notification_protocol/protocol.h').read_text()
        mutations={
            'missing_token': ('p->inject_failure||!wake_send(&p->wake)', 'p->inject_failure'),
            'skip_inspect': ('liza_scoped_status s=liza_scoped_receive(p->fifo,value);', 'liza_scoped_status s=CH_EMPTY;'),
            'clear_pending': ('p->pending=1;return 1;', 'p->pending=0;return 1;'),
            'hidden_fault': ('{p->fault=1;return 0;}', '{return 0;}'),
        }
        with tempfile.TemporaryDirectory(prefix='liza-notification-validation-') as tmp:
            tmp=Path(tmp)
            for name, replacement in [('baseline',None),*mutations.items()]:
                with self.subTest(name=name):
                    modified=source
                    if replacement:
                        old,new=replacement
                        self.assertEqual(source.count(old),1)
                        modified=source.replace(old,new)
                    (tmp/'protocol.h').write_text(modified)
                    exe=tmp/('trace.exe' if sys.platform=='win32' else 'trace')
                    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',
                         '-I',str(tmp),'-I',str(ROOT),'-I',str(ROOT/'liza/runtime'),
                         str(HERE/'trace.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
                    cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
                    built=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
                    self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                    run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=30)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                    if name=='baseline': check(run.stdout)
                    else:
                        with self.assertRaises(AssertionError) as caught: check(run.stdout)
                        print(name, str(caught.exception))

if __name__=='__main__': unittest.main()
