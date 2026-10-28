#!/usr/bin/env python3
"""Run existing native acceptance suites through a transparent Clang wrapper."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from policy import STRATEGIES
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--strategy',choices=[s for s in STRATEGIES if s not in ('guided','default')],default='cost-400')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
real=shutil.which('clang');wrapper=out/'clang';log=out/'injected.jsonl'
wrapper.write_text('#!'+sys.executable+'\nimport os,sys,json\nargs=sys.argv[1:]\nif "-O2" in args and any(a.endswith(".ll") for a in args):\n args += '+repr(STRATEGIES[a.strategy])+'\n with open('+repr(str(log))+',"a") as f: f.write(json.dumps(args)+"\\n")\nos.execv('+repr(real)+',['+repr(real)+']+args)\n')
wrapper.chmod(0o755)
env={**os.environ,'PATH':str(out)+os.pathsep+os.environ['PATH'],'PYTHONPATH':str(ROOT)}
results=[]
for suite in ('test_direct_storage.py','test_mutable_audit.py','test_variants.py','test_proxy.py'):
 cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p',suite,'-v']
 r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=600)
 (out/(suite+'.log')).write_text(r.stdout+r.stderr)
 results.append({'suite':suite,'command':cmd,'returncode':r.returncode})
 print(suite,r.returncode,flush=True)
 if r.returncode:break
records=log.read_text().splitlines() if log.exists() else []
(out/'report.json').write_text(json.dumps({'strategy':a.strategy,'extra_flags':STRATEGIES[a.strategy],'results':results,'injected_compilations':len(records)},indent=2)+'\n')
if any(r['returncode'] for r in results) or not records:raise SystemExit(1)
