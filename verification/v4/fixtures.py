"""Fixed programs for independent function, CFG and loop checks."""
from .check import SAFE, UNSAFE

PASS = 'fn pass<T>(value:T)->T{return move value}\n'
CALL = PASS + SAFE.replace('released=memory.release(move buffer)',
                           'next=pass(move buffer)\nreleased=memory.release(move next)')
RESULT_CALL = PASS + SAFE.replace('match move allocation',
                                  'forwarded=pass(move allocation)\nmatch move forwarded')
UPDATE = '''fn update(value:memory.Buffer<u8>)->memory.Buffer<u8> {
    return memory.set(move value,0,42)
}
''' + SAFE.replace('released=memory.release(move buffer)',
                   'next=update(move buffer)\nreleased=memory.release(move next)')
FACTORY = '''fn factory()->Result<memory.Region,MemoryError>:alloc {
    return memory.create(64)
}
''' + SAFE.replace('memory.create(64)', 'factory()')
CFG = PASS + SAFE.replace('released=memory.release(move buffer)', '''var next=move buffer
if true {next=pass(move next)} else {next=pass(move next)}
released=memory.release(move next)''')
LOOP = SAFE.replace('    match memory.create(64)',
                    '    var i:u32=0\n    while i<2 {\n    match memory.create(64)').replace(
                        '            return 0','            i=i+1').rsplit('}',1)[0]+'}\nreturn 0\n}\n'
LIVE_LOOP = SAFE.replace('released=memory.release(move buffer)', '''var next=move buffer
var i:u32=0
while i<2 {
    next=memory.set(move next,0,1)
    i=i+1
}
released=memory.release(move next)''')
CALL_UNSAFE = PASS + SAFE.replace('released=memory.release(move buffer)', '''next=pass(move buffer)
closed=memory.close(move region)
released=memory.release(move next)''').replace('            closed=memory.close(move region)\n','')
# Close on both allocation outcomes, so ordinary linearity still holds.
CALL_UNSAFE = CALL_UNSAFE.replace('Err(e)=>{}', 'Err(e)=>{closed=memory.close(move region)}')
RESOLVED_UNSAFE = CALL_UNSAFE.replace('next=pass(move buffer)', 'next=move buffer')
CFG_UNSAFE = CALL_UNSAFE.replace('next=pass(move buffer)', '''var next=move buffer
if true {next=pass(move next)} else {next=pass(move next)}''')
TWO_REGIONS = '''fn main()->u32:alloc {
match memory.create(64) { Err(e)=>{return 1} Ok(a)=>{
match memory.create(64) { Err(e)=>{c=memory.close(move a)\nreturn 1} Ok(b)=>{
match memory.alloc<u8>(a,4,0) {
Err(e)=>{c=memory.close(move a)}
Ok(data)=>{
c=memory.close(move a)
r=memory.release(move data)
}}
c=memory.close(move b)
return 0
}}}}
}'''
# The ordinary analyzer rejects changed provenance on the backedge. If that
# check is removed, the second iteration closes r while its current buffer lives.
LOOP_UNSAFE = '''fn main()->u32:alloc {
match memory.create(64) {Err(e)=>{return 1} Ok(a)=>{
match memory.create(64) {Err(e)=>{c=memory.close(move a)\nreturn 1} Ok(initial)=>{
var r=move initial
match memory.alloc<u8>(a,4,0) {Err(e)=>{c=memory.close(move r)\nd=memory.close(move a)\nreturn 1} Ok(first)=>{
var buffer=move first
var i:u32=0
while i<2 {
c=memory.close(move r)
match memory.create(64) {
Err(e)=>{x=memory.release(move buffer)\ny=memory.close(move a)\nreturn 1}
Ok(next)=>{r=move next}}
x=memory.release(move buffer)
match memory.alloc<u8>(r,4,0) {
Err(e)=>{failedClose=memory.close(move r)\ny=memory.close(move a)\nreturn 1}
Ok(next)=>{buffer=move next}}
i=i+1
}
x=memory.release(move buffer)
y=memory.close(move r)
z=memory.close(move a)
return 0
}}}}
}}
}'''
WRAP = '''fn wrap(value:memory.Buffer<u8>)->Result<memory.Buffer<u8>,MemoryError> {
return Ok(move value)
}
''' + SAFE.replace('released=memory.release(move buffer)', '''wrapped=wrap(move buffer)
match move wrapped {Err(e)=>{} Ok(b)=>{released=memory.release(move b)}}''')
TWO_BUFFERS = '''fn choose(first:memory.Buffer<u8>,second:memory.Buffer<u8>)->memory.Buffer<u8> {
r=memory.release(move first)
return move second
}
''' + SAFE.replace('released=memory.release(move buffer)', '''match memory.alloc<u8>(region,4,0) {
Err(e)=>{released=memory.release(move buffer)}
Ok(second)=>{next=choose(move buffer,move second)
released=memory.release(move next)}
}''')
TWO_REGIONS_SAFE = TWO_REGIONS.replace('c=memory.close(move a)\nr=memory.release(move data)',
                                     'r=memory.release(move data)\nc=memory.close(move a)')
