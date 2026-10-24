"""Windows-specific native acceptance; POSIX signal tests remain separate."""
from pathlib import Path
import ctypes
import importlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import test_io


@unittest.skipUnless(sys.platform=='win32' and shutil.which('clang'),'Windows Clang required')
class WindowsNative(unittest.TestCase):
    build=test_io.ConsoleNative.build
    test_utf8_nul_bytes_numbers_and_text_lifetime=test_io.ConsoleNative.test_utf8_nul_bytes_numbers_and_text_lifetime
    test_effectful_arguments_run_left_to_right=test_io.ConsoleNative.test_effectful_arguments_run_left_to_right
    test_cli_hello_and_runtime_cost=test_io.ConsoleNative.test_cli_hello_and_runtime_cost

    @classmethod
    def setUpClass(cls):
        cls.old_mode=ctypes.windll.kernel32.SetErrorMode(0x8003)

    @classmethod
    def tearDownClass(cls):
        ctypes.windll.kernel32.SetErrorMode(cls.old_mode)

    def test_examples_and_exe_names(self):
        expected={'answer':42,'conditions':42}
        for opt in ('0','2'):
            for source in sorted(Path('examples').glob('*.liza')):
                with self.subTest(source=source,opt=opt),tempfile.TemporaryDirectory() as d:
                    output=Path(d)/'tool'
                    r=subprocess.run([sys.executable,'-m','liza','build',str(source),'-O',opt,'-o',str(output)],capture_output=True)
                    self.assertEqual(r.returncode,0,r.stderr)
                    exe=Path(str(output)+'.exe');self.assertTrue(exe.exists())
                    r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                    self.assertEqual(r.returncode,expected.get(source.stem,0),source)

    def test_observable_traps(self):
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                source=test_io.program('x=console.write("before"); n:u8=255; bad=n+1; y=console.write("after"); return 0')
                exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertIn(r.returncode,(0x80000003,0xc000001d))
                self.assertEqual(r.stdout,b'before')

    def test_return_code_full_width(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'exit.liza';source.write_text('fn main()->u32{return 4294967295}',encoding='utf-8')
            r=subprocess.run([sys.executable,'-m','liza','run',str(source)],capture_output=True,timeout=20)
            self.assertEqual(r.returncode,0xffffffff,r.stderr)

    def test_windows_handles_and_console_unicode(self):
        # Real Win32 handles: redirected bytes, closed pipe, detached stdout,
        # and a console screen buffer whose UTF-16 content is inspected.
        harness=r'''
        #define WIN32_LEAN_AND_MEAN
        #include <windows.h>
        #include <stdint.h>
        extern uint64_t liza_rt_write(const uint8_t*,uint32_t);
        extern uint64_t liza_rt_write_text(const uint8_t*,uint32_t);
        extern uint64_t liza_rt_err_text(const uint8_t*,uint32_t);
        int main(void){
            HANDLE read,write;DWORD count;
            if(!CreatePipe(&read,&write,NULL,0))return 1;
            SetStdHandle(STD_OUTPUT_HANDLE,write);
            const uint8_t raw[]={0,255,10};uint8_t got[3];
            if(liza_rt_write(raw,3)!=3)return 2;
            if(!ReadFile(read,got,3,&count,NULL)||count!=3||got[0]!=0||got[1]!=255||got[2]!=10)return 3;
            CloseHandle(read);
            if(liza_rt_write(raw,3)!=((uint64_t)3<<32))return 4;
            CloseHandle(write);SetStdHandle(STD_OUTPUT_HANDLE,NULL);
            if(liza_rt_write(raw,3)!=((uint64_t)1<<32))return 5;
            if(liza_rt_write(raw,0)!=0)return 6;
            FreeConsole();if(!AllocConsole())return 7;
            HANDLE screen=CreateConsoleScreenBuffer(GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,CONSOLE_TEXTMODE_BUFFER,NULL);
            if(screen==INVALID_HANDLE_VALUE)return 8;
            SetStdHandle(STD_OUTPUT_HANDLE,screen);
            UINT old=GetConsoleOutputCP();SetConsoleOutputCP(437);
            const uint8_t text[]={0xd0,0x9b,0xd0,0xb8,0xd0,0xb7,0xd0,0xb0};
            if(liza_rt_write_text(text,8)!=8)return 9;
            WCHAR chars[4];COORD zero={0,0};
            if(!ReadConsoleOutputCharacterW(screen,chars,4,zero,&count)||count!=4)return 10;
            if(chars[0]!=0x41b||chars[1]!=0x438||chars[2]!=0x437||chars[3]!=0x430)return 11;
            if(GetConsoleOutputCP()!=437)return 12;
            SetStdHandle(STD_ERROR_HANDLE,screen);
            if(liza_rt_err_text(text,8)!=8)return 13;
            COORD four={4,0};
            if(!ReadConsoleOutputCharacterW(screen,chars,4,four,&count)||count!=4)return 14;
            if(chars[0]!=0x41b||chars[1]!=0x438||chars[2]!=0x437||chars[3]!=0x430)return 15;
            SetConsoleOutputCP(old);CloseHandle(screen);FreeConsole();return 0;
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                c=Path(d)/'test.c';exe=Path(d)/'test.exe';c.write_text(harness,encoding='utf-8')
                r=subprocess.run(['clang',opt,str(c),'liza/runtime/console_windows.c','-o',str(exe)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=15).returncode,0)


def load_tests(loader,tests,pattern):
    if sys.platform!='win32':return tests
    for module,name in [('test_compiler','FrontendTests'),('test_arrays','ArrayTypes'),
                        ('test_conversions','ConversionTypeTests'),('test_division','DivisionTypeTests'),
                        ('test_loops','LoopTypeTests'),('test_mutable','MutableTypeTests'),
                        ('test_numbers','NumericTypeTests'),('test_ownership','OwnershipTests'),
                        ('test_structures','StructureTests'),('test_variants','VariantTypes'),('test_io','Effects'),('test_file','FileTypes'),('test_file','FileNative'),('test_resources','ResourceTypes'),('test_resources','ResourceNative'),('test_updates','UpdateTypes'),('test_updates','UpdateNative'),('test_table','TableTypes'),('test_table','TableStorageNative'),('test_table','StorageProofs'),('test_table','StorageReuseNative'),('test_file_write','FileWriteTypes'),('test_file_write','CopyNative'),('test_cli','CliTypes'),('test_cli','CliNative'),('test_utf8_stream','StreamTypes'),('test_utf8_stream','StreamNative'),('test_utf8','Utf8Types'),('test_utf8','Utf8Native'),('test_vec_reserve','ReserveTypes'),('test_vec_reserve','ReserveNative'),('test_vectors','VectorTypes'),('test_vectors','VectorNative'),('test_regions','RegionTypes'),('test_regions','RegionNative'),('test_generics','GenericTests'),('test_modules','ModuleTests'),('test_modules','ModuleNativeTests')]:
        tests.addTests(loader.loadTestsFromTestCase(getattr(importlib.import_module(module),name)))
    return tests
