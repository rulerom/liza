"""Ordinary-module owned UTF-8, tested against runtime bytes and Python UTF-8."""
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

MODULE=Path(__file__).resolve().parents[1]/'examples/text/string.liza'
SOURCE='''import text.string
fn probe(data:View<u8>,capacity:u32)->u32:alloc {
 match memory.create(u64(capacity)) {Err(e)=>{return 100} Ok(region)=>{
 var status:u32=0
 match memory.alloc<u8>(region,capacity,255) {Err(e)=>{status=101} Ok(storage)=>{
 var current=text.string.from_buffer(move storage)
 var prefix:u32=0
 if capacity>=2 {
   seed:[u8;2]=[111,107];v=view seed[0..2]
   (next,result)=text.string.append(move current,v);current=move next
   match result {Ok(done)=>{prefix=2} Err(error)=>{status=102}}
 }
 (appended,result)=text.string.append(move current,data);current=move appended
 var accepted:bool=false
 match result {Ok(done)=>{accepted=true} Err(error)=>{match error {
   text.string.Error.Full=>{status=2}
   text.string.Error.InvalidUtf8(e)=>{status=1}
 }}}
 var expected=prefix
 if accepted {expected=expected+data.len}
 (observed,length,cap)=text.string.inspect(move current);current=move observed
 if length!=expected || cap!=capacity {status=103}
 var i:u32=0
 while i<expected {
   (next,item)=text.string.byte_at(move current,i);current=move next
   var want:u8=0
   if i<prefix {if i==0 {want=111} else {want=107}} else {want=data[i-prefix]}
   match item {None=>{status=104} Some(byte)=>{if byte!=want {status=105}}}
   i=i+1
 }
 (bounded,item)=text.string.byte_at(move current,expected);current=move bounded
 match item {None=>{} Some(byte)=>{status=106}}
 (maximal,last)=text.string.byte_at(move current,4294967295);current=move maximal
 match last {None=>{} Some(byte)=>{status=107}}
 current=text.string.clear(move current)
 (cleared,zero,old_capacity)=text.string.inspect(move current);current=move cleared
 if zero!=0 || old_capacity!=capacity {status=108}
 (empty,old_byte)=text.string.byte_at(move current,0);current=move empty
 match old_byte {None=>{} Some(byte)=>{status=109}}
 released=text.string.release(move current)
 }}
 closed=memory.close(move region);return status
 }}
}
fn main()->u32{return 0}
'''
BRIDGE='''
define i32 @run(ptr %bytes, i32 %length, i32 %capacity) {
 %a = insertvalue {ptr, i32} zeroinitializer, ptr %bytes, 0
 %v = insertvalue {ptr, i32} %a, i32 %length, 1
 %r = call i32 @liza_probe.probe({ptr, i32} %v, i32 %capacity)
 ret i32 %r
}
'''
HARNESS=r'''
#include <stdint.h>
#include <stdio.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
extern uint32_t run(const uint8_t*,uint32_t,uint32_t);
static uint8_t bytes[65536];
static uint32_t word(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
int main(void){
#ifdef _WIN32
 _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
#endif
 uint8_t header[8],out[4];size_t n;
 while((n=fread(header,1,8,stdin))!=0){
  if(n!=8)return 1;
  uint32_t cap=word(header),len=word(header+4);
  if(cap>65536||len>sizeof(bytes)||fread(bytes,1,len,stdin)!=len)return 2;
  uint32_t result=run(bytes,len,cap);
  for(int i=0;i<4;i++)out[i]=(uint8_t)(result>>(8*i));
  if(fwrite(out,1,4,stdout)!=4)return 3;
 }
 return ferror(stdin)?4:0;
}
'''

@unittest.skipUnless(shutil.which('clang'),'requires clang')
class OwnedStringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        (cls.root/'text').mkdir();shutil.copyfile(MODULE,cls.root/'text/string.liza')
        source=cls.root/'probe.liza';source.write_text(SOURCE)
        cls.module=lower(load_program(source))
        ir=cls.root/'probe.ll';ir.write_text(llvm(cls.module).replace('define i32 @main()','define i32 @example_entry()')+BRIDGE)
        c=cls.root/'harness.c';c.write_text(HARNESS);cls.executables=[]
        for opt in ('-O0','-O2'):
            exe=cls.root/('probe'+opt[1:]+('.exe' if sys.platform=='win32' else ''))
            r=subprocess.run(['clang','-Wno-override-module',opt,str(ir),str(c),*link_flags(cls.module),'-o',str(exe)],capture_output=True,text=True)
            if r.returncode:raise AssertionError(r.stderr)
            cls.executables.append(exe)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def check(self,cases):
        wire=b''.join(struct.pack('<II',cap,len(data))+data for cap,data in cases)
        expected=[]
        for cap,data in cases:
            try:data.decode('utf-8');valid=True
            except UnicodeDecodeError:valid=False
            expected.append(1 if not valid else (2 if len(data)>cap-(2 if cap>=2 else 0) else 0))
        for exe in self.executables:
            r=subprocess.run([str(exe)],input=wire,capture_output=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(len(r.stdout),4*len(cases))
            self.assertEqual([x[0] for x in struct.iter_unpack('<I',r.stdout)],expected)

    def test_utf8_capacity_and_atomic_errors(self):
        data=[b'',b'a',b'\0',b'abcdef','Привет🚀'.encode(),b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xf0\x9f',b'a'*8192]
        self.check([(cap,d) for d in data for cap in (0,1,2,3,len(d)+2,len(d)+3)])

    def test_random_runtime_inputs(self):
        rng=random.Random(482);cases=[]
        for _ in range(500):
            d=bytes(rng.randrange(256) for _ in range(rng.randrange(24)))
            cases.append((rng.randrange(32),d))
            d=''.join(chr(rng.choice([0,0x7f,0x80,0x7ff,0x800,0xd7ff,0xe000,0xffff,0x10000,0x10ffff])) for _ in range(8)).encode()
            cases.extend([(len(d)+2,d),(len(d)+1,d)])
        self.check(cases)

    def test_no_allocator_in_string_module(self):
        for fn in self.module:
            if fn.name.startswith('text.string.'):
                self.assertEqual(fn.effect_contract,'pure')
                self.assertFalse(any(op.op in ('region.create','region.alloc','vec.create','vec.reserve') for b in fn.blocks for op in b.operations))

    def test_private_and_linear_invariant(self):
        for source in (
            'fn bad(s:text.string.String)->u32 {(b,n)=move s;return memory.release(move b)}',
            'fn bad(b:memory.Buffer<u8>)->text.string.String {return text.string.String(move b,3)}',
            'fn bad(s:text.string.String)->text.string.String {return copy s}',
            'fn bad(s:text.string.String)->u32 {return 0}'):
            path=self.root/'bad.liza';path.write_text('import text.string\n'+source+'\nfn main()->u32{return 0}')
            with self.assertRaises(CompileError):lower(load_program(path))

if __name__=='__main__':unittest.main()
