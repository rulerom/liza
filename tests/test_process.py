"""Process ownership and native lifecycle; fixture children never use a shell."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from liza.frontend import Parser,CompileError
from liza.ir import lower
from test_httpws import build,array
ROOT=Path(__file__).resolve().parents[1]
CLEANUP='''
fn cleanup(child:process.Child)->u32:io,alloc {
 var owned=move child
 while true {match process.close(move owned) {
 Ok(done)=>{return 0} Err(failure)=>{
 (next,error)=move failure;owned=move next
 killed=process.kill(owned);waited=process.wait(owned)
 }}}
}
'''
def arguments(values):
    source=''
    for i,value in enumerate(values):
        data=value.encode();source+='a%d:[u8;%d]=%s;match process.argument(command,view a%d[0..%d]) {Err(e)=>{return 20} Ok(next%d)=>{command=next%d}}\n' % (i,len(data),array(data),i,len(data),i,i)
    return source

def source(body,args=(),extra=''):
    return CLEANUP+extra+'''fn main()->u32:io,alloc {
match cli.path_arg(1) {None=>{return 2} Some(executable)=>{
var command=process.command(true)
'''+arguments(args)+body+'\n}}}\n'

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class Process(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-process-');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.child=cls.root/('native child.exe' if sys.platform=='win32' else 'native child')
        result=subprocess.run(['clang',str(ROOT/'tests/native/process_child.c'),'-o',str(cls.child)],capture_output=True,timeout=120)
        if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))

    def run_program(self,program,args=(),expected=0,environment=None):
        for opt in ('0','2'):
            with tempfile.TemporaryDirectory(dir=self.root) as folder:
                root=Path(folder);entry=root/'probe.liza';entry.write_text(program)
                exe=build(entry,root,opt)
                run=subprocess.run([str(exe),str(self.child),*map(str,args)],capture_output=True,timeout=12,env=environment)
                self.assertEqual(run.returncode,expected,(opt,run.stdout,run.stderr))

    def test_zero_and_nonzero_exit_cached_receipt(self):
        for code in (0,37,259 if sys.platform=='win32' else 255):
            body='''match process.spawn(executable,command) {Err(e)=>{return 3} Ok(child)=>{
 first=process.wait(child);second=process.try_wait(child);closed=cleanup(move child)
 match first {Err(e)=>{return 4} Ok(status)=>{if status.code!='''+str(code)+''' {return 5}}}
 match second {Err(e)=>{return 6} Ok(found)=>{match found {None=>{return 7} Some(status)=>{if status.code!='''+str(code)+''' {return 8}}}}}
 return 0}}
'''
            self.run_program(source(body,['exit',str(code)]))

    def test_exact_arguments_env_override_no_shell(self):
        args=['arguments','','a b','"quote"','trailing\\','\\"',';$(touch forbidden)','Привет 🚀']
        key=b'LIZA_CHILD_TEST_TOKEN';value=b'local-test-only'
        body=f'''key:[u8;{len(key)}]={array(key)};value:[u8;{len(value)}]={array(value)}
match process.environment(command,view key[0..{len(key)}],view value[0..{len(value)}]) {{Err(e)=>{{return 3}} Ok(next)=>{{command=next}}}}
match process.spawn(executable,command) {{Err(e)=>{{return 4}} Ok(child)=>{{
 result=process.wait(child);closed=cleanup(move child)
 match result {{Err(e)=>{{return 5}} Ok(status)=>{{return status.code}}}}
}}}}
'''
        env=os.environ.copy();env['LIZA_CHILD_TEST_TOKEN']='parent-value'
        self.run_program(source(body,args),environment=env)
        self.assertFalse((Path.cwd()/'forbidden').exists())

    def test_close_running_returns_owner_then_kill_and_reap(self):
        body='''match process.spawn(executable,command) {Err(e)=>{return 3} Ok(child)=>{
 match process.close(move child) {Ok(done)=>{return 4} Err(failure)=>{
 (retained,error)=move failure
 match error {ProcessError.Running=>{} ProcessError.NotFound=>{} ProcessError.PermissionDenied=>{} ProcessError.Invalid=>{} ProcessError.TooLarge=>{} ProcessError.OutOfMemory=>{} ProcessError.Limit=>{} ProcessError.WrongThread=>{} ProcessError.Interrupted=>{} ProcessError.Unsupported=>{} ProcessError.Other=>{}}
 killed=process.kill(retained);result=process.wait(retained);closed=cleanup(move retained)
 match result {Err(e)=>{return 5} Ok(status)=>{if status.code==0 {return 6}}};return 0
 }}
}}
'''
        self.run_program(source(body,['hold']))

    def test_stop_marker_with_nonblocking_reactor_ticks(self):
        for opt in ('0','2'):
            with tempfile.TemporaryDirectory(dir=self.root) as folder:
                root=Path(folder);marker=root/'stop маркер'
                body='''match cli.path_arg(2) {None=>{return 2} Some(marker)=>{
 match net.reactor_create(0,1) {Err(e)=>{return 3} Ok(r)=>{
 stopped=net.reactor_stop_accepting(r)
 match process.spawn(executable,command) {Err(e)=>{c=net.reactor_close(move r);return 4} Ok(child)=>{
 var ticks:u32=0;var failure:u32=0
 while true {
 match process.try_wait(child) {Err(e)=>{failure=5;break} Ok(found)=>{match found {Some(status)=>{if ticks<3||status.code!=0 {failure=6};break} None=>{}}}}
 ticks=ticks+1
 if ticks==3 {match file.create_path(marker) {Err(e)=>{failure=7;break} Ok(f)=>{closed=file.close(move f)}}}
 waited=net.reactor_poll(r,10)
 if ticks>300 {failure=8;break}
 }
 c=cleanup(move child);closed=net.reactor_close(move r);removed=file.remove(marker);return failure
 }}
 }}
 }}
'''
                entry=root/'probe.liza';entry.write_text(source(body,['marker',str(marker)]));exe=build(entry,root,opt)
                run=subprocess.run([str(exe),str(self.child),str(marker)],capture_output=True,timeout=12)
                self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr))

    def test_owned_files_with_utf8_names_and_invalid_input(self):
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            directory=(Path(folder)/'данные 🚀').as_posix().encode()
            filename=(Path(folder)/'данные 🚀'/'запись.mp4').as_posix().encode()
            program='fn main()->u32:io {\n'
            for name,data in (('directory',directory),('filename',filename)):
                program+=f'{name}:[u8;{len(data)}]={array(data)}\n'
            program+=f'folder=view directory[0..{len(directory)}];path=view filename[0..{len(filename)}]\n'
            program+='''match file.mkdir_utf8(folder) {Err(e)=>{return 1} Ok(n)=>{}}
match file.create_utf8(path) {Err(e)=>{return 2} Ok(output)=>{
 data:[u8;3]=[1,2,3];written=file.write_chunk(output,view data[0..3]);closed=file.close(move output)
}}
match file.create_utf8(path) {Ok(unexpected)=>{closed=file.close(move unexpected);return 3} Err(e)=>{}}
match file.stat_utf8(path) {Err(e)=>{return 4} Ok(info)=>{if info.size!=3 {return 5}}}
match file.open_utf8(path) {Err(e)=>{return 6} Ok(input)=>{
 var failed=false;match file.read_chunk(input) {Err(e)=>{failed=true} Ok(chunk)=>{if chunk.len!=3||chunk.data[2]!=3 {failed=true}}}
 closed=file.close(move input);if failed {return 7}
}}
match file.remove_utf8(path) {Err(e)=>{return 8} Ok(n)=>{}}
zero:[u8;1]=[0];bad:[u8;1]=[255]
match file.stat_utf8(view zero[0..1]) {Ok(info)=>{return 9} Err(e)=>{}}
match file.stat_utf8(view bad[0..1]) {Ok(info)=>{return 10} Err(e)=>{}}
match file.stat_utf8(view bad[0..0]) {Ok(info)=>{return 11} Err(e)=>{}}
return 0
}'''
            self.run_program(program)

    def test_filesystem_metadata_and_nonrecursive_operations(self):
        program='''fn main()->u32:io {match cli.path_arg(1) {None=>{return 1} Some(path)=>{
 match file.stat(path) {Err(e)=>{return 2} Ok(info)=>{match info.kind {FileKind.Missing=>{} FileKind.Regular=>{return 3} FileKind.Directory=>{return 3} FileKind.Symlink=>{return 3} FileKind.Other=>{return 3}}}}
 match file.mkdir(path) {Err(e)=>{return 4} Ok(n)=>{}}
 again=file.mkdir(path)
 match file.stat(path) {Err(e)=>{return 5} Ok(info)=>{match info.kind {FileKind.Directory=>{} FileKind.Missing=>{return 6} FileKind.Regular=>{return 6} FileKind.Symlink=>{return 6} FileKind.Other=>{return 6}}}}
 match file.remove(path) {Ok(n)=>{return 7} Err(e)=>{}}
 match cli.path_arg(2) {None=>{return 8} Some(marker)=>{
 match file.create_path(marker) {Err(e)=>{return 9} Ok(f)=>{data:[u8;3]=[1,2,3];written=file.write_chunk(f,view data[0..3]);closed=file.close(move f)}}
 match file.stat(marker) {Err(e)=>{return 10} Ok(info)=>{if info.size!=3 {return 11}}}
 match file.remove(marker) {Err(e)=>{return 12} Ok(n)=>{}}
 match file.stat(marker) {Err(e)=>{return 13} Ok(info)=>{if info.size!=0 {return 14}}}
 return 0
 }}
}}}'''
        for opt in ('0','2'):
            with tempfile.TemporaryDirectory(dir=self.root) as folder:
                root=Path(folder);entry=root/'probe.liza';entry.write_text(program);exe=build(entry,root,opt)
                run=subprocess.run([str(exe),str(root/'directory'),str(root/'directory'/'marker')],capture_output=True,timeout=5)
                self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr))

    def test_static_linear_obligations(self):
        for body in (
            'return 0',
            'a=process.close(move child);b=process.wait(child);return 0',
            'other=copy child;c=cleanup(move child);return 0',
            'match process.close(move child) {Ok(done)=>{return 0} Err(failure)=>{return 0}}',
        ):
            program=source('match process.spawn(executable,command) {Err(e)=>{return 3} Ok(child)=>{'+body+'}}')
            with self.subTest(body=body),self.assertRaises(CompileError):lower(Parser(program).parse())

    def test_command_limits_and_invalid_bytes_before_spawn(self):
        invalid=[b'\x00',b'\xff',b'a'*1025]
        body=''
        for i,data in enumerate(invalid):
            body+='bad%d:[u8;%d]=%s;match process.argument(command,view bad%d[0..%d]) {Ok(unexpected)=>{return 3} Err(e)=>{}}\n' % (i,len(data),array(data),i,len(data))
        body+='''var i:u32=0;empty:[u8;0]=[]
while i<32 {match process.argument(command,view empty[0..0]) {Err(e)=>{return 4} Ok(next)=>{command=next}};i=i+1}
match process.argument(command,view empty[0..0]) {Ok(next)=>{return 5} Err(e)=>{}}
return 0'''
        self.run_program(source(body))

    def test_native_admission_signal_wait_failures_and_reaping(self):
        for opt in ('0','2'):
            exe=self.root/('ownership'+opt+('.exe' if sys.platform=='win32' else ''))
            command=['clang','-O'+opt,'-I'+str(ROOT/'liza/runtime'),str(ROOT/'tests/native/process_ownership.c'),'-o',str(exe)]
            if sys.platform!='win32':command+=['-pthread','-D_GNU_SOURCE']
            built=subprocess.run(command,capture_output=True,timeout=120)
            self.assertEqual(built.returncode,0,built.stderr)
            run=subprocess.run([str(exe),str(self.child)],capture_output=True,timeout=15)
            self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr))
            if sys.platform=="win32" and run.stderr:
                print(run.stderr.decode(errors="replace"),end="")
