/* Connected UDP rotation must neither reuse queued datagrams nor disturb TCP. */
#include "../../liza/runtime/reactor_common.h"
#include <stdio.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"failed %s line %d\n",#x,__LINE__);return 2;}} while(0)
int main(void) {
    const uint32_t loop=0x7f000001u;uint64_t first,second,alien,listener,peer;
    CHECK(!liza_rt_net_udp_bind(loop,0,&first));CHECK(!liza_rt_net_udp_bind(loop,0,&second));CHECK(!liza_rt_net_udp_bind(loop,0,&alien));
    uint16_t p1=(uint16_t)liza_rt_net_port(first),p2=(uint16_t)liza_rt_net_port(second);
    CHECK(!liza_rt_net_listen(0,&listener));
    reactor *r=NULL;CHECK(!liza_rt_reactor_udp_create(0,0,1,&r));
    uint64_t id[3];CHECK(!liza_rt_reactor_connect_at(r,loop,(uint16_t)liza_rt_net_port(listener),id));
    CHECK(!liza_rt_net_accept(listener,&peer));
    uint64_t finished=0;
    for(int i=0;i<1000&&!finished;i++){CHECK(!(liza_rt_reactor_poll(r,2)>>32));finished=liza_rt_reactor_finish_connect(r,id[0],id[1],id[2]);CHECK(!(finished>>32));}
    CHECK(finished==1);
    CHECK(!liza_rt_reactor_udp_replace_connected(r,loop,p1));
    uint16_t local1=(uint16_t)liza_rt_reactor_udp_port(r);CHECK(local1);
    struct sockaddr_in address;
#ifdef _WIN32
    int length=sizeof(address);
#else
    socklen_t length=sizeof(address);
#endif
    CHECK(!getpeername((net_socket)r->udp,(struct sockaddr*)&address,&length));CHECK(ntohs(address.sin_port)==p1);
    CHECK(liza_rt_reactor_udp_send(r,(const uint8_t*)"x",1,0,1,loop,p2)==net_failure(6));
    CHECK(liza_rt_reactor_udp_send(r,(const uint8_t*)"x",1,0,1,loop,p1)==1);
    uint8_t buffer[64];uint64_t meta=0;CHECK(!liza_rt_net_udp_receive(first,buffer,sizeof(buffer),&meta));CHECK((meta&65535)==1&&buffer[0]=='x');
    CHECK(liza_rt_net_udp_send(alien,(const uint8_t*)"bad",3,0,3,loop,local1)==3);
    CHECK(liza_rt_net_udp_send(first,(const uint8_t*)"good",4,0,4,loop,local1)==4);
    uint32_t error=4;
    for(int i=0;i<1000&&error==4;i++){CHECK(!(liza_rt_reactor_poll(r,2)>>32));error=liza_rt_reactor_udp_receive(r,buffer,sizeof(buffer),&meta);}
    CHECK(!error&&(meta&65535)==4&&!memcmp(buffer,"good",4));
    CHECK(liza_rt_net_udp_send(first,(const uint8_t*)"queued",6,0,6,loop,local1)==6);
    CHECK(!liza_rt_reactor_udp_replace_connected(r,loop,p2));
    uint16_t local2=(uint16_t)liza_rt_reactor_udp_port(r);CHECK(local2&&local2!=local1);
    CHECK(liza_rt_reactor_udp_receive(r,buffer,sizeof(buffer),&meta)==4);
    CHECK(liza_rt_reactor_udp_replace_connected(r,0,p1)==net_failure(6));CHECK(liza_rt_reactor_udp_port(r)==local2);
    CHECK(liza_rt_reactor_udp_send(r,(const uint8_t*)"y",1,0,1,loop,p2)==1);
    CHECK(!liza_rt_net_udp_receive(second,buffer,sizeof(buffer),&meta));CHECK(buffer[0]=='y');
    CHECK(!liza_rt_reactor_udp_close_endpoint(r));CHECK(!liza_rt_reactor_udp_close_endpoint(r));CHECK(liza_rt_reactor_udp_port(r)==net_failure(6));
    CHECK(liza_rt_reactor_write(r,id[0],id[1],id[2],(const uint8_t*)"tcp",3,0,3)==3);
    CHECK(liza_rt_net_read(peer,buffer,3)==3&&!memcmp(buffer,"tcp",3));
    CHECK(!liza_rt_reactor_udp_replace_connected(r,loop,p1));
    CHECK(!liza_rt_reactor_close(r));CHECK(!liza_rt_net_close(peer));CHECK(!liza_rt_net_close(listener));
    CHECK(!liza_rt_net_close(first));CHECK(!liza_rt_net_close(second));CHECK(!liza_rt_net_close(alien));
    puts("connected UDP rotation, peer filtering, stale-queue cleanup and TCP isolation passed");return 0;
}
