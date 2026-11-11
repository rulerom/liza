"""SG4-A1 UDP ownership, datagram semantics and unified wait acceptance."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_sg3 import liza, program, ROOT

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class SG4UDP(unittest.TestCase):
    def test_language_roundtrip_and_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'udp.exe'
            for opt in ('0','2'):
                built=liza('build',ROOT/'examples/workers/udp_group.liza','-O',opt,'-o',exe)
                self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                for _ in range(3):
                    run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            src=Path(tmp)/'reject.liza'
            helper='fn helper()->u32:io,alloc {x=groups.udp_bind(net.ipv4(127,0,0,1,0))\nreturn 0}'
            for source in (program(producer='return helper()',helpers=helper),
                           program(producer='return helper()',consumer='return helper()',helpers=helper),
                           program(owner='x=helper()',helpers=helper)):
                src.write_text(source)
                check=liza('check',src)
                self.assertNotEqual(check.returncode,0)
                self.assertRegex(check.stderr,'group role cannot|outside its assigned role')

    def test_receive_preserves_region(self):
        source=program(consumer='''match memory.create(4096) {Err(e)=>{return 1} Ok(region)=>{
 match memory.alloc<u8>(region,16,0) {Err(e)=>{} Ok(input)=>{
  (buffer,result)=groups.udp_receive(move input)
  closed=memory.close(move region)
  released=memory.release(move buffer)
  return 0
 }}
 closed=memory.close(move region)
 return 0
}}''')
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'origin.liza';src.write_text(source)
            result=liza('check',src)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('region',result.stderr.lower())

    def test_native_idle_fault_truncation_and_cleanup(self):
        suffix='windows' if sys.platform=='win32' else 'posix'
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'native.exe'
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DLIZA_SG2_TESTING',
                 '-I'+str(ROOT/'liza/runtime'),str(ROOT/'tests/fixtures/sg4_udp.c'),
                 str(ROOT/f'liza/runtime/net_{suffix}.c'),str(ROOT/f'liza/runtime/reactor_{suffix}.c'),
                 str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
            cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
            built=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            self.assertEqual(built.returncode,0,built.stderr)
            for mode in range(4):
                with self.subTest(mode=mode):
                    run=subprocess.run([str(exe),str(mode)],capture_output=True,text=True,timeout=15)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
