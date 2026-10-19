"""Inspect the selected runtime Result/match RTP path, not a general cost proof."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm

BRIDGE='''
define i32 @rtp_bridge(ptr %data, i32 %length, i32 %field) {
entry:
  %base = insertvalue {ptr, i32} zeroinitializer, ptr %data, 0
  %view = insertvalue {ptr, i32} %base, i32 %length, 1
  %result = call i32 @liza_rtp_inspect({ptr, i32} %view, i32 %field)
  ret i32 %result
}
'''

def inspect(output,clang='clang'):
    root=Path(output); root.mkdir(parents=True,exist_ok=True)
    source=(Path(__file__).resolve().parents[1]/'examples/rtp_result.liza').read_text()
    ir=root/'result.ll'
    ir.write_text(llvm(lower(Parser(source).parse())).replace('define i32 @main()', 'define i32 @example_entry()')+BRIDGE)
    for flags,suffix in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
        subprocess.run([clang,'-Wno-override-module','-O2',*flags,str(ir),'-o',str(root/('result.O2.'+suffix))],check=True,capture_output=True)
    optimized=(root/'result.O2.ll').read_text()
    # Include all remaining Liza callees: the optimizer need not inline parsing.
    bodies=re.findall(r'^define [^\n]*@liza_(?!main\b)[^\n]*\{\n(.*?)^}',optimized,re.M|re.S)
    body='\n'.join(bodies)
    if not bodies or not re.search(r'\bload\b',body): raise AssertionError('missing runtime reads')
    if re.search(r'\b(alloca|store|memcpy|memmove|malloc|calloc|realloc)\b',body): raise AssertionError('copy or heap allocation in selected path')
    # Source has no array materialization on this path; writes to the borrowed
    # packet would also violate readonly semantics. Output/ABI stack stores are
    # permitted and recorded, not confused with copying the input buffer.
    assembly=(root/'result.O2.s').read_text()
    selected=re.findall(r'^_?liza_(?!main:)[^\n]*:\s*[^\n]*\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',assembly,re.M|re.S)
    if not selected: raise AssertionError('cannot locate machine functions')
    machine='\n'.join(selected)
    if re.search(r'\b(memcpy|memmove|malloc|calloc|realloc)\b',machine): raise AssertionError('copy/allocation machine call')
    (root/'result.functions.O2.ll').write_text(body)
    (root/'result.functions.O2.s').write_text(machine)
    target=subprocess.run([clang,'-dumpmachine'],capture_output=True,text=True,check=True).stdout.strip()
    report=f'Target: {target}\nResult/match RTP path: runtime loads; no heap or bulk-copy calls. Aggregate return/ABI stores may remain; inspect artifacts for input-copy claims.\n'
    (root/'report.txt').write_text(report)
    return ir,report

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='build/result-cost'); parser.add_argument('--clang',default='clang')
    args=parser.parse_args(); print(inspect(args.output,args.clang)[1],end='')
