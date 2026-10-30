/* Scoped scalar workers. No user resource or borrow crosses the boundary. */
#include <stdint.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
typedef HANDLE liza_thread;
typedef CRITICAL_SECTION liza_mutex;
typedef CONDITION_VARIABLE liza_cond;
#else
#include <pthread.h>
typedef pthread_t liza_thread;
typedef pthread_mutex_t liza_mutex;
typedef pthread_cond_t liza_cond;
#endif

enum { LIZA_MAX_WORKERS = 8 };
typedef uint32_t (*liza_worker_fn)(uint32_t);
typedef struct { liza_mutex mutex; liza_cond cond; int state; } liza_gate;
typedef struct { liza_gate *gate; liza_worker_fn fn; uint32_t id, result; } liza_task;
#ifdef _WIN32
static DWORD WINAPI liza_thread_entry(LPVOID arg) {
#else
static void *liza_thread_entry(void *arg) {
#endif
    liza_task *task = arg;
    liza_gate *gate = task->gate;
#ifdef _WIN32
    EnterCriticalSection(&gate->mutex);
    while (!gate->state) if (!SleepConditionVariableCS(&gate->cond, &gate->mutex, INFINITE)) abort();
    int run = gate->state == 1;
    LeaveCriticalSection(&gate->mutex);
#else
    if (pthread_mutex_lock(&gate->mutex)) abort();
    while (!gate->state) if (pthread_cond_wait(&gate->cond, &gate->mutex)) abort();
    int run = gate->state == 1;
    if (pthread_mutex_unlock(&gate->mutex)) abort();
#endif
    if (run) task->result = task->fn(task->id);
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}
/* Result: status in high 32 bits, XOR of results in low 32 bits.
   1 = invalid count, 2 = thread or gate creation failure. */
uint64_t liza_rt_workers_run(uint32_t count, liza_worker_fn fn) {
    if (!count || count > LIZA_MAX_WORKERS) return (uint64_t)1 << 32;
    liza_gate gate = {0}; liza_thread threads[LIZA_MAX_WORKERS];
    liza_task tasks[LIZA_MAX_WORKERS] = {{0}}; uint32_t started = 0;
#ifdef _WIN32
    if (!InitializeCriticalSectionEx(&gate.mutex, 0, 0)) return (uint64_t)2 << 32;
    InitializeConditionVariable(&gate.cond);
#else
    if (pthread_mutex_init(&gate.mutex, NULL)) return (uint64_t)2 << 32;
    if (pthread_cond_init(&gate.cond, NULL)) { pthread_mutex_destroy(&gate.mutex); return (uint64_t)2 << 32; }
#endif
    for (uint32_t i = 0; i < count; ++i) {
        tasks[i].gate = &gate; tasks[i].fn = fn; tasks[i].id = i;
#ifdef LIZA_WORKERS_TEST_FAIL_AT
        if (i == LIZA_WORKERS_TEST_FAIL_AT) break;
#endif
#ifdef _WIN32
        threads[i] = CreateThread(NULL, 0, liza_thread_entry, &tasks[i], 0, NULL);
        if (!threads[i]) break;
#else
        if (pthread_create(&threads[i], NULL, liza_thread_entry, &tasks[i])) break;
#endif
        ++started;
    }
#ifdef _WIN32
    EnterCriticalSection(&gate.mutex); gate.state = started == count ? 1 : 2;
    WakeAllConditionVariable(&gate.cond); LeaveCriticalSection(&gate.mutex);
    for (uint32_t i = 0; i < started; ++i) {
        if (WaitForSingleObject(threads[i], INFINITE) != WAIT_OBJECT_0) abort();
        CloseHandle(threads[i]);
    }
    DeleteCriticalSection(&gate.mutex);
#else
    if (pthread_mutex_lock(&gate.mutex)) abort();
    gate.state = started == count ? 1 : 2;
    if (pthread_cond_broadcast(&gate.cond) || pthread_mutex_unlock(&gate.mutex)) abort();
    for (uint32_t i = 0; i < started; ++i) if (pthread_join(threads[i], NULL)) abort();
    pthread_cond_destroy(&gate.cond); pthread_mutex_destroy(&gate.mutex);
#endif
    if (started != count) return (uint64_t)2 << 32;
    uint32_t result = 0;
    for (uint32_t i = 0; i < count; ++i) result ^= tasks[i].result;
    return result;
}
