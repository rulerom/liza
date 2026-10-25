"""Native runtime-input tests of the bounded JSON library, at O0 and O2."""
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags
from tools.check_utf8_stream_cost import HARNESS, probe

KINDS = ['Syntax','InvalidNumber','InvalidEscape','InvalidSurrogate','InvalidUtf8',
         'UnexpectedEof','DepthLimit','SizeOverflow']
SOURCE = '''
fn status(s:JsonState)->u32 {
 match json.finish(s) {Ok(n)=>{return 0} Err(e)=>{match e.kind {
''' + '\n'.join('JsonErrorKind.%s=>{return %d}' % (k,i+1) for i,k in enumerate(KINDS)) + '''
 }}}
}
fn value(s:JsonState)->u64 {match json.finish(s) {Ok(n)=>{return n} Err(e)=>{return e.offset}}}
fn start()->JsonState {return json.create()}
fn feed(s:JsonState,v:View<u8>)->JsonState {return json.feed(s,v)}
fn main()->u32 {return 0}
'''

@unittest.skipUnless(shutil.which('clang'), 'requires clang')
class JsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.root=Path(cls.tmp.name)
        module=lower(Parser(SOURCE).parse())
        assert not link_flags(module), 'JSON must remain pure Liza'
        bridge="""
define void @stream_start(ptr %out) {
 call void @liza_json.create(ptr sret(%struct.JsonState) %out)
 ret void
}
define void @stream_feed(ptr %state, ptr %bytes, i32 %length) {
 %result = alloca %struct.JsonState
 %a = insertvalue {ptr, i32} zeroinitializer, ptr %bytes, 0
 %v = insertvalue {ptr, i32} %a, i32 %length, 1
 call void @liza_json.feed(ptr sret(%struct.JsonState) %result, ptr %state, {ptr, i32} %v)
 %n = load %struct.JsonState, ptr %result
 store %struct.JsonState %n, ptr %state
 ret void
}
define i32 @stream_status(ptr %state) {
 %r = call i32 @liza_status(ptr %state)
 ret i32 %r
}
define i64 @stream_value(ptr %state) {
 %r = call i64 @liza_value(ptr %state)
 ret i64 %r
}
"""
        bridge+='''
define i64 @stream_size() {
 %end = getelementptr %struct.JsonState, ptr null, i32 1
 %size = ptrtoint ptr %end to i64
 ret i64 %size
}
'''
        ir=cls.root/'json.ll';ir.write_text(llvm(module).replace('define i32 @main()','define i32 @example_entry()')+bridge)
        # Query LLVM's layout rather than assuming a C representation of JsonState.
        c=cls.root/'probe.c'
        harness=HARNESS.replace('#include <stdint.h>','#include <stdint.h>\n#include <stdlib.h>\nextern uint64_t stream_size(void);')
        harness=harness.replace('uint64_t state[8];stream_start(state);','void *state=malloc((size_t)stream_size());if(!state)return 6;stream_start(state);')
        harness=harness.replace('uint64_t value=stream_value(state);','uint64_t value=stream_value(state);free(state);')
        c.write_text(harness)
        cls.executables=[]
        for opt in ('-O0','-O2'):
            exe=cls.root/('probe'+opt[1:]+('.exe' if sys.platform=='win32' else ''))
            subprocess.run(['clang','-Wno-override-module',opt,str(ir),str(c),'-o',str(exe)],check=True,capture_output=True)
            cls.executables.append(exe)
        cls.cli=cls.root/('liza-json.exe' if sys.platform=='win32' else 'liza-json')
        subprocess.run([sys.executable,'-m','liza','build','examples/apps/liza_json.liza','-o',str(cls.cli)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def check_cases(self,cases,expected):
        for exe in self.executables:
            self.assertEqual(probe(exe,cases),expected,exe.name)

    def partitions(self,data):
        yield [data]
        yield [bytes([b]) for b in data]
        for i in range(len(data)+1):
            yield [data[:i],b'',data[i:]]
        for i in range(len(data)+1):
            for j in range(i,len(data)+1):
                yield [data[:i],data[i:j],data[j:]]

    def test_valid_partitions(self):
        docs=[b'0',b'-12.34e+56',b'true',b'false',b'null',b'[]',b'{}',
              b'{"x":[true,null,0]}',b'"\\uD83D\\uDE80"',b'"\\u0000"',b'"\\uDBFF\\uDFFF"',
              b'"\\\"\\\\\\/\\b\\f\\n\\r\\t"','"Привет🚀"'.encode(),b'{"x":1,"x":2}']
        cases=[];expected=[]
        for d in docs:
            parts=list(self.partitions(d));cases.extend(parts);expected.extend([(0,len(d))]*len(parts))
        self.check_cases(cases,expected)

    def test_invalid_partitions_and_offsets(self):
        docs=[(b'',6,0),(b' ',6,1),(b'[1,]',1,3),(b'{"a":1,}',1,7),
              (b'01',2,1),(b'1.',6,2),(b'1e+',6,3),(b'1e]',2,2),
              (b'"\\q"',3,2),(b'"\\u12x4"',3,5),(b'"\\uDC00"',4,1),
              (b'"\\uD800x"',4,1),(b'"\\uD800\\u0041"',4,1),
              (b'"\\uD800',4,1),(b'"\xed\xa0\x80"',5,1),
              (b'"\xf0\x9f',5,1),(b'"a\x00"',1,2),(b'\xef\xbb\xbf{}',1,0),
              (b'true false',1,5),(b'{"a" 0}',1,5),(b'[}',1,1),
              (b'NaN',1,0),(b'/*x*/null',1,0)]
        cases=[];expected=[]
        for d,kind,offset in docs:
            parts=list(self.partitions(d));cases.extend(parts);expected.extend([(kind,offset)]*len(parts))
        self.check_cases(cases,expected)

    def test_depth_and_unbounded_tokens(self):
        docs=[b'['*64+b'0'+b']'*64,b'['*65+b'0'+b']'*65,
              b'"'+b'a'*20000+b'"',b'1'+b'0'*20000,b'1e'+b'9'*20000]
        self.check_cases([[d[i:i+137] for i in range(0,len(d),137)] for d in docs],
                         [(0,len(docs[0])),(7,64)]+[(0,len(d)) for d in docs[2:]])

    def test_generated_against_python(self):
        rng=random.Random(9183)
        def value(depth):
            leaf=rng.choice([None,True,False,rng.randrange(-100000,100000),'a🚀\n"\\é'])
            if depth==0:return leaf
            return rng.choice([leaf,[value(depth-1) for _ in range(rng.randrange(4))],
                               {str(i):value(depth-1) for i in range(rng.randrange(4))}])
        cases=[];expected=[]
        for _ in range(120):
            d=json.dumps(value(3),ensure_ascii=bool(rng.randrange(2))).encode()
            # ASCII substitutions also test malformed grammar against an independent parser.
            variants=[d]
            if d:
                at=rng.randrange(len(d));variants.append(d[:at]+rng.choice([b',',b':',b' ',b']',b'0'])+d[at+1:])
            for data in variants:
                try:
                    parsed=json.loads(data.decode('utf-8'))
                    # Python accepts unpaired escaped surrogates; this profile does not.
                    json.dumps(parsed,ensure_ascii=False).encode('utf-8')
                    valid=True
                except (ValueError,UnicodeError):valid=False
                chunks=[];i=0
                while i<len(data):
                    n=rng.randrange(1,9);chunks.append(data[i:i+n]);i+=n
                cases.append(chunks);expected.append(valid)
        for exe in self.executables:
            self.assertEqual([s==0 for s,o in probe(exe,cases)],expected)

    def test_sticky_error_and_finish_snapshot(self):
        self.check_cases([[b'[',b'1',b']'],[b'01',b' '*10000,b'null']],[(0,3),(2,1)])

    def test_private_state(self):
        for expr in ('s.position','s.depth','s.encoding'):
            with self.assertRaises(CompileError):lower(Parser('fn main()->u32 {s=json.create();x='+expr+';return 0}').parse())

    def run_source(self,source,modules=None):
        program=Parser(source).parse()
        for fn in program:
            if modules and fn.name.text in modules:fn.module=modules[fn.name.text]
        ir=self.root/'state.ll';ir.write_text(llvm(lower(program)))
        for opt in ('-O0','-O2'):
            exe=self.root/('state'+opt[1:]+('.exe' if sys.platform=='win32' else ''))
            subprocess.run(['clang','-Wno-override-module',opt,str(ir),'-o',str(exe)],check=True,capture_output=True)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)

    def test_copy_input_lifetime_and_pending_status(self):
        self.run_source('''fn main()->u32 {
            var s=json.create()
            var input:[u8;2]=[91,49]
            {v=view input[0..2];s=json.feed(s,v)}
            input[0]=255
            match json.status(s) {Some(e)=>{return 1} None=>{}}
            match json.finish(s) {Ok(n)=>{return 2} Err(e)=>{}}
            snapshot=copy s
            {a:[u8;1]=[93];v=view a[0..1];s=json.feed(s,v)}
            match json.finish(s) {Ok(n)=>{if n!=3 {return 3}} Err(e)=>{return 4}}
            match json.finish(snapshot) {Ok(n)=>{return 5} Err(e)=>{if e.offset!=2 {return 6}}}
            return 0
        }''')

    def test_u64_size_limit(self):
        # Trusted test setup only: public clients cannot construct either state.
        self.run_source('''
        fn encoding()->Utf8StreamState {return Utf8StreamState(18446744073709551615,0,0,0,128,191,0,0)}
        fn seed()->JsonState {return JsonState(encoding(),18446744073709551615,[0;64],0,true,0,false,0,0,0,0,0,0,0,0)}
        fn main()->u32 {
            s=seed();a:[u8;1]=[32];v=view a[0..1];n=json.feed(s,v)
            match json.finish(n) {Ok(count)=>{return 1} Err(e)=>{
                if e.offset!=18446744073709551615 {return 2}
                match e.kind {JsonErrorKind.Syntax=>{return 3} JsonErrorKind.InvalidNumber=>{return 3} JsonErrorKind.InvalidEscape=>{return 3} JsonErrorKind.InvalidSurrogate=>{return 3} JsonErrorKind.InvalidUtf8=>{return 3} JsonErrorKind.UnexpectedEof=>{return 3} JsonErrorKind.DepthLimit=>{return 3} JsonErrorKind.SizeOverflow=>{return 0}}
            }}
        }''',{'encoding':'__liza_utf8_stream','seed':'__liza_json'})

    def test_cli(self):
        path=self.root/'конфигурация.json'
        for data,code,output in [(b'{"ok":true}',0,b'OK\n'),(b'"'+b'a'*2000000+b'"',0,b'OK\n'),(b'['*65,4,b'DepthLimit at byte 64\n'),
                                 (b'"'+b'a'*5000,1,b'UnexpectedEof at byte 5001\n')]:
            path.write_bytes(data)
            r=subprocess.run([str(self.cli),'check',str(path)],capture_output=True)
            self.assertEqual(r.returncode,code);self.assertEqual(r.stdout if code==0 else r.stderr,output)
        self.assertEqual(subprocess.run([str(self.cli),'format',str(path)],capture_output=True).returncode,2)
        self.assertEqual(subprocess.run([str(self.cli),'check',str(path)+'missing'],capture_output=True).returncode,3)

if __name__=='__main__':unittest.main()
