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
if __name__=='__main__':unittest.main()
