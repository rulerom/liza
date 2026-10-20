"""Inspect the bounded file result -> view -> RTP path, not total I/O cost."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm


def inspect(output,clang='clang'):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[1]
    source=(repo/'examples/rtp_file.liza').read_text(encoding='utf-8')
    ir=root/'rtp_file.ll';ir.write_text(llvm(lower(Parser(source).parse())))
    runtime=repo/('liza/runtime/file_windows.c' if sys.platform=='win32' else 'liza/runtime/file_posix.c')
    for name,path in [('rtp_file',ir),('runtime',runtime)]:
        for flags,suffix in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
            dest=root/(name+'.O2.'+suffix)
            subprocess.run([clang,'-Wno-override-module','-O2',*flags,str(path),'-o',str(dest)],check=True,capture_output=True)
            if re.search(r'\b(malloc|calloc|realloc|free)\b',dest.read_text()):
                raise AssertionError('unexpected heap dependency')
    optimized=(root/'rtp_file.O2.ll').read_text()
    match=re.search(r'^define [^\n]*@liza_main\([^\n]*\)[^\n]*\{\n(.*?)^}',optimized,re.M|re.S)
    if not match: raise AssertionError('missing main function')
    body=match.group(1)
    # The owned result is filled by a call. Creating/reading its view must not
    # materialize another array, including scalarized copies missed by memcpy checks.
    if re.search(r'\b(store|memcpy|memmove)\b',body):
        raise AssertionError('file result -> parser path contains stores/copies')
    if '@liza_parse_rtp' not in body or '@liza_file.read' not in body:
        raise AssertionError('expected runtime boundaries disappeared; review inspection')
    asm=(root/'rtp_file.O2.s').read_text()
    match=re.search(r'^_?liza_main:.*?\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.seh_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',asm,re.M|re.S)
    if not match: raise AssertionError('missing machine code')
    if re.search(r'\b(memcpy|memmove|rep)\b',match.group(1)):
        raise AssertionError('bulk copy in selected machine code')
    (root/'main.O2.ll').write_text(body)
    (root/'main.O2.s').write_text(match.group(1))
    report='Target: '+subprocess.run([clang,'-dumpmachine'],check=True,capture_output=True,text=True).stdout.strip()+'\n'
    report+='File result -> readonly view -> RTP parser: no buffer stores/copies in selected O2 main.\n'
    report+='Fixed 2048-byte capacity; no explicit heap calls in file runtime.\n'
    report+='Copies inside file.read and zero-initialization remain; OS/libc internals are outside this check.\n'
    (root/'report.txt').write_text(report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/file-cost');p.add_argument('--clang',default='clang');a=p.parse_args()
    print(inspect(a.output,a.clang),end='')
