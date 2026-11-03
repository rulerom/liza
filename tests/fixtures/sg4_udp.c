#define _POSIX_C_SOURCE 200809L
#define liza_rt_reactor_poll_sources sg4_poll
#include "sg3_common.h"
#undef liza_rt_reactor_poll_sources
#include <stdio.h>
atomic_int sg2_test_handback_gate,sg2_test_stale_receipt,sg2_test_supervisor_gate;
static atomic_int entered,returned;
static unsigned joins,closed,handback,destroyed;
static int mode;
static uint16_t port;
uint32_t liza_rt_net_udp_bind(uint32_t,uint16_t,uint64_t *);
uint32_t liza_rt_net_close(uint64_t);
uint64_t liza_rt_net_port(uint64_t);
uint64_t liza_rt_net_udp_send(uint64_t,const uint8_t *,uint32_t,uint32_t,uint32_t,uint32_t,uint16_t);
void sg3_test_config(liza_sg2_config *c){if(mode==1)c->data_fault=1;}
void sg2_test_event(const char *name,uint64_t generation,unsigned role){
    (void)generation;
    if(!strcmp(name,"reactor_close"))closed=1;
    if(!strcmp(name,"join")){if(role==1&&!closed)_Exit(90);joins++;}
    if(!strcmp(name,"handback"))handback=1;
    if(!strcmp(name,"destroy")){if(joins!=3||!handback||!closed)_Exit(91);destroyed=1;}
}
uint64_t liza_rt_reactor_poll_sources(reactor *,int32_t,sg3_source *,uint32_t);
uint64_t sg4_poll(reactor *r,int32_t timeout,sg3_source *sources,uint32_t count){
    if(timeout!=-1||count!=2)_Exit(92);
    atomic_store(&entered,1);
    uint64_t result=liza_rt_reactor_poll_sources(r,timeout,sources,count);
    atomic_store(&returned,1);return result;
}
static uint32_t producer(void){
    while(!atomic_load(&entered))sg_pause();
    if(mode==1){
        if(liza_rt_group_send(42)!=SG2_PUBLISHED_FAULT)return 1;
    }else if(mode==2||mode==3){
        uint64_t s;if(liza_rt_net_udp_bind(0x7f000001u,0,&s))return 2;
        uint8_t packet[8]={1,2,3,4,5,6,7,8};
        if(mode==3){
            if(liza_rt_group_send(42)!=SG2_PUBLISHED)return 22;
            uint64_t start=sg_now();
            while(sg_now()-start<250){
                if(liza_rt_net_udp_send(s,packet,8,0,4,0x7f000001u,port)>>32)return 23;
            }
            liza_rt_group_stop();
            return (int)liza_rt_net_close(s);
        }
        if(liza_rt_net_udp_send(s,packet,8,0,8,0x7f000001u,port)>>32)return 3;
        if(liza_rt_net_udp_send(s,packet,8,0,0,0x7f000001u,port)>>32)return 4;
        if(liza_rt_net_udp_send(s,packet,8,0,4,0x7f000001u,port)>>32)return 5;
        if(liza_rt_net_close(s))return 6;
        if(liza_rt_group_send(42)!=SG2_PUBLISHED)return 7;
        return 0;
    }else{
        uint64_t start=sg_now();while(sg_now()-start<750)sg_pause();
        if(atomic_load(&returned))return 8;
    }
    liza_rt_group_stop();return 0;
}
static uint32_t consumer(void){
    uint64_t occupied;
    if(liza_rt_net_udp_bind(0x7f000001u,0,&occupied))return 25;
    uint64_t occupied_port=liza_rt_net_port(occupied);
    if(occupied_port>>32)return 26;
    if(liza_rt_group_udp_bind(0x7f000001u,(uint16_t)occupied_port)!=1)return 27;
    if(liza_rt_net_close(occupied))return 28;
    if(liza_rt_group_udp_bind(0x7f000001u,0))return 10;
    uint64_t p=liza_rt_group_udp_port();if(p>>32)return 11;port=(uint16_t)p;
    uint8_t data[4];uint64_t meta;
    if(liza_rt_group_udp_receive(data,4,&meta)!=4)return 12; /* WouldBlock */
    if(liza_rt_group_udp_bind(0x7f000001u,0)!=6)return 13;
    if(liza_rt_group_listen(0)!=6)return 14;
    unsigned packets=0,command=0;
    for(;;){
        uint64_t event=liza_rt_group_next();uint32_t kind=(uint32_t)(event>>32);
        if(kind==0){if((uint32_t)event!=42)return 15;command++;}
        else if(kind==1){
            uint32_t e=liza_rt_group_udp_receive(data,4,&meta);
            if(mode==3){if(e||(meta&65535)!=4)return 24;}
            else if(packets==0){if(e!=8)return 16;}
            else if(packets==1){if(e||(meta&65535)!=0)return 17;}
            else {if(e||(meta&65535)!=4||data[0]!=1||data[3]!=4)return 18;}
            packets++;
        }else if(kind==3){return (mode==1||mode==3)&&command!=1?19:0;}
        else if(kind==4){liza_rt_group_stop();}
        else if(kind!=2)return 20;
        if(mode==2&&packets==3&&command==1){liza_rt_group_stop();return 0;}
    }
}
int main(int argc,char **argv){
    mode=argc>1?atoi(argv[1]):0;
    uint32_t p,c,f,control;
    uint32_t result=liza_rt_group_run(65536,65536,1048576,1048576,65536,2,2,5000,2000,producer,consumer,&p,&c,&f,&control);
    if(result!=(mode==1?SG2_FAULTED:SG2_OK)||p||c||!destroyed||control){fprintf(stderr,"result=%u p=%u c=%u fault=%u destroy=%u\n",result,p,c,f,destroyed);return 1;}
    /* Same endpoint can be rebound only after owner close + native joins. */
    uint64_t s;if(liza_rt_net_udp_bind(0x7f000001u,port,&s))return 2;
    return (int)liza_rt_net_close(s);
}
