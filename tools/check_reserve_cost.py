"""Audit explicit reserve: runtime counts, untouched tail, failure and no-op paths."""
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

SOURCE='''fn exercise(capacity:u32,requested:u32,seed:u64)->u32:alloc {
  match memory.create(1048576){Err(e)=>{return 1} Ok(region)=>{
    match vec.with_capacity<u64>(region,capacity){
      Err(e)=>{c=memory.close(move region)\nreturn 2}
      Ok(initial)=>{
        (filled,pushed)=vec.push(move initial,seed)
        (next,status)=vec.reserve(move filled,region,requested)
        var error=0
        match status {Ok(done)=>{} Err(reason)=>{error=3}}
        var expected=capacity
        if requested>capacity {expected=requested}
        if vec.capacity(next)!=expected || vec.len(next)!=1 {error=4}
        {v=vec.view(next)\nif v[0]!=seed {error=5}}
        x=vec.release(move next)
        c=memory.close(move region)
        return error
      }
    }
  }}
}
fn main()->u32{return 0}
'''

HARNESS=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
static size_t allocations=0,releases=0,copies=0,copied_bytes=0;
static void *counted_malloc(size_t n){allocations++;void *p=malloc(n);if(p)memset(p,0xa5,n);return p;}
static void counted_free(void *p){releases++;free(p);}
static void *counted_copy(void *to,const void *from,size_t bytes){copies++;copied_bytes+=bytes;return memcpy(to,from,bytes);}
#define malloc counted_malloc
#define free counted_free
#define memcpy counted_copy
#include "MEMORY_RUNTIME"
#undef memcpy
#undef malloc
#undef free
extern uint32_t liza_exercise(uint32_t,uint32_t,uint64_t);
#define REQUIRE(condition, code) do {if(!(condition))return code;} while(0)
int main(int argc,char **argv){
  uint64_t seed=argc>1?strtoull(argv[1],NULL,10):42;
  const uint32_t capacities[]={64,4096,16384};
  for(unsigned i=0;i<3;i++){
    size_t ac=allocations,fr=releases,cp=copies,bytes=copied_bytes;
    REQUIRE(liza_exercise(capacities[i],capacities[i]*2,seed)==0,10+i);
    REQUIRE(allocations==ac+1 && releases==fr+1,20+i);
    REQUIRE(copies==cp+1 && copied_bytes==bytes+sizeof(uint64_t),30+i);
    cp=copies;bytes=copied_bytes;
    REQUIRE(liza_exercise(capacities[i],capacities[i],seed)==0,40+i);
    REQUIRE(liza_exercise(capacities[i],0,seed)==0,50+i);
    REQUIRE(copies==cp && copied_bytes==bytes,60+i);
  }
  uint32_t error=0;
  void *r=liza_rt_region_create(128,&error);
  REQUIRE(r && !error,70);
  unsigned char *old=liza_rt_region_alloc(r,8,8,2,&error);
  REQUIRE(old && !error,71);
  memcpy(old,&seed,8);
  size_t ac=allocations,used=((LizaRegion*)r)->used,cp=copies,bytes=copied_bytes;
  unsigned char *next=liza_rt_vec_reserve(r,old,8,8,1,2,4,&error);
  REQUIRE(!error && next!=old && !memcmp(next,&seed,8),72);
  REQUIRE(allocations==ac && copies==cp+1 && copied_bytes==bytes+8,73);
  REQUIRE(((uintptr_t)next%8)==0 && ((LizaRegion*)r)->used==used+32,74);
  for(unsigned i=8;i<32;i++)REQUIRE(next[i]==0xa5,75);
  used=((LizaRegion*)r)->used;cp=copies;bytes=copied_bytes;
  REQUIRE(liza_rt_vec_reserve(r,next,8,8,1,4,32,&error)==next && error==2,76);
  REQUIRE(((LizaRegion*)r)->used==used && copies==cp && copied_bytes==bytes,77);
  REQUIRE(liza_rt_vec_reserve(r,next,UINT64_MAX,8,1,4,8,&error)==next && error==3,78);
  REQUIRE(((LizaRegion*)r)->used==used && copies==cp,79);
  REQUIRE(liza_rt_vec_reserve(r,next,8,8,1,4,4,&error)==next && !error,80);
  REQUIRE(liza_rt_vec_reserve(r,next,8,8,1,4,0,&error)==next && !error,81);
  REQUIRE(((LizaRegion*)r)->used==used && copies==cp && allocations==ac,82);
  /* Retry after failures: exactly the remaining 80 bytes must still fit. */
  REQUIRE(liza_rt_vec_reserve(r,next,8,8,1,4,10,&error)!=next && !error,83);
  REQUIRE(((LizaRegion*)r)->used==128 && allocations==ac,84);
  liza_rt_region_close(r);
  r=liza_rt_region_create(40,&error);
  REQUIRE(r && !error,85);
  REQUIRE(liza_rt_region_alloc(r,1,1,1,&error)!=NULL && !error,86);
  old=liza_rt_region_alloc(r,8,8,0,&error);cp=copies;
  next=liza_rt_vec_reserve(r,old,8,8,0,0,4,&error);
  REQUIRE(!error && ((uintptr_t)next%8)==0 && copies==cp && ((LizaRegion*)r)->used==40,87);
  for(unsigned i=0;i<32;i++)REQUIRE(next[i]==0xa5,88);
  liza_rt_region_close(r);
  r=liza_rt_region_create(0,&error);
  old=liza_rt_region_alloc(r,0,1,0,&error);cp=copies;
  REQUIRE(liza_rt_vec_reserve(r,old,0,1,0,0,UINT32_MAX,&error)==old && !error,89);
  REQUIRE(((LizaRegion*)r)->used==0 && copies==cp,90);
  liza_rt_region_close(r);
  return 0;
}
'''


def inspect(output,clang='clang'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    module=lower(Parser(SOURCE).parse())
    ir=output/'reserve.ll';ir.write_text(llvm(module).replace('define i32 @main()','define i32 @example_entry()'))
    (output/'reserve.liza').write_text(SOURCE)
    harness=output/'checks.c';harness.write_text(HARNESS.replace('MEMORY_RUNTIME',(ROOT/'liza/runtime/memory.c').as_posix()))
    report={'target':subprocess.check_output([clang,'-dumpmachine'],text=True).strip(),'capacities':[64,4096,16384],'optimizations':{}}
    for opt in (0,2):
        optimized=output/f'reserve.O{opt}.ll';assembly=output/f'reserve.O{opt}.s'
        for flags,dest in [(['-S','-emit-llvm'],optimized),(['-S'],assembly)]:
            subprocess.run([clang,'-Wno-override-module',f'-O{opt}',*flags,str(ir),'-o',str(dest)],check=True,capture_output=True,timeout=120)
        text=optimized.read_text()
        assert '@liza_rt_vec_reserve' in text
        # Scalar element path: all data copying belongs to the explicit runtime operation.
        assert not re.search(r'call[^\n]*@llvm.mem(?:cpy|move)',text)
        runtime_ir=output/f'runtime.O{opt}.ll';runtime_asm=output/f'runtime.O{opt}.s'
        for flags,dest in [(['-S','-emit-llvm'],runtime_ir),(['-S'],runtime_asm)]:
            subprocess.run([clang,f'-O{opt}',*flags,str(ROOT/'liza/runtime/memory.c'),'-o',str(dest)],check=True,capture_output=True,timeout=120)
        body=re.search(r'^define [^\n]*@liza_rt_vec_reserve\([^\n]*\)[^\n]*\{\n(.*?)^}',runtime_ir.read_text(),re.M|re.S)
        assert body and not re.search(r'@(?:malloc|calloc|realloc|free)\b',body.group())
        exe=output/(f'reserve.O{opt}'+('.exe' if sys.platform=='win32' else ''))
        subprocess.run([clang,'-Wno-override-module',f'-O{opt}',str(ir),str(harness),'-o',str(exe)],check=True,capture_output=True,timeout=120)
        for seed in ('17','18446744073709551615'):
            result=subprocess.run([str(exe.resolve()),seed],capture_output=True,timeout=15)
            assert result.returncode==0,(opt,result.returncode,result.stderr)
        report['optimizations'][str(opt)]={'one_region_heap_allocation':True,'growth_copies_only_initialized_prefix':True,'noop_no_allocation_or_copy':True,'unused_tail_untouched':True,'alignment_overflow_failure_atomicity':True,'runtime_inputs':True}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('O0/O2: explicit reserve preserves failures, copies only len, leaves tail untouched, and adds no heap allocation')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/reserve-cost');parser.add_argument('--clang',default='clang')
    args=parser.parse_args();inspect(args.output,args.clang)
