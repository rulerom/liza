#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
#include "process_common.h"
extern char **environ;
typedef struct {pid_t pid;pthread_t owner;uint32_t kind,code;} Child;
static uint32_t error_code(int e) {
    if(e==ENOENT||e==ENOTDIR)return 1;
    if(e==EACCES||e==EPERM)return 2;
    if(e==EINVAL||e==ENOEXEC)return 3;
    if(e==E2BIG||e==ENAMETOOLONG)return 4;
    if(e==ENOMEM)return 5;
    if(e==EAGAIN)return 6;
    if(e==EINTR)return 9;
    return 11;
}
void *liza_rt_process_spawn(const char *path,uint32_t inherit,const uint8_t *args,uint32_t an,const uint8_t *env,uint32_t en,uint32_t *error) {
    *error=0;
    if(!path||path[0]!='/') {*error=3;return 0;}
    if(strnlen(path,4097)>4096) {*error=4;return 0;}
    if(!reserve_slot()) {*error=6;return 0;}
    Child *child=calloc(1,sizeof(*child));Launch *l=calloc(1,sizeof(*l));
    if(!child||!l) {*error=5;goto fail;}
    if(inherit)for(char **p=environ;*p;p++) {
        size_t n=strnlen(*p,32769);if(n>32768) {*error=4;goto fail;}
        *error=add_env(l,*p,n);if(*error)goto fail;
    }
    *error=pack(l,args,an,env,en);if(*error)goto fail;
    l->argv[0]=(char*)path;
    posix_spawn_file_actions_t actions;posix_spawnattr_t attr;
    int e=posix_spawn_file_actions_init(&actions);
    if(e) {*error=error_code(e);goto fail;}
    e=posix_spawnattr_init(&attr);
    if(e) {posix_spawn_file_actions_destroy(&actions);*error=error_code(e);goto fail;}
#ifdef __APPLE__
    e=posix_spawnattr_setflags(&attr,POSIX_SPAWN_CLOEXEC_DEFAULT);
    for(int fd=0;fd<3&&!e;fd++)if(fcntl(fd,F_GETFD)!=-1)e=posix_spawn_file_actions_addinherit_np(&actions,fd);
#else
    e=posix_spawn_file_actions_addclosefrom_np(&actions,3);
#endif
    if(!e)e=posix_spawn(&child->pid,path,&actions,&attr,l->argv,l->envp);
    posix_spawnattr_destroy(&attr);posix_spawn_file_actions_destroy(&actions);
    if(e) {*error=error_code(e);goto fail;}
    child->owner=pthread_self();free(l);return child;
fail:
    free(l);free(child);release_slot();return 0;
}
uint32_t liza_rt_process_poll(void *handle,uint32_t block,uint32_t *kind,uint32_t *code) {
    Child *c=handle;*kind=0;*code=0;
    if(!c)return 3;
    if(!pthread_equal(c->owner,pthread_self()))return 8;
    if(!c->kind) {
        int status=0;pid_t result=waitpid(c->pid,&status,block?0:WNOHANG);
        if(result<0)return error_code(errno);
        if(result==0)return 0;
        if(WIFEXITED(status)) {c->kind=1;c->code=(uint32_t)WEXITSTATUS(status);}
        else if(WIFSIGNALED(status)) {c->kind=2;c->code=(uint32_t)WTERMSIG(status);}
        else return 11;
    }
    *kind=c->kind;*code=c->code;return 0;
}
uint32_t liza_rt_process_op(void *handle,uint32_t op) {
    Child *c=handle;
    if(!c)return 3;
    if(!pthread_equal(c->owner,pthread_self()))return 8;
    if(op!=1&&op!=2)return 3;
    uint32_t kind,code,error=liza_rt_process_poll(c,0,&kind,&code);
    if(error)return error;
    if(kind)return 0; /* Already reaped: never signal a recycled PID. */
    if(kill(c->pid,op==1?SIGTERM:SIGKILL)==0||errno==ESRCH)return 0;
    return error_code(errno);
}
uint32_t liza_rt_process_close(void *handle) {
    Child *c=handle;if(!c)return 3;
    if(!pthread_equal(c->owner,pthread_self()))return 8;
    if(!c->kind)return 7; /* Only wait/try_wait can establish the receipt. */
    free(c);release_slot();return 0;
}
