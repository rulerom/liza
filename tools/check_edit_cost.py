"""Owned edit/loop cost gate, including cold snapshot in amortized timings.

C is only an independent reference and scalar benchmark driver, not a compiler
backend. All table operations and the measured update loop are Liza programs.
"""
import argparse
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.check_table_cost import source_for, function_body, ROOT
from liza.frontend import Parser
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm

HARNESS=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
extern uint64_t liza_edit_rounds(void *,uint32_t,uint32_t);
extern uint64_t table_bytes(void);
extern void table_initialize(void *,uint32_t);
int main(int argc,char **argv) {
    if(argc!=4) return 90;
    uint32_t n=(uint32_t)strtoul(argv[1],0,10), seed=(uint32_t)strtoul(argv[2],0,10);
    uint32_t rounds=(uint32_t)strtoul(argv[3],0,10), state=seed;
    uint64_t *counts=calloc(n,sizeof(uint64_t)), expected=0;
    if(!counts) return 91;
    for(uint32_t i=0;i<rounds;i++) {
        state=state*UINT32_C(1664525)+UINT32_C(1013904223);
        expected+=counts[(state>>16)%n]++;
    }
    free(counts);
    size_t bytes=(size_t)table_bytes();
    void *table=malloc(bytes), *snapshot=malloc(bytes);
    if(!table || !snapshot) return 93;
    table_initialize(table,n);memcpy(snapshot,table,bytes);
    for(int trial=0;trial<6;trial++) {
        clock_t start=clock();
        uint64_t actual=liza_edit_rounds(table,seed,rounds);
        double ns=1e9*(double)(clock()-start)/CLOCKS_PER_SEC/rounds;
        if(actual!=expected || memcmp(table,snapshot,bytes)) {fprintf(stderr,"checksum mismatch\n");return 92;}
        if(trial) printf("%.4f\n",ns);
    }
    free(table);free(snapshot);return 0;
}
'''


BRIDGE=r'''
define i64 @table_bytes() {
entry:
  ret i64 ptrtoint (ptr getelementptr (%struct.ConnectionTable, ptr null, i32 1) to i64)
}
define void @table_initialize(ptr %table, i32 %n) {
entry:
  call void @llvm.memset.p0.i64(ptr %table, i8 0, i64 ptrtoint (ptr getelementptr (%struct.ConnectionTable, ptr null, i32 1) to i64), i1 false)
  br label %loop
loop:
  %i = phi i32 [0, %entry], [%next, %loop]
  %slot = getelementptr %struct.ConnectionTable, ptr %table, i32 0, i32 0, i32 %i
  store %struct.ConnectionSlot { i32 1, i1 true, i1 false, %struct.Connection { i64 0, i32 0, i64 0 } }, ptr %slot
  %next = add i32 %i, 1
  %done = icmp eq i32 %next, %n
  br i1 %done, label %exit, label %loop
exit:
  ret void
}
'''


def cyclic_blocks(body):
    # LLVM labels may carry predecessor comments after optimization.
    chunks=re.split(r'^([\w.$-]+):[^\n]*\n',body,flags=re.M)
    blocks={chunks[i]:chunks[i+1] for i in range(1,len(chunks),2)}
    edges={n:set(re.findall(r'label %([\w.$-]+)',text)) for n,text in blocks.items()}
    def reaches(start,target):
        pending=list(edges[start]);seen=set()
        while pending:
            node=pending.pop()
            if node==target:return True
            if node in seen:continue
            seen.add(node);pending.extend(edges.get(node,()))
        return False
    return {n:text for n,text in blocks.items() if reaches(n,n)}


def inspect(output,clang='clang',capacities=(64,4096,16384),modular=False,generic=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    report={'target':subprocess.check_output([clang,'-dumpmachine'],text=True).strip(),
            'note':'CPU clock ns/update includes cold phi copies per invocation; fixture initialization is outside timing. Input snapshot remains unchanged. Five trials after warmup; no timing threshold. Runtime LCG indices, checksum checked against independent C reference.',
            'modular':modular, 'generic':generic,
            'capacities':{}}
    for n in capacities:
        root=output/str(n);root.mkdir(exist_ok=True)
        if generic:
            (root/'tables').mkdir(exist_ok=True)
            (root/'tables/value_table.liza').write_text((ROOT/'examples/tables/value_table.liza').read_text())
            probe=(ROOT/'tests/fixtures/table_edit_rounds.liza').read_text()
            probe=probe.replace('table.slots.len',str(n))
            probe=probe.replace('table_get(', 'tables.value_table.get(').replace('table_edit(', 'tables.value_table.edit(')
            probe=probe.replace('ConnectionTable',f'tables.value_table.Table<Connection,{n}>').replace('ConnectionId(', 'tables.value_table.ConnectionId(')
            (root/'probe.liza').write_text('import tables.value_table\nstruct Connection { pub user_id:u64, pub state:u32, pub packets:u64 }\n'+probe+'\nfn main()->u32{return 0}\n')
            module=lower(load_program(root/'probe.liza'))
            symbols={i['declaration']:i['symbol'] for i in module.specializations}
            loop_name='probe.edit_rounds';owned_name='__liza_owned_'+symbols['tables.value_table.edit']
            bridge=BRIDGE.replace('%struct.ConnectionTable','%struct.'+symbols['tables.value_table.Table']).replace('%struct.ConnectionSlot','%struct.'+symbols['tables.value_table.Slot']).replace('%struct.Connection','%struct.probe.Connection')
        elif modular:
            library=(ROOT/'examples/tables/connections.liza').read_text()
            library=library.replace('[ConnectionSlot; 64]',f'[ConnectionSlot; {n}]')
            # Fixture initializes through a target-layout bridge; exclude the
            # unused large literal constructor from this measured compilation.
            library=library[:library.index('pub fn empty()')]+library[library.index('fn slot_matches('):]
            (root/'tables').mkdir(exist_ok=True)
            (root/'tables/connections.liza').write_text(library)
            probe=(ROOT/'tests/fixtures/table_edit_rounds.liza').read_text()
            probe=probe.replace('table.slots.len',str(n))
            probe=probe.replace('table_get(', 'tables.connections.get(').replace('table_edit(', 'tables.connections.edit(')
            probe=re.sub(r'\b(ConnectionTable|ConnectionId|Connection)\b',r'tables.connections.\1',probe)
            (root/'probe.liza').write_text('import tables.connections\n'+probe+'\nfn main()->u32{return 0}\n')
            module=lower(load_program(root/'probe.liza'))
            loop_name='probe.edit_rounds';owned_name='__liza_owned_tables.connections.edit'
            bridge=BRIDGE.replace('%struct.Connection','%struct.tables.connections.Connection')
        else:
            source=source_for(n).split('fn main()')[0]
            source=source[:source.index('fn table_empty()')]+source[source.index('fn slot_matches('):]
            source+=(ROOT/'tests/fixtures/table_edit_rounds.liza').read_text()+'\nfn main()->u32{return 0}\n'
            (root/'edit.liza').write_text(source)
            module=lower(Parser(source).parse())
            loop_name='edit_rounds';owned_name='__liza_owned_table_edit';bridge=BRIDGE
        raw=llvm(module).replace('define i32 @main()', 'define i32 @example_entry()')
        if modular or generic:
            raw+='\ndefine i64 @liza_edit_rounds(ptr %input, i32 %seed, i32 %rounds) {\nentry:\n  %value = call i64 @liza_probe.edit_rounds(ptr %input, i32 %seed, i32 %rounds)\n  ret i64 %value\n}\n'
        # A private test bridge initializes the input using LLVM's target layout.
        # No C layout assumption or aggregate ABI, and no edit algorithm here.
        if 'declare void @llvm.memset.p0.i64' not in raw:
            raw+='\ndeclare void @llvm.memset.p0.i64(ptr, i8, i64, i1)\n'
        raw+=bridge
        ir=root/'edit.ll';ir.write_text(raw)
        # Prove backend storage reuse before LLVM optimization: no bulk copies
        # on any cycle and no copies inside the selected owned implementation.
        loop=function_body(raw,loop_name)
        assert owned_name in loop
        assert cyclic_blocks(loop), 'probe must retain a runtime loop'
        for body in cyclic_blocks(loop).values():
            assert not re.search(r'@llvm.mem(?:cpy|move)',body), 'copy on loop cycle'
        owned=function_body(raw,owned_name)
        assert not re.search(r'@llvm.mem(?:cpy|move)',owned), 'copy inside owned edit'
        c=root/'driver.c';c.write_text(HARNESS)
        entry={}
        for opt in (0,2):
            optimized=root/f'edit.O{opt}.ll';assembly=root/f'edit.O{opt}.s'
            for flags,dest in [(['-S','-emit-llvm'],optimized),(['-S'],assembly)]:
                subprocess.run([clang,'-Wno-override-module',f'-O{opt}',*flags,str(ir),'-o',str(dest)],check=True,capture_output=True,timeout=240)
            text=optimized.read_text();owned=function_body(text,owned_name)
            assert not re.search(r'@llvm.mem(?:cpy|move)',owned)
            body=function_body(text,loop_name)
            for block in cyclic_blocks(body).values():
                assert not re.search(r'@llvm.mem(?:cpy|move)',block), 'optimized loop copies aggregate'
            # Keep both complete machine code and isolated owned edit for review.
            asm=assembly.read_text()
            machine=re.search(r'^"?_?liza_'+re.escape(owned_name)+r'"?:.*?\n(.*?)(?=^\s*\.cfi_endproc|^\s*\.seh_endproc|^\s*\.size|^[ \t]*[;#] -- End function)',asm,re.M|re.S)
            assert machine, 'missing owned machine function'
            assert not re.search(r'\b_?mem(?:cpy|move)\b',machine.group(0))
            (root/f'owned_edit.O{opt}.s').write_text(machine.group(0)+'\n')
            (root/f'owned_edit.O{opt}.ll').write_text(owned+'\n')
            exe=root/(f'edit.O{opt}'+('.exe' if sys.platform=='win32' else ''))
            stack=['-Wl,/stack:33554432'] if sys.platform=='win32' else []
            subprocess.run([clang,'-Wno-override-module',f'-O{opt}',str(ir),str(c),*stack,'-o',str(exe)],check=True,capture_output=True,timeout=240)
            samples=[]
            for seed in (17,4294967295):
                result=subprocess.run([str(exe.resolve()),str(n),str(seed),'1000000'],capture_output=True,text=True,timeout=180)
                if result.returncode:raise AssertionError(f'{n}/O{opt}: {result.returncode} {result.stderr}')
                samples.extend(float(v) for v in result.stdout.splitlines())
            entry[str(opt)]={'ns_per_update_samples':samples,'median_ns_per_update':statistics.median(samples),
                             'owned_edit_no_bulk_copy':True,'loop_no_bulk_copy':True,
                             'owned_edit_machine_lines':len(machine.group(0).splitlines()),
                             'cold_copy_sites':len(re.findall(r'@llvm.mem(?:cpy|move)',body))}
        report['capacities'][str(n)]=entry
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f'{n}: O0/O2 checksums and no-copy cycle passed; O2 median {entry["2"]["median_ns_per_update"]:.2f} ns/update (including amortized cold snapshot)',flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/edit-cost');p.add_argument('--clang',default='clang')
    p.add_argument('--capacity',type=int,choices=(64,4096,16384),action='append')
    p.add_argument('--modules',action='store_true',help='exercise public table API through whole-program imports')
    p.add_argument('--generics',action='store_true',help='exercise monomorphized Table<T,N>')
    a=p.parse_args();inspect(a.output,a.clang,a.capacity or (64,4096,16384),a.modules,a.generics)
