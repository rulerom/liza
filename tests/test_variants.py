from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
from test_arrays import compile_source, program
import test_arrays
from liza.frontend import CompileError
from liza.backend import llvm


class VariantTypes(unittest.TestCase):
    def test_context_and_recursive_types(self):
        for body in ['x:Option<u8>=Some(255); return 0',
                     'x:Option<Result<u8,u16>>=Some(Ok(2)); return 0',
                     'x=Some(3); match x {Some(n)=>{return n} None=>{return 0}}']:
            # Spaces separate the closing type delimiter from assignment.
            compile_source(program(body.replace('>=','> =')))
        bad=['enum E { A; A }', 'enum E { A(E) }',
             'enum E { A(Option<E>) }', 'enum E { A(View<u8>) }',
             'struct S {x:E} enum E { A(S) }']
        for declaration in bad:
            with self.subTest(declaration=declaration), self.assertRaises(CompileError):
                compile_source(declaration+program('return 0'))

    def test_pattern_and_ownership_errors(self):
        bad=['x=None; return 0', 'x=Ok(1); return 0',
             'x:Option<u8> = Some(256); return 0',
             'x:Option<u8> = Some(1); match x { Some(n)=>{return 0} }',
             'x:Option<u8> = None; match x {None=>{return 0} None=>{return 1} Some(n)=>{return 2}}',
             'x:Option<u8> = None; match x {None(n)=>{return 0} Some(n)=>{return 1}}',
             'x:Option<u8> = None; match x {None=>{return 0} Some=>{return 1}}',
             'x=Some(1); match move x {Some(n)=>{} None=>{}} y=x; return 0',
             'x=Some(1); match x {Some(n)=>{} None=>{}} return n',
             'a=[1]; v=view a[0..1]; x=Some(v); return 0',
             'x=Some(1); return x.value',
             'x=Some(1); y=Some(2); if x==y {return 0} return 1']
        for body in bad:
            with self.subTest(body=body),self.assertRaises(CompileError):
                compile_source(program(body))

    def test_match_lexical_borrows(self):
        compile_source(program('var a=[1]; x=Some(1); match x {Some(n)=>{v=view a[0..1]} None=>{}} b=move a; return b[0]'))
        with self.assertRaises(CompileError):
            compile_source(program('var a=[1]; x=Some(1); match x {Some(n)=>{v=view a[0..1]; b=move a} None=>{}} return 0'))
        with self.assertRaises(CompileError):
            compile_source(program('a=[1]; var v=view a[0..1]; x=Some([2]); match x {Some(b)=>{v=view b[0..1]} None=>{}} return v[0]'))


@unittest.skipUnless(shutil.which('clang'),'native tests require clang')
class VariantNative(unittest.TestCase):
    build=test_arrays.ArrayNative.build

    def test_nested_variants_phi_move_and_len(self):
        source='''enum E { Empty; Data([u32;2]) }
        struct S {x:Option<E>}
        fn main()->u32 {
            var x:Option<E> = None
            var i=0
            while i<3 {x=Some(E.Data([i,i+1])); i=i+1}
            s=S(copy x)
            match move x {
                Some(e)=>{match e {E.Empty=>{return 1} E.Data(a)=>{v=view a[0..2]; if v.len!=a.len || v[1]!=3 {return 2}}}}
                None=>{return 3}
            }
            x=None
            match s.x {Some(e)=>{} None=>{return 4}}
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_match_loop_edges_and_borrow_release(self):
        source=program("""var data=[1,2]; var n=0; var x:Option<u32> = Some(0)
        while true {
            match copy x {
                Some(k)=>{
                    v=view data[0..2]
                    n=n+v[0]
                    if n<3 {x=Some(n); continue}
                    break
                }
                None=>{return 1}
            }
        }
        other=move data
        if n!=3 || other[1]!=2 {return 2}
        return 0""")
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_active_arm_and_observable_traps(self):
        bodies=[('x:Option<u8> = None; match x {None=>{return 0} Some(n)=>{return u32(n+255)}}',False),
                ('x:u8=255; unused=Some(x+1); return 0',True),
                ('a=[1]; unused=[a[1]].len; return 0',True)]
        for opt in ('-O0','-O2'):
            for body,traps in bodies:
                with tempfile.TemporaryDirectory() as d:
                    exe=self.build(d,program(body),opt)
                    code=subprocess.run([str(exe)],capture_output=True,timeout=5).returncode
                    self.assertLess(code,0) if traps else self.assertEqual(code,0)

    def test_rtp_runtime_reference(self):
        from tools.check_result_cost import BRIDGE
        source=Path('examples/rtp_result.liza').read_text()
        def reference(p):
            error=0
            if len(p)<12: error=1
            elif p[0]>>6!=2: error=2
            else:
                offset=12+4*(p[0]&15)
                if len(p)<offset: error=3
                elif p[0]&16:
                    if len(p)-offset<4: error=4
                    else:
                        offset+=4+4*int.from_bytes(p[offset+2:offset+4],'big')
                        if offset>len(p): error=4
                if not error:
                    length=len(p)-offset
                    if p[0]&32:
                        if not length or not p[-1] or p[-1]>length: error=5
                        else: length-=p[-1]
            if error: return [0x80000000+error]*8
            return [p[0]>>6,p[1]>>7,p[1]&127,int.from_bytes(p[2:4],'big'),int.from_bytes(p[4:8],'big'),int.from_bytes(p[8:12],'big'),offset,length]
        base=bytes([128,224,18,52,1,2,3,4,5,6,7,8])
        packets=[base[:i] for i in range(13)]
        for flags in (128,129,143,144,160,176):
            for tail in (b'',b'\0',b'\1',b'\0\0\0\0',b'\0\0\0\1abcd',b'\0\0\0\1abcd\1',b'\xff'*64):
                packets.append(bytes([flags])+base[1:]+tail)
        rng=random.Random(11)
        for _ in range(200):
            p=bytearray(rng.randrange(256) for _ in range(rng.randrange(100)))
            if p: p[0]=(p[0]&63)|128
            packets.append(bytes(p))
        checks=[]
        for i,p in enumerate(packets):
            values=','.join(map(str,p)) or '0'
            expected=','.join(str(v)+'u' for v in reference(p))
            checks.append('{uint8_t p[]={'+values+'};uint32_t e[]={'+expected+'};for(uint32_t f=0;f<8;f++)if(rtp_bridge(p,'+str(len(p))+',f)!=e[f])return '+str(i%250+1)+';}')
        harness='#include <stdint.h>\nextern uint32_t rtp_bridge(const uint8_t*,uint32_t,uint32_t);\nint main(void){'+''.join(checks)+'return 0;}'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); ir=root/'module.ll'; c=root/'harness.c'; exe=root/'test'
            ir.write_text(llvm(compile_source(source)).replace('define i32 @main()', 'define i32 @example_entry()')+BRIDGE)
            c.write_text(harness)
            for opt in ('-O0','-O2'):
                subprocess.run(['clang','-Wno-override-module',opt,str(ir),str(c),'-o',str(exe)],check=True,capture_output=True)
                self.assertEqual(subprocess.run([str(exe)],timeout=10).returncode,0,opt)
