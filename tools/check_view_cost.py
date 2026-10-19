"""Reproducible O2 inspection of the runtime RTP view read path.

The LLVM bridge is test infrastructure, not a language FFI contract. It lets a
separately compiled C caller supply unknown bytes without passing C aggregates.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm

BRIDGE = '''
define i32 @rtp_bridge(ptr %data, i32 %length) {
entry:
  %base = insertvalue { ptr, i32 } zeroinitializer, ptr %data, 0
  %view = insertvalue { ptr, i32 } %base, i32 %length, 1
  %result = call i32 @liza_rtp_fields({ ptr, i32 } %view)
  ret i32 %result
}
'''
HARNESS = '''#include <stdint.h>
#include <stdlib.h>
extern uint32_t rtp_bridge(const uint8_t*, uint32_t);
int main(int argc, char **argv) {
    if (argc != 6) return 2;
    uint8_t data[4];
    for (int i=0; i<4; ++i) data[i]=(uint8_t)strtoul(argv[i+1],0,10);
    uint32_t expected=((uint32_t)(data[0]>>6)<<24)
        | ((uint32_t)(data[1]&127)<<16) | ((uint32_t)data[2]<<8) | data[3];
    return rtp_bridge(data,(uint32_t)strtoul(argv[5],0,10)) == expected ? 0 : 1;
}
'''


def inspect(output, clang='clang'):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    source=(Path(__file__).resolve().parents[1]/'examples/rtp_view.liza').read_text()
    module=llvm(lower(Parser(source).parse())).replace('define i32 @main()', 'define i32 @example_entry()')+BRIDGE
    ir=output/'rtp.ll'; ir.write_text(module)
    optimized=output/'rtp.O2.ll'; assembly=output/'rtp.O2.s'
    for flags,target in [(['-S','-emit-llvm'],optimized),(['-S'],assembly)]:
        subprocess.run([clang,'-Wno-override-module','-O2',*flags,str(ir),'-o',str(target)],check=True,capture_output=True)
    text=optimized.read_text()
    match=re.search(r'^define [^\n]*@liza_rtp_fields\([^\n]*\)[^\n]*\{\n(.*?)^}',text,re.M|re.S)
    if not match:
        raise AssertionError('cannot locate optimized RTP function')
    body=match.group(1)
    if re.search(r'\b(alloca|store|memcpy|memmove|malloc)\b',body):
        raise AssertionError('RTP view read path allocates or copies storage')
    if not re.search(r'\bload\b',body):
        raise AssertionError('runtime byte reads disappeared')
    asm=assembly.read_text()
    match=re.search(r'^_?liza_rtp_fields:.*?\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',asm,re.M|re.S)
    if not match:
        raise AssertionError('cannot locate RTP machine code')
    machine=match.group(1)
    if re.search(r'\b(memcpy|memmove|malloc)\b',machine):
        raise AssertionError('copy/allocation call in RTP machine code')
    # Inspect the selected body for the two tested target families. Do not
    # claim a portable proof based only on an instruction-name pattern.
    target=subprocess.run([clang,'-dumpmachine'],check=True,capture_output=True,text=True).stdout.strip()
    if target.startswith(('arm64','aarch64')):
        if re.search(r'^\s*(str\w*|stur\w*|stp)\s',machine,re.M):
            raise AssertionError('unexpected store in ARM RTP read path')
    elif target.startswith('x86_64'):
        if re.search(r'^\s*(?:mov\w*|vmov\w*)\s+[^\n]*,\s*[^\n]*\(',machine,re.M):
            raise AssertionError('unexpected store in x86 RTP read path')
    else:
        raise AssertionError(f'machine-code inspection not defined for {target}')
    (output/'rtp.function.O2.ll').write_text(body)
    (output/'rtp.function.O2.s').write_text(machine)
    report=f'Target: {target}\nRTP view reader: runtime loads; no array copies, stores or allocations in selected O2 function.\n'
    (output/'report.txt').write_text(report)
    return ir, report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='build/view-cost')
    parser.add_argument('--clang',default='clang')
    args=parser.parse_args()
    _,report=inspect(args.output,args.clang)
    print(report,end='')


if __name__=='__main__':
    main()
