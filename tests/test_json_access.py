"""Typed JSON range reader/writer; native bytes at O0/O2, no CAN logic in library."""
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

ROOT=Path(__file__).resolve().parents[1]
BRIDGE='''
define i32 @run(ptr %p, i32 %n, ptr %path, i32 %pn, ptr %e, i32 %en, i32 %mode, i32 %lim, i32 %depth, i32 %result, i32 %cap, i64 %want) {
 %a = insertvalue {ptr,i32} zeroinitializer, ptr %p, 0
 %v = insertvalue {ptr,i32} %a, i32 %n, 1
 %b = insertvalue {ptr,i32} zeroinitializer, ptr %path, 0
 %pv = insertvalue {ptr,i32} %b, i32 %pn, 1
 %c = insertvalue {ptr,i32} zeroinitializer, ptr %e, 0
 %ev = insertvalue {ptr,i32} %c, i32 %en, 1
 %r = call i32 @liza_probe({ptr,i32} %v, {ptr,i32} %pv, {ptr,i32} %ev, i32 %mode, i32 %lim, i32 %depth, i32 %result, i32 %cap, i64 %want)
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
extern uint32_t run(const uint8_t*,uint32_t,const uint8_t*,uint32_t,const uint8_t*,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint64_t);
static uint8_t data[65536],path[65536],expected[65536];
static uint32_t word(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
int main(void){
#ifdef _WIN32
 _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
#endif
 uint8_t header[40],out[4];size_t got;
 while((got=fread(header,1,40,stdin))!=0){
  if(got!=40)return 1;
  uint32_t n=word(header),pn=word(header+4),en=word(header+8),cap=word(header+28);
  if(n>65536||pn>65536||en>65536||cap>65536)return 2;
  if(fread(data,1,n,stdin)!=n||fread(path,1,pn,stdin)!=pn||fread(expected,1,en,stdin)!=en)return 3;
  uint64_t want=(uint64_t)word(header+32)|((uint64_t)word(header+36)<<32);
  uint32_t result=run(data,n,path,pn,expected,en,word(header+12),word(header+16),word(header+20),word(header+24),cap,want);
  for(unsigned i=0;i<4;i++)out[i]=(uint8_t)(result>>(i*8));
  if(fwrite(out,1,4,stdout)!=4)return 4;
 }
 return ferror(stdin)?5:0;
}
'''
def path_bytes(path):
    out=b''
    for key in path:
        if isinstance(key,int):out+=struct.pack('<BI',1,key)
        else:
            b=key.encode() if isinstance(key,str) else key
            out+=struct.pack('<BI',0,len(b))+b
    return out

def case(data,mode=0,path=(),expected=b'',want=0,error=0,limit=65536,depth=64,result=65536,capacity=65536):
    if isinstance(data,str):data=data.encode()
    return (data,path_bytes(path),expected,mode,limit,depth,result,capacity,want%(1<<64),error)

def quoted(s):
    return ('"'+''.join('\\u%04x'%ord(c) if ord(c)<32 else ('\\'+c if c in '\\"' else c) for c in s)+'"').encode()

def encoded(x):
    if isinstance(x,str):return quoted(x)
    if x is None:return b'null'
    if x is True:return b'true'
    if x is False:return b'false'
    if isinstance(x,int):return str(x).encode()
    if isinstance(x,list):return b'['+b','.join(map(encoded,x))+b']'
    return b'{'+b','.join(quoted(k)+b':'+encoded(v) for k,v in x.items())+b'}'

def command(op,value=b''):
    if isinstance(value,str):value=value.encode()
    if op in (4,5):return struct.pack('<BI',op,len(value))+value
    if op in (8,9):return struct.pack('<BIQ',op,0,value%(1<<64))
    return struct.pack('<BI',op,int(value) if isinstance(value,(int,bool)) else 0)

