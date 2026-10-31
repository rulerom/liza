/* Scoped, role-bound scalar channel group. No endpoint pointer reaches Liza. */
#include "scoped_channel_core.h"
#include <stdint.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
typedef HANDLE group_thread;
typedef CRITICAL_SECTION group_mutex;
typedef CONDITION_VARIABLE group_cond;
#else
#include <pthread.h>
typedef pthread_t group_thread;
typedef pthread_mutex_t group_mutex;
typedef pthread_cond_t group_cond;
#endif
typedef uint32_t (*group_fn)(void);
typedef struct {group_mutex lock;group_cond ready;int state;channel *c;} group;
typedef struct {group *g;group_fn fn;uint32_t role,result,discarded;} group_task;
static _Thread_local group_task *channel_current;
uint32_t liza_rt_channels_send(uint32_t value) {
    group_task *task=channel_current;
    if(!task || task->role!=0)abort();
    liza_scoped_status result=liza_scoped_send(task->g->c,value);
    if(result==CH_OK)return 0;
    if(result==CH_FULL)return 1;
    if(result==CH_CLOSED)return 2;
    abort();
}
uint64_t liza_rt_channels_receive(void) {
    group_task *task=channel_current;
    if(!task || task->role!=1)abort();
    uint32_t value=0;liza_scoped_status result=liza_scoped_receive(task->g->c,&value);
    if(result==CH_OK)return value;
    if(result==CH_EMPTY)return (uint64_t)1<<32;
    if(result==CH_CLOSED)return (uint64_t)2<<32;
    abort();
}
#ifdef _WIN32
static DWORD WINAPI group_entry(LPVOID value) {
#else
static void *group_entry(void *value) {
#endif
    group_task *task=value;group *g=task->g;
#ifdef _WIN32
    EnterCriticalSection(&g->lock);
    while(!g->state)if(!SleepConditionVariableCS(&g->ready,&g->lock,INFINITE))abort();
    int run=g->state==1;LeaveCriticalSection(&g->lock);
#else
    if(pthread_mutex_lock(&g->lock))abort();
    while(!g->state)if(pthread_cond_wait(&g->ready,&g->lock))abort();
    int run=g->state==1;if(pthread_mutex_unlock(&g->lock))abort();
#endif
    if(run){channel_current=task;task->result=task->fn();channel_current=NULL;
        if(task->role==0)liza_scoped_close_sender(g->c);else task->discarded=(uint32_t)liza_scoped_close_receiver(g->c);}
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}
/* Bits 63..56: status (0 success, 1 invalid budget, 2 start failure).
   Bits 55..32: discarded count. Low 32: XOR of role results. */
uint64_t liza_rt_channels_run(uint32_t n,uint64_t budget,group_fn producer,group_fn consumer) {
    group g={0};size_t bytes=0;
    if(budget>SIZE_MAX)return (uint64_t)1<<56;
    liza_scoped_status created=liza_scoped_create(n,(size_t)budget,&g.c,&bytes);
    if(created!=CH_OK)return (uint64_t)(created==CH_INVALID?1:2)<<56;
#ifdef _WIN32
    if(!InitializeCriticalSectionEx(&g.lock,0,0)){liza_scoped_destroy(g.c);return (uint64_t)2<<56;}
    InitializeConditionVariable(&g.ready);
#else
    if(pthread_mutex_init(&g.lock,NULL)){liza_scoped_destroy(g.c);return (uint64_t)2<<56;}
    if(pthread_cond_init(&g.ready,NULL)){pthread_mutex_destroy(&g.lock);liza_scoped_destroy(g.c);return (uint64_t)2<<56;}
#endif
    group_task tasks[2]={{&g,producer,0,0,0},{&g,consumer,1,0,0}};group_thread threads[2];unsigned started=0;
    for(unsigned i=0;i<2;i++) {
#ifdef CHANNEL_TEST_FAIL_AT
        if(i==CHANNEL_TEST_FAIL_AT)break;
#endif
#ifdef _WIN32
        threads[i]=CreateThread(NULL,0,group_entry,&tasks[i],0,NULL);if(!threads[i])break;
#else
        if(pthread_create(&threads[i],NULL,group_entry,&tasks[i]))break;
#endif
        ++started;
    }
#ifdef _WIN32
    EnterCriticalSection(&g.lock);g.state=started==2?1:2;WakeAllConditionVariable(&g.ready);LeaveCriticalSection(&g.lock);
    for(unsigned i=0;i<started;i++){if(WaitForSingleObject(threads[i],INFINITE)!=WAIT_OBJECT_0)abort();CloseHandle(threads[i]);}
    DeleteCriticalSection(&g.lock);
#else
    if(pthread_mutex_lock(&g.lock))abort();g.state=started==2?1:2;
    if(pthread_cond_broadcast(&g.ready)||pthread_mutex_unlock(&g.lock))abort();
    for(unsigned i=0;i<started;i++)if(pthread_join(threads[i],NULL))abort();
    pthread_cond_destroy(&g.ready);pthread_mutex_destroy(&g.lock);
#endif
    liza_scoped_destroy(g.c);
    if(started!=2)return (uint64_t)2<<56;
    return ((uint64_t)tasks[1].discarded<<32) | (tasks[0].result ^ tasks[1].result);
}
