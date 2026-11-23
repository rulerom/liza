"""Real connected UDP assignment rotation and Liza ownership binding."""
import shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_httpws import build
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ConnectedUdp(unittest.TestCase):
    def test_native_rotation_filters_peer_and_preserves_tcp(self):
        with tempfile.TemporaryDirectory(prefix='liza-connected-udp-') as folder:
            for opt in ('0','2'):
                exe=Path(folder)/('probe'+opt+('.exe' if sys.platform=='win32' else ''))
                platform='windows' if sys.platform=='win32' else 'posix'
                args=['clang','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror',str(ROOT/'tests/native/reactor_connected_udp.c'),str(ROOT/'liza/runtime'/('net_'+platform+'.c')),'-o',str(exe)]
                args+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
                result=subprocess.run(args,capture_output=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stderr)
                run=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(run.returncode,0,run.stderr)
    def test_language_owner_survives_close_and_replace(self):
        source='''fn main()->u32:io,alloc {
match net.reactor_udp_create(net.ipv4(0,0,0,0,0),1) {Err(e)=>{return 1} Ok(r)=>{
var failed=false
match net.reactor_udp_replace_connected(r,net.ipv4(127,0,0,1,9)) {Err(e)=>{failed=true} Ok(n)=>{}}
match net.reactor_udp_close_endpoint(r) {Err(e)=>{failed=true} Ok(n)=>{}}
match net.reactor_udp_replace_connected(r,net.ipv4(127,0,0,1,9)) {Err(e)=>{failed=true} Ok(n)=>{}}
closed=net.reactor_close(move r);if failed {return 2};return 0
}}}'''
        with tempfile.TemporaryDirectory(prefix='liza-connected-binding-') as folder:
            root=Path(folder);entry=root/'main.liza';entry.write_text(source)
            for opt in ('0','2'):
                out=root/opt;out.mkdir();exe=build(entry,out,opt)
                run=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(run.returncode,0,run.stderr)
