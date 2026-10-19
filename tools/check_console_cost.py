"""Record the console runtime's O2 code and check its explicit allocation policy."""
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
    module=llvm(lower(Parser((repo/'examples/hello.liza').read_text()).parse()))
    ir=root/'hello.ll';ir.write_text(module)
    runtime=repo/('liza/runtime/console_windows.c' if sys.platform == 'win32' else 'liza/runtime/console_posix.c')
    for name,source in [('hello',ir),('runtime',runtime)]:
        for flags,suffix in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
            dest=root/(name+'.O2.'+suffix)
            subprocess.run([clang,'-Wno-override-module','-O2',*flags,str(source),'-o',str(dest)],check=True,capture_output=True)
            text=dest.read_text()
            if re.search(r'\b(malloc|calloc|realloc|free|printf|fprintf|sprintf|snprintf|fwrite)\b',text):
                raise AssertionError('unexpected heap/stdio/formatting dependency')
    if '@liza_rt_write' not in (root/'hello.O2.ll').read_text():
        raise AssertionError('console effect disappeared')
    report='Target: '+subprocess.run([clang,'-dumpmachine'],capture_output=True,text=True,check=True).stdout.strip()+'\nConsole implementation: no heap calls or stdio formatting; static text and bounded number/conversion buffers. OS/libc internals are outside this check.\n'
    (root/'report.txt').write_text(report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/console-cost');p.add_argument('--clang',default='clang');a=p.parse_args()
    print(inspect(a.output,a.clang),end='')
