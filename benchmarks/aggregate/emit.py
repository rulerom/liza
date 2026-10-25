"""Emit an explicitly labelled ablation; only A3 is the production compiler."""
import json
from pathlib import Path
import runpy
import sys
from liza import backend

variant, output, clang = sys.argv[1:]
if variant in ('A1','A2'):
    backend.direct_owned_variant = lambda *args: None
if variant == 'A2':
    from local_reuse import caller_plan
    backend.caller_plan = caller_plan
if variant == 'A1':
    original = backend.llvm
    def abi(module, target=None):
        text=original(module,target)
        # Research-only promise for pointer-free JsonState in this pure module.
        # Input arguments may alias each other: do not give them noalias.
        for fn in module:
            if fn.name.startswith('__liza_owned_'):
                continue
            for line in text.splitlines():
                if line.startswith('define ') and '@liza_'+fn.name+'(' in line:
                    new=line.replace('ptr sret(%struct.JsonState)', 'ptr noalias sret(%struct.JsonState)')
                    for p in fn.params:
                        if p['type']=='JsonState':
                            new=new.replace('ptr %'+p['name'], 'ptr nocapture readonly %'+p['name'])
                    text=text.replace(line,new)
        return text
    backend.llvm=abi
sys.argv=[str(Path(__file__).parents[1]/'json'/'emit_liza.py'),output,clang]
runpy.run_path(sys.argv[0],run_name='__main__')
