"""Runtime partial-write probes and inspection of the borrowed byte path."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm

SOURCE='''fn send(f:File,data:View<u8>)->u32:io {
r=file.write_chunk(f,data);s=file.flush(f);closed=file.close(move f)
match r {Ok(n)=>{return n} Err(e)=>{return e.written}}
}
fn main()->u32{return 0}'''

HARNESS=r'''
#include <stdint.h>
#include <stddef.h>
static uint8_t input[2097155];
static uint32_t scenario,calls,seen,flushes,flush_fail;
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static BOOL WINAPI mock_write(HANDLE h,LPCVOID p,DWORD n,LPDWORD out,LPOVERLAPPED overlap) {
    if(p!=input+seen || n>1048576)ExitProcess(80);
    calls++;*out=0;
    if(scenario==2)return TRUE;
    if(scenario==3){SetLastError(ERROR_ACCESS_DENIED);return FALSE;}
    if(scenario==4){SetLastError(ERROR_FILE_TOO_LARGE);return FALSE;}
    if(scenario==5){SetLastError(ERROR_INVALID_HANDLE);return FALSE;}
    if((scenario==1 || scenario==6) && calls==2) {
        if(scenario==6){*out=1;seen++;}
        SetLastError(ERROR_DISK_FULL);return FALSE;
    }
    *out=(scenario==0 || scenario==1 || scenario==6) && calls==1?2:n;
    seen+=*out;return TRUE;
}
static BOOL WINAPI mock_flush(HANDLE h) {
    flushes++;if(flush_fail){SetLastError(ERROR_DISK_FULL);return FALSE;}return TRUE;
}
#define WriteFile mock_write
#define FlushFileBuffers mock_flush
#else
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
static ssize_t mock_write(int fd,const void *p,size_t n) {
    if(p!=input+seen || n>1048576)_Exit(80);
    calls++;
    if(scenario==2)return 0;
    if(scenario==3 && calls==1){errno=EINTR;return -1;}
    if(scenario==4){errno=EFBIG;return -1;}
    if(scenario==5){errno=EBADF;return -1;}
    if((scenario==1 || scenario==6) && calls==2){errno=scenario==1?ENOSPC:EAGAIN;return -1;}
    size_t wrote=(scenario==0 || scenario==1 || scenario==6) && calls==1?2:n;
    seen+=(uint32_t)wrote;return (ssize_t)wrote;
}
static int mock_flush(int fd) {
    flushes++;
    if(flush_fail){errno=ENOSPC;return -1;}
    if(flushes==1){errno=EINTR;return -1;}return 0;
}
#define write mock_write
#define fsync mock_flush
#endif
#include "RUNTIME"
int main(void) {
    for(scenario=0;scenario<7;scenario++) {
        calls=seen=0;
        uint64_t result=liza_rt_file_write(17,input,9),expected=0;
        if(scenario==0)expected=9;
        if(scenario==1)expected=((uint64_t)3<<32)|2;
        if(scenario==2)expected=(uint64_t)5<<32;
#ifdef _WIN32
        if(scenario==3)expected=(uint64_t)2<<32;
        if(scenario==6)expected=((uint64_t)3<<32)|3;
#else
        if(scenario==3)expected=9;
        if(scenario==6)expected=((uint64_t)4<<32)|2;
#endif
        if(scenario==4)expected=(uint64_t)6<<32;
        if(scenario==5)expected=(uint64_t)1<<32;
        if(result!=expected)return 1+scenario;
        if(liza_rt_file_write(17,input,0)!=0)return 10;
        if(scenario==2 && calls!=1)return 11;
    }
    scenario=7;seen=calls=0;
    if(liza_rt_file_write(17,input,sizeof input)!=sizeof input || calls!=3)return 12;
    flushes=flush_fail=0;if(liza_rt_file_flush(17)!=0)return 13;
#ifdef _WIN32
    if(flushes!=1)return 14;
#else
    if(flushes!=2)return 14;
#endif
    flush_fail=1;if(liza_rt_file_flush(17)!=3)return 15;
    return 0;
}
'''


def inspect(output,clang='clang'):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[1]
    runtime=repo/('liza/runtime/file_windows.c' if sys.platform=='win32' else 'liza/runtime/file_posix.c')
    ir=root/'write.ll';ir.write_text(llvm(lower(Parser(SOURCE).parse())))
    harness=root/'probe.c';harness.write_text(HARNESS.replace('RUNTIME',runtime.as_posix()))
    for opt in ('-O0','-O2'):
        exe=root/('probe'+opt+'.exe')
        subprocess.run([clang,opt,str(harness),*(['-pthread'] if sys.platform!='win32' else []),'-o',str(exe)],check=True,capture_output=True)
        result=subprocess.run([str(exe)],capture_output=True,timeout=10)
        assert result.returncode==0,(result.returncode,result.stderr)
        for name,source in [('write',ir),('runtime',runtime)]:
            for flags,suffix in [(['-S','-emit-llvm'],'ll'),(['-S'],'s')]:
                target=root/(name+'.'+opt[1:]+'.'+suffix)
                subprocess.run([clang,'-Wno-override-module',opt,*flags,str(source),'-o',str(target)],check=True,capture_output=True)
                text=target.read_text()
                assert not re.search(r'\b_?(malloc|calloc|realloc|free)\b',text),'heap allocation'
                if name=='write':
                    assert not re.search(r'\b_?(memcpy|memmove)\b',text),'view content copy'
                if name=='runtime' and suffix=='ll':
                    body=re.search(r'^define[^\n]*@liza_rt_file_write\(.*?^}',text,re.M|re.S)
                    assert body,'write runtime missing'
                    assert not re.search(r'\b(memcpy|memmove|memset)\b',body.group()),'write buffer copy'
    report='O0/O2: short/failed/zero writes and flush tested; original byte pointer advances without copying; no heap calls in selected writer.\n'
    (root/'report.txt').write_text(report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/file-write-cost');p.add_argument('--clang',default='clang');a=p.parse_args()
    print(inspect(a.output,a.clang),end='')
