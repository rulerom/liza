import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from transforms import scalarize,boundary_alias
from traffic import instrument
HERE=Path(__file__).resolve().parent

class Controls(unittest.TestCase):
    def test_noalias_conflict_and_checked_fallback(self):
        ir='''define i32 @plain(ptr %p, ptr %q) {
 store i32 1, ptr %p
 store i32 2, ptr %q
 %v = load i32, ptr %p
 ret i32 %v
}
'''
        ir+=ir.replace('@plain','@restricted').replace('ptr %p,','ptr noalias %p,')
        driver='''#include <stdio.h>
extern int plain(int*,int*),restricted(int*,int*);
int checked(int*p,int*q){return p==q?plain(p,q):restricted(p,q);}
int main(void){int x=0,y=0; int good=checked(&x,&y);int conflict=checked(&x,&x);int wrong=restricted(&x,&x);printf("[%d,%d,%d]",good,conflict,wrong);}
'''
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'a.ll').write_text(ir);(root/'a.c').write_text(driver)
            for opt in (0,2):
                subprocess.run(['clang',f'-O{opt}',root/'a.ll',root/'a.c','-o',root/'probe'],check=True,capture_output=True)
                good,conflict,wrong=json.loads(subprocess.check_output([root/'probe']))
                self.assertEqual((good,conflict),(1,2))
                # Deliberate LLVM UB is a negative control, never a valid invocation.
                if opt==2:self.assertNotEqual(wrong,conflict)

    def test_exact_traffic_on_known_accesses(self):
        ir='''define void @stream_feed(ptr %state, ptr %bytes, i32 %length) {
 %x = load i8, ptr %state
 %y = load i8, ptr %bytes
 %z = add i8 %x, %y
 store i8 %z, ptr %state
 ret void
}
'''
        counted,_=instrument(ir,'state',1)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'a.ll').write_text(counted)
            (root/'a.c').write_text('extern void stream_feed(void*,void*,unsigned);int main(void){unsigned char a=1,b=2;stream_feed(&a,&b,1);stream_feed(&a,&b,1);return a!=5;}')
            subprocess.run(['clang','-O0',root/'a.ll',root/'a.c',HERE/'traffic.c','-o',root/'probe'],check=True,capture_output=True)
            r=subprocess.run([root/'probe'],capture_output=True,check=True);counts=json.loads(r.stderr)
            self.assertEqual((counts['state_loads'],counts['state_stores'],counts['load_spans'],counts['store_spans']),(2,2,2,2))

    def test_metadata_and_parameter_alias_attributes(self):
        ir='define void @stream_feed(ptr noalias %state, ptr %bytes, i32 %length) {\n %v = load i8, ptr %state, !noalias !1\n ret void\n}\n'
        changed,_=instrument(ir,'state',1)
        self.assertNotIn('! !1',changed);self.assertNotIn('!noalias',changed);self.assertNotIn('ptr noalias',changed)

    def test_intrinsic_name_is_not_an_attribute(self):
        name='llvm.experimental.noalias.scope.decl'
        ir='declare void @'+name+'(metadata)\n'
        changed,_=instrument(ir,'state',1)
        self.assertIn('@'+name,changed)

    def test_boundary_is_narrow(self):
        with self.assertRaises(ValueError):boundary_alias('define void @unrelated(ptr %state) {}')

    def test_scalarization_preserves_fields_and_volatile(self):
        ir='%Pair = type { i8, i64 }\ndefine void @f(ptr %p, ptr %q) {\n %v = load %Pair, ptr %p\n store %Pair %v, ptr %q\n %w = load volatile %Pair, ptr %p\n ret void\n}\n'
        result,count=scalarize(ir)
        self.assertEqual(count,2);self.assertIn('load volatile %Pair',result)
        self.assertIn('load i64',result);self.assertIn('store i8',result)

if __name__=='__main__':unittest.main()
