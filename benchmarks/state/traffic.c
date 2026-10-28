#include <stdint.h>
#include <stdio.h>
static uintptr_t base;
static uint64_t size, active, calls[4], spans[2], offsets[2][256];
void s2_begin(const void *p,uint64_t n){base=(uintptr_t)p;size=n;active=1;}
void s2_end(void){active=0;}
void s2_record(unsigned k,const void *p,uint64_t n){
 if(!active)return;
 if(k>=2){calls[k]++;return;}
 uintptr_t a=(uintptr_t)p;
 if(a<base || a-base>=size || n>size-(a-base))return;
 calls[k]++;spans[k]+=n;offsets[k][a-base]++;
}
__attribute__((destructor)) static void report(void){
 fprintf(stderr,"{\"state_loads\":%llu,\"state_stores\":%llu,\"conditional_transfers\":%llu,\"overflow_intrinsics\":%llu,\"load_spans\":%llu,\"store_spans\":%llu,\"offsets\":[",calls[0],calls[1],calls[2],calls[3],spans[0],spans[1]);
 int first=1;for(unsigned k=0;k<2;k++)for(unsigned i=0;i<256;i++)if(offsets[k][i]){fprintf(stderr,"%s[%u,%u,%llu]",first?"":",",k,i,offsets[k][i]);first=0;}
 fprintf(stderr,"]}\n");
}
