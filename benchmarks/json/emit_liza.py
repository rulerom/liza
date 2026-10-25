"""Executed with PYTHONPATH and cwd set to the pinned source snapshot."""
import sys
import json
from pathlib import Path
from liza.frontend import Parser
from liza.ir import lower, dump
from liza.backend import llvm
from liza.stdlib import link_flags
from liza.target import resolve

KINDS = ['Syntax','InvalidNumber','InvalidEscape','InvalidSurrogate','InvalidUtf8','UnexpectedEof','DepthLimit','SizeOverflow']
SOURCE = '''
fn status(s:JsonState)->u32 {match json.finish(s) {Ok(n)=>{return 0} Err(e)=>{match e.kind {
''' + '\n'.join('JsonErrorKind.%s=>{return %d}' % (k,i+1) for i,k in enumerate(KINDS)) + '''
}}}}
fn value(s:JsonState)->u64 {match json.finish(s) {Ok(n)=>{return n} Err(e)=>{return e.offset}}}
fn pending(s:JsonState)->u32 {match json.status(s) {Some(e)=>{return 1} None=>{return 0}}}
fn start()->JsonState {return json.create()}
fn feed(s:JsonState,v:View<u8>)->JsonState {return json.feed(s,v)}
fn main()->u32 {return 0}
'''
BRIDGE = '''
define void @stream_start(ptr %out) {
 call void @liza_json.create(ptr sret(%struct.JsonState) %out)
 ret void
}
define void @stream_feed(ptr %state, ptr %bytes, i32 %length) {
 %result = alloca %struct.JsonState
 %a = insertvalue {ptr, i32} zeroinitializer, ptr %bytes, 0
 %v = insertvalue {ptr, i32} %a, i32 %length, 1
 call void @liza_json.feed(ptr sret(%struct.JsonState) %result, ptr %state, {ptr, i32} %v)
 %n = load %struct.JsonState, ptr %result
 store %struct.JsonState %n, ptr %state
 ret void
}
define i32 @stream_status(ptr %state) {
 %r = call i32 @liza_status(ptr %state)
 ret i32 %r
}
define i32 @stream_pending(ptr %state) {
 %r = call i32 @liza_pending(ptr %state)
 ret i32 %r
}
define i64 @stream_value(ptr %state) {
 %r = call i64 @liza_value(ptr %state)
 ret i64 %r
}
define i64 @stream_size() {
 %end = getelementptr %struct.JsonState, ptr null, i32 1
 %size = ptrtoint ptr %end to i64
 ret i64 %size
}
'''
if __name__ == '__main__':
    m=lower(Parser(SOURCE).parse())
    assert not link_flags(m)
    target=resolve(sys.argv[2])
    Path(sys.argv[1]).with_suffix('.target.json').write_text(json.dumps(target.metadata(),indent=2))
    Path(sys.argv[1]).with_suffix('.semantic.txt').write_text(dump(m))
    Path(sys.argv[1]).write_text(llvm(m,target).replace('define i32 @main()', 'define i32 @example_entry()')+BRIDGE)
