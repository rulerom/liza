"""Pacing configuration bounds are shared by the Liza client and service installer."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_httpws import build
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class RtspPacing(unittest.TestCase):
    def test_packet_size_defaults_bounds_and_types_at_o0_o2(self):
        base=dict(camera_ip='192.0.2.20',camera_url='rtsp://192.0.2.20/stream1',vg_ip='192.0.2.10',vg_peer='localhost',login='test',password='test-secret',conference='radio',client_version=618,run_ms=0)
        source='''import rtsp.config
fn main()->u32:io,alloc {
match rtsp.config.read() {Err(e)=>{return 2} Ok(config)=>{printed=console.print_u64(u64(config.rtp_max_packet_bytes));return 0}}
}'''
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-packet-size-') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples',root/'project')
            entry=root/'project/probe.liza';entry.write_text(source)
            for opt in ('0','2'):
                out=root/opt;out.mkdir();exe=build(entry,out,opt,root/'project')
                for value in ('missing',0,256,1200,1472,255,1473,True,.5,'1200',None):
                    with self.subTest(opt=opt,value=value):
                        config=dict(base)
                        if value!='missing':config['rtp_max_packet_bytes']=value
                        path=root/'config.json';path.write_text(json.dumps(config));path.chmod(0o600)
                        result=subprocess.run([str(exe),str(path)],capture_output=True,timeout=10)
                        valid=value=='missing' or type(value) is int and (value==0 or 256<=value<=1472)
                        self.assertEqual(result.returncode,0 if valid else 2,result.stderr)
                        if valid:self.assertEqual(result.stdout.strip(),str(0 if value=='missing' else value).encode())

    def test_config_defaults_bounds_and_types_at_o0_o2(self):
        base=dict(camera_ip='192.0.2.20',camera_url='rtsp://192.0.2.20/stream1',vg_ip='192.0.2.10',vg_peer='localhost',login='test',password='test-secret',conference='radio',client_version=618,run_ms=0)
        source='''import rtsp.config
fn main()->u32:io,alloc {
match rtsp.config.read() {Err(e)=>{return 2} Ok(config)=>{printed=console.print_u64(u64(config.rtp_pace_ms));return 0}}
}'''
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-pacing-') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples',root/'project')
            entry=root/'project/probe.liza';entry.write_text(source)
            for opt in ('0','2'):
                out=root/opt;out.mkdir();exe=build(entry,out,opt,root/'project')
                for value in ('missing',0,1,5,6,-1,True,.5,'1',None):
                    with self.subTest(opt=opt,value=value):
                        config=dict(base)
                        if value!='missing':config['rtp_pace_ms']=value
                        path=root/'config.json';path.write_text(json.dumps(config));path.chmod(0o600)
                        result=subprocess.run([str(exe),str(path)],capture_output=True,timeout=10)
                        valid=value=='missing' or type(value) is int and 0<=value<=5
                        self.assertEqual(result.returncode,0 if valid else 2,result.stderr)
                        if valid:self.assertEqual(result.stdout.strip(),str(0 if value=='missing' else value).encode())
                        self.assertNotIn(b'test-secret',result.stdout+result.stderr)
