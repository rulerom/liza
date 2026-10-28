#!/usr/bin/env python3
"""Existing trap/snapshot/effect and RTP tests with research IR transforms."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
real=shutil.which('clang');results=[]
for variant in ('scalar','staged'):
    folder=out/variant;folder.mkdir();wrapper=folder/'clang';log=folder/'injected.jsonl'
    wrapper.write_text('#!'+sys.executable+'\nimport os,sys,json,subprocess\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(HERE))+')\nfrom transforms import scalarize\nargs=sys.argv[1:]\nfor i,a in enumerate(args):\n if a.endswith(".ll") and Path(a).exists():\n  target=Path(a).with_suffix(".s2.ll")\n  if '+repr(variant)+'=="scalar": target.write_text(scalarize(Path(a).read_text())[0])\n  else: subprocess.run(['+repr(real)+',"-O1","-S","-emit-llvm",a,"-o",str(target)],check=True)\n  args[i]=str(target)\n  with open('+repr(str(log))+',"a") as f:f.write(json.dumps(args)+"\\n")\nos.execv('+repr(real)+',['+repr(real)+']+args)\n')
    wrapper.chmod(0o755);env={**os.environ,'PATH':str(folder)+os.pathsep+os.environ['PATH'],'PYTHONPATH':str(ROOT)}
    for suite in ('test_direct_storage.py','test_mutable_audit.py','test_variants.py'):
        cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p',suite,'-v']
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=600)
        (folder/(suite+'.log')).write_text(r.stdout+r.stderr);results.append({'variant':variant,'suite':suite,'returncode':r.returncode})
        print(variant,suite,r.returncode,flush=True)
        if r.returncode:raise RuntimeError('regression failed')
    if not log.exists():raise ValueError('no transform injections')
(out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
