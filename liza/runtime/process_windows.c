#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include "process_common.h"
typedef struct {HANDLE process,thread;DWORD owner;uint32_t kind,code;} Child;
static uint32_t error_code(DWORD e) {
    if(e==ERROR_FILE_NOT_FOUND||e==ERROR_PATH_NOT_FOUND)return 1;
    if(e==ERROR_ACCESS_DENIED||e==ERROR_PRIVILEGE_NOT_HELD)return 2;
    if(e==ERROR_BAD_EXE_FORMAT||e==ERROR_INVALID_PARAMETER||e==ERROR_INVALID_NAME)return 3;
    if(e==ERROR_FILENAME_EXCED_RANGE||e==ERROR_ENVVAR_NOT_FOUND)return 4;
    if(e==ERROR_NOT_ENOUGH_MEMORY||e==ERROR_OUTOFMEMORY)return 5;
    return 11;
}
static uint32_t quoted(wchar_t *out,uint32_t *at,const wchar_t *s) {
#define APPEND(ch) do {if(*at>=32766)return 4;out[(*at)++]=(ch);} while(0)
    APPEND(L'"');uint32_t slashes=0;
    for(;*s;s++) {
        if(*s==L'\\') {slashes++;continue;}
        uint32_t n=*s==L'"'?slashes*2+1:slashes;
        while(n--)APPEND(L'\\');slashes=0;APPEND(*s);
    }
    slashes*=2;while(slashes--)APPEND(L'\\');APPEND(L'"');out[*at]=0;return 0;
#undef APPEND
}
static int env_compare(const void *a,const void *b) {
    const wchar_t *x=*(wchar_t *const*)a,*y=*(wchar_t *const*)b;
    int xn=(int)(x[0]==L'='?1+wcscspn(x+1,L"="):wcscspn(x,L"="));
    int yn=(int)(y[0]==L'='?1+wcscspn(y+1,L"="):wcscspn(y,L"="));
    int order=CompareStringOrdinal(x,xn,y,yn,TRUE);
    return order==CSTR_LESS_THAN?-1:order==CSTR_GREATER_THAN?1:0;
}
void *liza_rt_process_spawn(const wchar_t *path,uint32_t inherit,const uint8_t *args,uint32_t an,const uint8_t *env,uint32_t en,uint32_t *error) {
    *error=0;
    if(!path||!((path[0]&&path[1]==L':'&&(path[2]==L'\\'||path[2]==L'/'))||(path[0]==L'\\'&&path[1]==L'\\'))) {*error=3;return 0;}
    if(!reserve_slot()) {*error=6;return 0;}
    Child *child=calloc(1,sizeof(*child));Launch *l=calloc(1,sizeof(*l));
    wchar_t *command=calloc(32768,sizeof(wchar_t)),*environment=calloc(32768,sizeof(wchar_t));
    if(!child||!l||!command||!environment) {*error=5;goto fail;}
    if(inherit) {
        wchar_t *block=GetEnvironmentStringsW();if(!block) {*error=error_code(GetLastError());goto fail;}
        for(const wchar_t *p=block;*p;p+=wcslen(p)+1) {
            char utf8[32768];int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,p,-1,utf8,sizeof(utf8),0,0);
            if(!n) {*error=4;break;}
            *error=add_env(l,utf8,(size_t)n-1);if(*error)break;
        }
        FreeEnvironmentStringsW(block);if(*error)goto fail;
    }
    *error=pack(l,args,an,env,en);if(*error)goto fail;
    uint32_t at=0;*error=quoted(command,&at,path);if(*error)goto fail;
    for(uint32_t i=1;l->argv[i];i++) {
        wchar_t wide[1025];if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,l->argv[i],-1,wide,1025)) {*error=3;goto fail;}
        if(at>=32766) {*error=4;goto fail;}command[at++]=L' ';
        *error=quoted(command,&at,wide);if(*error)goto fail;
    }
    wchar_t *entries[256];uint32_t used=0;
    for(uint32_t i=0;i<l->env_count;i++) {
        int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,l->envp[i],-1,environment+used,32767-used);
        if(!n) {*error=4;goto fail;}
        entries[i]=environment+used;used+=(uint32_t)n;
    }
    qsort(entries,l->env_count,sizeof(entries[0]),env_compare);
    /* Sorting pointers is insufficient: CreateProcess consumes a flat block. */
    wchar_t *sorted=calloc(32768,sizeof(wchar_t));if(!sorted) {*error=5;goto fail;}
    used=0;for(uint32_t i=0;i<l->env_count;i++) {size_t n=wcslen(entries[i])+1;memcpy(sorted+used,entries[i],n*sizeof(wchar_t));used+=(uint32_t)n;}
    STARTUPINFOW si={0};si.cb=sizeof(si);PROCESS_INFORMATION pi={0};
    BOOL ok=CreateProcessW(path,command,0,0,FALSE,CREATE_UNICODE_ENVIRONMENT,sorted,0,&si,&pi);
    DWORD e=ok?0:GetLastError();free(sorted);
    if(!ok) {*error=error_code(e);goto fail;}
    child->process=pi.hProcess;child->thread=pi.hThread;child->owner=GetCurrentThreadId();
    free(command);free(environment);free(l);return child;
fail:
    free(command);free(environment);free(l);free(child);release_slot();return 0;
}
uint32_t liza_rt_process_poll(void *handle,uint32_t block,uint32_t *kind,uint32_t *code) {
    Child *c=handle;*kind=0;*code=0;if(!c)return 3;
    if(c->owner!=GetCurrentThreadId())return 8;
    if(!c->kind) {
        DWORD result=WaitForSingleObject(c->process,block?INFINITE:0);
        if(result==WAIT_TIMEOUT)return 0;
        if(result!=WAIT_OBJECT_0)return error_code(GetLastError());
        DWORD exit_code;if(!GetExitCodeProcess(c->process,&exit_code))return error_code(GetLastError());
        c->kind=1;c->code=exit_code; /* 259 is a legal exit code once signalled. */
    }
    *kind=c->kind;*code=c->code;return 0;
}
uint32_t liza_rt_process_op(void *handle,uint32_t op) {
    Child *c=handle;if(!c)return 3;if(c->owner!=GetCurrentThreadId())return 8;
    if(op!=1&&op!=2)return 3;
    uint32_t kind,code,error=liza_rt_process_poll(c,0,&kind,&code);if(error||kind)return error;
    if(op==1)return 10; /* No portable, process-local analogue of SIGTERM. */
    if(TerminateProcess(c->process,137))return 0;
    return error_code(GetLastError());
}
uint32_t liza_rt_process_close(void *handle) {
    Child *c=handle;if(!c)return 3;if(c->owner!=GetCurrentThreadId())return 8;
    if(!c->kind)return 7;
    if(c->thread) {if(!CloseHandle(c->thread))return error_code(GetLastError());c->thread=0;}
    if(!CloseHandle(c->process))return error_code(GetLastError());
    free(c);release_slot();return 0;
}
