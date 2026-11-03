"""Language roles, ownership, and native SG2 composition through SG3."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/workers/reactor_group.liza'
CONFIG='GroupConfig(65536,65536,1048576,1048576,65536,2,2,5000,1000)'

def liza(*args):
    return subprocess.run([sys.executable,'-m','liza',*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=60)

def program(producer='return 0',consumer='return 0',owner='',helpers=''):
    return helpers+f'''\nfn producer()->u32:io,alloc {{{producer}}}
fn consumer()->u32:io,alloc {{{consumer}}}
fn main()->u32:io,alloc {{
 {owner}
 match groups.run({CONFIG}) {{Err(e)=>{{return 1}} Ok(r)=>{{return r.producer+r.consumer}}}}
}}
'''

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class SG3(unittest.TestCase):
    def test_network_and_ir(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('sg3.exe' if sys.platform=='win32' else 'sg3')
            for opt in ('0','2'):
                built=liza('build',EXAMPLE,'-O',opt,'-o',exe)
                self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                for _ in range(3):
                    run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            ir=liza('emit-ir',EXAMPLE)
            self.assertEqual(ir.returncode,0,ir.stderr)
            contract=json.loads(ir.stdout)['group_contract']
            self.assertEqual(contract['entries'],['reactor_group.producer','reactor_group.consumer'])
            self.assertEqual(contract['return_requires'],'all_native_joins_and_handback')
            self.assertEqual(contract['reachable_roles']['reactor_group.read_byte'],['consumer'])
            llvm=liza('emit-llvm',EXAMPLE)
            self.assertEqual(llvm.returncode,0,llvm.stderr)
            self.assertIn('@liza_rt_group_run',llvm.stdout)
            self.assertIn('@liza_rt_group_reactor()',llvm.stdout)
            self.assertNotIn('@liza___liza_reactor_create',llvm.stdout)

    def test_role_rejections(self):
        cases=[
            (program(producer='x=groups.next()\nreturn 0'),'group role cannot'),
            (program(consumer='x=groups.send(1)\nreturn 0'),'group role cannot'),
            (program(owner='x=groups.stop()'),'outside its assigned role'),
            (program(owner='x=producer()'),'callback cannot be called directly'),
            (program(producer='return consumer()'),'callback cannot be called directly'),
            (program(producer=f'x=groups.run({CONFIG})\nreturn 0'),'group role cannot'),
            (program(consumer='x=net.reactor_create(0,1)\nreturn 0'),'resource must'),
            (program(consumer='x=console.println("forbidden")\nreturn 0'),'group role cannot'),
            (program(consumer='x=helper<u32>(1)\nreturn 0', helpers='fn helper<T>(v:T)->u32:io {x=groups.send(1)\nreturn 0}'),'group role cannot'),
            (program(owner='x=helper<u32>(1)', helpers='fn helper<T>(v:T)->u32:io {return groups.busy()}'),'outside its assigned role'),
            ('fn main()->u32:io {return groups.stop()}','require groups.run'),
            (program(owner='x=channels.run(1,1024)'),'cannot mix'),
        ]
        # Creating and closing an independent Reactor is still forbidden in a role.
        cases.append((program(consumer='match net.reactor_create(0,1) {Err(e)=>{return 1} Ok(r)=>{x=net.reactor_close(move r)\nreturn 0}}'),'group role cannot'))
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'roles.liza'
            for source,message in cases:
                with self.subTest(message=message,source=source):
                    src.write_text(source)
                    result=liza('check',src)
                    self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertIn(message,result.stderr)

    def test_shared_helpers_use_intersection_of_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'shared.liza'
            for body,effect,allowed in [('return value-value','',True),
                                       ('x=groups.send(value)\nreturn 0',':io',False),
                                       ('x=groups.port()\nreturn 0',':io',False)]:
                with self.subTest(body=body):
                    helper=f'fn shared(value:u32)->u32{effect} {{{body}}}'
                    src.write_text(program(producer='return shared(7)',consumer='return shared(9)',helpers=helper))
                    result=liza('emit-ir',src)
                    if allowed:
                        self.assertEqual(result.returncode,0,result.stderr)
                        roles=json.loads(result.stdout)['group_contract']['reachable_roles']['shared.shared']
                        self.assertEqual(set(roles),{'producer','consumer'})
                        run=liza('run',src)
                        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                    else:
                        self.assertNotEqual(result.returncode,0)
                        self.assertIn('group role cannot',result.stderr)

    def test_imported_generic_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'helper.liza').write_text('pub fn publish<T>(value:T)->u32:io {x=groups.send(1)\nreturn 0}')
            src=root/'main.liza'
            src.write_text('import helper\n'+program(consumer='return helper.publish<u32>(1)'))
            result=liza('check',src)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('group role cannot',result.stderr)

    def test_results_reuse_and_budgets(self):
        source=f'''fn producer()->u32 {{return 7}}
fn consumer()->u32 {{return 9}}
fn main()->u32:io,alloc {{
 config={CONFIG}
 invalid=GroupConfig(1,65536,1048576,1048576,65536,2,2,5000,1000)
 match groups.run(invalid) {{Ok(r)=>{{return 1}} Err(e)=>{{match e {{
  GroupError.InvalidConfig=>{{}}
  GroupError.Busy=>{{return 2}}
  GroupError.StartupFailed=>{{return 3}}
  GroupError.Faulted(r)=>{{return 4}}
 }}}}}}
 var i:u32=0
 while i<10 {{
  match groups.run(config) {{Err(e)=>{{return 5}} Ok(r)=>{{if r.producer!=7 || r.consumer!=9 || r.fault!=0 || r.control_fault!=0 {{return 6}}}}}}
  i=i+1
 }}
 return 0
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'results.liza';src.write_text(source)
            for opt in ('0','2'):
                result=liza('run',src,'-O',opt)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_stop_from_producer(self):
        source=program(producer='x=groups.stop()\nreturn 0',consumer='''match groups.listen(0) {Err(e)=>{return 1} Ok(x)=>{}}
 match groups.next() {Err(e)=>{return 2} Ok(event)=>{match event {
 GroupEvent.Stopping=>{if groups.stopping()!=1 {return 3}\nreturn 0}
 GroupEvent.Closed=>{return 4}
 GroupEvent.Command(x)=>{return 5}
 GroupEvent.Network(x)=>{return 6}
 GroupEvent.NotificationFault=>{return 7}
 }}}''')
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'stop.liza';src.write_text(source)
            # Stop intent is asynchronous; closure may precede its observation.
            src.write_text(source.replace('GroupEvent.Closed=>{return 4}', 'GroupEvent.Closed=>{while groups.stopping()==0 {}\nreturn 0}'))
            result=liza('run',src)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_native_failure_outcomes_and_shutdown_publication(self):
        fault_source='''fn producer()->u32:io {
 match groups.send(42) {GroupPublication.PublishedFault=>{return 7} GroupPublication.Published=>{return 8} GroupPublication.NotPublished=>{return 9}}
}
fn consumer()->u32:io,alloc {
 match groups.listen(0) {Err(e)=>{return 1} Ok(x)=>{}}
 match groups.next() {Err(e)=>{return 2} Ok(event)=>{match event {
  GroupEvent.Command(v)=>{if v==42 {return 9}\nreturn 3}
  GroupEvent.Network(n)=>{return 4}
  GroupEvent.Closed=>{return 5}
  GroupEvent.Stopping=>{return 6}
  GroupEvent.NotificationFault=>{return 7}
 }}}
}
fn main()->u32:io,alloc {
 match groups.run(CONFIG) {Ok(r)=>{return 1} Err(e)=>{match e {
  GroupError.InvalidConfig=>{return 2}
  GroupError.Busy=>{return 3}
  GroupError.StartupFailed=>{return 4}
  GroupError.Faulted(r)=>{if r.producer!=7 {return 100+r.producer}\nif r.consumer!=9 {return 150+r.consumer}\nif r.fault!=1 {return 200+r.fault}\nreturn 0}
 }}}
}
'''.replace('CONFIG',CONFIG)
        startup_source=f'''fn producer()->u32 {{return 1/0}}
fn consumer()->u32 {{return 1/0}}
fn main()->u32:io,alloc {{
 match groups.run({CONFIG}) {{Ok(r)=>{{return 1}} Err(e)=>{{match e {{
 GroupError.StartupFailed=>{{return 0}}
 GroupError.Busy=>{{return 2}}
 GroupError.InvalidConfig=>{{return 3}}
 GroupError.Faulted(r)=>{{return 4}}
 }}}}}}
}}
'''
        stop_source=program(producer='x=groups.stop()\nreturn 0',consumer='while groups.stopping()==0 {}\nreturn 0')
        idle_source=program(producer='x=groups.stop()\nreturn 0', consumer='''match groups.listen(0) {Err(e)=>{return 1} Ok(x)=>{}}
 while true {match groups.next() {Err(e)=>{return 2} Ok(event)=>{match event {
 GroupEvent.Stopping=>{return 0}
 GroupEvent.Closed=>{}
 GroupEvent.Network(n)=>{return 3}
 GroupEvent.Command(v)=>{return 4}
 GroupEvent.NotificationFault=>{return 5}
 }}}}''')
        closed_idle_source=program(consumer='''match groups.listen(0) {Err(e)=>{return 1} Ok(x)=>{}}
 var closed:u32=0
 while true {match groups.next() {Err(e)=>{return 2} Ok(event)=>{match event {
 GroupEvent.Closed=>{closed=closed+1
if closed!=1 {return 3}}
 GroupEvent.Stopping=>{if closed!=1 {return 4}
return 0}
 GroupEvent.Network(n)=>{return 5}
 GroupEvent.Command(v)=>{return 6}
 GroupEvent.NotificationFault=>{return 7}
 }}}}''')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);suffix='windows' if sys.platform=='win32' else 'posix'
            src=tmp/'faults.liza';ir=tmp/'faults.ll';exe=tmp/('faults.exe' if sys.platform=='win32' else 'faults')
            # Copy just the private headers so the negative control changes publication order
            # without adding a production branch or weakening the normal memory orders.
            for name in ('sg3_common.h','sg2_common.h'):
                shutil.copyfile(ROOT/'liza/runtime'/name,tmp/name)
            original=(tmp/'sg2_common.h').read_text()
            old='atomic_store(&g->shutdown_deadline,sg_now()+g->config.shutdown_ms);atomic_store(&g->shutdown,1);'
            self.assertIn(old,original)
            reordered='atomic_store(&g->shutdown,1);SG_EVENT("test_reordered_stop",g->generation,0);atomic_store(&g->shutdown_deadline,sg_now()+g->config.shutdown_ms);'
            for source,macro,code in ((startup_source,'SG3_STARTUP_FAIL',0),(fault_source,'SG3_DATA_FAIL',0),
                                      (fault_source,'SG3_DOUBLE_FAIL',86),(stop_source,'SG3_NORMAL_STOP',0),
                                      (stop_source,'SG3_REORDER_STOP',92),(idle_source,'SG3_IDLE_STOP',0),(closed_idle_source,'SG3_CLOSED_IDLE',0)):
                with self.subTest(macro=macro):
                    src.write_text(source)
                    result=liza('emit-llvm',src,'-o',ir)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    (tmp/'sg2_common.h').write_text(original.replace(old,reordered) if macro=='SG3_REORDER_STOP' else original)
                    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DLIZA_SG2_TESTING','-D'+macro,
                         '-I',str(tmp),'-I',str(ROOT/'liza/runtime'),str(ir),str(ROOT/'tests/fixtures/sg3_faults.c'),
                         str(ROOT/f'liza/runtime/net_{suffix}.c'),str(ROOT/f'liza/runtime/reactor_{suffix}.c'),
                         str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
                    cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
                    built=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
                    self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                    result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
                    self.assertEqual(result.returncode,code,result.stdout+result.stderr)
                    if code==86:self.assertIn('sg3 escalation: no result',result.stderr)
                    if code==92:self.assertIn('shutdown_without_deadline',result.stderr)
