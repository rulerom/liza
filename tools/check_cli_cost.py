"""Inspect the CLI lookup/path boundary separately from CRT/OS startup costs."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm


def inspect(output,clang='clang'):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[1]
    suffix='windows' if sys.platform=='win32' else 'posix'
    ir=root/'liza-text.ll';ir.write_text(llvm(lower(load_program(repo/'examples/apps/liza_text.liza'))))
    for opt in ('-O0','-O2'):
        for label,source in [('app',ir),('cli',repo/f'liza/runtime/cli_{suffix}.c'),
                             ('file',repo/f'liza/runtime/file_{suffix}.c')]:
            for flags,extension in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
                target=root/f'{label}.{opt[1:]}.{extension}'
                subprocess.run([clang,'-Wno-override-module',opt,*flags,str(source),'-o',str(target)],check=True,capture_output=True)
                text=target.read_text()
                assert not re.search(r'\b_?(malloc|calloc|realloc|free)\b',text),'unexpected heap calls'
                if label=='cli':
                    assert not re.search(r'\b_?(memcpy|memmove|strdup|MultiByteToWideChar)\b',text),'argument/string copy'
                if label=='file' and extension=='ll':
                    body=re.search(r'^define[^\n]*@liza_rt_file_open_native\(.*?^}',text,re.M|re.S)
                    assert body,'native path entry missing'
                    assert not re.search(r'\b(memcpy|memmove|memset|MultiByteToWideChar)\b',body.group()),'native path copied or transcoded'
                    assert '@CreateFileW' in body.group() if suffix=='windows' else re.search(r'@(?:"\\01_)?open\b',body.group())
    report='O0/O2: CLI lookup and native path opening introduce no heap allocation, string copy or transcoding. CRT startup and OS internals are outside this check.\n'
    (root/'report.txt').write_text(report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/cli-cost');p.add_argument('--clang',default='clang');a=p.parse_args()
    print(inspect(a.output,a.clang),end='')
