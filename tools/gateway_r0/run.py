#!/usr/bin/env python3
"""R0 functional reproduction from a committed archive; no performance/proof claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT=Path(__file__).resolve().parents[2]
PILOT='90c9c2f0eab565397db00ceb4a89cf27116c5bc2'
BUILD='''import hashlib,json,subprocess
from pathlib import Path
import liza
from liza.modules import load_program
from liza.ir import lower,dump
from liza.backend import llvm
from liza.target import resolve
from liza.stdlib import link_flags
root=Path.cwd().resolve();out=Path(__file__).resolve().parent/'build';out.mkdir()
assert Path(liza.__file__).resolve().is_relative_to(root)
m=lower(load_program(root/'examples/apps/liza_proxy_ops.liza'));target=resolve('clang')
(out/'program.semantic.json').write_text(dump(m));ir=out/'program.ll';ir.write_text(llvm(m,target));commands=[]
for opt in (0,2):
 cmd=['clang',*target.flags,'-O'+str(opt),str(ir),*link_flags(m),'-o',str(out/('proxy-O'+str(opt)+('.exe' if __import__('os').name=='nt' else '')))];commands.append(cmd);subprocess.run(cmd,check=True,capture_output=True)
(out/'build.json').write_text(json.dumps({'target':target.metadata(),'commands':commands,'compiler_module':str(Path(liza.__file__).resolve())},indent=2)+'\\n')
'''
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def call(args,**kw):return subprocess.run([str(x) for x in args],check=True,text=True,capture_output=True,timeout=600,**kw)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--commit',default=PILOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--expect-clang',help='exact first line, fail closed on toolchain drift');a=p.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 report={'status':'incomplete','scope':'functional clean-archive reproduction','independent_engineer_acceptance':'pending','vn0':'not_run','performance':{k:'not_measured' for k in ('rss','cpu','throughput','drain_wall_time')},'tests':[]}
 try:
  commit=call(['git','rev-parse','--verify',a.commit+'^{commit}'],cwd=ROOT).stdout.strip();report['commit']=commit
  clang=shutil.which('clang')
  if not clang:raise ValueError('clang missing from PATH')
  version=call([clang,'--version']).stdout;report['toolchain']={'clang':version,'clang_binary_sha256':digest(Path(clang).resolve()),'python':sys.version,'python_binary_sha256':digest(Path(sys.executable).resolve()),'platform':platform.platform(),'machine':platform.machine()}
  if a.expect_clang and version.splitlines()[0]!=a.expect_clang:raise ValueError('Clang version drift')
  archive=out/'source.tar';call(['git','archive',commit,'-o',archive],cwd=ROOT);report['archive_sha256']=digest(archive)
  source=out/'source';source.mkdir()
  with tarfile.open(archive) as tar:
   members=tar.getmembers()
   for member in members:
    if not (member.isfile() or member.isdir()) or not (source/member.name).resolve().is_relative_to(source):raise ValueError('unsafe archive member')
   tar.extractall(source,members=members)
  report['source_hashes']={str(f.relative_to(source)):digest(f) for f in sorted(source.rglob('*')) if f.is_file()}
  report['application_sha256']=digest(source/'examples/apps/liza_proxy_ops.liza')
  env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME') and not k.startswith('LIZA_')}
  env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1',PYTHONPYCACHEPREFIX=str(out/'cache'))
  bootstrap=out/'build_snapshot.py';bootstrap.write_text(BUILD)
  call([sys.executable,bootstrap],cwd=source,env=env)
  report['build']=json.loads((out/'build/build.json').read_text())
  for suite,expected in [('test_proxy_ops.py',7),('test_proxy_lifecycle.py',11)]:
   cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p',suite,'-v'];started=time.monotonic()
   r=subprocess.run(cmd,cwd=source,env=env,text=True,capture_output=True,timeout=240)
   log=r.stdout+r.stderr;(out/(suite+'.log')).write_text(log)
   count=re.search(r'Ran (\d+) tests? in',log);skips=re.search(r'OK \(skipped=(\d+)\)',log)
   row={'suite':suite,'command':cmd,'returncode':r.returncode,'seconds':time.monotonic()-started,'tests':int(count[1]) if count else None,'skipped':int(skips[1]) if skips else 0};report['tests'].append(row)
   if r.returncode or row['tests']!=expected:raise ValueError('test failure/count drift: '+suite)
  report['status']='functional_reproduction_passed'
 except Exception as e:report['error']=str(e);raise
 finally:
  report['artifacts']={str(f.relative_to(out)):digest(f) for f in sorted(out.rglob('*')) if f.is_file() and f.parts[len(out.parts)] not in ('source','cache') and f.name!='report.json'}
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(report['status'],commit)

if __name__=='__main__':main()
