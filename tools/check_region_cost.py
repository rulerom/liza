"""Check region runtime failures, alignment and allocation-free update/view paths."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm

SOURCE='''fn update(b:memory.Buffer<u64>,i:u32,x:u64)->memory.Buffer<u64>{return memory.set(move b,i,x)}
fn first(data:View<u64>)->u64{return data[0]}
fn main()->u32:alloc {
match memory.create(64){Err(e)=>{return 1} Ok(r)=>{
match memory.alloc<u64>(r,8,7){Err(e)=>{c=memory.close(move r)\nreturn 2} Ok(initial)=>{
var b=move initial
var i=0
while i<8 {b=update(move b,i,u64(i))\ni=i+1}
var result=0
{v=memory.view(b)\nif first(v)!=0 || v[7]!=7 {result=3}}
x=memory.release(move b)
c=memory.close(move r)
return result
}}}}}'''

HARNESS=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
static int failing=0, allocations=0, releases=0;
static void *counted_malloc(size_t n){allocations++;return failing?NULL:malloc(n);}
static void counted_free(void *p){releases++;free(p);}
#define malloc counted_malloc
#define free counted_free
#include "MEMORY_RUNTIME"
#undef malloc
#undef free
extern uint32_t liza_main(void);
int main(void){
    if(liza_main()!=0 || allocations!=1 || releases!=1)return 10;
    failing=1;
    if(liza_main()!=1 || allocations!=2 || releases!=1)return 11;
    failing=0;
    uint32_t error=0;
    if(liza_rt_region_create(UINT64_MAX,&error)!=NULL || error!=3)return 12;
    void *r=liza_rt_region_create(32,&error);
    if(!r || error)return 13;
    if(!liza_rt_region_alloc(r,1,1,1,&error) || error)return 14;
    if(liza_rt_region_alloc(r,UINT64_MAX,8,2,&error)!=NULL || error!=3)return 15;
    if(liza_rt_region_alloc(r,8,8,4,&error)!=NULL || error!=2)return 16;
    void *data=liza_rt_region_alloc(r,8,8,3,&error);
    if(!data || error || ((uintptr_t)data%8)!=0)return 17;
    if(liza_rt_region_alloc(r,1,1,1,&error)!=NULL || error!=2)return 18;
    liza_rt_region_close(r);
    return 0;
}
'''


def inspect(output,clang='clang'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    module=lower(Parser(SOURCE).parse())
    raw=llvm(module).replace('define i32 @main()','define i32 @example_entry()')
    ir=output/'regions.ll';ir.write_text(raw)
    (output/'regions.liza').write_text(SOURCE)
    harness=output/'runtime_checks.c'
    harness.write_text(HARNESS.replace('MEMORY_RUNTIME',(ROOT/'liza/runtime/memory.c').as_posix()))
    report={'target':subprocess.check_output([clang,'-dumpmachine'],text=True).strip(),'optimizations':{}}
    for opt in (0,2):
        optimized=output/f'regions.O{opt}.ll';assembly=output/f'regions.O{opt}.s'
        for flags,dest in [(['-S','-emit-llvm'],optimized),(['-S'],assembly)]:
            subprocess.run([clang,'-Wno-override-module',f'-O{opt}',*flags,str(ir),'-o',str(dest)],check=True,capture_output=True,timeout=120)
        text=optimized.read_text()
        for name in ('update','first'):
            body=re.search(r'^define [^\n]*@liza_'+name+r'\([^\n]*\)[^\n]*\{\n(.*?)^}',text,re.M|re.S)
            assert body,name
            assert not re.search(r'@(?:llvm.mem(?:cpy|move)|liza_rt_region_|malloc|calloc|realloc)',body.group()),name
            (output/f'{name}.O{opt}.ll').write_text(body.group()+'\n')
            machine=re.search(r'^_?liza_'+name+r':.*?\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.seh_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',assembly.read_text(),re.M|re.S)
            assert machine, name
            assert not re.search(r'\b_?(?:memcpy|memmove|malloc|calloc|realloc|liza_rt_region_alloc)\b',machine.group()),name
            (output/f'{name}.O{opt}.s').write_text(machine.group()+'\n')
        exe=output/(f'regions.O{opt}'+('.exe' if sys.platform=='win32' else ''))
        subprocess.run([clang,'-Wno-override-module',f'-O{opt}',str(ir),str(harness),'-o',str(exe)],check=True,capture_output=True,timeout=120)
        result=subprocess.run([str(exe.resolve())],capture_output=True,timeout=10)
        assert result.returncode==0,(opt,result.returncode,result.stderr)
        report['optimizations'][str(opt)]={'allocation_count':1,'close_count':1,'injected_failure_checked':True,'alignment_overflow_failure_atomicity_checked':True,'update_view_no_allocation_or_bulk_copy':True}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('O0/O2: region failure, alignment, size overflow, atomicity and allocation-free update/view passed')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/region-cost');parser.add_argument('--clang',default='clang')
    args=parser.parse_args();inspect(args.output,args.clang)
