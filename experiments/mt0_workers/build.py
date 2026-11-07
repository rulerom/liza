#!/usr/bin/env python3
"""Build an experimental C launcher around the real Liza LLVM output."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def build(output, opt):
    with tempfile.TemporaryDirectory(prefix='liza-mt0-') as tmp:
        ir=Path(tmp)/'worker.ll'
        subprocess.run([sys.executable,'-m','liza','emit-llvm',str(HERE/'worker.liza'),'-o',str(ir)],cwd=ROOT,check=True)
        code=ir.read_text()
        # Diagnostic-only bridge: reserve C main for the launcher and export
        # a scalar ABI entry. Do not expose arbitrary user pointers to Liza.
        needle='define i32 @main() {'
        target='define i32 @liza_worker.mt_worker(i32 %p0) {'
        if code.count(needle)!=1 or code.count(target)!=1:raise RuntimeError('unexpected generated LLVM ABI')
        code=code.replace(needle,'define i32 @mt0_unused_main() {')
        code+='\ndefine i32 @liza_mt_worker(i32 %id) {\n  %v = call i32 @liza_worker.mt_worker(i32 %id)\n  ret i32 %v\n}\n'
        ir.write_text(code)
        command=['clang','-std=c11','-Wall','-Wextra','-Werror','-O'+opt,str(ir),str(HERE/'launcher.c'),'-o',str(output)]
        if sys.platform!='win32':command.append('-pthread')
        subprocess.run(command,cwd=ROOT,check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('-o',type=Path,required=True);p.add_argument('-O',choices=('0','2'),default='2');a=p.parse_args();build(a.o,a.O)
