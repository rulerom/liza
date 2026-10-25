"""Inspect emitted T2 String observers, not a claim about every borrow function."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm

ROOT=Path(__file__).resolve().parents[1]

def inspect(output,clang='clang'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    module=lower(load_program(ROOT/'examples/owned_string.liza'))
    source=output/'source.ll';source.write_text(llvm(module))
    for opt in ('-O0','-O2'):
        target=output/(opt[1:]+'.ll')
        subprocess.run([clang,'-Wno-override-module',opt,'-S','-emit-llvm',str(source),'-o',str(target)],check=True,capture_output=True)
        text=target.read_text()
        for name in ('length','capacity','byte_at'):
            matches=re.findall(r'^define [^\n]*@liza_text\.string\.'+name+r'\([^\n]*\n[\s\S]*?^}',text,re.M)
            assert len(matches)==1,(opt,name,'missing/ambiguous observer')
            body=matches[0]
            assert not re.search(r'\b(malloc|calloc|realloc|free|memcpy|memmove|memset)\b',body),(opt,name,'allocation or bulk operation')
            # The only external call accepted in an observer is a checked trap.
            # No opaque helper can hide a full-buffer copy from this inspection.
            targets=re.findall(r'\bcall\b[^\n]*?@([^ (]+)',body)
            assert all(t=='llvm.trap' or t.startswith('llvm.') for t in targets),(opt,name,targets)
            if name=='byte_at':assert re.search(r'load i8\b',body),(opt,'missing runtime byte read')
    report='O0/O2: String.length/capacity/byte_at inspect descriptors and runtime bytes; no allocator, bulk copy, or opaque helper calls.\n'
    (output/'report.txt').write_text(report)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/readonly-cost');parser.add_argument('--clang',default='clang')
    args=parser.parse_args();print(inspect(args.output,args.clang),end='')
