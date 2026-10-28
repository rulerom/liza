"""Emit the same M0 harness, changing only field sources in a copied Semantic IR."""
import importlib.util
import json
from pathlib import Path
import sys
from forward import forward
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.backend import llvm
from liza.target import resolve
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'benchmarks/json/emit_liza.py';spec=importlib.util.spec_from_file_location('base_emit',p);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
source=base.SOURCE.replace('fn feed(s:JsonState,v:View<u8>)->JsonState {return json.feed(s,v)}','fn feed(borrow mut s:JsonState,v:View<u8>)->u32 {return json.feed_mut(borrow mut s,v)}')
bridge=base.BRIDGE.replace(' %result = alloca %struct.JsonState\n','').replace(' call void @liza_json.feed(ptr sret(%struct.JsonState) %result, ptr %state, {ptr, i32} %v)\n %n = load %struct.JsonState, ptr %result\n store %struct.JsonState %n, ptr %state',' %code = call i32 @liza_json.feed_mut(ptr %state, {ptr, i32} %v)')
module=lower(Parser(source).parse());out=Path(sys.argv[1]);target=resolve(sys.argv[2])
out.with_suffix('.original.semantic.json').write_text(dump(module))
out.with_suffix('.original.ll').write_text(llvm(module,target).replace('define i32 @main()','define i32 @example_entry()')+bridge)
changed,certificates=forward(module)
out.with_suffix('.semantic.json').write_text(dump(changed));out.with_suffix('.certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
out.with_suffix('.target.json').write_text(json.dumps(target.metadata(),indent=2))
out.write_text(llvm(changed,target).replace('define i32 @main()','define i32 @example_entry()')+bridge)
