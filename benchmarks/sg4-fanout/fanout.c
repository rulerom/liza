/* Same callbacks, SG3 ABI, bounded table and Region allocation as Liza. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "config.h"
#include "packet.h"
uint32_t liza_rt_group_send(uint32_t);
uint32_t liza_rt_group_udp_bind(uint32_t,uint16_t);
uint64_t liza_rt_group_next(void);
uint32_t liza_rt_group_udp_receive(uint8_t *,uint32_t,uint64_t *);
uint64_t liza_rt_group_udp_send(const uint8_t *,uint32_t,uint32_t,uint32_t,uint32_t,uint16_t);
uint32_t liza_rt_group_run(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t(*)(void),uint32_t(*)(void),uint32_t*,uint32_t*,uint32_t*,uint32_t*);
void *liza_rt_region_create(uint64_t,uint32_t *);
void *liza_rt_region_alloc(void *,uint64_t,uint64_t,uint32_t,uint32_t *);
void liza_rt_region_close(void *);
static uint32_t producer(void){return liza_rt_group_send(42)==1?0:1;}
static uint32_t consumer(void){
 struct receiver {uint32_t ssrc;uint8_t active,known;uint32_t ipv4;uint16_t port;};
 struct receiver table[64]={0};
 for(unsigned i=0;i<RECEIVERS;i++)table[i]=(struct receiver){i,1,1,0x7f000001,ports[i]};
 if(liza_rt_group_udp_bind(0x7f000001,0))return 0x80000001;
 uint32_t error=0,accepted=0,status=0;int stopping=0;
 void *region=liza_rt_region_create(4096,&error);if(error)return 0x80000002;
 uint8_t *buffer=liza_rt_region_alloc(region,1,1,2048,&error);
 if(error)status=3;else{
  memset(buffer,0,2048);
  while(!status&&!stopping){
   uint64_t event=liza_rt_group_next();uint32_t kind=(uint32_t)(event>>32);
   if(kind==0){if((uint32_t)event!=42)status=5;}
   else if(kind==2){}
   else if(kind==3)stopping=1;
   else if(kind==4)status=6;
   else if(kind!=1)status=4;
   else{
    uint64_t meta;uint32_t e=liza_rt_group_udp_receive(buffer,2048,&meta);
    if(e){if(e!=3&&e!=4&&e!=8)status=7;}
    else{
     uint32_t length=(uint32_t)(meta&65535);struct rtp_header header;
     if(parse_rtp(buffer,length,&header)&&header.ssrc==0x10203040){
      accepted++;
      for(unsigned i=0;i<64;i++)if(table[i].active&&table[i].known)
       (void)liza_rt_group_udp_send(buffer,length,0,length,table[i].ipv4,table[i].port);
     }
    }
   }
  }
 }
 liza_rt_region_close(region);
 return status?0x80000000+status:accepted;
}
int main(void){uint32_t p,c,f,control;
 uint32_t e=liza_rt_group_run(65536,65536,1048576,1048576,65536,2,2,5000,2000,producer,consumer,&p,&c,&f,&control);
 return e?1:(p||c>=0x80000000?2:0);
}
