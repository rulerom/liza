"""Bounded integer formatting: full ranges, no resource mut borrow or allocator."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('clang'),'requires clang')
class BuilderTests(unittest.TestCase):
    def test_integer_boundaries_capacity_and_existing_prefix(self):
        cases=[('u64',n) for n in (0,1,9,10,99,100,2**32-1,2**63,2**64-1)]
        cases += [('i64',n) for n in (-2**63,-2**63+1,-100,-10,-1,0,1,2**63-1)]
        functions=[]
        calls=[]
        for index,(kind,value) in enumerate(cases):
            for capacity in (len(str(value))+1,len(str(value))):
                name='case'+str(len(calls))
                expected=('x'+str(value)).encode() if capacity>len(str(value)) else b'x'
                checks=''.join('match text.string.byte_at(s,%d){None=>{status=4}Some(byte)=>{if byte!=%d{status=5}}}'%(i,b) for i,b in enumerate(expected))
                functions.append('''fn '''+name+'''()->u32:alloc{
                match memory.create(32){Err(e)=>{return 1}Ok(r)=>{
                var status:u32=0
                match memory.alloc<u8>(r,'''+str(capacity)+''',255){Err(e)=>{status=2}Ok(b)=>{
                var s=text.string.from_buffer(move b)
                a:[u8;1]=[120];v=view a[0..1]
                (first,ok)=text.builder.append(move s,v);s=move first
                (next,result)=text.builder.append_'''+kind+'''(move s,'''+str(value)+''');s=move next
                match result {Ok(done)=>{if '''+str(capacity)+'''<'''+str(len(str(value))+1)+''' {status=3}}
                Err(e)=>{match e {text.string.Error.InvalidUtf8(bad)=>{status=7}
                text.string.Error.Full=>{if '''+str(capacity)+'''>='''+str(len(str(value))+1)+''' {status=3}}}}}
                if text.string.length(s)!='''+str(len(expected))+''' {status=6}
                '''+checks+'''
                released=text.string.release(move s)
                }}
                closed=memory.close(move r);return status
                }}}''')
                calls.append('if '+name+'()!=0{return '+str(len(calls)+1)+'}')
        source='import text.string\nimport text.builder\n'+'\n'.join(functions)+'\nfn main()->u32:alloc{'+''.join(calls)+'return 0}'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples/text',root/'text')
            entry=root/'probe.liza';entry.write_text(source)
            module=lower(load_program(entry))
            for fn in module:
                if fn.name.startswith('text.builder.'):
                    self.assertEqual(fn.effect_contract,'pure')
                    self.assertFalse(any(op.op in ('region.create','region.alloc','vec.create','vec.reserve') for b in fn.blocks for op in b.operations))
            ir=root/'probe.ll';ir.write_text(llvm(module))
            for opt in ('-O0','-O2'):
                exe=root/('probe'+('.exe' if sys.platform=='win32' else ''))
                subprocess.run(['clang','-Wno-override-module',opt,str(ir),*link_flags(module),'-o',str(exe)],check=True,capture_output=True)
                result=subprocess.run([str(exe)],capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,(opt,result.stderr))

if __name__=='__main__':unittest.main()
