"""Emit the same scalar harness with explicit mutation, no copy-back bridge."""
import importlib.util
import json
from pathlib import Path
import sys
from liza.frontend import Parser
from liza.ir import lower, dump
from liza.backend import llvm
from liza.target import resolve

path=Path(__file__).resolve().parents[1]/'json'/'emit_liza.py'
spec=importlib.util.spec_from_file_location('baseline_emit',path)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
source=base.SOURCE.replace('fn feed(s:JsonState,v:View<u8>)->JsonState {return json.feed(s,v)}',
                         'fn feed(borrow mut s:JsonState,v:View<u8>)->u32 {return json.feed_mut(borrow mut s,v)}')
bridge=base.BRIDGE.replace(' %result = alloca %struct.JsonState\n','')
bridge=bridge.replace(' call void @liza_json.feed(ptr sret(%struct.JsonState) %result, ptr %state, {ptr, i32} %v)\n %n = load %struct.JsonState, ptr %result\n store %struct.JsonState %n, ptr %state',
                      ' %code = call i32 @liza_json.feed_mut(ptr %state, {ptr, i32} %v)')
module=lower(Parser(source).parse());target=resolve(sys.argv[2]);out=Path(sys.argv[1])
out.with_suffix('.target.json').write_text(json.dumps(target.metadata(),indent=2))
out.with_suffix('.semantic.txt').write_text(dump(module))
out.write_text(llvm(module,target).replace('define i32 @main()', 'define i32 @example_entry()')+bridge)
