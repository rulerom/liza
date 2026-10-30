"""Scoped worker entry checks and native execution at both optimization levels."""
from pathlib import Path
import shutil
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/workers/scoped.liza'

def command(*args):
    return subprocess.run([sys.executable, '-m', 'liza', *map(str,args)],
                          cwd=ROOT, text=True, capture_output=True, timeout=60)

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class Workers(unittest.TestCase):
    def test_runs_and_checks_bounds(self):
        with tempfile.TemporaryDirectory(prefix='liza-workers-') as tmp:
            for opt in ('0','2'):
                exe=Path(tmp)/('scoped'+('.exe' if sys.platform=='win32' else ''))
                built=command('build',EXAMPLE,'-O',opt,'-o',exe)
                self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            src=Path(tmp)/'bounds.liza'
            src.write_text('fn worker(id:u32)->u32 {return id}\nfn main()->u32:io {\n if workers.run(0)>>32 != 1 {return 1}\n if workers.run(9)>>32 != 1 {return 2}\n if workers.run(1) != 0 {return 3}\n if workers.run(8) != 0 {return 4}\n return 0\n}\n')
            for opt in ('0','2'):
                result=command('build',src,'-O',opt,'-o',exe)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_rejects_invalid_entry(self):
        entries=['', 'fn worker(id:u64)->u32 {return 0}',
                 'fn worker(id:u32)->u64 {return 0}',
                 'fn worker<T>(id:u32)->u32 {return 0}']
        with tempfile.TemporaryDirectory(prefix='liza-workers-') as tmp:
            src=Path(tmp)/'check.liza'
            for entry in entries:
                with self.subTest(entry=entry):
                    src.write_text(entry+'\nfn main()->u32:io {\n result=workers.run(2)\n return 0\n}\n')
                    result=command('check',src)
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertIn('workers.run requires fn worker',result.stderr)

    def test_effect_ir_and_worker_trap(self):
        with tempfile.TemporaryDirectory(prefix='liza-workers-') as tmp:
            src=Path(tmp)/'effects.liza';out=Path(tmp)/'program.exe' if sys.platform=='win32' else Path(tmp)/'program'
            src.write_text('fn worker(id:u32)->u32 {return id}\nfn main()->u32 {\n value=workers.run(2)\n return 0\n}\n')
            result=command('check',src)
            self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('io',result.stderr)
            ir=command('emit-ir',EXAMPLE)
            self.assertEqual(ir.returncode,0,ir.stdout+ir.stderr)
            self.assertEqual(json.loads(ir.stdout)['worker_entry'],'scoped.worker')
            src.write_text('fn worker(id:u32)->u32 {\n value=1/(id-id)\n return value\n}\nfn main()->u32:io {\n result=workers.run(2)\n return 0\n}\n')
            for opt in ('0','2'):
                result=command('build',src,'-O',opt,'-o',out)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                result=subprocess.run([str(out)],capture_output=True,text=True,timeout=15)
                self.assertNotEqual(result.returncode,0)

    def test_native_workers_can_overlap(self):
        with tempfile.TemporaryDirectory(prefix='liza-workers-') as tmp:
            tmp=Path(tmp);source=tmp/'overlap.c';exe=tmp/('overlap'+('.exe' if sys.platform=='win32' else ''))
            source.write_text('#include <stdint.h>\n#include <stdatomic.h>\n#include <time.h>\nstatic atomic_uint entered;\nstatic uint32_t worker(uint32_t n){(void)n;atomic_fetch_add(&entered,1);time_t end=time(0)+5;while(atomic_load(&entered)<2 && time(0)<end){}return atomic_load(&entered)==2?1:0;}\nextern uint64_t liza_rt_workers_run(uint32_t, uint32_t (*)(uint32_t));\nint main(void){uint64_t r=liza_rt_workers_run(2,worker);return r==0 && atomic_load(&entered)==2?0:1;}\n')
            runtime=ROOT/'liza/runtime'/('workers_windows.c' if sys.platform=='win32' else 'workers_posix.c')
            cmd=['clang','-std=c11','-Wall','-Wextra','-Werror',str(source),str(runtime),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            built=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_partial_start_does_not_invoke_workers(self):
        with tempfile.TemporaryDirectory(prefix='liza-workers-') as tmp:
            tmp=Path(tmp);source=tmp/'fault.c'
            source.write_text('#include <stdint.h>\n#include <stdlib.h>\nstatic uint32_t called(uint32_t n){(void)n;abort();}\nextern uint64_t liza_rt_workers_run(uint32_t, uint32_t (*)(uint32_t));\nint main(void){return liza_rt_workers_run(8,called)==((uint64_t)2<<32)?0:1;}\n')
            runtime=ROOT/'liza/runtime'/('workers_windows.c' if sys.platform=='win32' else 'workers_posix.c')
            for fail in range(8):
                exe=tmp/('fault'+('.exe' if sys.platform=='win32' else ''))
                cmd=['clang','-std=c11','-Wall','-Wextra','-Werror',f'-DLIZA_WORKERS_TEST_FAIL_AT={fail}',str(source),str(runtime),'-o',str(exe)]
                if sys.platform!='win32':cmd.append('-pthread')
                built=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
                self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