def program(x):
    if isinstance(x,dict):return command(0)+b''.join(command(4,k)+program(v) for k,v in x.items())+command(1)
    if isinstance(x,list):return command(2)+b''.join(map(program,x))+command(3)
    if isinstance(x,str):return command(5,x)
    if x is None:return command(7)
    if isinstance(x,bool):return command(6,x)
    return command(8 if x>=0 else 9,x)

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class JsonAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='liza-json-access-');cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        cls.source=(ROOT/'tests/fixtures/json_access.liza').read_text()
        cls.module=lower(Parser(cls.source).parse())
        ir=cls.root/'probe.ll';ir.write_text(llvm(cls.module).replace('define i32 @main()','define i32 @example_entry()')+BRIDGE)
        c=cls.root/'probe.c';c.write_text(HARNESS);cls.executables=[]
        for opt in ('0','2'):
            exe=cls.root/('probe'+opt+('.exe' if sys.platform=='win32' else ''))
            r=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),str(c),*link_flags(cls.module),'-o',str(exe)],capture_output=True,text=True,timeout=120)
            if r.returncode:raise AssertionError(r.stderr)
            cls.executables.append(exe)

    def check(self,cases):
        wire=b''
        for data,path,expected,mode,limit,depth,result,cap,want,error in cases:
            wire+=struct.pack('<8IQ',len(data),len(path),len(expected),mode,limit,depth,result,cap,want)+data+path+expected
        for exe in self.executables:
            run=subprocess.run([str(exe)],input=wire,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,(exe.name,run.stderr))
            actual=[i[0] for i in struct.iter_unpack('<I',run.stdout)]
            self.assertEqual(len(actual),len(cases))
            for i,(got,c) in enumerate(zip(actual,cases)):
                self.assertEqual(got,c[-1],(exe.name,i,c[:4],got,c[-1]))

    def test_reader_types_and_ranges(self):
        self.check([
            case('{"n":null}',1,('n',),want=0),case('{"n":null}',2,('n',),error=2),
            case('{"n":null}',1,('missing',),error=1),case('[1]',1,('n',),error=2),
            case('{"b":true}',2,('b',),want=1),case('false',2),
            case('{"a":["x",{"x":2}]}',5,('a',),want=2),
            case('{"a":["x",{"x":2}]}',3,('a',1,'x'),want=2),
            case('[0]',1,(1,),error=9),case('[]',5),case('{}',5,error=2),
            case('"abc"',6,expected=b'abc'),case('""',6,capacity=0,result=0),
            case('{"\\u0074ype":"hello"}',6,('type',),expected=b'hello'),
            case('{"\\u0000":"x"}',6,('\0',),expected=b'x'),
        ])

    def test_unicode_keys_duplicates_and_limits(self):
        cases=[]
        for body in ('{"x":1,"x":2}', '{"type":1,"\\u0074ype":2}',
                     '{"x":{"a":1,"a":2}}', '[{"é":1,"\\u00e9":2}]',
                     '{"🚀":1,"\\ud83d\\ude80":2}'):
            cases.append(case(body,error=6))
        for text in ('"\\ud800"','"\\udc00"','"\\ud800\\u0041"','"\\uZZZZ"','"\\q"'):
            cases.append(case(text,error=3))
        for text in (b'"\xc0\x80"',b'"\xed\xa0\x80"',b'"\xf4\x90\x80\x80"',b'"\xf0\x9f"'):
            cases.append(case(text,error=3))
        for text in ('','{','{"a":}','true false','[1,]','{"a" 1}','01','null\0'):
            cases.append(case(text,error=5))
        cases += [case('{"é":"\\ud83d\\ude80"}',6,('é',),expected='🚀'.encode()),
                  case('{"x":"a"}',6,('x',),expected=b'a',result=0,error=4),
                  case('"abc"',6,expected=b'abc',capacity=2,error=4),
                  case('"abc"',6,expected=b'abc',capacity=3,result=3),
                  case('"abc"',error=4,limit=4),case('"abc"',limit=5),
                  case('[{}]',depth=1,error=4),case('[{}]',depth=2),
                  case('[]',depth=0,error=4),case('[]',depth=65,error=4),
                  case('[]',1,(b'\xff',),error=3),
                  case('{'+'"x":0, '*30+'"last":0}',error=6)]
        for s in ('\0\b\t\n\f\r"\\/','é𝄞🚀','\u007f\u0080\u07ff\u0800\uffff\U0010ffff',''):
            for ascii in (False,True):
                cases.append(case(json.dumps(s,ensure_ascii=ascii),6,expected=s.encode()))
        cases += [case('['*64+'0'+']'*64),case('['*65+'0'+']'*65,error=4)]
        self.check(cases)

    def test_invalid_document_remains_owned_but_unreadable(self):
        self.check([case('',7,error=8),case('true false',7,error=8),case('[]',7,limit=1,error=8),case('{"x":1,"x":2}',7,error=8)])

    def test_integer_ranges_and_wrong_types(self):
        cases=[]
        for n in (0,1,2**31,2**32,1794700000000,2**63-1,2**63,2**64-1):
            cases.append(case(str(n),3,want=n))
        for n in (-2**63,-1,0,1,2**63-1):cases.append(case(str(n),4,want=n))
        cases += [case('-0',3),case('-0',4)]
        for text in ('18446744073709551616','-1','-18446744073709551616'):
            cases.append(case(text,3,error=7))
        for text in ('9223372036854775808','-9223372036854775809'):
            cases.append(case(text,4,error=7))
        for text in ('1.0','1e0','-1E+2','184467440737095516160.0','true','null','"1"','[]','{}'):
            cases.extend([case(text,3,error=2),case(text,4,error=2)])
        self.check(cases)

    def test_can_corpus_typed_read_and_write(self):
        corpus=json.loads((ROOT/'tests/fixtures/can_examples.json').read_text())
        self.assertEqual(len(corpus['examples']),20)
        cases=[]
        def visit(document,value,path=()):
            kind=0 if value is None else 1 if isinstance(value,bool) else 2 if isinstance(value,int) else 3 if isinstance(value,str) else 4 if isinstance(value,dict) else 5
            cases.append(case(document,1,path,want=kind))
            if isinstance(value,str):cases.append(case(document,6,path,expected=value.encode()))
            elif isinstance(value,bool):cases.append(case(document,2,path,want=int(value)))
            elif isinstance(value,int):cases.append(case(document,3 if value>=0 else 4,path,want=value))
            elif isinstance(value,list):
                cases.append(case(document,5,path,want=len(value)))
                for i,v in enumerate(value):visit(document,v,path+(i,))
            elif isinstance(value,dict):
                for k,v in value.items():visit(document,v,path+(k,))
        for item in corpus['examples']:
            obj=item['message'];document=json.dumps(obj,separators=(',',':'))
            visit(document,obj)
            cases.append(case(program(obj),10,expected=encoded(obj)))
            self.assertEqual(json.loads(encoded(obj)),obj)
            for key,value in obj.items():
                missing=dict(obj);del missing[key]
                cases.append(case(json.dumps(missing),1,(key,),error=1))
                mode=6 if isinstance(value,str) else 2 if isinstance(value,bool) else 3 if isinstance(value,int) and value>=0 else 5 if isinstance(value,list) else None
                if mode is not None:
                    wrong=dict(obj);wrong[key]=None
                    cases.append(case(json.dumps(wrong),mode,(key,),error=2))
        self.check(cases)

    def test_writer_escaping_atomicity_and_grammar(self):
        values=[''.join(map(chr,range(128))),'','a','\0\b\t\n\f\r"\\/','Привет🚀','\U0010ffff',None,False,True,0,2**64-1,-2**63,[],{}, {'x':[True,None,{'quote"':'\\'}]}]
        self.check([case(program(x),10,expected=encoded(x),result=len(encoded(x)),capacity=len(encoded(x))) for x in values])
        cases=[]
        for s in ('abc','\0','🚀'):
            out=quoted(s)
            cases.append(case(command(5,s),10,error=4,result=len(out)-1,capacity=len(out)))
            cases.append(case(command(5,s),10,error=4,result=len(out),capacity=len(out)-1))
        for data in (b'\xff',b'\xed\xa0\x80',b'\xc0\x80'):
            cases.append(case(command(5,data),10,error=3))
        cases += [
            case(command(0)+command(4,'x')+command(8,1)+command(4,'x'),10,expected=b'{"x":1',error=6),
            case(command(0)+command(4,'é')+command(8,1)+command(4,'é'),10,expected='{"é":1'.encode(),error=6),
            case(command(0)+command(5,'x'),10,expected=b'{',error=2),
            case(command(0)+command(4,'x')+command(1),10,expected=b'{"x":',error=2),
            case(command(0)+command(4,'x'),10,expected=b'{"x":',error=5),
            case(command(2)+command(1),10,expected=b'[',error=2),
            case(command(3),10,error=2),case(command(7)+command(7),10,expected=b'null',error=5),
            case(command(0)+command(4,'x'),10,expected=b'{',result=4,error=4),
            case(command(2)+command(3),10,expected=b'[',result=1,error=4),
            case(command(2)+command(2),10,expected=b'[',depth=1,error=4),
            case(b'',10,result=2,capacity=1,error=4),case(b'',10,depth=0,error=4),
            case(command(0)+command(4,b'\xff'),10,expected=b'{',error=3),
            case(command(0)+command(4,'x')+command(5,b'\xff'),10,expected=b'{"x":',error=3),
            case(program({'type':'a','\\u0074ype':'b'}),10,expected=encoded({'type':'a','\\u0074ype':'b'})),
        ]
        self.check(cases)

    def test_random_values_and_decoded_key_spellings(self):
        rng=random.Random(9301);cases=[]
        alphabet=['a','"','\\','\0','\n','é','Ж','🚀','\U0010ffff']
        for _ in range(100):
            key=''.join(rng.choice(alphabet) for i in range(rng.randrange(10)))
            value=''.join(rng.choice(alphabet) for i in range(rng.randrange(20)))
            obj={key:value,'other':[None,False,rng.randrange(-(1<<63),1<<64)]}
            for ascii in (True,False):cases.append(case(json.dumps(obj,ensure_ascii=ascii),6,(key,),expected=value.encode()))
            cases.append(case(program(obj),10,expected=encoded(obj)))
        self.check(cases)

    def test_negative_library_mutations(self):
        mutants=[
            ('decoded-key','json_reader.liza','a=__liza_json_char(data,i);b=__liza_json_raw_char(key,j)',
             'a=__liza_json_raw_char(data,i);b=__liza_json_raw_char(key,j)',
             [case('{"\\u0074ype":"hello"}',6,('type',),expected=b'hello')]),
            ('duplicate','json_reader.liza','if __liza_json_keys_equal(data,previous,i,end)',
             'if false', [case('{"type":1,"\\u0074ype":2}',error=6)]),
            ('writer-utf8','json_writer.liza','match utf8.validate(data) {Err(e)=>{return Err(JsonAccessError.InvalidUnicode)} Ok(n)=>{}}',
             '', [case(command(5,b'\xff'),10,error=3)]),
        ]
        for label,file,before,after,cases in mutants:
            root=self.root/label;root.mkdir();shutil.copytree(ROOT/'liza/stdlib',root/'stdlib')
            source=root/'stdlib'/file;text=source.read_text();self.assertIn(before,text);source.write_text(text.replace(before,after))
            with patch('liza.stdlib.__file__',str(root/'stdlib.py')):
                module=lower(Parser(self.source).parse())
            ir=root/'mutant.ll';ir.write_text(llvm(module).replace('define i32 @main()','define i32 @example_entry()')+BRIDGE)
            c=root/'probe.c';c.write_text(HARNESS)
            original=self.executables
            for opt in ('0','2'):
                exe=root/('mutant'+opt+('.exe' if sys.platform=='win32' else ''))
                built=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),str(c),*link_flags(module),'-o',str(exe)],capture_output=True,text=True,timeout=120)
                self.assertEqual(built.returncode,0,built.stderr)
                try:
                    self.executables=[exe]
                    with self.assertRaises(AssertionError,msg=label+' O'+opt):self.check(cases)
                finally:self.executables=original

    def test_library_has_no_allocator_or_new_native_boundary(self):
        for fn in self.module:
            if fn.name.startswith(('json.','__liza_json_')):
                self.assertEqual(fn.effect_contract,'pure',fn.name)
                self.assertFalse(any(op.op in ('region.create','region.alloc','vec.create','vec.reserve') for b in fn.blocks for op in b.operations),fn.name)
        self.assertFalse(any('json' in f.name.text for f in self.module.externals))

