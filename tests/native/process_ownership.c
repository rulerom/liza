#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#ifndef _WIN32
#include <errno.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#include <pthread.h>
static int fail_signal,fail_wait,signal_calls;
static int real_signal(pid_t p,int s) {return kill(p,s);}
static pid_t real_wait(pid_t p,int *s,int flags) {return waitpid(p,s,flags);}
static int injected_signal(pid_t p,int s) {signal_calls++;if(fail_signal) {fail_signal=0;errno=EPERM;return -1;}return real_signal(p,s);}
static pid_t injected_wait(pid_t p,int *s,int flags) {if(fail_wait) {fail_wait=0;errno=EINTR;return -1;}return real_wait(p,s,flags);}
#define kill injected_signal
#define waitpid injected_wait
#include "process_posix.c"
#undef kill
#undef waitpid
#else
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static int fail_signal,fail_wait;
static BOOL injected_terminate(HANDLE p,UINT code) {
    if(fail_signal) {fail_signal=0;SetLastError(ERROR_ACCESS_DENIED);return FALSE;}
    return TerminateProcess(p,code);
}
static DWORD injected_wait(HANDLE p,DWORD delay) {
    if(fail_wait) {fail_wait=0;SetLastError(ERROR_INVALID_HANDLE);return WAIT_FAILED;}
    return WaitForSingleObject(p,delay);
}
#define TerminateProcess injected_terminate
#define WaitForSingleObject injected_wait
#include "process_windows.c"
#undef TerminateProcess
#undef WaitForSingleObject
#endif
static uint32_t foreign_poll,foreign_kill,foreign_close;
#ifdef _WIN32
static DWORD WINAPI foreign(LPVOID c) {
#else
static void *foreign(void *c) {
#endif
    uint32_t kind,code;foreign_poll=liza_rt_process_poll(c,0,&kind,&code);
    foreign_kill=liza_rt_process_op(c,2);foreign_close=liza_rt_process_close(c);return 0;
}
#define CHECK(test,n) do {if(!(test)) {result=n;goto cleanup;}} while(0)
int main(int argc,char **argv) {
    int result=0;void *children[8]={0};uint32_t error=0,kind=0,code=0;
#ifdef _WIN32
    wchar_t native_path[32768];MultiByteToWideChar(CP_UTF8,0,argv[1],-1,native_path,32768);
    const wchar_t *path=native_path;DWORD before,after;
    /* Independent raw WinAPI warm-up precedes all adapter measurements. The
       first failed CreateProcess can initialize persistent compatibility state. */
    DWORD raw_before,raw_after;GetProcessHandleCount(GetCurrentProcess(),&raw_before);
    STARTUPINFOW startup={0};startup.cb=sizeof(startup);PROCESS_INFORMATION info={0};
    wchar_t command_line[]=L"\"Z:\\liza-does-not-exist\\child.exe\"";
    if(CreateProcessW(L"Z:\\liza-does-not-exist\\child.exe",command_line,0,0,FALSE,0,0,0,&startup,&info)) {
        TerminateProcess(info.hProcess,137);WaitForSingleObject(info.hProcess,INFINITE);CloseHandle(info.hThread);CloseHandle(info.hProcess);
    }
    GetProcessHandleCount(GetCurrentProcess(),&raw_after);
    fprintf(stderr,"raw CreateProcess failure warm-up: %lu -> %lu\n",(unsigned long)raw_before,(unsigned long)raw_after);
    GetProcessHandleCount(GetCurrentProcess(),&before);
#else
    const char *path=argv[1];
#endif
    CHECK(argc==2,1);
    for(int i=0;i<8;i++) {children[i]=liza_rt_process_spawn(path,1,(const uint8_t*)"hold\0",5,0,0,&error);CHECK(children[i]&&error==0,2);}
    void *extra=liza_rt_process_spawn(path,1,(const uint8_t*)"hold\0",5,0,0,&error);
    CHECK(!extra&&error==6,3);
    CHECK(liza_rt_process_close(children[0])==7,4);
#ifdef _WIN32
    HANDLE thread=CreateThread(0,0,foreign,children[0],0,0);CHECK(thread,5);WaitForSingleObject(thread,INFINITE);CloseHandle(thread);
#else
    pthread_t thread;CHECK(pthread_create(&thread,0,foreign,children[0])==0,5);pthread_join(thread,0);
#endif
    CHECK(foreign_poll==8&&foreign_kill==8&&foreign_close==8,6);
#ifndef _WIN32
    fail_signal=1;CHECK(liza_rt_process_op(children[0],1)==2,7);
    CHECK(liza_rt_process_poll(children[0],0,&kind,&code)==0&&kind==0,8);
    fail_wait=1;CHECK(liza_rt_process_poll(children[0],1,&kind,&code)==9,9);
    CHECK(liza_rt_process_op(children[0],1)==0,10);
#else
    CHECK(liza_rt_process_op(children[0],1)==10,10);
    fail_signal=1;CHECK(liza_rt_process_op(children[0],2)==2,7);
    CHECK(liza_rt_process_poll(children[0],0,&kind,&code)==0&&kind==0,8);
    fail_wait=1;CHECK(liza_rt_process_poll(children[0],1,&kind,&code)==11,9);
#endif
    CHECK(liza_rt_process_op(children[0],2)==0,11);
    CHECK(liza_rt_process_poll(children[0],1,&kind,&code)==0&&kind!=0,12);
#ifndef _WIN32
    pid_t pid=((Child*)children[0])->pid;int status;errno=0;
    CHECK(real_wait(pid,&status,WNOHANG)==-1&&errno==ECHILD,13);
    int calls=signal_calls;CHECK(liza_rt_process_op(children[0],2)==0&&signal_calls==calls,14);
#endif
    CHECK(liza_rt_process_close(children[0])==0,15);children[0]=0;
#ifdef _WIN32
    DWORD steady_before,steady_after;
    GetProcessHandleCount(GetCurrentProcess(),&steady_before);
#endif
    /* Both startup failure and completed close release admission. */
#ifdef _WIN32
    const wchar_t *missing=L"Z:\\liza-does-not-exist\\child.exe";
#else
    const char *missing="/liza-does-not-exist/child";
#endif
    for(int repeat=0;repeat<12;repeat++) {
        #ifdef _WIN32
        DWORD missing_before,missing_after;GetProcessHandleCount(GetCurrentProcess(),&missing_before);
#endif
        void *bad=liza_rt_process_spawn(missing,1,0,0,0,0,&error);CHECK(!bad&&error==1,20);
#ifdef _WIN32
        GetProcessHandleCount(GetCurrentProcess(),&missing_after);
        if(missing_before!=missing_after)fprintf(stderr,"missing %d: %lu -> %lu\n",repeat,(unsigned long)missing_before,(unsigned long)missing_after);
#endif
    }
    for(int repeat=0;repeat<25;repeat++) {
#ifdef _WIN32
        DWORD cycle_before,cycle_spawned,cycle_closed;
        GetProcessHandleCount(GetCurrentProcess(),&cycle_before);
#endif
        children[0]=liza_rt_process_spawn(path,1,(const uint8_t*)"exit\0000\0",7,0,0,&error);CHECK(children[0],16);
#ifdef _WIN32
        GetProcessHandleCount(GetCurrentProcess(),&cycle_spawned);
#endif
        CHECK(liza_rt_process_poll(children[0],1,&kind,&code)==0&&kind==1&&code==0,18);
        CHECK(liza_rt_process_close(children[0])==0,19);children[0]=0;
#ifdef _WIN32
        GetProcessHandleCount(GetCurrentProcess(),&cycle_closed);
        if(cycle_before!=cycle_closed)fprintf(stderr,"cycle %d: before=%lu spawned=%lu closed=%lu\n",repeat,(unsigned long)cycle_before,(unsigned long)cycle_spawned,(unsigned long)cycle_closed);
#endif
    }
#ifdef _WIN32
    GetProcessHandleCount(GetCurrentProcess(),&steady_after);
    if(steady_before!=steady_after)fprintf(stderr,"steady handles: before=%lu after=%lu\n",(unsigned long)steady_before,(unsigned long)steady_after);
    CHECK(steady_before==steady_after,21);
#endif
cleanup:
    for(int i=0;i<8;i++)if(children[i]) {
        liza_rt_process_op(children[i],2);
        while(liza_rt_process_poll(children[i],1,&kind,&code)==9){}
        liza_rt_process_close(children[i]);
    }
#ifdef _WIN32
    GetProcessHandleCount(GetCurrentProcess(),&after);
    /* The first spawn can initialize process-wide Windows/CRT handles. Compare
       steady-state reuse above, and require all 7 remaining Child handle pairs
       to disappear during cleanup, rather than accepting a per-child leak. */
    if(!result&&after+14!=steady_after) {
        fprintf(stderr,"handles: initial=%lu steady=%lu final=%lu\n",(unsigned long)before,(unsigned long)steady_after,(unsigned long)after);result=17;
    }
#endif
#ifdef _WIN32
    if(result) {
        DWORD raw_before,raw_after;GetProcessHandleCount(GetCurrentProcess(),&raw_before);
        for(int i=0;i<12;i++) {
            STARTUPINFOW startup={0};startup.cb=sizeof(startup);PROCESS_INFORMATION info={0};
            wchar_t command_line[]=L"\"Z:\\liza-does-not-exist\\child.exe\"";
            if(CreateProcessW(L"Z:\\liza-does-not-exist\\child.exe",command_line,0,0,FALSE,0,0,0,&startup,&info)) {
                TerminateProcess(info.hProcess,137);WaitForSingleObject(info.hProcess,INFINITE);CloseHandle(info.hThread);CloseHandle(info.hProcess);
            }
        }
        GetProcessHandleCount(GetCurrentProcess(),&raw_after);
        fprintf(stderr,"raw CreateProcess missing-drive control: %lu -> %lu\n",(unsigned long)raw_before,(unsigned long)raw_after);
    }
#endif
    return result;
}
