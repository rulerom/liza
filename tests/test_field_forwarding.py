"""Production unchanged-field forwarding: deep joins, rejection and native traps."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from liza.frontend import Parser
from liza.ir import lower, dump
from liza import backend
from liza.field_forwarding import analyze

SOURCE=(Path(__file__).parent/'fixtures/field_forwarding.liza').read_text()
def module(source=SOURCE):return lower(Parser(source).parse())
def plans(m):return {f.name:analyze(f,m.structs,lambda t:False) for f in m}

class FieldForwarding(unittest.TestCase):
 def test_nested_phis_and_remote_write(self):
  m=module();p=plans(m)
  self.assertEqual(len(p['nested'].roots),2)
  self.assertFalse(p['remote_change'].roots)
  for ty,field,source in p['nested'].certificates.values():
   facts=p['nested'].facts[ty,field];self.assertEqual(facts[source].root,'p0')
   self.assertTrue(facts[source].through_phi)
   self.assertGreater(sum(f.through_phi and len(f.inputs)>1 for f in facts.values()),2)
 def test_ir_immutable_and_name_independent(self):
  m=module();before=dump(m);ir=backend.llvm(m);self.assertEqual(dump(m),before)
  renamed=module(SOURCE.replace('Packet','Route').replace('sequence','epoch').replace('nested','other'))
  self.assertEqual(len(plans(renamed)['other'].roots),2)
  self.assertIn('extractvalue %struct.Packet %p0, 0',ir)
 def test_other_roots_and_same_value_write_are_rejected(self):
  source='struct S {x:u64;y:u64} fn f(a:S,b:S,c:bool)->u64 {var n=a;if c {n=b} return n.x} fn g(a:S,c:bool)->u64 {var n=a;if c {n.x=a.x} return n.x} fn main()->u32{return 0}'
  self.assertTrue(all(not p.roots for p in plans(module(source)).values()))
 def test_modes_resources_layout_effects_and_cycles(self):
  for mode in ('readonly','mutable'):
   m=module();next(f for f in m if f.name=='nested').params[0]['mode']=mode
   self.assertFalse(plans(m)['nested'].roots)
  m=module();m.structs['Packet'].properties['copyable']=False
  self.assertFalse(plans(m)['nested'].roots)
  m=module();f=next(f for f in m if f.name=='nested')
  self.assertFalse(analyze(f,m.structs,lambda t:True).roots)
  f.effect_contract='io';self.assertFalse(plans(m)['nested'].roots)
  source='struct S {x:u64;y:u64} fn f(s:S,c:bool)->u64 {var n=s;while c {n.y=1} return n.x} fn main()->u32{return 0}'
  self.assertFalse(plans(module(source))['f'].roots)
 def test_shared_diamonds_are_linear_and_nonrecursive(self):
  body='\n'.join('if c {n.tag=7} else {n.tag=8}' for _ in range(250))
  m=module('struct Packet {sequence:u64;tag:u64} fn f(s:Packet,c:bool)->u64 {var n=s;'+body+';return n.sequence} fn main()->u32{return 0}')
  f=next(f for f in m if f.name=='f');p=plans(m)['f'];ops=sum(len(b.operations) for b in f.blocks)
  self.assertEqual(len(p.roots),1);self.assertLessEqual(p.visits,2*ops)
  self.assertLessEqual(sum(len(v) for v in p.facts.values()),2*(ops+len(f.params)))

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class FieldForwardingNative(unittest.TestCase):
 def test_branches_snapshots_and_negative_controls_o0_o2(self):
  m=module();good=backend.llvm(m)
  def unsafe(fn,structs,large):
   p=analyze(fn,structs,large)
   if fn.name=='remote_change':
    for b in fn.blocks:
     for op in b.operations:
      if op.op=='struct.field' and op.field_name=='sequence':p.roots[op.result]='p0'
   return p
  with patch.object(backend,'field_forwarding',side_effect=unsafe):bad=backend.llvm(m)
  match=re.search(r'(?ms)^define i64 @liza_increment.*?^}',good)
  body,count=re.subn(r'br i1 %[^,]+, label %[^,]+, label %([^\n]+)',r'br label %\1',match[0]);self.assertEqual(count,1)
  deleted=good[:match.start()]+body+good[match.end():]
  bridge='''
define i64 @other_trap() {
entry:
 %s = insertvalue %struct.Packet zeroinitializer, i64 -1, 1
 %r = call i64 @liza_other_field_trap(%struct.Packet %s, i1 true)
 ret i64 %r
}
define i64 @probe(i1 %a, i1 %b, i1 %c) {
entry:
 %s = insertvalue %struct.Packet zeroinitializer, i64 -1, 1
 %r = call %struct.Packet @liza_remote_change(%struct.Packet %s, i1 %a, i1 %b, i1 %c)
 %v = extractvalue %struct.Packet %r, 0
 ret i64 %v
}
'''
  driver='''#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
extern uint32_t liza_snapshots(bool,bool,bool);
extern uint64_t probe(bool,bool,bool),liza_increment(uint64_t),other_trap(void);
int main(int argc,char**argv){
 int n=atoi(argv[1]);
 if(n<8)return liza_snapshots(n&1,n&2,n&4);
 printf("%llu\\n",(unsigned long long)(n==8?probe(true,true,true):(n==9?liza_increment(UINT64_MAX):other_trap())));return 0;}
'''
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);c=root/'driver.c';c.write_text(driver)
   for label,ir in [('good',good),('wrong-field',bad),('deleted-trap',deleted)]:
    path=root/(label+'.ll');path.write_text(ir.replace('define i32 @main()','define i32 @unused_main()')+bridge)
    for opt in (0,2):
     exe=root/(label+str(opt)+'.exe')
     build=subprocess.run(['clang','-Wno-override-module','-O'+str(opt),str(path),str(c),'-o',str(exe)],capture_output=True,text=True)
     self.assertEqual(build.returncode,0,build.stderr)
     for n in range(11):
      with self.subTest(label=label,opt=opt,case=n):
       r=subprocess.run([str(exe),str(n)],capture_output=True,text=True,timeout=10)
       if n<8:self.assertEqual(r.returncode,0)
       elif (label,n) in [('wrong-field',8),('deleted-trap',9)]:
        self.assertEqual(r.returncode,0);self.assertEqual(r.stdout,'1\n' if n==8 else '0\n')
       elif sys.platform=='win32':self.assertIn(r.returncode & 0xffffffff,(0x80000003,0xc000001d))
       else:self.assertIn(r.returncode,(-4,-5))
