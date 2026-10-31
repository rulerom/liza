"""Liza-facing role restrictions, native channel and startup failure."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/workers/scoped_channel.liza'
def liza(*args):
    return subprocess.run([sys.executable,'-m','liza',*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=60)

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ScopedChannels(unittest.TestCase):
    def test_channel_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('channel.exe' if sys.platform=='win32' else 'channel')
            for opt in ('0','2'):
                b=liza('build',EXAMPLE,'-O',opt,'-o',exe)
                self.assertEqual(b.returncode,0,b.stdout+b.stderr)
                for _ in range(5):
                    r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            ir=liza('emit-ir',EXAMPLE)
            self.assertEqual(ir.returncode,0,ir.stdout+ir.stderr)
            self.assertEqual(json.loads(ir.stdout)['channel_entries'],['scoped_channel.producer','scoped_channel.consumer'])
    def test_budget_and_sender_close(self):
        program = """fn producer()->u32:io {
 status=channels.send(42)
 if status!=0 {return 1}
 return 0
}
fn consumer()->u32:io {
 var got:u32=0
 var closed:u32=0
 while closed==0 {
  result=channels.receive()
  status=result>>32
  if status==0 {if u32.wrap(result)!=42 {return 2} got=got+1}
  if status==2 {closed=1}
 }
 if got!=1 {return 2}
 return 0
}
fn main()->u32:io,alloc {
 a=channels.run(0,1024)
 if a>>56!=1 {return 1}
 b=channels.run(65537,1048576)
 if b>>56!=1 {return 2}
 c=channels.run(1,1)
 if c>>56!=1 {return 3}
 d=channels.run(1,1024)
 if d!=0 {return 4}
 return 0
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'budget.liza';src.write_text(program)
            for opt in ('0','2'):
                r=liza('run',src,'-O',opt)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_runtime_core_matches_reviewed_probe(self):
        for ext in ('c','h'):
            probe=(ROOT/'experiments/scoped_channel'/('channel.'+ext)).read_text()
            expected=probe.replace('"channel.h"','"scoped_channel_core.h"').replace('ch_', 'liza_scoped_')
            self.assertEqual((ROOT/'liza/runtime'/('scoped_channel_core.'+ext)).read_text(),expected)

    def test_startup_failure_before_user_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('fail.exe' if sys.platform=='win32' else 'fail')
            suffix='windows' if sys.platform=='win32' else 'posix'
            for flag in ('CHANNEL_TEST_FAIL_AT=0','CHANNEL_TEST_FAIL_AT=1','CH_TEST_FAIL_ALLOC'):
                cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-D'+flag,str(ROOT/'tests/fixtures/scoped_channel_start_failure.c'),str(ROOT/f'liza/runtime/channels_{suffix}.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
                if sys.platform!='win32':cmd.append('-pthread')
                b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
                self.assertEqual(b.returncode,0,b.stdout+b.stderr)
                r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_discard_accounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('discard.exe' if sys.platform=='win32' else 'discard')
            suffix='windows' if sys.platform=='win32' else 'posix'
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'tests/fixtures/scoped_channel_discard.c'),str(ROOT/f'liza/runtime/channels_{suffix}.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(b.returncode,0,b.stdout+b.stderr)
            r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_rejects_wrong_role_and_unscoped_access(self):
        cases=[
            ('fn producer()->u32:io {x=channels.receive()\nreturn 0}', 'fn consumer()->u32 {return 0}', 'return 0', 'channel role cannot'),
            ('fn producer()->u32 {return 0}', 'fn consumer()->u32:io {x=channels.send(1)\nreturn 0}', 'return 0', 'channel role cannot'),
            ('fn producer()->u32:io {x=channels.send(1)\nreturn 0}', 'fn consumer()->u32 {return 0}', 'x=producer()\nreturn 0', 'outside its assigned role'),
            ('fn producer()->u32:io,alloc {x=channels.run(1,1024)\nreturn 0}', 'fn consumer()->u32 {return 0}', 'return 0', 'channel role cannot'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'roles.liza'
            for prod,cons,body,expected in cases:
                with self.subTest(prod=prod,cons=cons):
                    src.write_text(prod+'\n'+cons+'\nfn main()->u32:io,alloc {\n group=channels.run(1,1024)\n'+body+'\n}\n')
                    r=liza('check',src)
                    self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
                    self.assertIn(expected,r.stderr)
    def test_rejects_unaudited_io_and_unscoped_channel(self):
        cases=[
            ('fn helper()->u32:io {match console.println("x") {Ok(n)=>{return 0} Err(e)=>{return 1}}}',
             'fn producer()->u32:io {return helper()}', 'channel role cannot'),
            ("""fn helper()->u32:io,alloc {
 match net.reactor_create(0,1) {
  Err(e)=>{return 0}
  Ok(r)=>{
   a=net.reactor_watch_shutdown(r)
   b=net.reactor_close(move r)
   return 0
  }
 }
}""", 'fn producer()->u32:io,alloc {return helper()}', 'channel role cannot'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'scope.liza'
            for helper,producer,expected in cases:
                with self.subTest(helper=helper):
                    src.write_text(helper+'\n'+producer+'\nfn consumer()->u32 {return 0}\nfn main()->u32:io,alloc {\n x=channels.run(1,1024)\n return 0\n}\n')
                    r=liza('check',src)
                    self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
                    self.assertIn(expected,r.stderr)
            src.write_text('fn main()->u32:io {\n x=channels.send(1)\n return 0\n}\n')
            r=liza('check',src)
            self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('channel operations require channels.run',r.stderr)

    def test_imported_generic_role_cannot_be_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'helper.liza').write_text('pub fn send<T>(x:T)->u32:io {return channels.send(1)}\n')
            src=root/'main.liza';src.write_text('import helper\nfn producer()->u32:io {return helper.send<u32>(1)}\nfn consumer()->u32:io {return helper.send<u32>(2)}\nfn main()->u32:io,alloc {\n x=channels.run(1,1024)\n return 0\n}\n')
            r=liza('check',src)
            self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('channel role cannot',r.stderr)
if __name__=='__main__':unittest.main()
