"""Opaque File ownership, normal-exit obligations, and streaming native I/O."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import test_io
from liza.frontend import CompileError
from liza.ir import dump


def compile_source(source):
    return test_io.compile_source(source)


def with_file(body):
    return 'fn main()->u32:io{match file.open("input.bin"){Err(e)=>{return 1} Ok(f)=>{'+body+'}}}'


class ResourceTypes(unittest.TestCase):
    def test_move_only_and_normal_exit_obligations(self):
        bad = [
            with_file('return 0'),
            with_file('g=f;c=file.close(move g);return 0'),
            with_file('g=copy f;c=file.close(move f);return 0'),
            with_file('a=[move f];return 0'),
            with_file('c=file.close(f);return 0'),
            with_file('c=file.close(move f);d=file.close(move f);return 0'),
            with_file('c=file.close(move f);r=file.read_chunk(f);return 0'),
            with_file('r=file.read_chunk(move f);return 0'),
            'fn main()->u32:io{r=file.open("x");return 0}',
            'fn main()->u32:io{match file.open("x"){Ok(_)=>{return 0}Err(e)=>{return 1}}}',
            'fn main()->u32:io{r=file.open("x");match r {Ok(f)=>{c=file.close(move f);return 0}Err(e)=>{return 1}}}',
            'fn identity(f:File)->File{return f} fn main()->u32{return 0}',
            'fn bad(f:File)->u32{return 0} fn main()->u32{return 0}',
            'struct S {file:File} fn main()->u32{return 0}',
            'fn bad(f:[File;0])->u32{return 0} fn main()->u32{return 0}',
            'fn bad(f:View<File>)->u32{return 0} fn main()->u32{return 0}',
            with_file('n=u64(f);c=file.close(move f);return 0'),
            'fn main()->u32{f:File=0;return 0}',
            'fn main()->u32:io{var r=file.open("x");r=file.open("y");return 0}',
        ]
        for source in bad:
            with self.subTest(source=source), self.assertRaises(CompileError):
                compile_source(source)

    def test_cfg_and_loop_obligations(self):
        bad = [
            with_file('if true {c=file.close(move f)} return 0'),
            with_file('while true {c=file.close(move f)}'),
            'fn main()->u32:io{while true {r=file.open("x");continue}}',
            'fn main()->u32:io{while true {r=file.open("x");break} return 0}',
            'fn main()->u32:io{if true {r=file.open("x")} return 0}',
            'fn consume(f:File)->bool:io{c=file.close(move f);return true} '+
            with_file('x=false && consume(move f);return 0'),
            with_file('while true {match file.open("y"){Err(e)=>{return 2}Ok(g)=>{c=file.close(move g);break}}} c=file.close(move f);return 0'),
        ]
        for source in bad:
            with self.subTest(source=source), self.assertRaises(CompileError):
                compile_source(source)
        good = [
            with_file('if true {c=file.close(move f);return 0} c=file.close(move f);return 1'),
            with_file('if true {c=file.close(move f)} else {c=file.close(move f)} return 0'),
            with_file('while true {c=file.close(move f);break} return 0'),
            'fn main()->u32:io{var i:u32=0;while i<3 {match file.open("x"){Err(e)=>{return 1}Ok(f)=>{c=file.close(move f);i=i+1;continue}}} return 0}',
            'fn identity(f:File)->File{return move f} '+with_file('g=identity(move f);c=file.close(move g);return 0'),
            'fn main()->u32:io{var r=file.open("x");match move r {Ok(f)=>{c=file.close(move f)}Err(e)=>{}} r=file.open("y");match move r {Ok(f)=>{c=file.close(move f)}Err(e)=>{}} return 0}',
        ]
        for source in good:
            with self.subTest(source=source): compile_source(source)

    def test_variants_and_borrow_metadata(self):
        source='enum Owner { Empty; Open(File) } fn pass(f:File)->Owner{return Owner.Open(move f)} '+with_file('o=pass(move f);match move o {Owner.Empty=>{return 1}Owner.Open(g)=>{r=file.read_chunk(g);c=file.close(move g);return 0}}')
        m=compile_source(source);data=json.loads(dump(m))
        self.assertEqual(data['version'],15)
        for t in ('File','Owner','Result<File,FileError>'):
            self.assertEqual(data['type_properties'][t],{'copyable':False,'implicit_copy':False})
        calls=[o for f in m for b in f.blocks for o in b.operations if o.op=='call']
        self.assertTrue(any(o.callee=='file.read_chunk' and o.parameter_modes==['borrow'] for o in calls))
        fn=next(f for f in m if f.name=='file.read_chunk')
        self.assertEqual(fn.params[0]['mode'],'borrow')
        compile_source('fn main()->u32:io{r:Option<File> = None;match move r {None=>{return 0}Some(f)=>{c=file.close(move f);return 1}}}')

    def test_call_order_and_effects(self):
        prefix='fn sink(f:File,r:Result<FileChunk,FileFailure>)->u32:io{c=file.close(move f);return 0} '
        with self.assertRaises(CompileError): compile_source(prefix+with_file('return sink(move f,file.read_chunk(f))'))
        for source in ['fn main()->u32{r=file.open("x");return 0}',
                       'fn bad(f:File)->File{r=file.read_chunk(f);return move f} fn main()->u32{return 0}',
                       'fn bad(f:File)->u32{r=file.close(move f);return 0} fn main()->u32{return 0}']:
            with self.subTest(source=source),self.assertRaises(CompileError): compile_source(source)


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ResourceNative(unittest.TestCase):
    build=test_io.ConsoleNative.build

    def test_streaming_sizes_and_exact_bytes(self):
        source=Path('examples/file_stream.liza').read_text(encoding='utf-8')
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                root=Path(d)/'examples/data';root.mkdir(parents=True)
                path=root/'rtp.bin'
                r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                self.assertEqual(r.returncode,1,r.stderr)
                for n in (0,1,2047,2048,2049,6144,7001):
                    with self.subTest(opt=opt,length=n):
                        data=bytes((i*31)%256 for i in range(n));path.write_bytes(data)
                        r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                        self.assertEqual(r.returncode,0,r.stderr)
                        self.assertEqual(r.stdout,data)

    def test_transfer_return_variants_and_repeated_open(self):
        source='''fn pass(f:File)->File{return move f}
        fn get()->Result<File,FileError>:io{return file.open("Лиза.bin")}
        fn main()->u32:io{
            var i:u32=0
            while i<100 {
                match get() {
                    Err(e)=>{return 1}
                    Ok(original)=>{
                        f=pass(move original)
                        match file.read_chunk(f){Err(e)=>{c=file.close(move f);return 2}Ok(chunk)=>{
                            if chunk.len!=1 || chunk.eof || chunk.data[0]!=42 || chunk.data[1]!=0 {c=file.close(move f);return 3}
                        }}
                        match file.read_chunk(f){Err(e)=>{c=file.close(move f);return 4}Ok(chunk)=>{
                            if !chunk.eof || chunk.len!=0 {c=file.close(move f);return 5}
                        }}
                        match file.close(move f){Err(e)=>{return 6}Ok(n)=>{}}
                    }
                }
                i=i+1
            }
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                (Path(d)/'Лиза.bin').write_bytes(b'*');exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=15)
                self.assertEqual(r.returncode,0,r.stderr)

    def test_io_order_and_close_on_read_failure(self):
        # Scalar ABI test double exercises the generated program, not libc.
        # No C aggregate ABI assumptions and no OS-specific fault behavior.
        from liza.backend import llvm
        source='''fn main()->u32:io {
            match file.open("x") {
                Err(e)=>{return 1}
                Ok(f)=>{
                    var status:u32=0
                    match file.read_chunk(f){Err(e)=>{status=2}Ok(chunk)=>{}}
                    match file.close(move f){Err(e)=>{if status==0 {return 3}}Ok(n)=>{}}
                    return status
                }
            }
        }'''
        harness=r'''
        #include <stdint.h>
        #include <string.h>
        static int scenario, opened, reads, closes, order_error;
        uint32_t liza_rt_file_open(const uint8_t *p,uint32_t n,uint64_t *out){
            *out=0;
            if(scenario==1)return 1;
            opened=1;*out=42;return 0;
        }
        uint64_t liza_rt_read_chunk(uint64_t h,uint8_t *out){
            if(!opened||h!=42||closes)order_error=1;
            reads++;memset(out,0,2048);
            if(scenario==2||scenario==4)return (uint64_t)7<<32;
            out[0]=42;return 1;
        }
        uint32_t liza_rt_file_close(uint64_t h){
            if(!opened||h!=42||reads!=1||closes)order_error=1;
            closes++;opened=0;return scenario==3||scenario==4?7:0;
        }
        extern uint32_t liza_main(void);
        int main(void){
            for(scenario=0;scenario<5;scenario++){
                opened=reads=closes=order_error=0;
                uint32_t expected=scenario==0?0:scenario==1?1:scenario==3?3:2;
                if(liza_main()!=expected||order_error||opened)return 10+scenario;
                if(closes!=(scenario==1?0:1))return 20+scenario;
            }
            return 0;
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);ir=root/'module.ll';c=root/'harness.c';exe=root/('test.exe' if sys.platform=='win32' else 'test')
                ir.write_text(llvm(compile_source(source)).replace('define i32 @main()', 'define i32 @example_main()'))
                c.write_text(harness)
                r=subprocess.run(['clang','-Wno-override-module',opt,str(ir),str(c),'-o',str(exe)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)

    @unittest.skipUnless(sys.platform in ('darwin','linux'),'POSIX resource syscall faults')
    def test_chunk_short_read_eintr_and_no_close_retry(self):
        runtime=(Path(__file__).resolve().parents[1]/'liza/runtime/file_posix.c').as_posix()
        harness=r'''
        #include <stdint.h>
        #include <string.h>
        #include <errno.h>
        #include <fcntl.h>
        #include <unistd.h>
        static int opens, reads, closes;
        static int mock_open(const char *p,int flags,...){
            if(++opens==1){errno=EINTR;return -1;}return 17;
        }
        static ssize_t mock_read(int fd,void *p,size_t n){
            if(++reads==1){errno=EINTR;return -1;}
            if(reads==2){*(uint8_t*)p=42;return 1;}
            if(reads==3)return 0;
            errno=EAGAIN;return -1;
        }
        static int mock_close(int fd){closes++;errno=EINTR;return -1;}
        #define open mock_open
        #define read mock_read
        #define close mock_close
        #include "RUNTIME"
        int main(void){
            uint64_t handle;uint8_t bytes[2048];
            if(liza_rt_file_open((const uint8_t*)"x",1,&handle)||handle!=17||opens!=2)return 1;
            if(liza_rt_read_chunk(handle,bytes)!=1||reads!=2||bytes[0]!=42||bytes[1])return 2;
            if(liza_rt_read_chunk(handle,bytes)!=0||reads!=3||bytes[0])return 3;
            if(liza_rt_read_chunk(handle,bytes)!=((uint64_t)6<<32)||reads!=4)return 4;
            if(liza_rt_file_close(handle)!=7||closes!=1)return 5;
            return 0;
        }'''.replace('RUNTIME',runtime)
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                c=Path(d)/'test.c';exe=Path(d)/'test';c.write_text(harness)
                r=subprocess.run(['clang',opt,str(c),'-o',str(exe)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(subprocess.run([str(exe)],timeout=10).returncode,0)

    def test_chunks_own_bytes_after_another_read_and_close(self):
        source=with_file('''
            match file.read_chunk(f) {
                Err(e)=>{c=file.close(move f);return 2}
                Ok(first)=>{
                    a=first.data;v=view a[0..first.len]
                    match file.read_chunk(f) {
                        Err(e)=>{c=file.close(move f);return 3}
                        Ok(second)=>{
                            c=file.close(move f)
                            b=second.data;w=view b[0..second.len]
                            x=console.write_bytes(v);y=console.write_bytes(w)
                            return 0
                        }
                    }
                }
            }
        ''')
        data=bytes(i//2048+1 for i in range(4097))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                (Path(d)/'input.bin').write_bytes(data);exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                self.assertEqual((r.returncode,r.stdout),(0,data[:4096]),r.stderr)
