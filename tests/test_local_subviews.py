"""T2-B: immediate-parent bounds, inherited lexical loans and descriptor cost."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.backend import llvm
from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.modules import load_program
from liza.stdlib import link_flags

ROOT = Path(__file__).resolve().parents[1]


def compile_source(source):
    return lower(Parser(source).parse())


def main(body):
    return 'fn main()->u32 {' + body + '}'


def check_guard_order(body):
    """Check each emitted subview: the success edge dominates offset and GEP.

    Deliberately checks the lowering, not whether invalid machine code happens
    to trap later. This small check applies to the emitted straight-line blocks.
    """
    matches = list(re.finditer(r'%([\w]+)_parent_length = extractvalue', body))
    if not matches:
        raise AssertionError('missing subview')
    for match in matches:
        name = match.group(1)
        guard = re.search(r'br i1 %' + name + r'_invalid, label %[^,]+, label %([^\s]+)', body)
        if not guard:
            raise AssertionError('missing subview guard')
        success = body.index(guard.group(1) + ':', guard.end())
        for suffix in ('_length = sub', '_offset = zext', '_ptr = getelementptr'):
            if body.index('%' + name + suffix) < success:
                raise AssertionError('address/length computation precedes bounds guard')


class SubviewTypes(unittest.TestCase):
    def reject(self, source, pattern):
        with self.assertRaisesRegex(CompileError, pattern):
            compile_source(source)

    def test_nested_root_move_update_and_argument_order(self):
        prefix = 'var a=[1,2];p=view a[0..2];q=view p[0..1];'
        for action in ('x=move a', 'a=[3,4]', 'a[0]=9'):
            with self.subTest(action=action):
                self.reject(main(prefix + action + ';return 0'), 'readonly')
        self.reject('fn take(a:[u32;2])->u32{return 0} fn f(v:View<u32>,n:u32)->u32{return n}' +
                    main(prefix + 'return f(q,take(move a))'), 'readonly')
        self.reject('fn take(a:[u32;2])->u32{return 0}' +
                    main(prefix + 's=view q[take(move a)..1];return 0'), 'readonly')

    def test_lifetime_escape_and_aggregate_escape(self):
        self.reject(main('a=[1];var v=view a[0..1];{b=[2];p=view b[0..1];v=view p[0..1]}return v[0]'),
                    'lifetime')
        for suffix in ('return q', 'x=[q];return 0'):
            self.reject('fn bad(p:View<u32>)->' + ('View<u32>' if suffix=='return q' else 'u32') +
                        '{q=view p[0..p.len];' + suffix + '}'+main('return 0'), 'views cannot|view')
        self.reject('struct Saved {v:View<u8>}'+main('return 0'), 'views cannot')

    def test_scope_releases_original_root_not_parent_descriptor(self):
        # An inner descriptor may end before a child: backing storage is outer.
        compile_source(main('var a=[1,2];{var v=view a[0..1];{p=view a[0..2];v=view p[1..2]}'
                            'if v[0]!=2{return 1}}a[0]=3;b=move a;return b[0]-3'))
        compile_source('fn probe(p:View<u32>)->u32{var v=view p[0..0];'
                       '{alias=copy p;v=view alias[0..0]}return v.len}'+main('return 0'))
        compile_source('fn probe(p:View<u32>)->u32{q=view p[0..p.len];'
                       'moved=move p;return q.len+moved.len}'+main('return 0'))
        # Same textual names in independent scopes must remain independent.
        compile_source(main('{a=[1];p=view a[0..1];q=view p[0..1]}'
                            '{var a=[2];a[0]=3}return 0'))

    def test_cfg_preserves_all_possible_roots(self):
        prefix='var a=[1];var b=[2];var p=view a[0..1];'
        for control in ('if true {p=view b[0..1]}', 'while false {p=view b[0..1]}'):
            for owner in ('a','b'):
                self.reject(main(prefix+control+'q=view p[0..1];x=move '+owner+';return 0'), 'readonly')

    def test_resource_region_and_generic_readonly_projection(self):
        header='''struct Box<T>{value:T}
        struct Holder {buffer:memory.Buffer<u8>}
        fn observe<T>(borrow b:Box<T>)->u32 {
            bytes=memory.view(b.value.buffer)
            prefix=view bytes[0..2]
            nested=view prefix[1..2]
            return u32(nested[0])
        }
        '''
        module=compile_source(header+'''fn probe(b:memory.Buffer<u8>)->u32{
            h=Box<Holder>(Holder(move b));n=observe(h)
            (inner,)=move h;(storage,)=move inner
            done=memory.release(move storage);return n
        }'''+main('return 0'))
        observed=next(f for f in module if any(o.op=='buffer.view' for b in f.blocks for o in b.operations))
        operations=[o for block in observed.blocks for o in block.operations]
        view=next(o for o in operations if o.op=='buffer.view')
        self.assertEqual(view.owner_binding,'p0')
        children=[o for o in operations if o.op=='view.create']
        self.assertEqual(children[0].owner_binding,view.result)
        self.assertEqual(children[1].owner_binding,children[0].result)
        for action in ('x=memory.release(move b);', 'b=memory.set(move b,0,9);x=memory.release(move b);',
                       'x=memory.close(move r);y=memory.release(move b);'):
            source='''fn main()->u32:alloc{
            match memory.create(16){Err(e)=>{return 1}Ok(r)=>{
            match memory.alloc<u8>(r,4,0){Err(e)=>{x=memory.close(move r);return 2}Ok(initial)=>{
            var b=move initial;p=memory.view(b);q=view p[0..1];
            '''+action+('return 0' if 'close' in action else 'c=memory.close(move r);return 0')+'}}}}}'
            self.reject(source,'readonly|depend|live')

    def test_semantic_ir_links_and_traps(self):
        module=compile_source('fn probe(v:View<u8>)->u32{p=view v[0..v.len];q=view p[0..p.len];return q.len}'+main('return 0'))
        ops=[o for b in module[0].blocks for o in b.operations if o.op=='view.create']
        self.assertEqual(len(ops),2)
        self.assertEqual(ops[0].args[0], 'p0')
        self.assertEqual(ops[1].args[0], ops[0].result)
        for op in ops:
            self.assertEqual(op.owner_binding,op.args[0])
            self.assertEqual(op.storage_relation,'borrow_argument_0')
            self.assertEqual(op.source_type,'View<u8>')
            self.assertTrue(op.may_trap)
            self.assertEqual(op.bounds_policy,'trap')

    def test_bounds_dominate_address_and_negative_control(self):
        text=llvm(compile_source('fn probe(v:View<u8>,s:u32,e:u32)->u32{p=view v[s..e];return p.len}'+main('return 0')))
        check_guard_order(text)
        line=next(line for line in text.splitlines(True) if '_ptr = getelementptr' in line)
        # Deliberately move GEP before the validation block.
        mutant=text.replace(line,'')
        at=mutant.index(' = extractvalue')
        at=mutant.rfind('\n',0,at)+1
        mutant=mutant[:at]+line+mutant[at:]
        with self.assertRaisesRegex(AssertionError,'precedes'):
            check_guard_order(mutant)


@unittest.skipUnless(shutil.which('clang'),'requires clang')
class SubviewNative(unittest.TestCase):
    def build(self, root, module, opt, extra='', harness=None):
        ir=root/'module.ll'
        text=llvm(module)
        if harness:
            text=text.replace('define i32 @main()', 'define i32 @test_entry()')
        ir.write_text(text+extra)
        files=[str(ir)]
        if harness:
            c=root/'harness.c';c.write_text(harness);files.append(str(c))
        exe=root/('test'+('.exe' if sys.platform=='win32' else ''))
        r=subprocess.run(['clang','-Wno-override-module',opt,*files,*link_flags(module),'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        return exe

    def test_dynamic_parent_bounds_binary_and_empty(self):
        module=compile_source('''fn probe(v:View<u8>,s:u32,e:u32,read:bool)->u32{
            p=view v[1..4];q=view p[s..e]
            if read {return u32(q[0])}
            return q.len
        }'''+main('return 0'))
        bridge='''
define i32 @run(ptr %data,i32 %s,i32 %e,i1 %read) {
 %a=insertvalue {ptr,i32} zeroinitializer,ptr %data,0
 %v=insertvalue {ptr,i32} %a,i32 8,1
 %r=call i32 @liza_probe({ptr,i32} %v,i32 %s,i32 %e,i1 %read)
 ret i32 %r
}
'''
        harness='''#include <stdint.h>
#include <stdlib.h>
extern uint32_t run(const uint8_t*,uint32_t,uint32_t,_Bool);
int main(int argc,char**argv){uint8_t b[8]={99,0,128,255,66,77,88,99};
if(argc!=5)return 2;return run(b,strtoul(argv[1],0,10),strtoul(argv[2],0,10),atoi(argv[3]))==strtoul(argv[4],0,10)?0:1;}
'''
        cases=[(0,3,1,0),(1,3,1,128),(2,3,1,255),(3,3,0,0),(0,0,0,0),
               (0,3,0,3),(0,4,0,None),(2,1,0,None),(3,3,1,None),
               (4294967295,4294967295,0,None),(0,4294967295,0,None)]
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as folder:
                exe=self.build(Path(folder),module,opt,bridge,harness)
                for s,e,read,expected in cases:
                    with self.subTest(opt=opt,case=(s,e,read)):
                        r=subprocess.run([str(exe),str(s),str(e),str(read),str(expected or 0)],capture_output=True,timeout=10)
                        if expected is None:self.assertNotIn(r.returncode,(0,1,2))
                        else:self.assertEqual(r.returncode,0,r.stderr)

    def test_generic_large_elements_and_phi(self):
        source='''struct Row {data:[u32;80]}
        fn last<T>(v:View<T>)->T {q=view v[1..2];return q[0]}
        fn main()->u32{
            a=[Row([7;80]),Row([9;80]),Row([11;80])]
            p=view a[0..3];var q=view p[0..2]
            var i=0;while i<2 {q=view p[1..3];i=i+1}
            row=last(q);return row.data[79]-11
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as folder:
                exe=self.build(Path(folder),compile_source(source),opt)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)

    def test_string_write_logical_length_and_owner_reuse(self):
        source='''import text.string
        fn main()->u32:io,alloc{
        match memory.create(32){Err(e)=>{return 1}Ok(r)=>{
        match memory.alloc<u8>(r,32,255){Err(e)=>{c=memory.close(move r);return 2}Ok(b)=>{
        var s=text.string.from_buffer(move b)
        a:[u8;7]=[65,0,240,159,154,128,10];v=view a[0..7]
        (next,status)=text.string.append(move s,v);s=move next
        match status {Err(e)=>{x=text.string.release(move s);c=memory.close(move r);return 3}Ok(done)=>{}}
        match text.string.write(s){Err(e)=>{x=text.string.release(move s);c=memory.close(move r);return 6}Ok(n)=>{if n!=7 {x=text.string.release(move s);c=memory.close(move r);return 4}}}
        s=text.string.clear(move s)
        match text.string.write(s){Err(e)=>{x=text.string.release(move s);c=memory.close(move r);return 7}Ok(n)=>{if n!=0 {x=text.string.release(move s);c=memory.close(move r);return 5}}}
        x=text.string.release(move s);c=memory.close(move r);return 0
        }}}}}
        '''
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'text').mkdir()
            (root/'text/string.liza').write_text((ROOT/'examples/text/string.liza').read_text())
            file=root/'probe.liza';file.write_text(source)
            module=lower(load_program(file))
            for opt in ('-O0','-O2'):
                exe=self.build(root,module,opt)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(r.stdout,b'A\0\xf0\x9f\x9a\x80\n')

    def test_descriptor_cost_o0_o2(self):
        text=llvm(compile_source('fn probe(v:View<u8>,s:u32,e:u32)->u32{p=view v[s..e];return u32(p[0])}'+main('return 0')))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.ll';source.write_text(text)
            for opt in ('-O0','-O2'):
                out=root/'out.ll'
                subprocess.run(['clang','-Wno-override-module',opt,'-S','-emit-llvm',str(source),'-o',str(out)],capture_output=True,check=True)
                body=re.search(r'^define .*@liza_probe\([^\n]*\)[^\n]*\{\n(.*?)^}',out.read_text(),re.M|re.S).group(1)
                self.assertNotRegex(body,r'\b(alloca|store|memcpy|memmove|malloc)\b')
                self.assertRegex(body,r'\bload i8\b')


if __name__=='__main__':unittest.main()
