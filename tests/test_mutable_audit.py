"""Independent finite permission oracle and observable native M0 audit.

The expected matrix uses source modes/roots only, never compiler loan metadata.
This is a bounded regression audit, not a proof of all source programs.
"""
from itertools import product
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

MODES=('value','readonly','mutable')
PREFIX={'value':'','readonly':'borrow ','mutable':'borrow mut '}
STRUCT='struct S {n:u32}\n'


def allowed(first, second, same_root):
    if not same_root:
        return True
    # Acquiring a writer forbids later access of every kind, including value
    # reads. A readonly loan only forbids a subsequent writer. A value read
    # takes an independent snapshot before the next argument is evaluated.
    return first!='mutable' and not (first=='readonly' and second=='mutable')


def argument(mode,root):
    return ('borrow mut ' if mode=='mutable' else '')+root


def program(first,second,left,right):
    signature=f"fn exercise({PREFIX[first]}p:S,{PREFIX[second]}q:S)->u32"
    body=' {before=p.n*10+q.n;'
    if first=='mutable':body+='p.n=p.n+3;'
    if second=='mutable':body+='q.n=q.n+5;'
    body+='return before}\n'
    changes={'a':0,'b':0}
    if first=='mutable':changes[left]+=3
    if second=='mutable':changes[right]+=5
    before=(1 if left=='a' else 2)*10+(1 if right=='a' else 2)
    caller='fn main()->u32 {var a=S(1);var b=S(2);old_a=copy a;old_b=copy b;'
    caller+=f'got=exercise({argument(first,left)},{argument(second,right)});'
    caller+=f'if got!={before} || a.n!={1+changes["a"]} || b.n!={2+changes["b"]} {{return 1}}'
    caller+='if old_a.n!=1 || old_b.n!=2 {return 2} return 0}'
    return STRUCT+signature+body+caller


class PermissionAudit(unittest.TestCase):
    def test_complete_two_argument_matrix(self):
        for first,second,left,right in product(MODES,MODES,('a','b'),('a','b')):
            with self.subTest(first=first,second=second,left=left,right=right):
                source=program(first,second,left,right)
                if allowed(first,second,left==right):lower(Parser(source).parse())
                else:
                    with self.assertRaises(CompileError):lower(Parser(source).parse())

    def test_pending_loan_survives_nested_argument_call(self):
        for outer,inner,same in product(('readonly','mutable'),MODES,(False,True)):
            source=STRUCT+f'''fn hold({PREFIX[outer]}s:S,n:u32)->u32 {{return n}}
fn nested({PREFIX[inner]}s:S)->u32 {{return s.n}}
fn main()->u32 {{var a=S(1);var b=S(2);
return hold({argument(outer,'a')},nested({argument(inner,'a' if same else 'b')}))}}'''
            with self.subTest(outer=outer,inner=inner,same=same):
                if allowed(outer,inner,same):lower(Parser(source).parse())
                else:
                    with self.assertRaises(CompileError):lower(Parser(source).parse())


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class NativeAudit(unittest.TestCase):
    def execute(self,source,expect_trap=False,stdout=b''):
        module=lower(Parser(source).parse())
        for opt in ('-O0','-O2'):
            with self.subTest(opt=opt),tempfile.TemporaryDirectory() as directory:
                path=Path(directory);ir=path/'test.ll';ir.write_text(llvm(module));exe=path/'test.exe'
                built=subprocess.run(['clang','-Wno-override-module',opt,str(ir),*link_flags(module),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(built.returncode,0,built.stderr)
                result=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(result.stdout,stdout)
                if expect_trap:
                    if sys.platform=='win32':self.assertIn(result.returncode & 0xffffffff,(0x80000003,0xc000001d))
                    else:self.assertLess(result.returncode,0)
                else:self.assertEqual(result.returncode,0,result.stderr)

    def test_all_permitted_combinations_preserve_snapshots_and_writes(self):
        cases=[]
        for first,second,left,right in product(MODES,MODES,('a','b'),('a','b')):
            if allowed(first,second,left==right):
                index=len(cases)
                text=program(first,second,left,right).replace(STRUCT,'')
                text=text.replace('exercise',f'exercise{index}').replace('main',f'case{index}')
                cases.append(text)
        self.execute(STRUCT+'\n'.join(cases)+'\nfn main()->u32 {return '+'+'.join(f'case{i}()' for i in range(len(cases)))+'}')

    def test_sibling_scopes_do_not_share_binding_identity(self):
        self.execute(STRUCT+'''fn change(borrow mut value:S)->u32 {value.n=3;return 0}
fn main()->u32 {
 {var value:u32=7;value=value+1;if value!=8 {return 1}}
 {var value=S(1);snapshot=copy value;done=change(borrow mut value);
  if value.n!=3 || snapshot.n!=1 {return 2}}
 {var value:u32=9;value=value-1;if value!=8 {return 3}}
 return 0
}''')

    def test_bounds_trap_precedes_rhs_io(self):
        template='''struct Storage {data:[u32;2]}
fn rhs()->u32:io {written=console.write("R");return 7}
fn write(borrow mut s:Storage,index:u32)->u32:io {s.data[index]=rhs();return 0}
fn main()->u32:io {var s=Storage([0;2]);done=write(borrow mut s,INDEX);return 0}'''
        self.execute(template.replace('INDEX','1'),stdout=b'R')
        for index in ('2','4294967295'):
            self.execute(template.replace('INDEX',index),expect_trap=True,stdout=b'')

    def test_write_before_err_and_io_remains_visible(self):
        self.execute(STRUCT+'''fn observe(borrow s:S)->u32:io {
 if s.n==9 {written=console.write("9")} else {written=console.write("?")}
 return s.n
}
fn change(borrow mut s:S)->Result<u32,u32>:io {
 s.n=9;seen=observe(s);return Err(1)
}
fn main()->u32:io {var s=S(0);match change(borrow mut s){Ok(n)=>{return 1} Err(e)=>{}}
 return s.n-9}''',stdout=b'9')
