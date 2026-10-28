"""Native sanity check: instrumentation must count executions, not static sites."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from run import instrument, transform

IR = '''define i32 @helper(i32 %x) {
entry:
  %next = add i32 %x, 1
  ret i32 %next
}
define i32 @main() {
entry:
  %x = call i32 @helper(i32 0)
  %y = call i32 @helper(i32 %x)
  ret i32 0
}
'''

class Instrumentation(unittest.TestCase):
    def test_native_entry_counts(self):
        ir, names = instrument(IR)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            (path/'a.ll').write_text(ir)
            (path/'counter.c').write_text('#include <stdio.h>\nstatic int n[2]; void parity_enter(unsigned x){n[x]++;}\n__attribute__((destructor)) static void done(void){printf("[%d,%d]",n[0],n[1]);}')
            subprocess.run(['clang','-O0',str(path/'a.ll'),str(path/'counter.c'),'-o',str(path/'probe')],check=True,capture_output=True)
            counts = json.loads(subprocess.check_output([str(path/'probe')]))
            self.assertEqual(dict(zip(names,counts)), {'helper':2,'main':1})

    def test_missing_function_fails_closed(self):
        with self.assertRaises(ValueError): transform(IR, ['missing'])

    def test_existing_attributes_fail_closed(self):
        with self.assertRaises(ValueError): transform(IR.replace(') {', ') alwaysinline {'), ['helper'])

    def test_checks_and_effect_order_preserved(self):
        guarded = IR.replace('%next = add i32 %x, 1', '%next = add i32 %x, 1\n  call void @llvm.trap()') + '\ndeclare void @llvm.trap()\n'
        changed = transform(guarded, ['helper'])
        self.assertEqual(changed.replace(' alwaysinline {', ' {'), guarded)

if __name__ == '__main__': unittest.main()
