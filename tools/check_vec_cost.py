"""Bounded vector runtime-input cost gate, with counted region allocations."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm

SOURCE='''fn reserve(capacity:u32)->u32:alloc {
  match memory.create(u64(capacity)*8){Err(e)=>{return 1} Ok(region)=>{
    match vec.with_capacity<u64>(region,capacity){Err(e)=>{c=memory.close(move region)\nreturn 2} Ok(v)=>{x=vec.release(move v)}}
    c=memory.close(move region)\nreturn 0
  }}
}
fn cycle(v:vec.Vec<u64>,index:u32,value:u64)->vec.Vec<u64> {
    (updated,status)=vec.set(move v,index,value)
    (shorter,item)=vec.pop(move updated)
    match item {
      Some(previous)=>{
        (restored,pushed)=vec.push(move shorter,previous +% 1)
        return move restored
      }
      None=>{return move shorter}
    }
}
fn exercise(capacity:u32,iterations:u32,seed:u64)->u32:alloc {
    match memory.create(u64(capacity)*8) {Err(e)=>{return 1} Ok(region)=>{
      match vec.with_capacity<u64>(region,capacity) {
        Err(e)=>{c=memory.close(move region)\nreturn 2}
        Ok(initial)=>{
          (filled,status)=vec.push(move initial,seed)
          var current=move filled
          var i=0
          while i<iterations {
            current=cycle(move current,0,seed +% u64(i))
            i=i+1
          }
          var error=0
          {data=vec.view(current)
            if data[0] != seed +% u64(iterations) {error=3}
          }
          x=vec.release(move current)
          c=memory.close(move region)
          return error
        }
      }
    }}}
fn main()->u32{return 0}
'''
HARNESS=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
static int allocations=0,releases=0,fail=0,inspect_tail=0,tail_changed=0;
static size_t last_size;
static void *counted_malloc(size_t size){allocations++;if(fail)return NULL;void *p=malloc(size);if(p)memset(p,0xa5,size);last_size=size;return p;}
static void counted_free(void *p){releases++;if(inspect_tail){unsigned char *bytes=p;for(size_t i=last_size-4096*8;i<last_size;i++)if(bytes[i]!=0xa5)tail_changed=1;}free(p);}
#define malloc counted_malloc
#define free counted_free
#include "MEMORY_RUNTIME"
#undef malloc
#undef free
extern uint32_t liza_reserve(uint32_t);
extern uint32_t liza_exercise(uint32_t,uint32_t,uint64_t);
int main(int argc,char **argv){
  uint64_t seed=argc>1?strtoull(argv[1],NULL,10):42;
  const uint32_t capacities[]={64,4096,16384};
  for(unsigned i=0;i<3;i++){
    if(liza_exercise(capacities[i],10000,seed)!=0)return 10+i;
    if(allocations!=(int)i+1||releases!=(int)i+1)return 20+i;
  }
  inspect_tail=1;
  if(liza_reserve(4096)!=0||tail_changed||allocations!=4||releases!=4)return 29;
  inspect_tail=0;
  fail=1;
  if(liza_exercise(64,10000,seed)!=1||allocations!=5||releases!=4)return 30;
  return 0;
}
'''


def inspect(output,clang='clang'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    module=lower(Parser(SOURCE).parse())
    raw=llvm(module).replace('define i32 @main()','define i32 @example_entry()')
    ir=output/'vectors.ll';ir.write_text(raw)
    (output/'vectors.liza').write_text(SOURCE)
    harness=output/'runtime_checks.c'
    harness.write_text(HARNESS.replace('MEMORY_RUNTIME',(ROOT/'liza/runtime/memory.c').as_posix()))
    report={'target':subprocess.check_output([clang,'-dumpmachine'],text=True).strip(),'capacities':[64,4096,16384],'iterations':10000,'optimizations':{}}
    for opt in (0,2):
        optimized=output/f'vectors.O{opt}.ll';assembly=output/f'vectors.O{opt}.s'
        for flags,dest in [(['-S','-emit-llvm'],optimized),(['-S'],assembly)]:
            subprocess.run([clang,'-Wno-override-module',f'-O{opt}',*flags,str(ir),'-o',str(dest)],check=True,capture_output=True,timeout=120)
        body=re.search(r'^define [^\n]*@liza_cycle\([^\n]*\)[^\n]*\{\n(.*?)^}',optimized.read_text(),re.M|re.S)
        assert body,'cycle LLVM body'
        assert not re.search(r'@(?:llvm.mem(?:cpy|move)|liza_rt_region_|malloc|calloc|realloc)',body.group())
        (output/f'cycle.O{opt}.ll').write_text(body.group()+'\n')
        machine=re.search(r'^_?liza_cycle:.*?\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.seh_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',assembly.read_text(),re.M|re.S)
        assert machine,'cycle assembly'
        assert not re.search(r'\b_?(?:memcpy|memmove|malloc|calloc|realloc|liza_rt_region_alloc)\b',machine.group())
        (output/f'cycle.O{opt}.s').write_text(machine.group()+'\n')
        exe=output/(f'vectors.O{opt}'+('.exe' if sys.platform=='win32' else ''))
        subprocess.run([clang,'-Wno-override-module',f'-O{opt}',str(ir),str(harness),'-o',str(exe)],check=True,capture_output=True,timeout=120)
        for seed in ('17','18446744073709551615'):
            result=subprocess.run([str(exe.resolve()),seed],capture_output=True,timeout=15)
            assert result.returncode==0,(opt,result.returncode,result.stderr)
        report['optimizations'][str(opt)]={'one_allocation_per_region':True,'injected_allocation_failure':True,'cycle_no_allocation_or_bulk_copy':True,'runtime_inputs':True,'unused_capacity_untouched':True}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('O0/O2: bounded Vec runtime inputs, one region allocation, no allocation/bulk copy in set/pop/push cycle passed')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/vec-cost');parser.add_argument('--clang',default='clang')
    args=parser.parse_args();inspect(args.output,args.clang)
