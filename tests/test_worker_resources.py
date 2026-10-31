"""Real worker-local regions/reactors and fail-closed runtime call graph."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def liza(*args):
    return subprocess.run([sys.executable,'-m','liza',*map(str,args)],cwd=ROOT,text=True,capture_output=True,timeout=60)

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class WorkerResources(unittest.TestCase):
    def test_regions_and_reactors(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('resources.exe' if sys.platform=='win32' else 'resources')
            for opt in ('0','2'):
                b=liza('build',ROOT/'examples/workers/worker_reactor.liza','-O',opt,'-o',exe)
                self.assertEqual(b.returncode,0,b.stdout+b.stderr)
                for _ in range(10):
                    r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=20)
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_concurrent_reactor_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('identity.exe' if sys.platform=='win32' else 'identity')
            suffix='windows' if sys.platform=='win32' else 'posix'
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'liza/runtime'),
                 str(ROOT/'tests/fixtures/worker_reactor_identity.c'),str(ROOT/f'liza/runtime/net_{suffix}.c'),
                 str(ROOT/f'liza/runtime/workers_{suffix}.c'),'-o',str(exe)]
            cmd += ['-lws2_32'] if sys.platform=='win32' else ['-pthread']
            built=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_exhaustion_after_bind_closes_once_and_reports_close_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('exhaustion.exe' if sys.platform=='win32' else 'exhaustion')
            suffix='windows' if sys.platform=='win32' else 'posix'
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'liza/runtime'),
                 str(ROOT/'tests/fixtures/worker_reactor_exhaustion.c'),str(ROOT/f'liza/runtime/net_{suffix}.c'),'-o',str(exe)]
            cmd += ['-lws2_32'] if sys.platform=='win32' else ['-pthread']
            built=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_imported_generic_does_not_bypass_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'helper.liza').write_text('pub fn call<T>(x:T)->u32:io {\n match console.println("x") {Ok(n)=>{return 0} Err(e)=>{return 1}}\n}\n')
            (root/'main.liza').write_text('import helper\nfn worker(id:u32)->u32:io {return helper.call<u32>(id)}\nfn main()->u32:io {\n x=workers.run(2)\n return 0\n}\n')
            r=liza('check',root/'main.liza')
            self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('worker cannot call unaudited external',r.stderr)
            (root/'helper.liza').write_text('pub fn call<T>(x:T)->u32 {return 7}\n')
            r=liza('check',root/'main.liza')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_rejects_unaudited_calls_transitively(self):
        examples=[
            'fn helper()->u32:io {match console.println("x") {Ok(n)=>{return 0} Err(e)=>{return 1}}}',
            'fn helper()->u32:io {r=workers.run(1)\n return 0}',
            '''fn helper()->u32:io,alloc {
              match net.reactor_create(0,1) {
                Err(e)=>{return 0}
                Ok(r)=>{
                  a=net.reactor_watch_shutdown(r)
                  b=net.reactor_close(move r)
                  return 0
                }
              }
            }''',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'example.liza'
            for helper in examples:
                with self.subTest(helper=helper):
                    src.write_text(helper+'\nfn worker(id:u32)->u32:io,alloc {return helper()}\nfn main()->u32:io {\n x=workers.run(2)\n return 0\n}\n')
                    result=liza('check',src)
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertIn('worker cannot call unaudited external',result.stderr)
if __name__=='__main__':unittest.main()
