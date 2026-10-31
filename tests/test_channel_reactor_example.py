"""Control messages drive a worker-owned reactor on real loopback TCP."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/workers/channel_reactor.liza'

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ChannelReactorExample(unittest.TestCase):
    def test_control_and_reactor_lifecycle(self):
        source=EXAMPLE.read_text()
        cases=[('normal',source,0),
               ('bad_command',source.replace('var command:u32=1','var command:u32=2',1),2),
               ('failed_connect',source.replace('net.reactor_connect(reactor,u16.wrap(port))','net.reactor_connect(reactor,0)',1),4)]
        with tempfile.TemporaryDirectory(prefix='liza-channel-reactor-') as tmp:
            tmp=Path(tmp)
            for name,content,expected in cases:
                with self.subTest(case=name):
                    if name!='normal':
                        self.assertNotEqual(content,source)
                        block=('            if result.producer!=0 || result.consumer!=0 || result.discarded!=0 {return 2}\n'
                               '            return 0')
                        self.assertIn(block,content)
                        content=content.replace(block,'            return result.consumer',1)
                    src=tmp/'example.liza';src.write_text(content)
                    exe=tmp/('example.exe' if sys.platform=='win32' else 'example')
                    for opt in ('0','2'):
                        build=subprocess.run([sys.executable,'-m','liza','build',str(src),'-O',opt,'-o',str(exe)],cwd=ROOT,text=True,capture_output=True,timeout=60)
                        self.assertEqual(build.returncode,0,build.stdout+build.stderr)
                        for _ in range(3):
                            run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
                            self.assertEqual(run.returncode,expected,run.stdout+run.stderr)
    def test_consumer_exits_before_producer(self):
        source="""fn producer()->u32:io {
 while true {
  status=channels.send(7)
  if status==2 {return 17}
 }
}
fn consumer()->u32:io,alloc {
 match net.reactor_create(0,1) {
  Err(e)=>{return 24}
  Ok(reactor)=>{
   match net.reactor_close(move reactor) {Err(e)=>{return 25} Ok(done)=>{return 23}}
  }
 }
}
fn main()->u32:io,alloc {
 match channels.run(1,1024) {
  Err(e)=>{return 1}
  Ok(r)=>{if r.producer!=17 || r.consumer!=23 || r.discarded>1 {return 2} return 0}
 }
}
""".replace('{return 2} return 0','{return 2}\n return 0')
        with tempfile.TemporaryDirectory(prefix='liza-channel-early-') as tmp:
            tmp=Path(tmp);src=tmp/'early.liza';src.write_text(source)
            exe=tmp/('early.exe' if sys.platform=='win32' else 'early')
            for opt in ('0','2'):
                build=subprocess.run([sys.executable,'-m','liza','build',str(src),'-O',opt,'-o',str(exe)],cwd=ROOT,text=True,capture_output=True,timeout=60)
                self.assertEqual(build.returncode,0,build.stdout+build.stderr)
                for _ in range(10):
                    run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=15)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_early_exit_releases_channel_once(self):
        with tempfile.TemporaryDirectory(prefix='liza-channel-free-') as tmp:
            tmp=Path(tmp);suffix='windows' if sys.platform=='win32' else 'posix'
            obj=tmp/'core.o';exe=tmp/('early.exe' if sys.platform=='win32' else 'early')
            compile_core=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Dfree=tracked_free','-c',str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(obj)]
            built=subprocess.run(compile_core,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            link=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'tests/fixtures/scoped_channel_early_exit.c'),str(ROOT/f'liza/runtime/channels_{suffix}.c'),str(obj),'-o',str(exe)]
            if sys.platform!='win32':link.append('-pthread')
            built=subprocess.run(link,text=True,capture_output=True,timeout=30)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            run=subprocess.run([str(exe)],text=True,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__':unittest.main()
