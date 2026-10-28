#!/usr/bin/env python3
"""Run selected existing suites with the research transform at every llvm() call."""
import argparse,json,sys,unittest
from pathlib import Path
from liza import backend
from forward import forward
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
real=backend.llvm;calls=[]
def changed(module,*args,**kw):
 transformed,certificates=forward(module);calls.append({'functions':[f.name for f in module],'certificates':certificates})
 return real(transformed,*args,**kw)
backend.llvm=changed
results=[]
for suite in ('test_direct_storage.py','test_mutable_audit.py','test_variants.py','test_proxy.py'):
 tests=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=suite)
 with (a.output/(suite+'.log')).open('w') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(tests)
 results.append({'suite':suite,'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped)})
 print(suite,results[-1],flush=True)
 if not r.wasSuccessful():break
(a.output/'report.json').write_text(json.dumps({'suites':results,'llvm_calls':calls},indent=2)+'\n')
if len(results)!=4 or any(x['errors'] or x['failures'] for x in results):sys.exit(1)
