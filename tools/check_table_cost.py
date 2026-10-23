"""Connection-table acceptance and cost evidence; does not assert zero-copy.

Only fixture capacity/initialization is expanded. All table algorithms and
acceptance scenarios compile as ordinary Liza 0.0.15, without added syntax.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower, dump
from liza.backend import llvm

ROOT = Path(__file__).resolve().parents[1]


def source_for(capacity):
    if capacity not in (64, 4096, 16384):
        raise ValueError('supported capacities are 64, 4096 and 16384')
    source = (ROOT/'examples/tables/connections.liza').read_text()
    source += 'fn main()'+(ROOT/'examples/connection_table.liza').read_text().split('fn main()',1)[1]
    source = source.replace('pub ', '').replace('tables.connections.', '')
    source = re.sub(r'\b(empty|get|add|edit|del)(?=\s*\()', lambda m: 'table_'+m[0], source)
    source = source.replace('[ConnectionSlot; 64]', f'[ConnectionSlot; {capacity}]')
    start = source.index('    return ConnectionTable([')
    end = source.index('\n', start)
    source = source[:start]+'    return ConnectionTable(['+', '.join(['empty']*capacity)+'])'+source[end:]
    return source


HARNESS = r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
extern uint32_t liza_check_reuse(uint32_t);
extern uint32_t liza_check_invalid(uint32_t);
extern uint32_t liza_check_retirement(uint32_t);
extern uint32_t liza_check_full(uint32_t);
int main(int argc, char **argv) {
    if(argc!=3) return 99;
    uint32_t n=(uint32_t)strtoul(argv[1],0,10), seed=(uint32_t)strtoul(argv[2],0,10), r;
    if((r=liza_check_reuse(seed))) {printf("reuse:%u\n",r);return 1;}
    uint32_t invalid[]={0,n-1,n,UINT32_MAX};
    for(unsigned i=0;i<4;i++) if((r=liza_check_invalid(invalid[i]))) {printf("invalid:%u:%u\n",invalid[i],r);return 2;}
    if((r=liza_check_retirement(seed%n))) {printf("retirement:%u\n",r);return 3;}
    if((r=liza_check_full(seed))) {printf("full:%u\n",r);return 4;}
    puts("OK");return 0;
}'''


def function_body(text, name):
    m = re.search(r'^define [^\n]*@"?liza_'+re.escape(name)+r'"?\([^\n]*\)[^\n]*\{\n(.*?)^}', text, re.M|re.S)
    if not m:
        raise AssertionError('missing function '+name)
    return m.group(0)


def inspect(output, clang='clang', capacities=(64,4096)):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    report={'target':subprocess.check_output([clang,'-dumpmachine'],text=True).strip(),
            'toolchain':subprocess.check_output([clang,'--version'],text=True).splitlines()[0],
            'note':'Instruction counts are static evidence, not dynamic copy-byte totals. Timings are whole acceptance runs, not operation benchmarks.',
            'capacities':{}}
    for n in capacities:
        root=output/str(n);root.mkdir(exist_ok=True)
        source=source_for(n)
        (root/'connection_table.liza').write_text(source)
        library=source[:source.index('fn main()')]
        source=library+(ROOT/'tests/fixtures/connection_table_cases.liza').read_text()+'\nfn main()->u32{return 0}\n'
        module=lower(Parser(source).parse())
        (root/'semantic.json').write_text(dump(module))
        ir=root/'table.ll';ir.write_text(llvm(module).replace('define i32 @main()', 'define i32 @example_entry()'))
        c=root/'harness.c';c.write_text(HARNESS)
        entry={'semantic_operations':{},'optimizations':{}}
        for fn in module:
            if fn.name in ('table_get','table_add','table_edit','table_del'):
                counts={}
                for b in fn.blocks:
                    for op in b.operations: counts[op.op]=counts.get(op.op,0)+1
                entry['semantic_operations'][fn.name]=counts
        for opt in (0,2):
            optimized=root/f'table.O{opt}.ll';assembly=root/f'table.O{opt}.s'
            for flags,dest in [(['-S','-emit-llvm'],optimized),(['-S'],assembly)]:
                subprocess.run([clang,'-Wno-override-module',f'-O{opt}',*flags,str(ir),'-o',str(dest)],check=True,capture_output=True,timeout=240)
            exe=root/(f'table.O{opt}.exe' if sys.platform=='win32' else f'table.O{opt}')
            # O0 baseline intentionally materializes many large SSA values.
            # Reserve explicit stack space on Windows (default is only 1 MiB).
            stack=['-Wl,/stack:33554432'] if sys.platform=='win32' else []
            subprocess.run([clang,'-Wno-override-module',f'-O{opt}',str(ir),str(c),*stack,'-o',str(exe)],check=True,capture_output=True,timeout=240)
            elapsed=[]
            for seed in (17,4294967295):
                start=time.perf_counter()
                result=subprocess.run([str(exe.resolve()),str(n),str(seed)],capture_output=True,text=True,timeout=180)
                if result.returncode or result.stdout.strip()!='OK':
                    raise AssertionError(f'{n}/O{opt}/seed={seed}: code={result.returncode}, {result.stdout} {result.stderr}')
                elapsed.append(time.perf_counter()-start)
            text=optimized.read_text();asm=assembly.read_text()
            functions={}
            for name in ('table_get','table_add','table_edit','table_del'):
                body=function_body(text,name)
                (root/f'{name}.O{opt}.ll').write_text(body+'\n')
                machine=re.search(r'^_?liza_'+name+r':.*?\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.seh_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',asm,re.M|re.S)
                if not machine: raise AssertionError('missing machine code for '+name)
                (root/f'{name}.O{opt}.s').write_text(machine.group(0)+'\n')
                if opt==2 and name=='table_get' and re.search(r'\b(store|alloca|memcpy|memmove)\b',body):
                    raise AssertionError('get materializes storage instead of reading the selected slot')
                functions[name]={'store_sites':len(re.findall(r'\bstore\b',body)),
                                 'copy_instructions':[line.strip() for line in body.splitlines() if re.search(r'call.*@llvm\.mem(?:cpy|move)',line)],
                                 'machine_lines':len(machine.group(0).splitlines()),
                                 'llvm_lines' :len(body.splitlines()),
                                 'memcpy_sites':len(re.findall(r'call[^\n]*@llvm\.memcpy',body)),
                                 'memmove_sites':len(re.findall(r'call[^\n]*@llvm\.memmove',body)),
                                 'alloca_sites':len(re.findall(r'\balloca\b',body)),
                                 'aggregate_loads':len(re.findall(r'\bload (?:%struct\.|\[)',body)),
                                 'aggregate_stores':len(re.findall(r'\bstore (?:%struct\.|\[)',body)),
                                 'byval_input':'byval(' in body.splitlines()[0],
                                 'sret_output':'sret(' in body.splitlines()[0]}
            entry['optimizations'][str(opt)]={'functions':functions,'acceptance_seconds':elapsed,
                                             'assembly_bytes':len(asm.encode()),
                                             'bulk_copy_symbol_mentions':len(re.findall(r'\b(?:_?memcpy|_?memmove)\b',asm))}
        entry['get_no_materialization_O2']=True
        edit=entry['optimizations']['2']['functions']['table_edit']
        entry['edit_has_bulk_copies_O2']=bool(edit['memcpy_sites']+edit['memmove_sites'])
        report['capacities'][str(n)]=entry
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f'{n} slots: O0/O2 acceptance passed; IR and assembly saved.',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/table-cost');p.add_argument('--clang',default='clang')
    p.add_argument('--capacity',type=int,choices=(64,4096),action='append')
    a=p.parse_args();r=inspect(a.output,a.clang,a.capacity or (64,4096))
    print('Target: '+r['target'])
