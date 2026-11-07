/* Experimental scoped Liza worker launcher, not a public runtime API. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
typedef HANDLE thread_t;
typedef CRITICAL_SECTION mutex_t;
typedef CONDITION_VARIABLE condition_t;
#else
#include <pthread.h>
typedef pthread_t thread_t;
typedef pthread_mutex_t mutex_t;
typedef pthread_cond_t condition_t;
#endif
extern uint32_t liza_mt_worker(uint32_t id);
enum { MAX_WORKERS=8 };
typedef struct { mutex_t lock; condition_t cond; int state; } gate;
typedef struct { gate *g; uint32_t id, result; int ran; } task;
#ifdef _WIN32
static DWORD WINAPI entry(LPVOID value) {
#else
static void *entry(void *value) {
#endif
    task *t=(task *)value;gate *g=t->g;
#ifdef _WIN32
    EnterCriticalSection(&g->lock);
    while(!g->state) SleepConditionVariableCS(&g->cond,&g->lock,INFINITE);
    int run=g->state==1;LeaveCriticalSection(&g->lock);
#else
    pthread_mutex_lock(&g->lock);
    while(!g->state) pthread_cond_wait(&g->cond,&g->lock);
    int run=g->state==1;pthread_mutex_unlock(&g->lock);
#endif
    if(run){t->result=liza_mt_worker(t->id);t->ran=1;}
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    char *end;long count=strtol(argv[1],&end,10);if(end==argv[1]||*end||count<1||count>MAX_WORKERS)return 2;
    long fail=strtol(argv[2],&end,10);if(end==argv[2]||*end||fail< -1||fail>=count)return 2;
    gate g={0};thread_t threads[MAX_WORKERS];task tasks[MAX_WORKERS]={0};int started=0;
#ifdef _WIN32
    InitializeCriticalSection(&g.lock);InitializeConditionVariable(&g.cond);
#else
    if(pthread_mutex_init(&g.lock,NULL))return 3;
    if(pthread_cond_init(&g.cond,NULL)){pthread_mutex_destroy(&g.lock);return 3;}
#endif
    for(int i=0;i<count;i++){
        tasks[i].g=&g;tasks[i].id=(uint32_t)i;
        if(i==fail)break;
#ifdef _WIN32
        threads[i]=CreateThread(NULL,0,entry,&tasks[i],0,NULL);
        if(!threads[i])break;
#else
        if(pthread_create(&threads[i],NULL,entry,&tasks[i]))break;
#endif
        started++;
    }
#ifdef _WIN32
    EnterCriticalSection(&g.lock);g.state=started==count?1:2;WakeAllConditionVariable(&g.cond);LeaveCriticalSection(&g.lock);
    for(int i=0;i<started;i++){if(WaitForSingleObject(threads[i],INFINITE)!=WAIT_OBJECT_0)return 3;CloseHandle(threads[i]);}
    DeleteCriticalSection(&g.lock);
#else
    pthread_mutex_lock(&g.lock);g.state=started==count?1:2;pthread_cond_broadcast(&g.cond);pthread_mutex_unlock(&g.lock);
    for(int i=0;i<started;i++)if(pthread_join(threads[i],NULL))return 3;
    pthread_cond_destroy(&g.cond);pthread_mutex_destroy(&g.lock);
#endif
    int ran=0;for(int i=0;i<started;i++)ran+=tasks[i].ran;
    printf("started=%d ran=%d\n",started,ran);
    if(started!=count)return ran?4:3;
    for(int i=0;i<count;i++)if(!tasks[i].ran||tasks[i].result!=(uint32_t)(10000*(i+1)))return 4;
    return 0;
}
