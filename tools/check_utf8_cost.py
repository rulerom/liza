"""Runtime-input UTF-8 probe and allocation/copy inspection at O0/O2.

The C/LLVM bridge is test infrastructure, not a language FFI API.
"""
import argparse
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

SOURCE = '''
fn error_code(error:Utf8Error)->u64 {
    var kind:u64=0
    match error.kind {
        Utf8ErrorKind.InvalidEncoding=>{kind=1}
        Utf8ErrorKind.OutOfBounds=>{kind=2}
        Utf8ErrorKind.NotBoundary=>{kind=3}
        Utf8ErrorKind.ReversedRange=>{kind=4}
    }
    return 9223372036854775808 | (kind << 32) | u64(error.offset)
}
fn probe(data:View<u8>, operation:u32, index:u32, end:u32)->u64 {
    if operation==0 {
        match utf8.validate(data) {Ok(done)=>{return 0} Err(e)=>{return error_code(e)}}
    }
    if operation==1 {
        match utf8.count(data) {Ok(n)=>{return u64(n)} Err(e)=>{return error_code(e)}}
    }
    if operation==2 || operation==3 {
        match utf8.next(data,index) {
            Err(e)=>{return error_code(e)}
            Ok(item)=>{match item {
                None=>{return 4611686018427387904}
                Some(step)=>{if operation==2{return u64(step.value)}return u64(step.next)}
            }}
        }
    }
    if operation==4 {
        match utf8.is_boundary(data,index) {Err(e)=>{return error_code(e)} Ok(b)=>{if b{return 1}return 0}}
    }
    match utf8.range(data,index,end) {
        Err(e)=>{return error_code(e)}
        Ok(r)=>{return (u64(r.start) << 32) | u64(r.end)}
    }
}
fn main()->u32 {return 0}
'''

BRIDGE = '''
define i64 @utf8_probe(ptr %data, i32 %length, i32 %operation, i32 %index, i32 %end) {
  %a = insertvalue { ptr, i32 } zeroinitializer, ptr %data, 0
  %b = insertvalue { ptr, i32 } %a, i32 %length, 1
  %r = call i64 @liza_probe({ ptr, i32 } %b, i32 %operation, i32 %index, i32 %end)
  ret i64 %r
}
'''
HARNESS = r'''
#include <stdint.h>
#include <stdio.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
extern uint64_t utf8_probe(const uint8_t*,uint32_t,uint32_t,uint32_t,uint32_t);
static uint8_t data[5000000];
static uint32_t little(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
int main(void) {
#ifdef _WIN32
    _setmode(_fileno(stdin),_O_BINARY); _setmode(_fileno(stdout),_O_BINARY);
#endif
    uint8_t header[16],out[8]; size_t n;
    while((n=fread(header,1,16,stdin))!=0) {
        if(n!=16)return 1;
        uint32_t length=little(header+12);
        if(length>sizeof(data)||fread(data,1,length,stdin)!=length)return 2;
        uint64_t result=utf8_probe(data,length,little(header),little(header+4),little(header+8));
        for(int j=0;j<8;j++)out[j]=(uint8_t)(result>>(j*8));
        if(fwrite(out,1,8,stdout)!=8)return 3;
    }
    return ferror(stdin)?4:0;
}
'''


def build(output, opt, clang='clang'):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    module = lower(Parser(SOURCE).parse())
    assert not link_flags(module), 'UTF-8 library acquired a runtime dependency'
    ir = output/'utf8.ll'
    ir.write_text(llvm(module).replace('define i32 @main()', 'define i32 @example_entry()')+BRIDGE)
    harness = output/'harness.c'; harness.write_text(HARNESS)
    exe = output/('probe.exe' if sys.platform=='win32' else 'probe')
    subprocess.run([clang, '-Wno-override-module', opt, str(ir), str(harness), '-o', str(exe)],
                   check=True, capture_output=True)
    return exe, ir


def probe(exe, cases):
    wire = b''.join(struct.pack('<IIII', op, start, end, len(data))+data for op,data,start,end in cases)
    result = subprocess.run([str(exe)], input=wire, capture_output=True, timeout=60)
    assert result.returncode==0, (result.returncode,result.stderr)
    assert len(result.stdout)==8*len(cases), 'incomplete probe results'
    return [v[0] for v in struct.iter_unpack('<Q', result.stdout)]


def inspect(output, clang='clang'):
    output = Path(output)
    for opt in ('-O0','-O2'):
        directory = output/opt[1:]
        exe, ir = build(directory,opt,clang)
        for flags,suffix in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
            target = directory/('optimized.'+suffix)
            subprocess.run([clang,'-Wno-override-module',opt,*flags,str(ir),'-o',str(target)],check=True,capture_output=True)
            text = target.read_text()
            assert not re.search(r'\b_?(?:malloc|calloc|realloc|free|memcpy|memmove)\b',text), 'allocation or bulk copy'
            if suffix=='ll':
                assert re.search(r'load i8\b',text), 'runtime byte reads disappeared'
                assert not re.search(r'alloca \[\d+ x i8\]',text), 'input materialized on stack'
        cases = [(1,b'A\xd0\x9b\xf0\x9f\x98\x80\0',0,0),
                 (1,b'A\xed\xa0\x80',0,0), (5,b'\xc2\x80',0,2)]
        assert probe(exe,cases)==[4,(1<<63)|(1<<32)|1,2]
    report = 'O0/O2: UTF-8 runtime byte reads; no heap calls or bulk input copies in generated IR and assembly.\n'
    (output/'report.txt').write_text(report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='build/utf8-cost')
    parser.add_argument('--clang',default='clang')
    args=parser.parse_args()
    print(inspect(args.output,args.clang),end='')
