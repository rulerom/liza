"""Streaming runtime-input probe; the opaque C bridge is only test infrastructure."""
import argparse
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

SOURCE='''
fn status(s:Utf8StreamState)->u32 {
    match utf8_stream.finish(s) {
        Ok(n)=>{return 0}
        Err(e)=>{match e.kind {
            Utf8StreamErrorKind.InvalidEncoding=>{return 1}
            Utf8StreamErrorKind.SizeOverflow=>{return 2}
        }}
    }
}
fn value(s:Utf8StreamState)->u64 {
    match utf8_stream.finish(s) {Ok(n)=>{return n} Err(e)=>{return e.offset}}
}
fn start()->Utf8StreamState {return utf8_stream.create()}
fn feed(s:Utf8StreamState,v:View<u8>)->Utf8StreamState {return utf8_stream.feed(s,v)}
fn main()->u32 {return 0}
'''
BRIDGE='''
define void @stream_start(ptr %out) {
  %s = call %struct.Utf8StreamState @liza_utf8_stream.create()
  store %struct.Utf8StreamState %s, ptr %out
  ret void
}
define void @stream_feed(ptr %state, ptr %bytes, i32 %length) {
  %s = load %struct.Utf8StreamState, ptr %state
  %a = insertvalue { ptr, i32 } zeroinitializer, ptr %bytes, 0
  %v = insertvalue { ptr, i32 } %a, i32 %length, 1
  %n = call %struct.Utf8StreamState @liza_utf8_stream.feed(%struct.Utf8StreamState %s, { ptr, i32 } %v)
  store %struct.Utf8StreamState %n, ptr %state
  ret void
}
define i32 @stream_status(ptr %state) {
  %s = load %struct.Utf8StreamState, ptr %state
  %r = call i32 @liza_status(%struct.Utf8StreamState %s)
  ret i32 %r
}
define i64 @stream_value(ptr %state) {
  %s = load %struct.Utf8StreamState, ptr %state
  %r = call i64 @liza_value(%struct.Utf8StreamState %s)
  ret i64 %r
}
'''
HARNESS=r'''
#include <stdint.h>
#include <stdio.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
extern void stream_start(void*);
extern void stream_feed(void*,const uint8_t*,uint32_t);
extern uint32_t stream_status(const void*);
extern uint64_t stream_value(const void*);
static uint8_t bytes[5000000];
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
int main(void) {
#ifdef _WIN32
    _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
#endif
    uint8_t header[4],out[12];size_t n;
    while((n=fread(header,1,4,stdin))!=0) {
        if(n!=4)return 1;
        uint32_t chunks=word(header);uint64_t state[8];stream_start(state);
        for(uint32_t i=0;i<chunks;i++) {
            if(fread(header,1,4,stdin)!=4)return 2;
            uint32_t size=word(header);
            if(size>sizeof(bytes)||fread(bytes,1,size,stdin)!=size)return 3;
            stream_feed(state,bytes,size);
            // finish is a snapshot, not a destructive EOF transition.
            (void)stream_status(state);(void)stream_value(state);
        }
        uint32_t status=stream_status(state);uint64_t value=stream_value(state);
        for(int i=0;i<4;i++)out[i]=(uint8_t)(status>>(i*8));
        for(int i=0;i<8;i++)out[4+i]=(uint8_t)(value>>(i*8));
        if(fwrite(out,1,12,stdout)!=12)return 4;
    }
    return ferror(stdin)?5:0;
}
'''


def build(output,opt,clang='clang'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    module=lower(Parser(SOURCE).parse())
    assert not link_flags(module)
    ir=output/'stream.ll'
    ir.write_text(llvm(module).replace('define i32 @main()','define i32 @example_entry()')+BRIDGE)
    c=output/'harness.c';c.write_text(HARNESS)
    exe=output/('probe.exe' if sys.platform=='win32' else 'probe')
    subprocess.run([clang,'-Wno-override-module',opt,str(ir),str(c),'-o',str(exe)],check=True,capture_output=True)
    return exe,ir


def probe(exe,cases):
    wire=b''.join(struct.pack('<I',len(chunks))+b''.join(struct.pack('<I',len(c))+c for c in chunks) for chunks in cases)
    r=subprocess.run([str(exe)],input=wire,capture_output=True,timeout=60)
    assert r.returncode==0,(r.returncode,r.stderr)
    assert len(r.stdout)==12*len(cases)
    return list(struct.iter_unpack('<IQ',r.stdout))


def inspect(output,clang='clang'):
    output=Path(output)
    for opt in ('-O0','-O2'):
        folder=output/opt[1:];exe,ir=build(folder,opt,clang)
        for flags,suffix in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
            target=folder/('optimized.'+suffix)
            subprocess.run([clang,'-Wno-override-module',opt,*flags,str(ir),'-o',str(target)],check=True,capture_output=True)
            text=target.read_text()
            assert not re.search(r'\b_?(malloc|calloc|realloc|free|memcpy|memmove)\b',text),'allocation or bulk copy'
            if suffix=='ll':
                assert re.search(r'load i8\b',text),'runtime byte reads disappeared'
                assert not re.search(r'alloca \[\d+ x i8\]',text),'chunk materialization'
        assert probe(exe,[[b'A\xf0',b'',b'\x9f\x98',b'\x80'],[b'A\xed',b'\xa0\x80'],[b'A\xe2']])==[(0,2),(1,1),(1,1)]
    report='O0/O2: streaming UTF-8 reads runtime chunks; no heap calls or bulk chunk copies in LLVM and assembly.\n'
    (output/'report.txt').write_text(report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='build/utf8-stream-cost')
    parser.add_argument('--clang',default='clang');args=parser.parse_args()
    print(inspect(args.output,args.clang),end='')
