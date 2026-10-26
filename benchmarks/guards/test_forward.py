"""Research policy boundaries; independent proof/native controls live in check.py."""
import copy,unittest
from liza.frontend import Parser
from liza.ir import lower,dump
from forward import forward
from check import FIXTURE
import symbolic as s

class Policy(unittest.TestCase):
 def module(self,source=FIXTURE):return lower(Parser(source).parse())
 def test_original_module_is_unchanged(self):
  m=self.module();before=dump(m);_,sites=forward(m)
  self.assertEqual(before,dump(m));self.assertTrue(sites)
 def test_names_are_irrelevant(self):
  for source in (FIXTURE,FIXTURE.replace('positive','routing').replace('position','sequence').replace('Sample','Packet')):
   _,sites=forward(self.module(source));self.assertEqual(len(sites),2)
 def test_one_changed_phi_input_is_rejected(self):
  _,sites=forward(self.module());self.assertFalse(any(x['function']=='changed' for x in sites))
 def test_mutable_root_is_rejected(self):
  m=self.module()
  for fn in m:
   for p in fn.params:p['mode']='mutable'
  self.assertEqual(forward(m)[1],[])
 def test_resource_and_pointer_backed_shapes_are_rejected(self):
  for property_name,value in [('copyable',False)]:
   m=self.module();m.structs['Sample'].properties[property_name]=value;self.assertEqual(forward(m)[1],[])
  m=self.module();m.structs['Sample'].fields=[('field'+str(i),'u64') for i in range(65)];self.assertEqual(forward(m)[1],[])
 def test_cycle_is_rejected(self):
  m=self.module();f=next(f for f in m if f.name=='positive')
  phi=next(o for b in f.blocks for o in b.operations if o.op=='phi');phi.args[0]=phi.result
  self.assertFalse(any(x['function']=='positive' for x in forward(m)[1]))
 def test_distinct_roots_are_not_merged(self):
  source='struct S {x:u64;y:u64} fn f(a:S,b:S,c:bool)->u64 {var n=a;if c {n=b} return n.x} fn main()->u32{return 0}'
  self.assertEqual(forward(self.module(source))[1],[])
 def test_unknown_symbolic_operations_fail_closed(self):
  with self.assertRaises(s.Unsupported):s.llvm(s.SMT(),'define i64 @bad(i64 %p0) {\nb0:\n %v = freeze i64 %p0\n ret i64 %v\n}','bad',{'p0':s.S('x',64)})
  with self.assertRaises(s.Unsupported):s.order({'a':0},{'a':['a']})

if __name__=='__main__':unittest.main()
