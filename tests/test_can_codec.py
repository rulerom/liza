"""Native typed CAN decoding and assignment lifecycle, without TLS dependency."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_httpws import build,array
ROOT=Path(__file__).resolve().parents[1]

PRELUDE="""import can.messages
import can.logic
import can.words
import can.text
fn classify(message:can.messages.Message)->u32 {
 match message {
 can.messages.Message.Hello(v)=>{return 1} can.messages.Message.Ready(v)=>{return 2}
 can.messages.Message.Heartbeat(v)=>{return 3} can.messages.Message.HeartbeatOk(v)=>{return 4}
 can.messages.Message.Job(v)=>{return 5} can.messages.Message.Ack(v)=>{return 6}
 can.messages.Message.Event(v)=>{return 7} can.messages.Message.Cancel(v)=>{return 8}
 can.messages.Message.Control(v)=>{return 9} can.messages.Message.Failure(v)=>{return 10}
 can.messages.Message.Unknown(v)=>{return 11}}
}
fn probe(data:View<u8>)->u32:alloc {
 match memory.create(8192) {Err(e)=>{return 99} Ok(region)=>{
 match memory.alloc<u8>(region,4096,0) {Err(e)=>{c=memory.close(move region);return 99} Ok(initial)=>{
 match memory.alloc<u8>(region,1024,0) {Err(e)=>{b=memory.release(move initial);c=memory.close(move region);return 99} Ok(scratch)=>{
 var buffer=move initial;var i:u32=0
 while i<data.len {buffer=memory.set(move buffer,i,data[i]);i=i+1}
 (document,decoded,result)=can.messages.parse(move buffer,data.len,move scratch)
 b=memory.release(move document);s=memory.release(move decoded);c=memory.close(move region)
 match result {Err(e)=>{return 0} Ok(message)=>{return classify(message)}}
 }}}}}}
}
"""

STATE="""
fn main()->u32 {
 node=can.words.literal_worker();job=can.words.literal_job_id();assignment=can.words.literal_assignment_id()
 var state=can.logic.create(node,1);hello=can.logic.take(borrow mut state)
 ready=can.messages.Message.Ready(can.messages.Ready(node,can.words.literal_worker(),100,100,90000,1,1))
 r=can.logic.receive(borrow mut state,ready,1,100,1000);if r!=0||!state.registered {return 1}
 work=can.messages.Message.Job(can.messages.Assignment(job,assignment,can.words.literal_example_echo(),can.words.literal_echo(),100))
 stale=can.logic.receive(borrow mut state,work,0,100,1000);if state.active {return 2}
 accepted=can.logic.receive(borrow mut state,work,1,100,1000);if !state.active {return 3}
 wrong=can.logic.finish(borrow mut state,2,job,assignment,4);if wrong||!state.active {return 4}
 foreign=can.logic.finish(borrow mut state,1,job,node,4);if foreign||!state.active {return 5}
 done=can.logic.finish(borrow mut state,1,job,assignment,4);if !done||state.active {return 6}
 duplicate=can.logic.finish(borrow mut state,1,job,assignment,4);if duplicate {return 7}
 reset=can.logic.invalidate(borrow mut state,2);if reset!=0||state.count!=0||state.active {return 8}
 late=can.logic.receive(borrow mut state,work,1,100,1000);if state.active {return 9}
 var heartbeat=can.logic.create(node,1);h=can.logic.take(borrow mut heartbeat)
 reg=can.logic.receive(borrow mut heartbeat,ready,1,100,1000)
 t1=can.logic.tick(borrow mut heartbeat,200,1000,false);q1=can.logic.take(borrow mut heartbeat)
 t2=can.logic.tick(borrow mut heartbeat,300,1000,false);q2=can.logic.take(borrow mut heartbeat)
 if heartbeat.heartbeat_ack_due!=1200 {return 10}
 expired=can.logic.tick(borrow mut heartbeat,1200,1000,false);if expired!=1 {return 11}
 return 0
}
"""

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class CanCodec(unittest.TestCase):
    def test_published_corpus_and_mutated_required_fields(self):
        cases=[]
        types={'hello':1,'hello_ok':2,'heartbeat':3,'heartbeat_ok':4,'job':5,'job_ack':6,'job_event':7,'job_cancel':8,'control':9,'error':10}
        corpus=json.loads((ROOT/'tests/fixtures/can_examples.json').read_text())['examples']
        for example in corpus:
            message=example['message']
            cases.append((json.dumps(message,ensure_ascii=False).encode(),types.get(message.get('type'),11) if 'type' in message else 0))
        required={'hello':['node_id','role','assignment_protocol'],'hello_ok':['node_id','role','server_time','heartbeat_ms','lease_timeout_ms','max_concurrent_jobs','assignment_protocol'],'heartbeat_ok':['server_time'],'job':['job_id','assignment_id','job_type','payload','server_time'],'job_ack':['job_id','assignment_id'],'job_event':['job_id','assignment_id','status'],'job_cancel':['job_id','assignment_id'],'control':['request_id','method','params','expects_reply'],'error':['code']}
        for example in corpus:
            message=example['message']
            for key in required.get(message.get('type'),[]):
                for value in ('missing',None,[]):
                    bad=dict(message)
                    if value=='missing':del bad[key]
                    else:bad[key]=value
                    cases.append((json.dumps(bad).encode(),0))
        cases.extend([(b'{"type":"heartbeat_ok","server_time":1,"server_time":2}',0),(b'{"type":"job_cancel","job_id":"\\ud800","assignment_id":"x"}',0)])
        with tempfile.TemporaryDirectory(prefix='liza-can-codec-') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples/can',root/'can');source=PRELUDE+'fn main()->u32:io,alloc {\n'
            for i,(data,expected) in enumerate(cases):
                source+=f'd{i}:[u8;{len(data)}]={array(data)};r{i}=probe(view d{i}[0..{len(data)}]);n{i}=console.print_u64(u64(r{i}));l{i}=console.println("");\n'
            source+='return 0}';entry=root/'probe.liza';entry.write_text(source)
            for opt in ('0','2'):
                out=root/opt;out.mkdir();exe=build(entry,out,opt,root)
                run=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(run.returncode,0,run.stderr)
                observed=list(map(int,run.stdout.splitlines()))
                self.assertEqual(len(observed),len(cases))
                for i,(got,(_,want)) in enumerate(zip(observed,cases)):
                    self.assertEqual(got,want,(opt,i,cases[i][0]))

    def test_generation_identity_slot_and_heartbeat_deadline(self):
        with tempfile.TemporaryDirectory(prefix='liza-can-state-') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples/can',root/'can');entry=root/'probe.liza';entry.write_text(PRELUDE+STATE)
            for opt in ('0','2'):
                out=root/opt;out.mkdir();exe=build(entry,out,opt,root)
                run=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(run.returncode,0,(opt,run.stderr))

    def test_negative_identity_and_deadline_mutations(self):
        original=(ROOT/'examples/can/logic.liza').read_text()
        mutations=[
            ('generation','generation!=state.generation||generation!=state.active_generation||','',4),
            ('assignment','||!can.text.equal(assignment,state.assignment)','',5),
            ('heartbeat','if !state.waiting_heartbeat {state.heartbeat_ack_due=now+operation_ms}',
             'state.heartbeat_ack_due=now+operation_ms',10),
        ]
        for name,before,after,expected in mutations:
            with self.subTest(name=name),tempfile.TemporaryDirectory(prefix='liza-can-mutation-') as folder:
                self.assertEqual(original.count(before),1)
                root=Path(folder);shutil.copytree(ROOT/'examples/can',root/'can')
                (root/'can/logic.liza').write_text(original.replace(before,after))
                entry=root/'probe.liza';entry.write_text(PRELUDE+STATE)
                exe=build(entry,root,'2',root)
                run=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(run.returncode,expected,(name,run.stderr))