class JsonAccessOwnership(unittest.TestCase):
    def reject(self,source,pattern):
        with self.assertRaisesRegex((CompileError,ValueError),pattern):lower(Parser(source+'\nfn main()->u32{return 0}').parse())

    def test_private_document_and_linear_storage(self):
        self.reject('fn bad(d:JsonDocument)->JsonDocument{return copy d}','copy|resource')
        self.reject('fn bad(d:JsonDocument)->u32{return 0}','closed|transferred')
        self.reject('fn bad(d:JsonDocument)->u32{(b,n,s,e,l,v)=move d;return memory.release(move b)}','private')
        self.reject('fn bad(b:memory.Buffer<u8>)->JsonDocument{return JsonDocument(move b,0,0,0,0,true)}','private')
        self.reject('fn bad(d:JsonDocument)->u32{b=json.into_buffer(move d);k=json.kind(d);return memory.release(move b)}','after move')
        self.reject('fn bad(w:JsonWriter)->JsonWriter{return copy w}','copy|resource')
        self.reject('fn bad(w:JsonWriter)->u32{(b,n,l,m,d,s,t,r,v)=move w;return memory.release(move b)}','private')

    def test_document_preserves_region_dependency(self):
        prefix="""fn main()->u32:alloc {
        match memory.create(8) {Err(e)=>{return 1} Ok(r)=>{
        match memory.alloc<u8>(r,1,48) {Err(e)=>{c=memory.close(move r);return 1} Ok(b)=>{
        (doc,result)=json.parse(move b,1,JsonLimits(1,1,1))
        """
        suffix='return 0}}}}}'
        lower(Parser(prefix+'f=json.release(move doc);c=memory.close(move r);'+suffix).parse())
        with self.assertRaisesRegex((CompileError,ValueError),'region|storage|borrow|live'):
            lower(Parser(prefix+'c=memory.close(move r);f=json.release(move doc);'+suffix).parse())
