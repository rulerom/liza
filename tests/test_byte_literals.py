"""Static byte views: exact bytes, conservative escape rules and descriptor cost."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.backend import llvm
from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.modules import load_program
from liza.stdlib import link_flags


def compile_source(source):
    return lower(Parser(source).parse())


class ByteLiteralTypes(unittest.TestCase):
    def test_static_origin_and_no_runtime_dependencies(self):
        module = compile_source('fn main()->u32 {v=b"PLAY";return v.len}')
        ops = [op for fn in module for block in fn.blocks for op in block.operations]
        literal = next(op for op in ops if op.op == 'bytes.literal')
        self.assertEqual(literal.type, 'View<u8>')
        self.assertEqual(literal.storage_relation, 'static_readonly')
        self.assertEqual(literal.args, ['PLAY'])
        self.assertEqual(link_flags(module), [])
        self.assertFalse(module.externals)

    def test_invalid_escapes_and_non_ascii(self):
        for literal in [r'b"\x"', r'b"\x0"', r'b"\xGG"', r'b"\u0041"',
                        r'b"\q"', 'b"Лиза"', 'b"\t"', 'b"\r"', 'b"\n"']:
            with self.subTest(literal=literal), self.assertRaises(CompileError):
                compile_source('fn main()->u32 {v='+literal+';return v.len}')

    def test_readonly_types_and_escape_restrictions(self):
        for source in [
            'fn main()->u32 {var v=b"PLAY";v[0]=0;return 0}',
            'fn main()->u32 {a:[u8;4]=b"PLAY";return 0}',
            'fn main()->u32 {t:Text=b"PLAY";return 0}',
            'fn main()->u32 {a=[b"PLAY"];return 0}',
            'struct S {v:View<u8>} fn main()->u32 {return 0}',
            'fn bad()->View<u8> {return b"PLAY"} fn main()->u32 {return 0}',
            'fn main()->u32 {v=b"PLAY";gone=move v;return v.len}',
        ]:
            with self.subTest(source=source), self.assertRaises(CompileError):
                compile_source(source)

    def test_static_subview_survives_inner_descriptor(self):
        compile_source('fn read(v:View<u8>)->u32{return u32(v[0])}'
                       'fn main()->u32 {var out=b"";{v=b"PLAY";out=view v[1..3]}'
                       'if read(out)!=76 {return 1};return 0}')
        # Literal support must not relax the lifetime of ordinary array views.
        with self.assertRaisesRegex(CompileError, 'lifetime'):
            compile_source('fn main()->u32 {var out=b"";{a:[u8;1]=[1];out=view a[0..1]};return out.len}')
        with self.assertRaisesRegex(CompileError, 'readonly'):
            compile_source('fn main()->u32 {var a:[u8;1]=[1];var out=b"";'
                           'if true {out=view a[0..1]}else{out=b"X"};a[0]=2;return out.len}')


@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class ByteLiteralNative(unittest.TestCase):
    def test_exact_binary_output_o0_o2(self):
        expected = bytes(range(256))
        literal = 'b"' + ''.join('\\x%02x' % b for b in expected) + '"'
        source = ('fn emit(v:View<u8>)->u32:io {match console.write_bytes(v) {'
                  'Ok(n)=>{return u32(n)} Err(e)=>{return 0}}}'
                  'fn main()->u32:io {empty=b"";if emit(empty)!=0{return 1};'
                  'if emit('+literal+')!=256 {return 2};'
                  'var tail=b"";{v=b"PLAY";tail=view v[1..4]};'
                  'if emit(tail)!=3 {return 3};'
                  r'if emit(b"\0\n\r\t\\\"")!=6 {return 4};return 0}')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entry = root/'source.liza'
            entry.write_text(source)
            module = lower(load_program(entry))
            ir = root/'source.ll'
            ir.write_text(llvm(module))
            for opt in ('-O0', '-O2'):
                exe = root/('probe.exe' if sys.platform == 'win32' else 'probe')
                built = subprocess.run(['clang', '-Wno-override-module', opt, str(ir),
                                        *link_flags(module), '-o', str(exe)], capture_output=True)
                self.assertEqual(built.returncode, 0, built.stderr)
                run = subprocess.run([str(exe)], capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected+b'LAY\0\n\r\t\\"')

    def test_static_literal_cost_o0_o2(self):
        source = ('fn consume(v:View<u8>,i:u32)->u32 {return u32(v[i])}'
                  'fn probe(i:u32)->u32 {return consume(b"PLAY",i)}'
                  'fn main()->u32{return probe(0)-80}')
        text = llvm(compile_source(source))
        self.assertRegex(text, r'private constant \[4 x i8\] c"\\50\\4C\\41\\59"')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ir = root/'source.ll'
            ir.write_text(text)
            for opt in ('-O0', '-O2'):
                out = root/'output.ll'
                built = subprocess.run(['clang', '-Wno-override-module', opt, '-S', '-emit-llvm',
                                        str(ir), '-o', str(out)], capture_output=True)
                self.assertEqual(built.returncode, 0, built.stderr)
                body = re.search(r'^define .*@liza_probe\([^\n]*\)[^\n]*\{\n(.*?)^}',
                                 out.read_text(), re.M|re.S).group(1)
                self.assertNotRegex(body, r'\b(alloca|store|memcpy|memmove|malloc|liza_rt_)\b')
                assembly = root/'output.s'
                subprocess.run(['clang', '-Wno-override-module', opt, '-S', str(ir),
                                '-o', str(assembly)], capture_output=True, check=True)
                self.assertNotRegex(assembly.read_text(), r'\b(memcpy|memmove|malloc|calloc)\b')


if __name__ == '__main__':
    unittest.main()
