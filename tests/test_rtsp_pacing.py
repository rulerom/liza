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
    def test_config_defaults_bounds_and_types_at_o0_o2(self):
        base=dict(camera_ip='192.0.2.20',camera_url='rtsp://192.0.2.20/stream1',vg_ip='192.0.2.10',vg_peer='localhost',login='test',password='test-secret',conference='radio',client_version=618,run_ms=0)
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-pacing-') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples',root/'project')
            entry=root/'project/probe.liza'
            for field,limit in (('rtp_pace_ms',5),('vg_resume_quiet_ms',30000)):
                source = ('import rtsp.config\nfn main()->u32:io,alloc {\n'
                          'match rtsp.config.read() {Err(e)=>{return 2} Ok(config)=>{'
                          'printed=console.print_u64(u64(config.'+field+'));return 0}}\n}')
                entry.write_text(source)
                for opt in ('0','2'):
                    out=root/(field+opt);out.mkdir();exe=build(entry,out,opt,root/'project')
                    for value in ('missing',0,1,limit,limit+1,-1,True,.5,'1',None):
                        with self.subTest(field=field,opt=opt,value=value):
                            config=dict(base)
                            if value!='missing':config[field]=value
                            path=root/'config.json';path.write_text(json.dumps(config));path.chmod(0o600)
                            result=subprocess.run([str(exe),str(path)],capture_output=True,timeout=10)
                            valid=value=='missing' or type(value) is int and 0<=value<=limit
                            self.assertEqual(result.returncode,0 if valid else 2,result.stderr)
                            if valid:self.assertEqual(result.stdout.strip(),str(0 if value=='missing' else value).encode())
                            self.assertNotIn(b'test-secret',result.stdout+result.stderr)
