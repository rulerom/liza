#include "channel.h"
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
typedef SRWLOCK ch_mutex;
static int lock_init(ch_mutex *m) {InitializeSRWLock(m);return 0;}
static void lock(ch_mutex *m) {AcquireSRWLockExclusive(m);}
static void unlock(ch_mutex *m) {ReleaseSRWLockExclusive(m);}
static void lock_destroy(ch_mutex *m) {(void)m;}
#else
#include <pthread.h>
typedef pthread_mutex_t ch_mutex;
static int lock_init(ch_mutex *m) {return pthread_mutex_init(m,NULL);}
static void lock(ch_mutex *m) {if(pthread_mutex_lock(m))abort();}
static void unlock(ch_mutex *m) {if(pthread_mutex_unlock(m))abort();}
static void lock_destroy(ch_mutex *m) {if(pthread_mutex_destroy(m))abort();}
#endif
struct channel {
    ch_mutex mutex;
    size_t capacity,head,tail,count;
    int sender_closed,receiver_closed;
    uint32_t slots[];
};
ch_status ch_create(size_t n,size_t budget,channel **out,size_t *bytes) {
    if(!out || !bytes)return CH_INVALID;
    *out=NULL;*bytes=0;
    if(!n || n>65536 || n>(SIZE_MAX-sizeof(channel))/sizeof(uint32_t))return CH_INVALID;
    size_t cost=sizeof(channel)+n*sizeof(uint32_t);
    if(cost>budget)return CH_INVALID;
#ifdef CH_TEST_FAIL_ALLOC
    channel *c=NULL;
#else
    channel *c=malloc(cost);
#endif
    if(!c)return CH_NOMEM;
    if(lock_init(&c->mutex)){free(c);return CH_NOMEM;}
    c->capacity=n;c->head=c->tail=c->count=0;c->sender_closed=c->receiver_closed=0;
    *bytes=cost;*out=c;return CH_OK;
}
ch_status ch_send(channel *c,uint32_t value) {
    lock(&c->mutex);
    if(c->sender_closed || c->receiver_closed){unlock(&c->mutex);return CH_CLOSED;}
    if(c->count==c->capacity){
#ifdef CH_TEST_BREAK_FULL
        c->slots[c->head]^=1; /* Negative control: corrupt state on Full. */
#endif
        unlock(&c->mutex);return CH_FULL;
    }
    /* Lock reserves the tail; publish only after the complete scalar copy. */
    c->slots[c->tail]=value;
    c->tail = c->tail+1==c->capacity ? 0 : c->tail+1;
    ++c->count;unlock(&c->mutex);return CH_OK;
}
ch_status ch_receive(channel *c,uint32_t *value) {
    lock(&c->mutex);
    if(c->receiver_closed){unlock(&c->mutex);return CH_CLOSED;}
    if(!c->count){ch_status status=c->sender_closed?CH_CLOSED:CH_EMPTY;unlock(&c->mutex);return status;}
    *value=c->slots[c->head];
    c->head = c->head+1==c->capacity ? 0 : c->head+1;
    --c->count;unlock(&c->mutex);return CH_OK;
}
void ch_close_sender(channel *c) {lock(&c->mutex);c->sender_closed=1;unlock(&c->mutex);}
size_t ch_close_receiver(channel *c) {
    lock(&c->mutex);size_t discarded=c->count;
    c->receiver_closed=1;c->count=0;c->head=c->tail;
    unlock(&c->mutex);return discarded;
}
void ch_destroy(channel *c) {lock_destroy(&c->mutex);free(c);}
