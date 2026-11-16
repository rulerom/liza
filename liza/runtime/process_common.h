#ifndef LIZA_PROCESS_COMMON_H
#define LIZA_PROCESS_COMMON_H
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
/* No raw environment or command contents enter error reporting. */
static _Atomic uint32_t process_slots;
static int reserve_slot(void) {
    uint32_t n=atomic_load(&process_slots);
    while(n<8) {if(atomic_compare_exchange_weak(&process_slots,&n,n+1))return 1;}
    return 0;
}
static void release_slot(void) {atomic_fetch_sub(&process_slots,1);}
typedef struct {
    char args[8192],env[32768];
    char *argv[34],*envp[257];
    uint32_t env_used,env_count;
} Launch;
static size_t key_length(const char *s) {
#ifdef _WIN32
    /* Preserve Windows hidden drive-current-directory keys such as =C:. */
    if(s[0]=='=')return 1+strcspn(s+1,"=");
#endif
    return strcspn(s,"=");
}
static int same_key(const char *a,const char *b) {
    size_t an=key_length(a),bn=key_length(b);
    if(an!=bn)return 0;
    for(size_t i=0;i<an;i++) {
        unsigned char x=a[i],y=b[i];
#ifdef _WIN32
        if(x>='a'&&x<='z')x-=32;
        if(y>='a'&&y<='z')y-=32;
#endif
        if(x!=y)return 0;
    }
    return 1;
}
static uint32_t add_env(Launch *l,const char *s,size_t n) {
    if(n+1>sizeof(l->env)-l->env_used)return 4;
    uint32_t slot=l->env_count;
    for(uint32_t i=0;i<l->env_count;i++)if(same_key(s,l->envp[i])) {slot=i;break;}
    if(slot==l->env_count) {if(l->env_count==256)return 4;l->env_count++;}
    memcpy(l->env+l->env_used,s,n);l->env[l->env_used+n]=0;
    l->envp[slot]=l->env+l->env_used;l->env_used+=(uint32_t)n+1;
    l->envp[l->env_count]=0;return 0;
}
static uint32_t pack(Launch *l,const uint8_t *args,uint32_t an,const uint8_t *env,uint32_t en) {
    if(an>8192||en>8192)return 4;
    if((an&&!args)||(en&&!env))return 3;
    if(an)memcpy(l->args,args,an);
    uint32_t i=0,count=1;
    while(i<an) {
        if(count==33)return 4;
        uint32_t start=i;while(i<an&&l->args[i])i++;
        if(i==an)return 3;
        if(i-start>1024)return 4;
        l->argv[count++]=l->args+start;i++;
    }
    l->argv[count]=0;i=0;count=0;
    while(i<en) {
        if(++count>32)return 4;
        uint32_t start=i;while(i<en&&env[i])i++;
        if(i==en)return 3;
        const char *s=(const char*)env+start;size_t n=i-start,k=strcspn(s,"=");
        if(k==0||k>128||k==n||n-k-1>4096)return 3;
        for(size_t j=0;j<k;j++)if((unsigned char)s[j]<33||(unsigned char)s[j]>126)return 3;
        /* Duplicate override keys are rejected; inherited keys may be replaced. */
        uint32_t p=0;while(p<start) {const char *old=(const char*)env+p;if(same_key(s,old))return 3;p+=(uint32_t)strlen(old)+1;}
        uint32_t error=add_env(l,s,n);if(error)return error;i++;
    }
    return 0;
}
#endif
