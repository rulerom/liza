import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mt0_build',HERE/'build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class Workers(unittest.TestCase):
    def test_parallel_and_failed_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            for opt in ('0','2'):
                exe=Path(tmp)/('workers'+('.exe' if sys.platform=='win32' else ''))
                build.build(exe,opt)
                for n in (1,2,4,8):
                    with self.subTest(opt=opt,workers=n):
                        p=subprocess.run([str(exe),str(n),'-1'],capture_output=True,text=True,timeout=15)
                        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
                        self.assertEqual(p.stdout.strip(),f'started={n} ran={n}')
                        for fail in range(n):
                            p=subprocess.run([str(exe),str(n),str(fail)],capture_output=True,text=True,timeout=15)
                            self.assertEqual(p.returncode,3,p.stderr+p.stdout)
                            self.assertEqual(p.stdout.strip(),f'started={fail} ran=0')
                for args in (('0','-1'),('9','-1'),('2','2'),('','-1'),('2','')):
                    p=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=15)
                    self.assertEqual(p.returncode,2)
if __name__=='__main__':unittest.main()
